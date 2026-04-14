import ctypes
import os
import threading
import time
from traceback import print_exc

# Constants
VCI_USBCAN2 = 4
STATUS_OK = 1
STATUS_ERR = 0

BAUDRATE_MAP = {
    # Key: baud_string, Value: (Timing0, Timing1)
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

# Struct Definition for ControlCAN
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

# Device type constants
DEVICE_TYPES = {
    "VCI_USBCAN1 (Type 3)": 3,
    "VCI_USBCAN2 (Type 4)": 4,
    "VCI_USBCAN_2E_U (Type 21)": 21,
}


class AcePowerCANController:
    def __init__(self, dll_path='ControlCAN.dll'):
        self.lib = None
        self.dev_type = VCI_USBCAN2
        self.dev_idx = 0
        self.can_idx = 0
        self.connected = False
        self.rx_thread = None
        self.rx_running = False
        self.on_data_received_callback = None
        self.on_tx_log_callback = None # New: callback for logging tx frames
        self.on_all_rx_callback = None # New: for raw bus monitor
        
        self.monitor_address = 1
        
        try:
            self.lib = ctypes.windll.LoadLibrary(os.path.abspath(dll_path))
        except Exception as e:
            print(f"Error loading {dll_path}: {e}")

    def scan_devices(self, dev_type=4):
        """Quét tất cả thiết bị USB-CAN đang cắm vào máy.
        Trả về list các dict: [{index, serial, fw_version, hw_type}, ...]
        """
        if not self.lib:
            raise RuntimeError("ControlCAN DLL is not loaded.")
        
        # Thử VCI_FindUsbDevice2 trước (hỗ trợ trả thông tin chi tiết)
        max_devices = 8
        info_array = (VCI_BOARD_INFO * max_devices)()
        devices = []
        
        try:
            count = self.lib.VCI_FindUsbDevice2(ctypes.byref(info_array))
            if count > 0:
                for i in range(min(count, max_devices)):
                    serial = bytes(info_array[i].str_Serial_Num).decode('ascii', errors='ignore').strip('\x00')
                    hw_type = bytes(info_array[i].str_hw_Type).decode('ascii', errors='ignore').strip('\x00')
                    fw_ver = info_array[i].fw_Version
                    fw_str = f"V{(fw_ver >> 8) & 0xFF}.{fw_ver & 0xFF:02d}"
                    devices.append({
                        'index': i,
                        'serial': serial,
                        'fw_version': fw_str,
                        'hw_type': hw_type,
                        'display': f"Device {i}: SN={serial}, FW={fw_str}"
                    })
                return devices
        except Exception:
            pass
        
        # Fallback: thử open từng device index để kiểm tra chúng có tồn tại không
        for idx in range(4):
            try:
                ret = self.lib.VCI_OpenDevice(dev_type, idx, 0)
                if ret == STATUS_OK:
                    info = VCI_BOARD_INFO()
                    self.lib.VCI_ReadBoardInfo(dev_type, idx, ctypes.byref(info))
                    serial = bytes(info.str_Serial_Num).decode('ascii', errors='ignore').strip('\x00')
                    hw_type = bytes(info.str_hw_Type).decode('ascii', errors='ignore').strip('\x00')
                    fw_ver = info.fw_Version
                    fw_str = f"V{(fw_ver >> 8) & 0xFF}.{fw_ver & 0xFF:02d}"
                    devices.append({
                        'index': idx,
                        'serial': serial,
                        'fw_version': fw_str,
                        'hw_type': hw_type,
                        'display': f"Device {idx}: SN={serial}, FW={fw_str}"
                    })
                    self.lib.VCI_CloseDevice(dev_type, idx)
            except Exception:
                continue
        
        return devices

    def connect(self, dev_type=VCI_USBCAN2, dev_idx=0, can_idx=0, baud_rate="125 Kbps"):
        if not self.lib:
            raise RuntimeError("ControlCAN DLL is not loaded.")
        
        self.dev_type = dev_type
        self.dev_idx = dev_idx
        self.can_idx = can_idx
        
        # 1. Open Device
        if self.lib.VCI_OpenDevice(self.dev_type, self.dev_idx, 0) != STATUS_OK:
            raise Exception("Failed to open CAN device. Is it plugged in?")
        
        # 2. Init Channel
        t0, t1 = BAUDRATE_MAP.get(baud_rate, (0x03, 0x1C)) # Default 125kbps
        config = VCI_INIT_CONFIG(0x00000000, 0xFFFFFFFF, 0, 1, t0, t1, 0)
        if self.lib.VCI_InitCAN(self.dev_type, self.dev_idx, self.can_idx, ctypes.byref(config)) != STATUS_OK:
            self.lib.VCI_CloseDevice(self.dev_type, self.dev_idx)
            raise Exception("Failed to initialize CAN channel.")
            
        # 3. Start Channel
        if self.lib.VCI_StartCAN(self.dev_type, self.dev_idx, self.can_idx) != STATUS_OK:
            self.lib.VCI_CloseDevice(self.dev_type, self.dev_idx)
            raise Exception("Failed to start CAN channel.")
            
        self.connected = True
        
        # Start Receiver thread
        self.rx_running = True
        self.rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self.rx_thread.start()
        
    def disconnect(self):
        self.rx_running = False
        if self.rx_thread:
            self.rx_thread.join(timeout=1.0)
        if self.lib and self.connected:
            self.lib.VCI_CloseDevice(self.dev_type, self.dev_idx)
        self.connected = False

    def build_id(self, protocol_type=1, group_addr=0, module_addr=1):
        # bits [25:28] protocol, bits [21:24] monitor, bits [14:20] module
        # According to standard Acepower U2T-A040B protocol
        msg_id = (protocol_type << 25) | (self.monitor_address << 21) | (module_addr << 14)
        return msg_id

    def send_frame(self, can_id, data_bytes, meaning=""):
        if not self.connected:
            raise Exception("Device not connected.")
            
        obj = VCI_CAN_OBJ()
        obj.ID = can_id
        obj.SendType = 0
        obj.RemoteFlag = 0
        obj.ExternFlag = 1 # 29-bit extended!
        obj.DataLen = len(data_bytes)
        for i in range(len(data_bytes)):
            obj.Data[i] = data_bytes[i]
            
        res = self.lib.VCI_Transmit(self.dev_type, self.dev_idx, self.can_idx, ctypes.byref(obj), 1)
        if res == 1:
            if self.on_tx_log_callback:
                self.on_tx_log_callback(can_id, list(data_bytes), meaning)
            return True
        else:
            print(f"Error sending frame ID {hex(can_id)}")
            return False

    # ---- Module Controls ----

    def set_voltage(self, module_addr, v_volts):
        """Set output voltage (mV)"""
        m_volts = int(v_volts * 1000)
        data = bytearray(8)
        data[0] = 0x10
        data[1] = 0x02
        data[4] = (m_volts >> 24) & 0xFF
        data[5] = (m_volts >> 16) & 0xFF
        data[6] = (m_volts >> 8) & 0xFF
        data[7] = m_volts & 0xFF
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, f"Set Voltage: {v_volts}V")

    def set_current(self, module_addr, i_amps):
        """Set output current (mA)"""
        m_amps = int(i_amps * 1000)
        data = bytearray(8)
        data[0] = 0x10
        data[1] = 0x03
        data[4] = (m_amps >> 24) & 0xFF
        data[5] = (m_amps >> 16) & 0xFF
        data[6] = (m_amps >> 8) & 0xFF
        data[7] = m_amps & 0xFF
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, f"Set Limit Current: {i_amps}A")

    def power_on(self, module_addr):
        """Power ON"""
        data = bytearray([0x10, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, "Command: Power ON")

    def power_off(self, module_addr):
        """Power OFF"""
        data = bytearray([0x10, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01])
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, "Command: Power OFF")
        
    def read_voltage(self, module_addr):
        """Request Read Output Voltage"""
        data = bytearray([0x12, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, "Request: Read Voltage")

    def read_current(self, module_addr):
        """Request Read Output Current"""
        data = bytearray([0x12, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, "Request: Read Current")
        
    def read_status(self, module_addr):
        """Request Read Status"""
        data = bytearray([0x12, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, "Request: Read Status")

    def read_ac_input(self, module_addr):
        """Request Read AC Line Voltage (Line AB)"""
        data = bytearray([0x12, 0x14, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, "Request: Read AC Input (AB)")

    def read_temperature(self, module_addr):
        """Request Read Inlet Temperature"""
        data = bytearray([0x12, 0x1E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, "Request: Read Temperature")
        
    def read_fan_speed(self, module_addr, fan_idx=1):
        """Request Read Fan Speed (1, 2, or 3)"""
        cmd = 120 + (fan_idx - 1)
        data = bytearray([0x12, cmd, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        can_id = self.build_id(module_addr=module_addr)
        self.send_frame(can_id, data, f"Request: Read Fan {fan_idx} Speed")

    def _rx_loop(self):
        buffer_size = 50
        vci_obj_array = (VCI_CAN_OBJ * buffer_size)()
        
        while self.rx_running:
            if not self.connected:
                time.sleep(0.1)
                continue
                
            num_read = self.lib.VCI_Receive(self.dev_type, self.dev_idx, self.can_idx, ctypes.byref(vci_obj_array), buffer_size, 100)
            if num_read > 0:
                for i in range(num_read):
                    frame = vci_obj_array[i]
                    frame_id = frame.ID
                    frame_data = list(frame.Data)[:frame.DataLen]
                    
                    # Notify Bus Monitor (all frames)
                    if self.on_all_rx_callback:
                        self.on_all_rx_callback(frame_id, frame_data, "Receive", frame.ExternFlag, frame.RemoteFlag)
                    
                    if len(frame_data) == 8:
                        msg_code = frame_data[0]
                        cmd_type = frame_data[1]
                        
                        # Check for 'Response' msg logic (Read resp = 0x13, Set resp = 0x11)
                        if msg_code == 0x13: # Group 1, MsgType 3 (Read Data Resp)
                            val = (frame_data[4] << 24) | (frame_data[5] << 16) | (frame_data[6] << 8) | frame_data[7]
                            res_type = ""
                            actual_val = 0
                            
                            if cmd_type == 0x00: # Voltage
                                res_type = "VOLTAGE"
                                actual_val = val / 1000.0 # V
                            elif cmd_type == 0x01: # Current
                                res_type = "CURRENT"
                                actual_val = val / 1000.0 # A
                            elif cmd_type == 0x08: # Status
                                res_type = "STATUS"
                                actual_val = val
                                
                            if self.on_data_received_callback:
                                self.on_data_received_callback(res_type, actual_val)
                                
            else:
                time.sleep(0.01) # Avoid cpu hog
