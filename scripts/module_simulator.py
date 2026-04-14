import time
import ctypes
import threading
from acepower_can import (VCI_CAN_OBJ, AcePowerCANController, DEVICE_TYPES, BAUDRATE_MAP)

class AcePowerModuleSimulator:
    def __init__(self, dev_idx=0, can_idx=0):
        self.ctrl = AcePowerCANController()
        self.dev_idx = dev_idx
        self.can_idx = can_idx
        
        # Simulated State
        self.is_on = False
        self.set_v = 100.0
        self.set_i = 10.0
        self.act_v = 0.0
        self.act_i = 0.0
        
        self.running = False

    def start(self, dev_type=4, baud="125 Kbps"):
        print(f"--- Mô phỏng Module AcePower (Addr: 1) đang khởi động ---")
        try:
            self.ctrl.connect(dev_type=dev_type, dev_idx=self.dev_idx, can_idx=self.can_idx, baud_rate=baud)
            self.running = True
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()
            print("Simulator đang lắng nghe lệnh từ Trạm sạc (PC)...")
            print("Nhấn Ctrl+C để dừng.")
        except Exception as e:
            print(f"Lỗi khởi động Simulator: {e}")

    def _run(self):
        buffer_size = 50
        vci_obj_array = (VCI_CAN_OBJ * buffer_size)()
        
        while self.running:
            # Mô phỏng đặc tính điện áp (tăng dần khi ON, giảm khi OFF)
            if self.is_on:
                if self.act_v < self.set_v: self.act_v += 5.0
                if self.act_v > self.set_v: self.act_v -= 5.0
                self.act_i = self.set_i * 0.95 # Giả lập có tải
            else:
                if self.act_v > 0.5: self.act_v *= 0.8
                else: self.act_v = 0.0
                self.act_i = 0.0

            num_read = self.ctrl.lib.VCI_Receive(self.ctrl.dev_type, self.ctrl.dev_idx, self.ctrl.can_idx, ctypes.byref(vci_obj_array), buffer_size, 100)
            
            if num_read > 0:
                for i in range(num_read):
                    frame = vci_obj_array[i]
                    self.handle_frame(frame)
            
            time.sleep(0.1)

    def handle_frame(self, frame):
        data = list(frame.Data)[:frame.DataLen]
        if len(data) < 2: return
        
        msg_type = data[0] & 0x0F
        cmd = data[1]
        
        # ID Phản hồi (Module 1 -> Monitor 1)
        # Protocol=1, Monitor=1, Module=1 -> 0x03214000
        res_id = 0x03214000 

        # --- Xử lý lệnh SET (MessageType 0x00) ---
        if msg_type == 0x00:
            if cmd == 0x02: # Set Volt
                val = (data[4] << 24) | (data[5] << 16) | (data[6] << 8) | data[7]
                self.set_v = val / 1000.0
                print(f"[SET] Cài áp: {self.set_v}V")
            elif cmd == 0x03: # Set Curr
                val = (data[4] << 24) | (data[5] << 16) | (data[6] << 8) | data[7]
                self.set_i = val / 1000.0
                print(f"[SET] Cài dòng: {self.set_i}A")
            elif cmd == 0x04: # Power On/Off
                state = data[7]
                self.is_on = (state == 0)
                print(f"[CMD] Module: {'ON' if self.is_on else 'OFF'}")

        # --- Xử lý lệnh READ (MessageType 0x02) ---
        elif msg_type == 0x02:
            if cmd == 0x00: # Read Volt
                val_mv = int(self.act_v * 1000)
                self.send_response(res_id, 0x00, val_mv)
            elif cmd == 0x01: # Read Curr
                val_ma = int(self.act_i * 1000)
                self.send_response(res_id, 0x01, val_ma)
            elif cmd == 0x08: # Read Status
                # Bit 25 = 1 if OFF
                st = (1 << 25) if not self.is_on else 0
                self.send_response(res_id, 0x08, st)

    def send_response(self, can_id, cmd, value):
        data = bytearray(8)
        data[0] = 0x13 # Group 1, MsgType 3 (Read Response)
        data[1] = cmd
        data[4] = (value >> 24) & 0xFF
        data[5] = (value >> 16) & 0xFF
        data[6] = (value >> 8) & 0xFF
        data[7] = value & 0xFF
        self.ctrl.send_frame(can_id, data, f"Simu Response: {cmd}")

    def stop(self):
        self.running = False
        self.ctrl.disconnect()

if __name__ == '__main__':
    # Chỉnh sửa Index thiết bị nếu bạn dùng 2 adapter.
    # Thường GUI dùng Dev 0, Simulator dùng Dev 1.
    simu = AcePowerModuleSimulator(dev_idx=1, can_idx=0)
    simu.start(dev_type=4, baud="125 Kbps")
    
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        simu.stop()
        print("Simulator đã dừng.")
