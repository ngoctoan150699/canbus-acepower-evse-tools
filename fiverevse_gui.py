# -*- coding: utf-8 -*-
import sys
import os
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QGroupBox, QLineEdit, QMessageBox,
                             QGridLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QTabWidget, QSpinBox, QCheckBox, QDoubleSpinBox, QTextEdit)
from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot, Qt, QDateTime
from PyQt5.QtGui import QFont, QColor, QBrush, QIcon

from fiverevse_can import FiverevseCANController, BAUDRATE_MAP, DEVICE_TYPES, resource_path, log_debug

# Command reference for Fiverevse V2.6
COMMAND_DATA = [
    ("0x0021", "Set Voltage", "W", "0.1V scaling (V*10)", "03 F0 00 21 00 00 [V*10]"),
    ("0x0022", "Set Current", "W", "Percentage (I/20)*1024", "03 F0 00 22 00 00 [I_scaled]"),
    ("0x0230", "Boot/Power ON", "W", "Bitmask for addr 1-31", "03 F0 02 30 00 00 00 [mask]"),
    ("0x0202", "Comprehensive Query", "R", "Status, V, I query", "50 F0 02 02 00 00 00 00"),
    ("0x0203", "DC Status Reply", "R", "Reply with V and I", "41 F0 02 03 [V] [I] [Status]"),
]

