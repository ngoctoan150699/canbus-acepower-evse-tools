import sys
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QComboBox, QPushButton, QGroupBox, QLineEdit, QMessageBox,
                             QGridLayout, QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QTabWidget, QSpinBox, QCheckBox, QDoubleSpinBox)
from PyQt5.QtCore import QTimer, pyqtSignal, pyqtSlot, Qt, QDateTime
from PyQt5.QtGui import QFont, QColor, QBrush, QIcon

from acepower_can import AcePowerCANController, BAUDRATE_MAP, DEVICE_TYPES

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

    def init_ui(self):
        self.setWindowTitle('AcePower AB-U2T - Ultimate Controller')
        self.resize(1250, 900)
        
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
        self.tabs.addTab(self.create_ref_tab(), "COMMAND REFERENCE")
        layout.addWidget(self.tabs)

        self.setCentralWidget(central_widget)
        
        self.signal_data_received.connect(self.update_ui_from_can)
        self.signal_tx_log.connect(self.add_log_entry)
        self.signal_bus_monitor.connect(self.add_bus_entry)
        self._toggle_control_state(False)

    def create_control_tab(self):
        tab = QWidget(); l = QVBoxLayout(tab)
        l.setContentsMargins(10, 10, 10, 10)
        
        # Module Info Row
        info_row = QHBoxLayout()
        info_row.addWidget(QLabel("Mục tiêu Điều khiển:"))
        self.combo_module_addr = QComboBox()
        self.combo_module_addr.addItem("0 (TẤT CẢ MODULE - Broadcast)")
        self.combo_module_addr.addItems([str(i) for i in range(1, 32)])
        self.combo_module_addr.setFixedWidth(250)
        info_row.addWidget(self.combo_module_addr)
        info_row.addStretch()
        l.addLayout(info_row)

        mid = QHBoxLayout(); mid.setSpacing(15)
        
        # 1. Control Panel
        g_ctrl = QGroupBox("CÀI ĐẶT GIÁ TRỊ MỤC TIÊU")
        l_ctrl = QVBoxLayout()
        
        # Grid for better alignment
        grid_inputs = QGridLayout()
        
        # Voltage Input
        grid_inputs.addWidget(QLabel("⚡ ĐIỆN ÁP (V):"), 0, 0)
        self.spin_set_v = QDoubleSpinBox()
        self.spin_set_v.setRange(0.00, 1000.00)
        self.spin_set_v.setValue(100.00)
        self.spin_set_v.setSuffix(" V")
        self.spin_set_v.setDecimals(2)
        self.spin_set_v.setFixedHeight(40)
        self.spin_set_v.setFont(QFont("Segoe UI", 12, QFont.Bold))
        grid_inputs.addWidget(self.spin_set_v, 0, 1)
        
        btn_v = QPushButton("SET V"); btn_v.setFixedWidth(80); btn_v.setFixedHeight(40)
        btn_v.clicked.connect(self.action_set_voltage)
        btn_v.setStyleSheet("background: #0d6efd; color: white; border: none; font-weight: bold;")
        grid_inputs.addWidget(btn_v, 0, 2)
        
        # Current Input
        grid_inputs.addWidget(QLabel("🌡 DÒNG ĐIỆN (A):"), 1, 0)
        self.spin_set_i = QDoubleSpinBox()
        self.spin_set_i.setRange(0.00, 125.00)
        self.spin_set_i.setValue(10.00)
        self.spin_set_i.setSuffix(" A")
        self.spin_set_i.setDecimals(2)
        self.spin_set_i.setFixedHeight(40)
        self.spin_set_i.setFont(QFont("Segoe UI", 12, QFont.Bold))
        grid_inputs.addWidget(self.spin_set_i, 1, 1)
        
        btn_i = QPushButton("SET I"); btn_i.setFixedWidth(80); btn_i.setFixedHeight(40)
        btn_i.clicked.connect(self.action_set_current)
        btn_i.setStyleSheet("background: #0d6efd; color: white; border: none; font-weight: bold;")
        grid_inputs.addWidget(btn_i, 1, 2)
        
        l_ctrl.addLayout(grid_inputs)
        
        l_ctrl.addSpacing(20)
        pwr_box = QHBoxLayout()
        self.btn_power_on = QPushButton("⚡ POWER ON"); self.btn_power_on.setFixedHeight(50)
        self.btn_power_on.setStyleSheet("background: #198754; color: white; font-size: 16px; border: none;")
        self.btn_power_on.clicked.connect(self.action_power_on)
        self.btn_power_off = QPushButton("⛔ POWER OFF"); self.btn_power_off.setFixedHeight(50)
        self.btn_power_off.setStyleSheet("background: #dc3545; color: white; font-size: 16px; border: none;")
        self.btn_power_off.clicked.connect(self.action_power_off)
        pwr_box.addWidget(self.btn_power_on, 2)
        pwr_box.addWidget(self.btn_power_off, 1)
        l_ctrl.addLayout(pwr_box)
        g_ctrl.setLayout(l_ctrl)
        mid.addWidget(g_ctrl, 1)
        
        # 2. Monitoring Panel
        g_mon = QGroupBox("TRẠNG THÁI THỰC TẾ")
        l_mon = QVBoxLayout()
        
        f_v = QFrame(); f_v.setStyleSheet("background: #f0f7ff; border: 2px solid #cfe2ff; border-radius: 12px;")
        lv = QVBoxLayout(f_v); lv.addWidget(QLabel("⚡ VOLTAGE OUTPUT"), alignment=Qt.AlignCenter)
        self.lbl_v = QLabel("-- V"); self.lbl_v.setFont(QFont("Digital-7", 50, QFont.Bold))
        self.lbl_v.setStyleSheet("color: #084298"); lv.addWidget(self.lbl_v, alignment=Qt.AlignCenter)
        l_mon.addWidget(f_v)
        
        f_i = QFrame(); f_i.setStyleSheet("background: #fff8eb; border: 2px solid #ffe69c; border-radius: 12px;")
        li = QVBoxLayout(f_i); li.addWidget(QLabel("🌡 CURRENT OUTPUT"), alignment=Qt.AlignCenter)
        self.lbl_i = QLabel("-- A"); self.lbl_i.setFont(QFont("Digital-7", 50, QFont.Bold))
        self.lbl_i.setStyleSheet("color: #997404"); li.addWidget(self.lbl_i, alignment=Qt.AlignCenter)
        l_mon.addWidget(f_i)
        
        g_mon.setLayout(l_mon)
        mid.addWidget(g_mon, 1)
        l.addLayout(mid)

        # 3. Action History
        l.addWidget(QLabel("<b>NHẬT KÝ LỆNH GỬI ĐI:</b>"))
        self.tab_mini_log = QTableWidget(0, 3); self.tab_mini_log.setHorizontalHeaderLabels(["Thời gian", "Frame ID", "Mô tả lệnh"])
        self.tab_mini_log.horizontalHeader().setStretchLastSection(True); self.tab_mini_log.setMinimumHeight(150)
        l.addWidget(self.tab_mini_log)
        return tab

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
        self.combo_device.clear(); self.scanned_devices = []
        dt = DEVICE_TYPES.get(self.combo_type.currentText(), 4)
        try:
            devs = self.can_ctrl.scan_devices(dt)
            if devs:
                self.scanned_devices = devs
                for d in devs: self.combo_device.addItem(d['display'])
                self.btn_connect.setEnabled(True)
                self.combo_device.setStyleSheet("background: #e7f1ff;")
            else: QMessageBox.warning(self, "Không thấy", "Không phát hiện USB-CAN Adapter!")
        except Exception as e: QMessageBox.critical(self, "Lỗi Quét", str(e))

    def on_connect_clicked(self):
        if not self.can_ctrl.connected:
            sel = self.combo_device.currentIndex()
            if sel < 0: return
            dev = self.scanned_devices[sel]; dt = DEVICE_TYPES.get(self.combo_type.currentText(), 4)
            bd = self.combo_baud.currentText(); ch = int(self.combo_type.currentText().split("(")[1][5]) # Quick dirty extract
            try:
                self.can_ctrl.connect(dt, dev['index'], 0, bd) 
                self.btn_connect.setText("NGẮT KẾT NỐI ❌"); self.btn_connect.setStyleSheet("background: #dc3545; color: white;")
                self._ui_lock(True); self._toggle_control_state(True); self.poll_timer.start()
            except Exception as e: QMessageBox.critical(self, "Lỗi Kết Nối", str(e))
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
                if addr == 0: return # Không poll tự động khi ở chế độ Broadcast
                self.can_ctrl.read_voltage(addr); self.can_ctrl.read_current(addr)
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

    def closeEvent(self, event): self.can_ctrl.disconnect(); event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv); app.setFont(QFont("Segoe UI", 9))
    window = AcePowerControllerGUI(); window.show(); sys.exit(app.exec_())
