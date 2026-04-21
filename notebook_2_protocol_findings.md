# Phân tích Giao thức CAN từ NotebookLM (Link 2) - 30kW V2G & 40kW Module

Dựa trên NotebookLM mới bạn cung cấp (`555350cd...`), tôi đã trích xuất các thông tin quan trọng. Lưu ý rằng notebook này chứa nhiều tài liệu từ các hãng khác nhau (Fiverevse, ACES Energy, Tonhe). Dưới đây là các khung lệnh điều khiển module nguồn tìm thấy trong đó:

---

## 1. Giao thức Fiverevse (Fiver) - Chi tiết từ PDF V2.6
Đây là thông tin trích dẫn trực tiếp từ file `Fiverevse EV Charger Module CAN BUS Communication Protocol-V2.6.pdf` bạn vừa cung cấp.

*   **Baudrate**: 125kbps.
*   **Cấu trúc CAN ID (29-bit Extended)**:
    *   **Protocol Code (7 bits)**: Cố định là `0x60`.
    *   **Destination Address (11 bits)**: Địa chỉ đích (Module sạc).
    *   **Source Address (11 bits)**: Địa chỉ nguồn (với Group: 5 bits và Subaddress: 6 bits).

### A. Lệnh Thiết lập (Message Type: Byte 0 = `0x03`)
Mọi lệnh Set sử dụng: **Byte 0 = `0x03`**, **Byte 1 = `0xF0`** (No error).

| Chức năng | Message ID (Byte 2-3) | Logic / Đơn vị | Ví dụ Hex Data (8 Bytes) |
| :--- | :--- | :--- | :--- |
| **Cài đặt Điện áp** | `0x00 0x21` | Giá trị * 10 (0.1V) | `03 F0 00 21 00 00 11 94` (Set 450.0V) |
| **Cài đặt Dòng giới hạn** | `0x00 0x22` | `(Dòng / 20A) * 1024` | `03 F0 00 22 00 00 08 00` (Set 40A) |
| **Bật/Tắt (Boot/Shutdown)**| `0x02 0x30` | Bitmask (Module 1 = bit 1) | `03 F0 02 30 00 00 00 02` (Bật Module 1) |

> [!IMPORTANT]
> **Về V2G/Xả điện**: Tài liệu V2.6 này confirm chỉ dành cho các module sạc DC **đơn hướng (unidirectional)**. Không có bất kỳ lệnh nào liên quan đến Xả (Discharge), V2G hay V2H trong protocol V2.6 này.

### B. Lệnh Truy vấn (Message Type: Byte 0 = `0x50`)
Dùng để đọc tất cả trạng thái của module (Điện áp, dòng điện thực tế, mã lỗi).
*   **Message ID**: `0x0202` (Comprehensive query).
*   **Ví dụ Hex**: `50 F0 02 02 00 00 00 00`

---

## 2. Giao thức GB/T 27930 (BMS to Charger)
Đây là giao thức tiêu chuẩn quốc gia của Trung Quốc dùng cho việc giao tiếp giữa xe (BMS) và bộ sạc (CCS). Các module AcePower/Tonhe đời mới thường hỗ trợ hoặc được điều khiển qua cổng gateway dùng chuẩn này.

*   **Baudrate**: 250kbps.
*   **ID Định dạng**: J1939 (29-bit).

### A. Lệnh Thiết lập từ BMS (Gửi xuống Bộ sạc)
*   **CAN ID**: `0x1806E5F4`
*   **Dữ liệu (8 Bytes)**:
    *   **Byte 0-1**: Điện áp sạc tối đa cho phép (0.1V/bit, Little Endian).
    *   **Byte 2-3**: Dòng điện sạc tối đa cho phép (0.1A/bit, Offset -400, hoặc 0.1A trực tiếp tùy phiên bản).
    *   **Byte 4**: Lệnh điều khiển (0: Mở sạc, 1: Ngắt sạc).

### B. Frame Phản hồi trạng thái (Bộ sạc gửi lên)
*   **CAN ID**: `0x18FF50E5`
*   **Dữ liệu (8 Bytes)**:
    *   **Byte 0-1**: Điện áp đầu ra thực tế (0.1V).
    *   **Byte 2-3**: Dòng điện đầu ra thực tế (0.1A).
    *   **Byte 4**: Trạng thái (Bit 0: Lỗi phần cứng, Bit 1: Quá nhiệt, Bit 2: Lỗi kết nối).

---

## 3. Thông tin về AcePower 30kW V2G (Sơ bộ)
Tài liệu trong notebook xác nhận Module 30kW V2G có khả năng **Xả (Discharge)** với các chế độ:
*   **Chế độ 2**: DC-AC Off-grid (Xả độc lập)
*   **Chế độ 3**: DC-AC Grid-Tied (Xả hòa lưới)
*   **Chế độ 4**: AC-DC Bidirectional (Sạc/Xả 2 chiều)

> [!WARNING]
> Tài liệu kỹ thuật cụ thể (Manual) về Byte lệnh để kích hoạt Xả (Discharge) cho AcePower V2G **không có sẵn trực tiếp** trong notebook này (chỉ có bảng thông số phần cứng).

---

## 3. So sánh & Khuyến nghị
| Đặc điểm | Giao thức cũ (Module_protocol_docs) | Giao thức Fiver (Notebook 2) |
| :--- | :--- | :--- |
| **Byte 0** | `0x10` (Set), `0x12` (Read) | `0x03` (Set), `0x50` (Query) |
| **Đơn vị Áp** | **mV** (1V = 1000) | **0.1V** (1V = 10) |
| **Đơn vị Dòng**| **mA** (1A = 1000) | **%** (Tính theo dòng base 20A) |

**Cần xác nhận**: Bạn hãy thử bắn lệnh `12 08 00 00 00 00 00 00` (ở file cũ). Nếu module **không phản hồi**, hãy chuyển sang thử giao thức Fiver này với lệnh Query trạng thái `50 F0 00 00 00 00 00 00`.

Nếu bạn có thêm file PDF manual cụ thể của dòng V2G này, hãy tải lên NotebookLM đó, tôi sẽ đọc được ngay lập tức các mã hex xả điện cho bạn!
