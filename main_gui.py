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

from acepower_can import AcePowerCANController, BAUDRATE_MAP, DEVICE_TYPES, resource_path, log_debug

# Dữ liệu phục vụ tab tra cứu
COMMAND_DATA = [
    ("0", "Read Voltage", "R", "mV - Đọc áp", "12 00 00 00 00 00 00 00"),
    ("1", "Read Current", "R", "mA - Đọc dòng", "12 01 00 00 00 00 00 00"),
    ("2", "Set Voltage", "W", "Cài điện áp (mV)", "10 02 00 00 [Data 4 bytes]"),
    ("3", "Set Current", "W", "Cài dòng tối đa (mA)", "10 03 00 00 [Data 4 bytes]"),
    ("4", "Power ON", "W", "Mở nguồn", "10 04 00 00 00 00 00 00"),
    ("4", "Power OFF", "W", "Tắt nguồn", "10 04 00 00 00 00 00 01"),
    ("8", "Read Status", "R", "Đọc mã lỗi module", "12 08 00 00 00 00 00 00"),
    ("20", "Read AC Vin", "R", "mV - Đọc áp đầu vào", "12 14 00 00 00 00 00 00"),
    ("30", "Temperature", "R", "m℃ - Nhiệt độ nạp", "12 1E 00 00 00 00 00 00"),
    ("120", "Fan 1 Speed", "R", "RPM - Tốc độ quạt 1", "12 78 00 00 00 00 00 00"),
]