class FiverevseControllerGUI(QMainWindow):
    signal_data_received = pyqtSignal(str, float)
    signal_tx_log = pyqtSignal(int, list, str)
    signal_bus_monitor = pyqtSignal(int, list, str, int, int)

    def __init__(self):
        super().__init__()
        self.can_ctrl = FiverevseCANController()
        self.can_ctrl.on_data_received_callback = self._on_can_data
        self.can_ctrl.on_tx_log_callback = self._on_tx_log
        self.can_ctrl.on_all_rx_callback = self._on_all_rx
        self.scanned_devices = []
        self.rx_count = 0
        
        self.init_ui()
        
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_module)
        self.poll_timer.setInterval(1000)
        
    def init_ui(self):
        self.setWindowTitle('Fiverevse EV Charger - V2.6 Protocol Controller')
        self.resize(1250, 900)
        
        # Set Window Icon
        icon_path = resource_path("charging-station (1).png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Premium Modern Style
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QTabWidget::pane { border: 1px solid #dee2e6; background: white; border-top: none; }
            QTabBar::tab { 
                background: #e9ecef; padding: 12px 30px; border: 1px solid #dee2e6; 
                border-bottom: none; margin-right: 2px; border-top-left-radius: 4px; border-top-right-radius: 4px;
            }
            QTabBar::tab:selected { background: white; border-bottom: 2px solid #0d6efd; color: #0d6efd; font-weight: bold; }
            QGroupBox { 
                font-weight: bold; border: 1px solid #e0e0e0; border-radius: 8px; 
                margin-top: 20px; background: #ffffff; padding-top: 25px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; color: #004085; padding: 0 5px; }
            QPushButton { 
                padding: 8px 18px; border-radius: 6px; border: 1px solid #ced4da; 
                background: #ffffff; color: #495057; font-weight: 500;
            }
            QPushButton:hover { background: #f1f3f5; border-color: #0d6efd; color: #0d6efd; }
            QPushButton#btnConnect { background: #198754; color: white; border: none; font-size: 14px; }
            QPushButton#btnConnect:disabled { background: #6c757d; }
            QPushButton#btnScan { background: #0dcaf0; color: white; border: none; }
            QLineEdit, QComboBox { 
                padding: 7px; border: 1px solid #ced4da; border-radius: 6px; 
                background: #fdfdfd; selection-background-color: #0d6efd;
            }
            QTableWidget { border: 1px solid #dee2e6; gridline-color: #f1f3f5; selection-background-color: #e7f1ff; selection-color: #0d6efd; }
            QHeaderView::section { background: #f8f9fa; padding: 5px; border: 1px solid #dee2e6; font-weight: bold; color: #495057; }
        """)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # --- TOP: CONNECTION AREA ---
        group_conn = QGroupBox("KẾT NỐI HỆ THỐNG")
        l_conn = QHBoxLayout()
        l_conn.setSpacing(15)
        
        l_conn.addWidget(QLabel("Loại Driver:"))
        self.combo_type = QComboBox(); self.combo_type.addItems(list(DEVICE_TYPES.keys())); self.combo_type.setCurrentIndex(1)
        l_conn.addWidget(self.combo_type)
        
        l_conn.addWidget(QLabel("Tốc độ (Baud):"))
        self.combo_baud = QComboBox(); self.combo_baud.addItems(list(BAUDRATE_MAP.keys())); self.combo_baud.setCurrentText("125 Kbps")
        l_conn.addWidget(self.combo_baud)
        
        self.btn_scan = QPushButton("🔍 QUÉT THIẾT BỊ"); self.btn_scan.setObjectName("btnScan")
        self.btn_scan.clicked.connect(self.on_scan_clicked)
        l_conn.addWidget(self.btn_scan)
        
        self.combo_device = QComboBox(); self.combo_device.setMinimumWidth(350)
        self.combo_device.setPlaceholderText("Hãy bấm quét tìm adapter...")
        l_conn.addWidget(self.combo_device, stretch=1)
        
        self.btn_connect = QPushButton("KẾT NỐI ⚡"); self.btn_connect.setObjectName("btnConnect")
        self.btn_connect.setEnabled(False)
        self.btn_connect.clicked.connect(self.on_connect_clicked)
        l_conn.addWidget(self.btn_connect)
        group_conn.setLayout(l_conn)
        layout.addWidget(group_conn)

        # --- MIDDLE: TABS ---
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_control_tab(), "FIVEREVSE CONTROL")
        self.tabs.addTab(self.create_can_tool_tab(), "BUS ANALYZER")
        self.tabs.addTab(self.create_protocol_docs_tab(), "PROTOCOL V2.6 DOCS")
        self.tabs.addTab(self.create_ref_tab(), "COMMAND REFERENCE")
        layout.addWidget(self.tabs)

        self.setCentralWidget(central_widget)
        
        self.signal_data_received.connect(self.update_ui_from_can)
        self.signal_tx_log.connect(self.add_log_entry)
        self.signal_bus_monitor.connect(self.add_bus_entry)
        self._toggle_control_state(False)

    def create_control_tab(self):
        tab = QWidget(); main_l = QVBoxLayout(tab)
        main_l.setContentsMargins(15, 15, 15, 15)
        
        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("<b>ĐANG ĐIỀU KHIỂN MODULE (ADDR):</b>"))
        self.combo_module_addr = QSpinBox()
        self.combo_module_addr.setRange(1, 63); self.combo_module_addr.setValue(1)
        self.combo_module_addr.setFixedWidth(100)
        info_row.addWidget(self.combo_module_addr)
        info_row.addStretch()
        main_l.addLayout(info_row)

        dash_layout = QHBoxLayout()
        
        # --- COL 1: CONTROL PANEL ---
        g_ctrl = QGroupBox("CÀI ĐẶT FIVERVSE")
        l_ctrl = QVBoxLayout()
        grid_inputs = QGridLayout()
        
        grid_inputs.addWidget(QLabel("⚡ ĐIỆN ÁP SET (V):"), 0, 0)
        self.spin_set_v = QDoubleSpinBox()
        self.spin_set_v.setRange(0.00, 1000.00); self.spin_set_v.setValue(450.00)
        self.spin_set_v.setFixedHeight(45); self.spin_set_v.setFont(QFont("Segoe UI", 12, QFont.Bold))
        grid_inputs.addWidget(self.spin_set_v, 0, 1)
        btn_v = QPushButton("SET V"); btn_v.setFixedSize(80, 45); btn_v.clicked.connect(self.action_set_voltage)
        btn_v.setStyleSheet("background: #0d6efd; color: white; font-weight: bold; border-radius: 6px;")
        grid_inputs.addWidget(btn_v, 0, 2)
        
        grid_inputs.addWidget(QLabel("🌡 DÒNG GIỚI HẠN (A):"), 1, 0)
        self.spin_set_i = QDoubleSpinBox()
        self.spin_set_i.setRange(0.00, 100.00); self.spin_set_i.setValue(20.00)
        self.spin_set_i.setFixedHeight(45); self.spin_set_i.setFont(QFont("Segoe UI", 12, QFont.Bold))
        grid_inputs.addWidget(self.spin_set_i, 1, 1)
        btn_i = QPushButton("SET I"); btn_i.setFixedSize(80, 45); btn_i.clicked.connect(self.action_set_current)
        btn_i.setStyleSheet("background: #0d6efd; color: white; font-weight: bold; border-radius: 6px;")
        grid_inputs.addWidget(btn_i, 1, 2)
        l_ctrl.addLayout(grid_inputs)
        
        l_ctrl.addStretch()
        pwr_box = QHBoxLayout()
        self.btn_power_on = QPushButton("⚡ BOOT MODULE"); self.btn_power_on.setFixedHeight(60)
        self.btn_power_on.setStyleSheet("background: #198754; color: white; font-size: 16px; font-weight: bold;")
        self.btn_power_on.clicked.connect(lambda: self.action_boot(True))
        self.btn_power_off = QPushButton("⛔ SHUTDOWN"); self.btn_power_off.setFixedHeight(60)
        self.btn_power_off.setStyleSheet("background: #dc3545; color: white; font-size: 16px; font-weight: bold;")
        self.btn_power_off.clicked.connect(lambda: self.action_boot(False))
        pwr_box.addWidget(self.btn_power_on, 2); pwr_box.addWidget(self.btn_power_off, 1)
        l_ctrl.addLayout(pwr_box)
        g_ctrl.setLayout(l_ctrl)
        dash_layout.addWidget(g_ctrl, 3)
        
        # --- COL 2: PRIMARY MONITOR ---
        g_mon = QGroupBox("GIÁ TRỊ ĐẦU RA (REAL-TIME)")
        l_mon = QVBoxLayout()
        f_v = QFrame(); f_v.setStyleSheet("background: #000; border: 2px solid #555; border-radius: 10px;")
        lv = QVBoxLayout(f_v); lv.addWidget(QLabel("<font color='white'>⚡ OUTPUT VOLTAGE</font>"), alignment=Qt.AlignCenter)
        self.lbl_v = QLabel("0.0 V"); self.lbl_v.setFont(QFont("Digital-7", 60, QFont.Bold))
        self.lbl_v.setStyleSheet("color: #00ff00;"); lv.addWidget(self.lbl_v, alignment=Qt.AlignCenter)
        l_mon.addWidget(f_v)
        
        f_i = QFrame(); f_i.setStyleSheet("background: #000; border: 2px solid #555; border-radius: 10px;")
        li = QVBoxLayout(f_i); li.addWidget(QLabel("<font color='white'>🌡 OUTPUT CURRENT</font>"), alignment=Qt.AlignCenter)
        self.lbl_i = QLabel("0.0 A"); self.lbl_i.setFont(QFont("Digital-7", 60, QFont.Bold))
        self.lbl_i.setStyleSheet("color: #ffcc00;"); li.addWidget(self.lbl_i, alignment=Qt.AlignCenter)
        l_mon.addWidget(f_i)
        g_mon.setLayout(l_mon)
        dash_layout.addWidget(g_mon, 4)
        
        # --- COL 3: STATUS ---
        g_status = QGroupBox("TRẠNG THÁI HỆ THỐNG")
        l_st = QVBoxLayout()
        lay, self.led_comm = self._create_led("Giao tiếp CAN"); l_st.addLayout(lay)
        lay, self.led_ready = self._create_led("Ready to Boot"); l_st.addLayout(lay)
        lay, self.led_fault = self._create_led("Lỗi Module (Fault)"); l_st.addLayout(lay)
        lay, self.led_ov = self._create_led("Quá áp (OV)"); l_st.addLayout(lay)
        lay, self.led_ot = self._create_led("Quá nhiệt (OT)"); l_st.addLayout(lay)
        l_st.addStretch()
        g_status.setLayout(l_st)
        dash_layout.addWidget(g_status, 3)
        
        main_l.addLayout(dash_layout)
        main_l.addWidget(QLabel("<b>NHẬT KÝ LỆNH (TX):</b>"))
        self.tab_mini_log = QTableWidget(0, 3); self.tab_mini_log.setHorizontalHeaderLabels(["Thời gian", "Frame ID", "Mô tả lệnh"])
        self.tab_mini_log.horizontalHeader().setStretchLastSection(True); self.tab_mini_log.setMaximumHeight(200)
        main_l.addWidget(self.tab_mini_log)
        
        return tab

    def _create_led(self, text):
        layout = QHBoxLayout()
        led = QLabel(); led.setFixedSize(16, 16); led.setStyleSheet("background: #ced4da; border-radius: 8px; border: 1px solid #adb5bd;")
        layout.addWidget(led); layout.addWidget(QLabel(text)); layout.addStretch()
        return (layout, led)

    def create_can_tool_tab(self):
        tab = QWidget(); l = QVBoxLayout(tab)
        g_send = QGroupBox("SEND RAW FRAME")
        gs = QGridLayout()
        gs.addWidget(QLabel("CAN ID (Hex):"), 0, 0); self.raw_id = QLineEdit("1802F001"); gs.addWidget(self.raw_id, 0, 1)
        gs.addWidget(QLabel("Data (Hex):"), 0, 2); self.raw_data = QLineEdit("50 F0 02 02 00 00 00 00"); gs.addWidget(self.raw_data, 0, 3)
        btn = QPushButton("GỬI"); btn.clicked.connect(self.on_send_raw_clicked); gs.addWidget(btn, 0, 4)
        g_send.setLayout(gs); l.addWidget(g_send)
        
        self.cb_recv = QCheckBox("Enable Monitoring"); self.cb_recv.setChecked(True); l.addWidget(self.cb_recv)
        self.table_bus = QTableWidget(0, 6); self.table_bus.setHorizontalHeaderLabels(["Time", "Dir", "ID (Hex)", "Format", "DLC", "Data"])
        self.table_bus.horizontalHeader().setStretchLastSection(True)
        l.addWidget(self.table_bus)
        return tab

    def create_protocol_docs_tab(self):
        tab = QWidget(); l = QVBoxLayout(tab)
        info = QTextEdit(); info.setReadOnly(True)
        info.setHtml("""
            <h2>Giao thức Fiverevse V2.6 (Trích dẫn)</h2>
            <p><b>Cấu hình:</b> 125kbps, Extended Frame.</p>
            <p><b>Cấu trúc ID:</b> 0x60 (bits 28:22) | Dest (bits 21:11) | Source (bits 10:0).</p>
            <h3>Quy trình vận hành:</h3>
            <ol>
                <li>Cài điện áp (x10) - Msg ID 0x0021</li>
                <li>Cài giới hạn dòng ((I/20)*1024) - Msg ID 0x0022</li>
                <li>Gửi lệnh Boot (Bitmask) - Msg ID 0x0230</li>
            </ol>
            <p><i>Lưu ý: Luôn kiểm tra Bit 13 (Ready to Boot) từ bản tin trạng thái trước khi bật nguồn.</i></p>
        """)
        l.addWidget(info); return tab

    def create_ref_tab(self):
        tab = QWidget(); l = QVBoxLayout(tab)
        table = QTableWidget(len(COMMAND_DATA), 5); table.setHorizontalHeaderLabels(["ID Lệnh", "Tên", "Loại", "Mô tả", "Ví dụ Payload"])
        for i, (cid, name, typ, desc, ex) in enumerate(COMMAND_DATA):
            table.setItem(i, 0, QTableWidgetItem(cid)); table.setItem(i, 1, QTableWidgetItem(name))
            table.setItem(i, 2, QTableWidgetItem(typ)); table.setItem(i, 3, QTableWidgetItem(desc)); table.setItem(i, 4, QTableWidgetItem(ex))
        table.horizontalHeader().setStretchLastSection(True); l.addWidget(table); return tab

    # --- Handlers ---
    def on_scan_clicked(self):
        dt = DEVICE_TYPES.get(self.combo_type.currentText(), 4)
        devs = self.can_ctrl.scan_devices(dt)
        if devs:
            self.scanned_devices = devs; self.combo_device.clear()
            for d in devs: self.combo_device.addItem(d['display'])
            self.btn_connect.setEnabled(True)
        else: QMessageBox.warning(self, "Lỗi", "Không thấy thiết bị.")

    def on_connect_clicked(self):
        if not self.can_ctrl.connected:
            sel = self.combo_device.currentIndex()
            if sel < 0: return
            ok, msg = self.can_ctrl.connect(DEVICE_TYPES.get(self.combo_type.currentText()), self.scanned_devices[sel]['index'], 0, self.combo_baud.currentText())
            if ok:
                self.btn_connect.setText("NGẮT ❌"); self._toggle_control_state(True); self.poll_timer.start()
            else: QMessageBox.warning(self, "Lỗi", msg)
        else:
            self.poll_timer.stop(); self.can_ctrl.disconnect(); self.btn_connect.setText("KẾT NỐI ⚡"); self._toggle_control_state(False)

    def _toggle_control_state(self, conn):
        self.btn_power_on.setEnabled(conn); self.btn_power_off.setEnabled(conn)

    def action_set_voltage(self): self.can_ctrl.set_voltage(self.combo_module_addr.value(), self.spin_set_v.value())
    def action_set_current(self): self.can_ctrl.set_current(self.combo_module_addr.value(), self.spin_set_i.value())
    def action_boot(self, on): self.can_ctrl.boot_module(self.combo_module_addr.value(), on)

    def poll_module(self): self.can_ctrl.query_status(self.combo_module_addr.value())

    def _on_can_data(self, t, v): self.signal_data_received.emit(t, v)
    def _on_tx_log(self, i, d, m): self.signal_tx_log.emit(i, d, m)
    def _on_all_rx(self, i, d, h, e, r): self.signal_bus_monitor.emit(i, d, h, e, r)

    @pyqtSlot(int, list, str)
    def add_log_entry(self, cid, data, meaning):
        r = self.tab_mini_log.rowCount(); self.tab_mini_log.insertRow(r)
        self.tab_mini_log.setItem(r, 0, QTableWidgetItem(QDateTime.currentDateTime().toString("HH:mm:ss")))
        self.tab_mini_log.setItem(r, 1, QTableWidgetItem(f"0x{cid:08X}")); self.tab_mini_log.setItem(r, 2, QTableWidgetItem(meaning))
        self.tab_mini_log.scrollToBottom()

    @pyqtSlot(int, list, str, int, int)
    def add_bus_entry(self, cid, data, dir, ext, rem):
        if not self.cb_recv.isChecked() and dir == "Receive": return
        r = self.table_bus.rowCount(); self.table_bus.insertRow(r)
        self.table_bus.setItem(r, 0, QTableWidgetItem(QDateTime.currentDateTime().toString("HH:mm:ss.zzz")))
        self.table_bus.setItem(r, 1, QTableWidgetItem(dir)); self.table_bus.setItem(r, 2, QTableWidgetItem(f"0x{cid:08X}"))
        self.table_bus.setItem(r, 3, QTableWidgetItem("Ext" if ext else "Std")); self.table_bus.setItem(r, 4, QTableWidgetItem(str(len(data))))
        self.table_bus.setItem(r, 5, QTableWidgetItem(" ".join([f"{x:02X}" for x in data])))
        if dir == "TX":
            for c in range(6): self.table_bus.item(r, c).setForeground(QBrush(QColor("blue")))
        self.table_bus.scrollToBottom()
        if r > 200: self.table_bus.removeRow(0)

    @pyqtSlot(str, float)
    def update_ui_from_can(self, t, v):
        if t == "VOLTAGE": self.lbl_v.setText(f"{v:.1f} V")
        elif t == "CURRENT": self.lbl_i.setText(f"{v:.1f} A")
        elif t == "STATUS":
            st = int(v)
            self._set_led(self.led_ready, (st >> 13) & 1)
            self._set_led(self.led_fault, (st >> 2) & 1)
            self._set_led(self.led_ov, (st >> 0) & 1)
            self._set_led(self.led_ot, (st >> 1) & 1)
            self._set_led(self.led_comm, 1, "green")

    def _set_led(self, led_widget, active, color="red"):
        c = color if active else "#ced4da"
        led_widget.setStyleSheet(f"background: {c}; border-radius: 8px; border: 1px solid #000;")

    def on_send_raw_clicked(self):
        try:
            cid = int(self.raw_id.text(), 16); data = bytearray.fromhex(self.raw_data.text().replace(" ",""))
            self.can_ctrl.send_frame(cid, data, "Raw Custom")
        except: pass

    def closeEvent(self, event): self.can_ctrl.disconnect(); event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv); window = FiverevseControllerGUI(); window.show(); sys.exit(app.exec_())
