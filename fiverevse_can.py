import ctypes
import os
import threading
import time
import sys
import re

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def log_debug(message):
    try:
        with open("fiverevse_debug_log.txt", "a", encoding="utf-8") as f:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{ts}] {message}\n")
    except:
        pass

# Constants for USBCAN-2E-U or similar
VCI_USBCAN2 = 4
STATUS_OK = 1
STATUS_ERR = 0

BAUDRATE_MAP = {
    "10 Kbps": (0x31, 0x1C),
    "20 Kbps": (0x18, 0x1C),
    "50 Kbps": (0x09, 0x1C),
    "100 Kbps": (0x04, 0x1C),
    "125 Kbps": (0x03, 0x1C),
    "250 Kbps": (0x01, 0x1C),
    "500 Kbps": (0x00, 0x1C),
    "800 Kbps": (0x00, 0x16),
    "1000 Kbps": (0x00, 0x14)
}

class VCI_INIT_CONFIG(ctypes.Structure):
    _fields_ = [("AccCode", ctypes.c_uint32),
                ("AccMask", ctypes.c_uint32),
                ("Reserved", ctypes.c_uint32),
                ("Filter", ctypes.c_ubyte),
                ("Timing0", ctypes.c_ubyte),
                ("Timing1", ctypes.c_ubyte),
                ("Mode", ctypes.c_ubyte)]

class VCI_CAN_OBJ(ctypes.Structure):
    _fields_ = [("ID", ctypes.c_uint),
                ("TimeStamp", ctypes.c_uint),
                ("TimeFlag", ctypes.c_ubyte),
                ("SendType", ctypes.c_ubyte),
                ("RemoteFlag", ctypes.c_ubyte),
                ("ExternFlag", ctypes.c_ubyte),
                ("DataLen", ctypes.c_ubyte),
                ("Data", ctypes.c_ubyte * 8),
                ("Reserved", ctypes.c_ubyte * 3)]

class VCI_BOARD_INFO(ctypes.Structure):
    _fields_ = [("hw_Version", ctypes.c_ushort),
                ("fw_Version", ctypes.c_ushort),
                ("dr_Version", ctypes.c_ushort),
                ("in_Version", ctypes.c_ushort),
                ("irq_Num", ctypes.c_ushort),
                ("can_Num", ctypes.c_ubyte),
                ("str_Serial_Num", ctypes.c_ubyte * 20),
                ("str_hw_Type", ctypes.c_ubyte * 40),
                ("Reserved", ctypes.c_ubyte * 4)]

DEVICE_TYPES = {
    "VCI_USBCAN1 (Type 3)": 3,
    "VCI_USBCAN2 (Type 4)": 4,
    "VCI_USBCAN_2E_U (Type 21)": 21,
}

