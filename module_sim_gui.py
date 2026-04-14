# -*- coding: utf-8 -*-
import sys
import threading
import time
import ctypes
import re
import random
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QGroupBox, QLineEdit, QMessageBox,
                             QGridLayout, QTextEdit, QSpinBox, QCheckBox)
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QDateTime
from PyQt5.QtGui import QFont, QIcon

import os
from acepower_can import AcePowerCANController, BAUDRATE_MAP, DEVICE_TYPES, VCI_CAN_OBJ, resource_path, log_debug

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
        self.ac_vin = 220.0
        self.temp_c = 32.0
        self.fan_rpm = 0
        
        self.rx_running = False
        self.scanned_devices = []
        
        self.can_ctrl.on_all_rx_callback = self.on_can_raw_data
        
        self.init_ui()
        self.signal_rx.connect(self.update_log)
        
        self.sim_thread_running = True
        self.sim_thread = threading.Thread(target=self.physics_loop, daemon=True)
        self.sim_thread.start()
        
        # Initial UI state (Auto-scan removed for stability)

    def init_ui(self):
        self.setWindowTitle('AcePower Module Simulator (Simple Mode)')
        self.resize(1000, 750)
        
        # Set Window Icon
        icon_path = resource_path("charging-station.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
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
        
        h_st.addWidget(QLabel("Sim ID:"))
        self.spin_addr = QSpinBox()
        self.spin_addr.setRange(1, 64)
        self.spin_addr.setValue(1)
        self.spin_addr.setFixedWidth(50)
        h_st.addWidget(self.spin_addr)
        
        self.lbl_status = QLabel("STATE: OFF | V: 0.00V | I: 0.00A")
        self.lbl_status.setFont(QFont("Consolas", 12, QFont.Bold))
        h_st.addWidget(self.lbl_status, stretch=1)
        
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
        log_debug("Simu UI: Scan Button Clicked")
        dt = DEVICE_TYPES.get(self.combo_type.currentText(), 4)
        try:
            devs = self.can_ctrl.scan_devices(dt)
            if devs:
                log_debug(f"Simu UI: Found {len(devs)} devices")
                self.combo_device.clear()
                self.scanned_devices = devs
                for d in devs: self.combo_device.addItem(d['display'])
                self.btn_connect.setEnabled(True)
                if len(devs) > 1: self.combo_device.setCurrentIndex(1)
            else:
                log_debug("Simu UI: No devices found")
                QMessageBox.warning(self, "No Devices", "No USB-CAN adapters found. Check cables.")
        except Exception as e:
            log_debug(f"Simu UI: Scan Error: {e}")
            QMessageBox.warning(self, "Scan Error", str(e))
    

    def toggle_connection(self):
        if not self.can_ctrl.connected:
            sel = self.combo_device.currentIndex()
            if sel < 0: return
            dev = self.scanned_devices[sel]; dt = DEVICE_TYPES.get(self.combo_type.currentText(), 4)
            bd = self.combo_baud.currentText()
            
            ok, msg = self.can_ctrl.connect(dt, dev['index'], 0, bd)
            if ok:
                self.can_ctrl.on_all_rx_callback = self.on_can_raw_data
                self.btn_connect.setText("Disconnect"); self.btn_scan.setEnabled(False)
                self.signal_rx.emit(f"+++ Connected to {dev['display']}")
            else:
                QMessageBox.warning(self, "Fail", msg)
        else:
            self.can_ctrl.disconnect()
            self.btn_connect.setText("Connect"); self.btn_scan.setEnabled(True)
            self.signal_rx.emit("--- Disconnected.")

    def on_can_raw_data(self, can_id, data, direction, extern, remote):
        if direction == "Receive":
            # Mock frame to reuse handle_frame logic
            class MockFrame: pass
            f = MockFrame(); f.ID = can_id; f.Data = data; f.DataLen = len(data)
            self.handle_frame(f)



    def handle_frame(self, frame):
        data = list(frame.Data)[:frame.DataLen]
        self.signal_rx.emit(f"RECV ID: 0x{frame.ID:08X} | DATA: {' '.join([f'{x:02X}' for x in data])}")
        
        if len(data) < 2: return
        
        # Parse Module Address from ID (Bits 14-20)
        target_addr = (frame.ID >> 14) & 0x7F
        my_addr = self.spin_addr.value()
        
        # Only respond if it matches my ID or is Broadcast (0)
        if target_addr != 0 and target_addr != my_addr:
            return
            
        msg_type = data[0] & 0x0F
        cmd = data[1]
        
        # Build Response ID based on my Sim ID
        # Logic: 0x03210000 | (my_addr << 14)
        res_id = 0x03210000 | (my_addr << 14)

        if msg_type == 0x00: # SET
            self.send_auto_res(res_id, cmd, 0, msg_type_res=0x01)
            if cmd == 0x02: self.set_v = ((data[4]<<24)|(data[5]<<16)|(data[6]<<8)|data[7]) / 1000.0
            elif cmd == 0x03: self.set_i = ((data[4]<<24)|(data[5]<<16)|(data[6]<<8)|data[7]) / 1000.0
            elif cmd == 0x04: self.is_on = (data[7] == 0)
        elif msg_type == 0x02: # READ
            if cmd == 0x00: self.send_auto_res(res_id, 0x00, int(self.act_v*1000))
            elif cmd == 0x01: self.send_auto_res(res_id, 0x01, int(self.act_i*1000))
            elif cmd == 0x14: self.send_auto_res(res_id, 0x14, int(self.ac_vin*1000))
            elif cmd == 0x1E: self.send_auto_res(res_id, 0x1E, int(self.temp_c*100)) # mC
            elif 0x78 <= cmd <= 0x7A: self.send_auto_res(res_id, cmd, int(self.fan_rpm))
            elif cmd == 0x08:
                st = (1 << 25) if not self.is_on else 0
                if self.cb_fault_fan.isChecked(): st |= (1 << 9)
                if self.cb_fault_ac.isChecked(): st |= (1 << 0)
                # DC Fault simulated if current > set i * 1.1
                if self.act_i > self.set_i * 1.1: st |= (1 << 1)
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
            # 1. AC Voltage simulation (stable around 220V)
            self.ac_vin = 220.0 + random.uniform(-1.5, 1.5)
            
            # 2. Power Output Simulation
            if self.is_on:
                # Voltage Ramping
                diff = self.set_v - self.act_v
                if abs(diff) > 0.5:
                    step = 5.0 if diff > 0 else -5.0
                    self.act_v += step
                else:
                    self.act_v = self.set_v
                
                # Add tiny ripple to voltage
                self.act_v += random.uniform(-0.05, 0.05) if self.act_v > 0 else 0
                
                # Current follows load logic (simulated load resistance)
                target_i = self.set_i * 0.95
                if self.act_i < target_i: self.act_i += 1.0
                elif self.act_i > target_i: self.act_i -= 0.5
                self.act_i += random.uniform(-0.02, 0.02)
                
                # Fan Speed logic
                self.fan_rpm = 4500 + random.randint(-50, 50)
                
                # Heatup logic
                if self.temp_c < 55.0: self.temp_c += 0.05 * (self.act_i / 10.0)
            else:
                # Voltage discharge
                if self.act_v > 0:
                    self.act_v *= 0.92
                    if self.act_v < 1.0: self.act_v = 0
                self.act_i = 0
                self.fan_rpm = 0
                # Cooldown logic
                if self.temp_c > 32.0: self.temp_c -= 0.02
            
            # UI Update
            st_text = "RUNNING" if self.is_on else "SHUTDOWN"
            color = "green" if self.is_on else "red"
            status_str = f"STATE: {st_text} | V: {self.act_v:.1f}V | I: {self.act_i:.1f}A | AC: {self.ac_vin:.1f}V | Temp: {self.temp_c:.1f}C"
            self.lbl_status.setText(status_str)
            self.lbl_status.setStyleSheet(f"color: {color}; font-weight: bold;")
            
            time.sleep(0.1)

    @pyqtSlot(str)
    def update_log(self, text):
        self.txt_log.append(text)

    def closeEvent(self, event):
        self.rx_running = False; self.sim_thread_running = False; self.can_ctrl.disconnect(); event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = SimpleModuleSimulator(); win.show(); sys.exit(app.exec_())
