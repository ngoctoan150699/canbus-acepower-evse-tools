# 📖 Hướng dẫn Giao thức CAN: AcePower AB-U2T / MIDA U2T-A030B-X

File này mô tả chi tiết cấu trúc Frame và quy trình logic để điều khiển module nguồn. Agent cần đọc kỹ các quy tắc này trước khi thực hiện bất kỳ lệnh CAN nào.

## 1. Cấu hình Lớp Vật lý
*   **Baudrate**: 125 Kbps.
*   **Định dạng ID**: 29-bit Extended ID.
*   **Thứ tự Byte (Endianness)**: Big Endian (Motorola) cho tất cả các giá trị 32-bit (Bytes 4-7).

## 2. Quy tắc Định danh (ID Mapping)
Mọi ID được cấu trúc theo phân đoạn bit. Công thức tính ID:
*   **Gửi (Request)**: `0x02200000 | (ModuleAddr << 14)`
*   **Nhận (Response)**: `0x03210000 | (ModuleAddr << 14)`
*Ví dụ: Module địa chỉ 1 -> ID Gửi: 0x02204000, ID Nhận: 0x03214000.*

## 3. Quy trình Vận hành Frame (State Machine)
Để module xuất điện an toàn, **bắt buộc** phải tuân theo thứ tự:

1.  **Set V/I (Standby)**: Gửi lệnh `10 02` (Voltage) và `10 03` (Current). Lúc này module chưa ra điện.
2.  **Power ON**: Gửi lệnh `10 04` với Byte 7 = `0x00`. Module bắt đầu đóng relay và xuất điện.
3.  **Polling (Monitoring)**: Duy trì gửi lệnh Read `12 08` (Status) định kỳ. Nếu không có Polling, module có thể tự ngắt.
4.  **Power OFF**: Gửi lệnh `10 04` với Byte 7 = `0x01`.

## 4. Quy tắc Mã hóa Dữ liệu (Data Encoding)
Tất cả các tham số đo lường đều sử dụng hệ số **x1000** (milli-units):
*   **Điện áp (V)**: Đơn vị mV. Ví dụ 500V = 500,000 (`0x0007A120`).
*   **Dòng điện (A)**: Đơn vị mA. Ví dụ 10A = 10,000 (`0x00002710`).
*   **Nhiệt độ (T)**: Đơn vị m℃. Ví dụ 25.5°C = 25,500 (`0x0000639C`).

## 5. Bóc tách chi tiết từng Frame (Payload Analysis)

### A. Nhóm lệnh Cài đặt (Byte 0 = 0x10)
| Chức năng | Byte 1 | Byte 2-3 | Byte 4-7 (Dữ liệu 32-bit) |
| :--- | :--- | :--- | :--- |
| **Set Voltage** | `0x02` | `0x00` | Giá trị điện áp tính bằng **mV** |
| **Set Current** | `0x03` | `0x00` | Giá trị dòng điện tính bằng **mA** |
| **Power ON/OFF**| `0x04` | `0x00` | `0x00` (Bật) hoặc `0x01` (Tắt) |

### B. Nhóm lệnh Đọc (Byte 0 = 0x12)
| Chức năng | Byte 1 | Mục tiêu |
| :--- | :--- | :--- |
| **Read Voltage** | `0x00` | Yêu cầu module gửi điện áp DC thực tế |
| **Read Current** | `0x01` | Yêu cầu module gửi dòng điện DC thực tế |
| **Read Status**  | `0x08` | Yêu cầu module gửi Bitmask lỗi (AC/DC/Temp/Fan) |
| **Read AC Vin**  | `0x14` | Yêu cầu module gửi điện áp AC đầu vào |
| **Read Temp**    | `0x1E` | Yêu cầu module gửi nhiệt độ Inlet |

### C. Nhóm phản hồi từ Module (Byte 0 = 0x13)
*Dữ liệu thực tế nằm ở Byte 4-7 (32-bit Big Endian).*
*   **Voltage/Current/Temp**: Lấy dữ liệu chia cho 1000.
*   **Status**: Giải mã Bitmask lỗi (Xem phần 6).

## 6. Giải mã trạng thái Lỗi (Status Bitmask 0x08)
Dữ liệu 32-bit từ lệnh `0x13 08` (Byte 4-7):
*   **Bit 0**: Lỗi AC Input. | **Bit 1**: Lỗi DC Output. | **Bit 2**: Quá nhiệt (OT).
*   **Bit 9**: Lỗi Quạt. | **Bit 25**: Trạng thái chạy (0 = ON, 1 = OFF).

## 7. Tra cứu nhanh: Các Frame cụ thể cho Module 1 (Addr 0x01)
*Sử dụng ID gửi: `0x02204000` | ID phản hồi: `0x03214000`*

| Chức năng | Frame Data (Hex) | Giải thích |
| :--- | :--- | :--- |
| **Cài áp 450V** | `10 02 00 00 00 06 DD D0` | 450,000 mV |
| **Cài dòng 10A** | `10 03 00 00 00 00 27 10` | 10,000 mA |
| **Mở nguồn (ON)**| `10 04 00 00 00 00 00 00` | Xuất điện áp DC |
| **Tắt nguồn (OFF)**| `10 04 00 00 00 00 00 01` | Ngắt điện áp DC |
| **Đọc Nhiệt độ** | `12 1E 00 00 00 00 00 00` | Phản hồi ví dụ: `13 1E 00 00 00 00 63 9C` (25.5°C) |

## 8. Phương pháp Điều khiển Nâng cao

### Cách A: Cài đặt Hi/Lo Mode thủ công (Dùng khi Module đang OFF)
Để chuyển đổi dải áp (ví dụ lên mức >500V), bạn phải gửi lệnh `0x95`:
1.  **Bắt buộc Tắt nguồn**: `10 04 00 00 00 00 00 01`
2.  **Set Mode (`0x95`)**: `10 95 00 00 00 00 00 [1:Hi / 2:Lo / 3:Auto]`
3.  Cài áp (`10 02`) và Bật nguồn (`10 04`).

### Cách B: Lệnh tổng hợp AllSetData (MessageType 11 / 0x0B)
Gửi 1 Frame cấu hình tất cả. **LƯU Ý: Đơn vị là 0.1V / 0.1A**.
*   **Byte 0**: `0x0B` (hoặc `0x1B` tùy GroupAddress).
*   **Byte 1 (Config)**: `0x00` (On-Hi), `0x01` (Off), `0x02` (On-Lo).
*   **Byte 2-3**: Dòng giới hạn (đơn vị 0.1A).
*   **Byte 4-5**: Điện áp Pin (đơn vị 0.1V).
*   **Byte 6-7**: Điện áp đích (đơn vị 0.1V).

---
**LƯU Ý QUAN TRỌNG**: 
* Nhiệt độ (Command `0x1E`) **phải chia cho 1000** để ra độ C.
* Tuyệt đối không nhầm lẫn giữa đơn vị **mV** (lệnh đơn) và **0.1V** (lệnh AllSetData).