class FiverevseCANController:
    def __init__(self, dll_path='ControlCAN.dll'):
        self.lib = None
        self.dev_type = VCI_USBCAN2
        self.dev_idx = 0
        self.can_idx = 0
        self.connected = False
        self.rx_thread = None
        self.rx_running = False
        
        # Callbacks
        self.on_data_received_callback = None
        self.on_tx_log_callback = None
        self.on_all_rx_callback = None
        
        # Protocol Settings
        self.source_group = 0 # 5 bits
        self.source_subaddr = 240 # 0x0F0 in 11-bit Source Addr (common for controller)
        
        try:
            full_path = resource_path(dll_path)
            self.lib = ctypes.windll.LoadLibrary(full_path)
        except Exception as e:
            print(f"Error loading {dll_path}: {e}")

    def build_id(self, dest_addr):
        # Fiverevse V2.6: Protocol=0x60 (7 bits), Dest (11 bits), Source (11 bits)
        # Source = (Group << 6) | Subaddr
        source_addr = (self.source_group << 6) | (self.source_subaddr & 0x3F)
        if self.source_subaddr == 240: # Custom 0x0F0 logic from PDF reference
            source_addr = 0x0F0 
            
        msg_id = (0x60 << 22) | (dest_addr << 11) | source_addr
        return msg_id

    def scan_devices(self, dev_type=4):
        if not self.lib: return []
        devices = []
        for idx in range(4):
            try:
                if self.lib.VCI_OpenDevice(dev_type, idx, 0) == STATUS_OK:
                    info = VCI_BOARD_INFO()
                    self.lib.VCI_ReadBoardInfo(dev_type, idx, ctypes.byref(info))
                    serial = bytes(info.str_Serial_Num).decode('ascii', errors='ignore').strip('\x00')
                    devices.append({'index': idx, 'serial': serial, 'display': f"Device {idx}: SN={serial}"})
                    self.lib.VCI_CloseDevice(dev_type, idx)
            except: pass
        return devices

    def connect(self, dev_type, dev_idx, can_idx, baud_rate):
        self.dev_type = dev_type
        self.dev_idx = dev_idx
        self.can_idx = can_idx
        try:
            if self.lib.VCI_OpenDevice(self.dev_type, self.dev_idx, 0) != STATUS_OK:
                return False, "Failed to open device"
            t0, t1 = BAUDRATE_MAP.get(baud_rate, (0x03, 0x1C)) # Default 125k
            config = VCI_INIT_CONFIG(0x00000000, 0xFFFFFFFF, 0, 1, t0, t1, 0)
            self.lib.VCI_InitCAN(self.dev_type, self.dev_idx, self.can_idx, ctypes.byref(config))
            self.lib.VCI_StartCAN(self.dev_type, self.dev_idx, self.can_idx)
            self.connected = True
            self.rx_running = True
            self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
            self.rx_thread.start()
            return True, "Connected"
        except Exception as e: return False, str(e)

    def disconnect(self):
        self.rx_running = False
        if self.rx_thread: self.rx_thread.join(timeout=0.5)
        if self.lib and self.connected: self.lib.VCI_CloseDevice(self.dev_type, self.dev_idx)
        self.connected = False

    def send_frame(self, can_id, data_bytes, meaning=""):
        if not self.connected: return False
        obj = VCI_CAN_OBJ()
        obj.ID = can_id
        obj.SendType = 0
        obj.ExternFlag = 1
        obj.DataLen = 8
        ctypes.memmove(obj.Data, bytes(data_bytes), 8)
        res = self.lib.VCI_Transmit(self.dev_type, self.dev_idx, self.can_idx, ctypes.byref(obj), 1)
        if res == 1:
            if self.on_tx_log_callback: self.on_tx_log_callback(can_id, list(data_bytes), meaning)
            return True
        return False

    # ---- Control Commands ----
    def set_voltage(self, dest_addr, voltage_v):
        """Set Output Voltage (0.1V scaling)"""
        val = int(voltage_v * 10)
        data = [0x03, 0xF0, 0x00, 0x21, 0x00, 0x00, (val >> 8) & 0xFF, val & 0xFF]
        return self.send_frame(self.build_id(dest_addr), data, f"Set Voltage: {voltage_v}V")

    def set_current(self, dest_addr, current_a):
        """Set Real-time Current Position (Limit) based on 20A ref"""
        # Formula: (Target / 20A) * 1024
        val = int((current_a / 20.0) * 1024)
        data = [0x03, 0xF0, 0x00, 0x22, 0x00, 0x00, (val >> 8) & 0xFF, val & 0xFF]
        return self.send_frame(self.build_id(dest_addr), data, f"Set Current: {current_a}A")

    def boot_module(self, dest_addr, on=True):
        """Boot/Power-on module (uses bitmask for address)"""
        # Message ID 0x0230 for addr 1-31. 
        # Mod 1 = bit 1 (0x02), Mod 2 = bit 2 (0x04)
        bit_val = 1 << dest_addr if dest_addr < 32 else 0 # Simple logic for single mod
        if not on: bit_val = 0
        data = [0x03, 0xF0, 0x02, 0x30, 0x00, 0x00, (bit_val >> 8) & 0xFF, bit_val & 0xFF]
        return self.send_frame(self.build_id(dest_addr), data, "Power ON" if on else "Power OFF")

    def query_status(self, dest_addr):
        """Comprehensive Query"""
        data = [0x50, 0xF0, 0x02, 0x02, 0x00, 0x00, 0x00, 0x00]
        return self.send_frame(self.build_id(dest_addr), data, "Comprehensive Query")

    def _rx_loop(self):
        vci_obj_array = (VCI_CAN_OBJ * 50)()
        while self.rx_running:
            if not self.connected:
                time.sleep(0.1); continue
            num = self.lib.VCI_Receive(self.dev_type, self.dev_idx, self.can_idx, ctypes.byref(vci_obj_array), 50, 100)
            if num > 0 and num < 0x7FFFFFFF:
                for i in range(num):
                    obj = vci_obj_array[i]
                    f_id = obj.ID
                    f_data = list(obj.Data)[:8]
                    if self.on_all_rx_callback:
                        self.on_all_rx_callback(f_id, f_data, "Receive", obj.ExternFlag, obj.RemoteFlag)
                    
                    # Parse Fiverevse Messages
                    # Type = Byte 0. Type 0x41 is Reply.
                    if f_data[0] == 0x41:
                        msg_id = (f_data[2] << 8) | f_data[3]
                        if msg_id == 0x0203: # DC Status (Usually contains V/I)
                            # PDF says Byte 4-5 is Voltage (0.1V), 6-7 is Current (0.1A)
                            v_raw = (f_data[4] << 8) | f_data[5]
                            i_raw = (f_data[6] << 8) | f_data[7]
                            if self.on_data_received_callback:
                                self.on_data_received_callback("VOLTAGE", v_raw / 10.0)
                                self.on_data_received_callback("CURRENT", i_raw / 10.0)
                        elif msg_id == 0x0202: # Comprehensive Reply
                            # Might contain status bits
                            status_bits = (f_data[4] << 8) | f_data[5]
                            if self.on_data_received_callback:
                                self.on_data_received_callback("STATUS", status_bits)
            else: time.sleep(0.01)