class AcePowerControllerGUI(QMainWindow):
    signal_data_received = pyqtSignal(str, float)
    signal_tx_log = pyqtSignal(int, list, str)
    signal_bus_monitor = pyqtSignal(int, list, str, int, int)

    def __init__(self):
        super().__init__()
        self.can_ctrl = AcePowerCANController()
        self.can_ctrl.on_data_received_callback = self._on_can_data
        self.can_ctrl.on_tx_log_callback = self._on_tx_log
        self.can_ctrl.on_all_rx_callback = self._on_all_rx
        self.scanned_devices = []
        self.rx_count = 0
        
        self.init_ui()
        
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_module)
        self.poll_timer.setInterval(1000)
        
        # Initial UI state
        # (Auto-scan removed to prevent startup crashes on some systems)

    def init_ui(self):
        self.setWindowTitle('AcePower AB-U2T - Ultimate Controller')
        self.resize(1250, 900)
        
        # Set Window Icon
        icon_path = resource_path("charging-station.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Premium Modern Style (Improved White Theme)
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
        self.tabs.addTab(self.create_control_tab(), "ACEPOWER CONTROL")
        self.tabs.addTab(self.create_can_tool_tab(), "BUS ANALYZER")
        self.tabs.addTab(self.create_protocol_docs_tab(), "PROTOCOL DOCS (U2T-A030A-AG)")
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
        main_l.setSpacing(10)
        
        # --- Row 1: Module Selector ---
        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("<b>ĐANG ĐIỀU KHIỂN:</b>"))
        self.combo_module_addr = QComboBox()
        self.combo_module_addr.addItem("0 (TẤT CẢ MODULE - Broadcast)")
        self.combo_module_addr.addItems([str(i) for i in range(1, 61)])
        self.combo_module_addr.setFixedWidth(280)
        self.combo_module_addr.setStyleSheet("font-size: 13px; font-weight: bold; height: 30px;")
        info_row.addWidget(self.combo_module_addr)
        info_row.addStretch()
        main_l.addLayout(info_row)

        # --- Row 2: The Main Dashboard (3 Columns) ---
        dash_layout = QHBoxLayout()
        dash_layout.setSpacing(15)
        
        # --- COL 1: CONTROL PANEL ---
        g_ctrl = QGroupBox("CÀI ĐẶT MỤC TIÊU")
        l_ctrl = QVBoxLayout()
        l_ctrl.setSpacing(12)
        
        grid_inputs = QGridLayout()
        grid_inputs.setVerticalSpacing(15)
        
        # Voltage
        grid_inputs.addWidget(QLabel("⚡ ĐIỆN ÁP SET (V):"), 0, 0)
        self.spin_set_v = QDoubleSpinBox()
        self.spin_set_v.setRange(0.00, 1000.00); self.spin_set_v.setValue(100.00)
        self.spin_set_v.setFixedHeight(45); self.spin_set_v.setFont(QFont("Segoe UI", 12, QFont.Bold))
        grid_inputs.addWidget(self.spin_set_v, 0, 1)
        btn_v = QPushButton("SET V"); btn_v.setFixedSize(80, 45); btn_v.clicked.connect(self.action_set_voltage)
        btn_v.setStyleSheet("background: #0d6efd; color: white; font-weight: bold; border-radius: 6px;")
        grid_inputs.addWidget(btn_v, 0, 2)
        
        # Current
        grid_inputs.addWidget(QLabel("🌡 DÒNG ĐIỆN SET (A):"), 1, 0)
        self.spin_set_i = QDoubleSpinBox()
        self.spin_set_i.setRange(0.00, 125.00); self.spin_set_i.setValue(10.00)
        self.spin_set_i.setFixedHeight(45); self.spin_set_i.setFont(QFont("Segoe UI", 12, QFont.Bold))
        grid_inputs.addWidget(self.spin_set_i, 1, 1)
        btn_i = QPushButton("SET I"); btn_i.setFixedSize(80, 45); btn_i.clicked.connect(self.action_set_current)
        btn_i.setStyleSheet("background: #0d6efd; color: white; font-weight: bold; border-radius: 6px;")
        grid_inputs.addWidget(btn_i, 1, 2)
        l_ctrl.addLayout(grid_inputs)
        
        l_ctrl.addStretch()
        
        pwr_box = QHBoxLayout()
        self.btn_power_on = QPushButton("⚡ POWER ON"); self.btn_power_on.setFixedHeight(60)
        self.btn_power_on.setStyleSheet("background: #198754; color: white; font-size: 16px; font-weight: bold;")
        self.btn_power_on.clicked.connect(self.action_power_on)
        self.btn_power_off = QPushButton("⛔ POWER OFF"); self.btn_power_off.setFixedHeight(60)
        self.btn_power_off.setStyleSheet("background: #dc3545; color: white; font-size: 16px; font-weight: bold;")
        self.btn_power_off.clicked.connect(self.action_power_off)
        pwr_box.addWidget(self.btn_power_on, 2); pwr_box.addWidget(self.btn_power_off, 1)
        l_ctrl.addLayout(pwr_box)
        g_ctrl.setLayout(l_ctrl)
        dash_layout.addWidget(g_ctrl, 3)
        
        # --- COL 2: PRIMARY MONITOR (BIG GAUGES) ---
        g_mon = QGroupBox("GIÁ TRỊ ĐẦU RA (REAL-TIME)")
        l_mon = QVBoxLayout()
        
        # Stylish Voltage Frame
        f_v = QFrame(); f_v.setStyleSheet("background: #000; border: 2px solid #555; border-radius: 10px;")
        lv = QVBoxLayout(f_v); lv.addWidget(QLabel("<font color='white'>⚡ VOLTAGE OUTPUT</font>"), alignment=Qt.AlignCenter)
        self.lbl_v = QLabel("0.00 V"); self.lbl_v.setFont(QFont("Digital-7", 60, QFont.Bold))
        self.lbl_v.setStyleSheet("color: #00ff00;"); lv.addWidget(self.lbl_v, alignment=Qt.AlignCenter)
        l_mon.addWidget(f_v)
        
        # Stylish Current Frame
        f_i = QFrame(); f_i.setStyleSheet("background: #000; border: 2px solid #555; border-radius: 10px;")
        li = QVBoxLayout(f_i); li.addWidget(QLabel("<font color='white'>🌡 CURRENT OUTPUT</font>"), alignment=Qt.AlignCenter)
        self.lbl_i = QLabel("0.00 A"); self.lbl_i.setFont(QFont("Digital-7", 60, QFont.Bold))
        self.lbl_i.setStyleSheet("color: #ffcc00;"); li.addWidget(self.lbl_i, alignment=Qt.AlignCenter)
        l_mon.addWidget(f_i)
        
        g_mon.setLayout(l_mon)
        dash_layout.addWidget(g_mon, 4)
        
        # --- COL 3: MODULE DETAILS & STATUS LEDS ---
        g_status = QGroupBox("CHI TIẾT & TRẠNG THÁI")
        l_st = QVBoxLayout()
        l_st.setSpacing(8)
        
        # Secondary Data (AC, Temp, Fan)
        sub_grid = QGridLayout()
        sub_grid.addWidget(QLabel("AC Input:"), 0, 0); self.lbl_ac_vin = QLabel("--- V"); self.lbl_ac_vin.setStyleSheet("font-weight: bold; color: #0d6efd;"); sub_grid.addWidget(self.lbl_ac_vin, 0, 1)
        sub_grid.addWidget(QLabel("Temp:"), 1, 0); self.lbl_temp = QLabel("--- °C"); self.lbl_temp.setStyleSheet("font-weight: bold; color: #dc3545;"); sub_grid.addWidget(self.lbl_temp, 1, 1)
        sub_grid.addWidget(QLabel("Fan:"), 2, 0); self.lbl_fan = QLabel("--- RPM"); self.lbl_fan.setStyleSheet("font-weight: bold; color: #198754;"); sub_grid.addWidget(self.lbl_fan, 2, 1)
        l_st.addLayout(sub_grid)
        
        l_st.addSpacing(10)
        l_st.addWidget(QLabel("<b>CẢNH BÁO LỖI:</b>"))
        
        # LED Indicators
        lay, self.led_comm = self._create_led("Giao tiếp CAN"); l_st.addLayout(lay)
        lay, self.led_ac = self._create_led("Lỗi AC Input"); l_st.addLayout(lay)
        lay, self.led_dc = self._create_led("Lỗi DC Output"); l_st.addLayout(lay)
        lay, self.led_tem = self._create_led("Quá nhiệt (OT)"); l_st.addLayout(lay)
        lay, self.led_fan = self._create_led("Lỗi Quạt (Fan)"); l_st.addLayout(lay)
        
        l_st.addStretch()
        g_status.setLayout(l_st)
        dash_layout.addWidget(g_status, 3)
        
        main_l.addLayout(dash_layout)

        # --- Row 3: Action History (Compact) ---
        main_l.addWidget(QLabel("<b>NHẬT KÝ LỆNH VẬN HÀNH:</b>"))
        self.tab_mini_log = QTableWidget(0, 3); self.tab_mini_log.setHorizontalHeaderLabels(["Thời gian", "Frame ID", "Mô tả lệnh"])
        self.tab_mini_log.horizontalHeader().setStretchLastSection(True); self.tab_mini_log.setMaximumHeight(200)
        main_l.addWidget(self.tab_mini_log)
        
        return tab

    def _create_led(self, text):
        layout = QHBoxLayout()
        led = QLabel(); led.setFixedSize(16, 16); led.setStyleSheet("background: #ced4da; border-radius: 8px; border: 1px solid #adb5bd;")
        label = QLabel(text); label.setStyleSheet("font-size: 11px;")
        layout.addWidget(led); layout.addWidget(label); layout.addStretch()
        return (layout, led)

    def create_can_tool_tab(self):
        tab = QWidget(); l = QVBoxLayout(tab)
        l.setContentsMargins(10, 10, 10, 10)
        
        g_send = QGroupBox("SEND RAW COMMAND")
        gs = QGridLayout()
        gs.addWidget(QLabel("Format:"), 0, 0); self.raw_fmt = QComboBox(); self.raw_fmt.addItems(["Standard", "Extended"]); self.raw_fmt.setCurrentIndex(1); gs.addWidget(self.raw_fmt, 0, 1)
        gs.addWidget(QLabel("CAN ID (Hex):"), 0, 2); self.raw_id = QLineEdit("02204000"); gs.addWidget(self.raw_id, 0, 3)
        gs.addWidget(QLabel("Data (Hex):"), 1, 0); self.raw_data = QLineEdit("12 00 00 00 00 00 00 00"); gs.addWidget(self.raw_data, 1, 1, 1, 3)
        self.btn_send_raw = QPushButton("GỬI FRAME"); self.btn_send_raw.clicked.connect(self.on_send_raw_clicked)
        self.btn_send_raw.setStyleSheet("background: #0dcaf0; color: white; border: none; font-weight: bold;")
        gs.addWidget(self.btn_send_raw, 1, 4)
        g_send.setLayout(gs); l.addWidget(g_send)
        
        row_tool = QHBoxLayout()
        self.cb_recv = QCheckBox("Enable Bus Listening"); self.cb_recv.setChecked(True); row_tool.addWidget(self.cb_recv)
        row_tool.addStretch()
        btn_cls = QPushButton("Clear Monitor"); btn_cls.clicked.connect(lambda: (self.table_bus.setRowCount(0), setattr(self, 'rx_count', 0)))
        row_tool.addWidget(btn_cls)
        l.addLayout(row_tool)

        self.table_bus = QTableWidget(0, 9); 
        self.table_bus.setHorizontalHeaderLabels(["Index", "Time", "Ch", "Dir", "Frame ID", "Type", "Format", "DLC", "Data Hex"])
        self.table_bus.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); self.table_bus.horizontalHeader().setStretchLastSection(True)
        l.addWidget(self.table_bus)
        return tab

    def create_protocol_docs_tab(self):
        tab = QWidget(); l = QVBoxLayout(tab)
        l.setContentsMargins(15, 15, 15, 15)
        
        header = QLabel("TÀI LIỆU GIAO THỨC ACEPOWER U2T-A030A-AG (30KW)")
        header.setStyleSheet("font-size: 18px; color: #004085; font-weight: bold; margin-bottom: 10px;")
        l.addWidget(header)
        
        info = QTextEdit()
        info.setReadOnly(True)
        info.setHtml("""
            <h3>1. Cấu hình CAN Bus</h3>
            <ul>
                <li><b>Baudrate:</b> 125 Kbps (Mặc định)</li>
                <li><b>Frame Type:</b> Extended Frame (29-bit ID)</li>
            </ul>
            
            <h3>2. Cấu trúc CAN ID (29-bit)</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <th>Bits [28:25]</th>
                    <th>Bits [24:21]</th>
                    <th>Bits [20:14]</th>
                    <th>Bits [13:0]</th>
                </tr>
                <tr>
                    <td><b>Protocol ID (0x01)</b></td>
                    <td><b>Monitor Address</b></td>
                    <td><b>Module Address</b></td>
                    <td><b>Group Address / Reserved</b></td>
                </tr>
            </table>
            <p><i>Ví dụ: 0x02204000 (Monitor 1 -> Module 1)</i></p>

            <h3>3. Danh sách câu lệnh (Data Payload)</h3>
            <table border="1" style="border-collapse: collapse; width: 100%;">
                <tr style="background-color: #f2f2f2;">
                    <th>Byte 0 (Msg Type)</th>
                    <th>Byte 1 (Command)</th>
                    <th>Mô tả</th>
                    <th>Công thức dữ liệu</th>
                </tr>
                <tr>
                    <td>0x10</td><td>0x02</td><td>Cài đặt điện áp</td><td>Dữ liệu 4 byte (mV), Big-endian</td>
                </tr>
                <tr>
                    <td>0x10</td><td>0x03</td><td>Cài đặt dòng điện</td><td>Dữ liệu 4 byte (mA), Big-endian</td>
                </tr>
                <tr>
                    <td>0x10</td><td>0x04</td><td>Bật/Tắt nguồn</td><td>B7=0: ON, B7=1: OFF</td>
                </tr>
                <tr>
                    <td>0x12</td><td>0x00</td><td>Đọc điện áp đầu ra</td><td>Phản hồi 0x13 0x00 (mV)</td>
                </tr>
                <tr>
                    <td>0x12</td><td>0x01</td><td>Đọc dòng điện đầu ra</td><td>Phản hồi 0x13 0x01 (mA)</td>
                </tr>
                <tr>
                    <td>0x12</td><td>0x08</td><td>Đọc trạng thái lỗi</td><td>Phản hồi mã lỗi Bitmask</td>
                </tr>
            </table>

            <h3>4. Mã lỗi Status (Command 0x08)</h3>
            <ul>
                <li><b>Bit 0:</b> AC Input Fault (Lỗi điện áp xoay chiều)</li>
                <li><b>Bit 1:</b> DC Output Fault (Lỗi điện áp một chiều)</li>
                <li><b>Bit 2:</b> Over Temperature (Quá nhiệt)</li>
                <li><b>Bit 9:</b> Fan Fault (Lỗi quạt)</li>
                <li><b>Bit 25:</b> Module Power State (0: ON, 1: OFF)</li>
            </ul>
        """)
        l.addWidget(info)
        return tab

    def create_ref_tab(self):
        tab = QWidget(); l = QVBoxLayout(tab)
        l.setContentsMargins(10, 10, 10, 10)
        l.addWidget(QLabel("<b>TRA CỨU GIAO THỨC ACEPOWER (PROTOCOL U2T-A040B-X)</b>"))
        
        table = QTableWidget(len(COMMAND_DATA), 5)
        table.setHorizontalHeaderLabels(["Mã Lệnh", "Tên Lệnh", "Loại", "Mô tả dữ liệu", "Example Data Payload (HEX)"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents); table.horizontalHeader().setStretchLastSection(True)
        
        for i, (code, name, type, desc, ex) in enumerate(COMMAND_DATA):
            table.setItem(i, 0, QTableWidgetItem(code))
            table.setItem(i, 1, QTableWidgetItem(name))
            table.setItem(i, 2, QTableWidgetItem(type))
            table.setItem(i, 3, QTableWidgetItem(desc))
            item_ex = QTableWidgetItem(ex); item_ex.setForeground(QBrush(QColor("#0d6efd"))); item_ex.setFont(QFont("Consolas", 10))
            table.setItem(i, 4, item_ex)
            
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        l.addWidget(table)
        l.addWidget(QLabel("<i>* Ghi chú: ID 29-bit bao gồm Protocol (0x01), Monitor Addr, Module Addr và Group Addr.</i>"))
        return tab

    # --- LOGIC HANDLERS (Same as before but with robust error handling) ---
    def on_send_raw_clicked(self):
        try:
            cid = int(self.raw_id.text(), 16); data = bytearray.fromhex(self.raw_data.text().replace(" ",""))
            if self.can_ctrl.send_frame(cid, data, "Raw Custom Command"):
                pass
        except Exception as e: QMessageBox.warning(self, "Lỗi Input", f"Sai định dạng Hex: {e}")

    def on_scan_clicked(self):
        log_debug("UI: Scan Button Clicked")
        dt = DEVICE_TYPES.get(self.combo_type.currentText(), 4)
        try:
            devs = self.can_ctrl.scan_devices(dt)
            if devs:
                log_debug(f"UI: Found {len(devs)} devices")
                self.combo_device.clear() # Only clear if we have results to show
                self.scanned_devices = devs
                for d in devs: self.combo_device.addItem(d['display'])
                self.btn_connect.setEnabled(True)
                self.combo_device.setStyleSheet("background: #e7f1ff;")
            else:
                log_debug("UI: No devices found")
                self.btn_connect.setEnabled(False)
                # We DON'T clear the list here to avoid IndexErrors in other parts of UI
                QMessageBox.warning(self, "Không tìm thấy thiết bị", "Không phát hiện USB-CAN Adapter nào đang kết nối. Hãy kiểm tra cáp và thử lại.")
        except Exception as e:
            log_debug(f"UI: Scan Error: {e}")
            QMessageBox.warning(self, "Lỗi Quét", f"Không thể quét thiết bị: {e}")

    def on_connect_clicked(self):
        if not self.can_ctrl.connected:
            sel = self.combo_device.currentIndex()
            if sel < 0: return
            dev = self.scanned_devices[sel]; dt = DEVICE_TYPES.get(self.combo_type.currentText(), 4)
            bd = self.combo_baud.currentText()
            
            ok, msg = self.can_ctrl.connect(dt, dev['index'], 0, bd)
            if ok:
                self.btn_connect.setText("NGẮT KẾT NỐI ❌"); self.btn_connect.setStyleSheet("background: #dc3545; color: white;")
                self._ui_lock(True); self._toggle_control_state(True); self.poll_timer.start()
            else:
                QMessageBox.warning(self, "Lỗi Kết Nối", msg)
        else:
            self.poll_timer.stop(); self.can_ctrl.disconnect()
            self.btn_connect.setText("KẾT NỐI ⚡"); self.btn_connect.setStyleSheet("background: #198754; color: white;")
            self._ui_lock(False); self._toggle_control_state(False)

    def _ui_lock(self, locked):
        self.btn_scan.setEnabled(not locked); self.combo_type.setEnabled(not locked)
        self.combo_baud.setEnabled(not locked); self.combo_device.setEnabled(not locked)

    def _toggle_control_state(self, conn):
        self.btn_power_on.setEnabled(conn); self.btn_power_off.setEnabled(conn)
        self.btn_send_raw.setEnabled(conn)

    def action_set_voltage(self):
        try:
            m_addr_str = self.combo_module_addr.currentText()
            addr = int(re.search(r'\d+', m_addr_str).group())
            self.can_ctrl.set_voltage(addr, self.spin_set_v.value())
        except: pass

    def action_set_current(self):
        try:
            m_addr_str = self.combo_module_addr.currentText()
            addr = int(re.search(r'\d+', m_addr_str).group())
            self.can_ctrl.set_current(addr, self.spin_set_i.value())
        except: pass

    def action_power_on(self):
        try:
            addr = int(re.search(r'\d+', self.combo_module_addr.currentText()).group())
            self.can_ctrl.power_on(addr)
        except: pass

    def action_power_off(self):
        try:
            addr = int(re.search(r'\d+', self.combo_module_addr.currentText()).group())
            self.can_ctrl.power_off(addr)
        except: pass

    def poll_module(self):
        if self.can_ctrl.connected:
            try:
                addr_str = self.combo_module_addr.currentText()
                addr = int(re.search(r'\d+', addr_str).group())
                if addr == 0: return 
                # Poll all parameters
                self.can_ctrl.read_voltage(addr)
                self.can_ctrl.read_current(addr)
                self.can_ctrl.read_status(addr)
                self.can_ctrl.read_ac_vin(addr)
                self.can_ctrl.read_temp(addr)
            except: pass

    def _on_can_data(self, t, v): self.signal_data_received.emit(t, v)
    def _on_tx_log(self, i, d, m): self.signal_tx_log.emit(i, d, m)
    def _on_all_rx(self, i, d, h, e, r): self.signal_bus_monitor.emit(i, d, h, e, r)

    @pyqtSlot(int, list, str)
    def add_log_entry(self, cid, data, meaning):
        r = self.tab_mini_log.rowCount(); self.tab_mini_log.insertRow(r)
        self.tab_mini_log.setItem(r, 0, QTableWidgetItem(QDateTime.currentDateTime().toString("HH:mm:ss")))
        self.tab_mini_log.setItem(r, 1, QTableWidgetItem(f"0x{cid:08X}"))
        self.tab_mini_log.setItem(r, 2, QTableWidgetItem(meaning))
        self.tab_mini_log.scrollToBottom()
        self.add_bus_entry(cid, data, "TX", 1, 0)

    @pyqtSlot(int, list, str, int, int)
    def add_bus_entry(self, cid, data, dir, ext, rem):
        if not self.cb_recv.isChecked() and dir == "Receive": return
        self.rx_count += 1
        r = self.table_bus.rowCount(); self.table_bus.insertRow(r)
        self.table_bus.setItem(r, 0, QTableWidgetItem(str(self.rx_count)))
        self.table_bus.setItem(r, 1, QTableWidgetItem(QDateTime.currentDateTime().toString("HH:mm:ss.zzz")))
        self.table_bus.setItem(r, 2, QTableWidgetItem("ch1"))
        self.table_bus.setItem(r, 3, QTableWidgetItem(dir))
        self.table_bus.setItem(r, 4, QTableWidgetItem(f"0x{cid:08X}"))
        self.table_bus.setItem(r, 5, QTableWidgetItem("Data"))
        self.table_bus.setItem(r, 6, QTableWidgetItem("Ext" if ext else "Std"))
        self.table_bus.setItem(r, 7, QTableWidgetItem(str(len(data))))
        self.table_bus.setItem(r, 8, QTableWidgetItem(" ".join([f"{x:02X}" for x in data])))
        if dir == "TX":
            for c in range(9): self.table_bus.item(r, c).setForeground(QBrush(QColor("blue")))
        self.table_bus.scrollToBottom()
        if self.table_bus.rowCount() > 500: self.table_bus.removeRow(0)

    @pyqtSlot(str, float)
    def update_ui_from_can(self, t, v):
        if t == "VOLTAGE": self.lbl_v.setText(f"{v:.2f} V")
        elif t == "CURRENT": self.lbl_i.setText(f"{v:.2f} A")
        elif t == "AC_VIN": self.lbl_ac_vin.setText(f"{v:.2f} V")
        elif t == "TEMP": self.lbl_temp.setText(f"{v/100:.1f} °C") # Giả định mC
        elif t == "FAN": self.lbl_fan.setText(f"{int(v)} RPM")
        elif t == "STATUS":
            st = int(v)
            # Update LEDs: Bit 0: AC, Bit 1: DC, Bit 2: OT, Bit 9: Fan
            self._set_led(self.led_ac, (st >> 0) & 1)
            self._set_led(self.led_dc, (st >> 1) & 1)
            self._set_led(self.led_tem, (st >> 2) & 1)
            self._set_led(self.led_fan, (st >> 9) & 1)
            # Power LED (Bit 25)
            self._set_led(self.led_comm, 0, "green") # Giao tiếp OK

    def _set_led(self, led_widget, error, forced_color=None):
        if forced_color: color = forced_color
        else: color = "red" if error else "green"
        led_widget.setStyleSheet(f"background: {color}; border-radius: 8px; border: 1px solid #000;")

    def closeEvent(self, event): self.can_ctrl.disconnect(); event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv); app.setFont(QFont("Segoe UI", 9))
    window = AcePowerControllerGUI(); window.show(); sys.exit(app.exec_())
