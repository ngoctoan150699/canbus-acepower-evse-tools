import sys
import threading
import time
import ctypes
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QGroupBox, QLineEdit, QMessageBox,
                             QGridLayout, QTextEdit, QSpinBox, QCheckBox)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QDateTime
from PyQt5.QtGui import QFont

from acepower_can import AcePowerCANController, BAUDRATE_MAP, DEVICE_TYPES, VCI_CAN_OBJ

class SimpleModuleSimulator(QMainWindow):
    signal_rx = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.can_ctrl = AcePowerCANController()
        
        # State
        self.is_on = False
        self.act_v = 0.0
        self.act_i = 0.0
        self.set_v = 100.0
        self.set_i = 10.0
        
        self.rx_running = False
        self.scanned_devices = []
        
        self.init_ui()
        self.signal_rx.connect(self.update_log)
        
        self.sim_thread_running = True
        self.sim_thread = threading.Thread(target=self.physics_loop, daemon=True)
        self.sim_thread.start()

    def init_ui(self):
        self.setWindowTitle('AcePower Module Simulator (Simple Mode)')
        self.resize(1000, 750)
        
        central = QWidget()
        main_layout = QVBoxLayout(central)

        # 1. Port Settings
        group_settings = QGroupBox("Port Settings")
        grid = QGridLayout()
        grid.addWidget(QLabel("Device Type:"), 0, 0)
        self.combo_type = QComboBox(); self.combo_type.addItems(list(DEVICE_TYPES.keys())); self.combo_type.setCurrentIndex(1)
        grid.addWidget(self.combo_type, 0, 1)
        
        grid.addWidget(QLabel("Baud:"), 0, 2)
        self.combo_baud = QComboBox(); self.combo_baud.addItems(list(BAUDRATE_MAP.keys())); self.combo_baud.setCurrentText("125 Kbps")
        grid.addWidget(self.combo_baud, 0, 3)
        
        self.btn_scan = QPushButton("Scan")
        self.btn_scan.clicked.connect(self.on_scan_clicked)
        grid.addWidget(self.btn_scan, 0, 4)

        self.combo_device = QComboBox(); self.combo_device.setMinimumWidth(350)
        self.combo_device.setPlaceholderText("Scan to see available devices...")
        grid.addWidget(self.combo_device, 1, 0, 1, 4)
        
        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setEnabled(False)
        self.btn_connect.clicked.connect(self.toggle_connection)
        grid.addWidget(self.btn_connect, 1, 4)
        
        group_settings.setLayout(grid)
        main_layout.addWidget(group_settings)

        # 2. Virtual State
        group_status = QGroupBox("Status & Control")
        h_st = QHBoxLayout()
        self.lbl_status = QLabel("STATE: OFF | V: 0.00V | I: 0.00A")
        self.lbl_status.setFont(QFont("Consolas", 12, QFont.Bold))
        h_st.addWidget(self.lbl_status)
        
        self.cb_fault_fan = QCheckBox("Simulate Fan Fail")
        self.cb_fault_ac = QCheckBox("Simulate AC Over")
        h_st.addWidget(self.cb_fault_fan); h_st.addWidget(self.cb_fault_ac)
        
        group_status.setLayout(h_st)
        main_layout.addWidget(group_status)

        # 3. Log
        main_layout.addWidget(QLabel("Communication Log (RECV from PC / SENT from SIM):"))
        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setFont(QFont("Consolas", 10))
        main_layout.addWidget(self.txt_log)

        # 4. Manual Send
        group_send = QGroupBox("Manual Response")
        row_send = QHBoxLayout()
        row_send.addWidget(QLabel("ID (Hex):"))
        self.edit_id = QLineEdit("03214000")
        row_send.addWidget(self.edit_id)
        row_send.addWidget(QLabel("Data (Hex):"))
        self.edit_data = QLineEdit("13 00 00 00 00 00 00 00")
        row_send.addWidget(self.edit_data, stretch=1)
        self.btn_send = QPushButton("Send")
        self.btn_send.clicked.connect(self.manual_send)
        row_send.addWidget(self.btn_send)
        group_send.setLayout(row_send)
        main_layout.addWidget(group_send)

        self.setCentralWidget(central)

    def on_scan_clicked(self):
        self.combo_device.clear(); self.scanned_devices = []
        dt = DEVICE_TYPES.get(self.combo_type.currentText(), 4)
        try:
            devs = self.can_ctrl.scan_devices(dt)
            if devs:
                self.scanned_devices = devs
                for d in devs: self.combo_device.addItem(d['display'])
                self.btn_connect.setEnabled(True)
            else: QMessageBox.warning(self, "No Dev", "No USB-CAN found.")
        except Exception as e: QMessageBox.critical(self, "Error", str(e))

    def toggle_connection(self):
        if not self.rx_running:
            sel = self.combo_device.currentIndex()
            if sel < 0: return
            dev = self.scanned_devices[sel]; dt = DEVICE_TYPES.get(self.combo_type.currentText(), 4)
            bd = self.combo_baud.currentText()
            try:
                self.can_ctrl.connect(dt, dev['index'], 0, bd)
                self.rx_running = True
                self.btn_connect.setText("Disconnect"); self.btn_scan.setEnabled(False)
                threading.Thread(target=self.rx_loop, daemon=True).start()
                self.signal_rx.emit(f"Connected to {dev['display']}")
            except Exception as e: QMessageBox.critical(self, "Error", str(e))
        else:
            self.rx_running = False; self.can_ctrl.disconnect(); self.btn_connect.setText("Connect"); self.btn_scan.setEnabled(True)

    def rx_loop(self):
        buffer_size = 50
        vci_obj_array = (VCI_CAN_OBJ * buffer_size)()
        error_count = 0
        while self.rx_running and self.can_ctrl.connected:
            try:
                num = self.can_ctrl.lib.VCI_Receive(self.can_ctrl.dev_type, self.can_ctrl.dev_idx, self.can_ctrl.can_idx, ctypes.byref(vci_obj_array), buffer_size, 0)
                if num > 0:
                    error_count = 0
                    for i in range(num): self.handle_frame(vci_obj_array[i])
                elif num < 0: # Lỗi từ thư viện
                    error_count += 1
                    if error_count > 5:
                        self.signal_rx.emit("!!! Critical RX Error (995/Aborted). Disconnecting...")
                        self.rx_running = False
                        break
                    time.sleep(0.5)
            except:
                time.sleep(0.5)
            time.sleep(0.01)

    def handle_frame(self, frame):
        data = list(frame.Data)[:frame.DataLen]
        self.signal_rx.emit(f"RECV ID: 0x{frame.ID:08X} | DATA: {' '.join([f'{x:02X}' for x in data])}")
        
        if len(data) < 2: return
        msg_type = data[0] & 0x0F
        cmd = data[1]
        res_id = 0x03214000 

        if msg_type == 0x00: # SET
            self.send_auto_res(res_id, cmd, 0, msg_type_res=0x01)
            if cmd == 0x02: self.set_v = ((data[4]<<24)|(data[5]<<16)|(data[6]<<8)|data[7]) / 1000.0
            elif cmd == 0x03: self.set_i = ((data[4]<<24)|(data[5]<<16)|(data[6]<<8)|data[7]) / 1000.0
            elif cmd == 0x04: self.is_on = (data[7] == 0)
        elif msg_type == 0x02: # READ
            if cmd == 0x00: self.send_auto_res(res_id, 0x00, int(self.act_v*1000))
            elif cmd == 0x01: self.send_auto_res(res_id, 0x01, int(self.act_i*1000))
            elif cmd == 0x08:
                st = (1 << 25) if not self.is_on else 0
                if self.cb_fault_fan.isChecked(): st |= (1 << 9)
                if self.cb_fault_ac.isChecked(): st |= (1 << 0)
                self.send_auto_res(res_id, 0x08, st)

    def send_auto_res(self, res_id, cmd, val, msg_type_res=0x03):
        d0 = 0x10 | msg_type_res
        d = bytearray([d0, cmd, 0, 0, (val>>24)&0xFF, (val>>16)&0xFF, (val>>8)&0xFF, val&0xFF])
        self.can_ctrl.send_frame(res_id, d, f"SIM Res {cmd}")
        self.signal_rx.emit(f"SENT ID: 0x{res_id:08X} | DATA: {d.hex(' ').upper()}")

    def manual_send(self):
        try:
            cid = int(self.edit_id.text(), 16); payload = bytearray.fromhex(self.edit_data.text().replace(" ", ""))
            self.can_ctrl.send_frame(cid, payload, "Manual"); self.signal_rx.emit(f"SENT MANUAL ID: 0x{cid:08X}")
        except Exception as e: QMessageBox.warning(self, "Err", str(e))

    def physics_loop(self):
        while self.sim_thread_running:
            if self.is_on:
                # Dâng áp từ từ (Ramping up)
                diff = self.set_v - self.act_v
                if abs(diff) > 0.5:
                    step = 5.0 if diff > 0 else -5.0
                    self.act_v += step
                    if (step > 0 and self.act_v > self.set_v) or (step < 0 and self.act_v < self.set_v):
                        self.act_v = self.set_v
                else:
                    self.act_v = self.set_v
                
                # Mô phỏng dòng điện có tải (khoảng 95% dòng limit)
                self.act_i = self.set_i * 0.95 if self.act_v > 50 else 0
            else:
                # Tụt áp khi tắt nguồn
                if self.act_v > 0:
                    self.act_v *= 0.92
                    if self.act_v < 1.0: self.act_v = 0
                self.act_i = 0
            
            # Cập nhật giao diện Simulator
            st_text = "RUNNING" if self.is_on else "SHUTDOWN"
            color = "green" if self.is_on else "red"
            self.lbl_status.setText(f"STATE: {st_text} | ACT V: {self.act_v:.2f}V | ACT I: {self.act_i:.2f}A")
            self.lbl_status.setStyleSheet(f"color: {color}; font-weight: bold;")
            
            time.sleep(0.1) # Cập nhật mượt mà 10Hz

    @pyqtSlot(str)
    def update_log(self, text):
        self.txt_log.append(text)

    def closeEvent(self, event):
        self.rx_running = False; self.sim_thread_running = False; self.can_ctrl.disconnect(); event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = SimpleModuleSimulator(); win.show(); sys.exit(app.exec_())
