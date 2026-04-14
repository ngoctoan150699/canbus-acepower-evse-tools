# AcePower U2T-A030A-AG CAN Protocol Specification (Simulator Guide)

Tài liệu này hướng dẫn các frame CAN cụ thể để mô phỏng một module nguồn AcePower thực thụ, bao gồm cách gửi thông số (Áp, Dòng) và cách giả lập các mã lỗi (Faults) về ứng dụng quản lý.

## 1. Cấu trúc CAN ID (29-bit Extended)

Mọi Frame giao tiếp với AcePower đều sử dụng định dạng **29-Bit Extended ID**.

*   **ID từ PC (Request)**: `0x02200000 | (ModuleAddr << 14)`
*   **ID từ Module (Response)**: `0x03210000 | (ModuleAddr << 14)`

> [!TIP]
> Nếu Module Address là **1**, ID phản hồi sẽ là: `0x03214000`.

---

## 2. Định dạng dữ liệu (Payload - 8 Bytes)

Mọi phản hồi từ Module (Simulator) về PC phải có cấu trúc:
`[Byte 0] [Byte 1] [00] [00] [Data 0] [Data 1] [Data 2] [Data 3]`

*   **Byte 0**: Luôn là `0x13` (Mã phản hồi lệnh đọc).
*   **Byte 1**: Mã lệnh (Command Type).
*   **Byte 4-7**: Giá trị dữ liệu (32-bit Signed/Unsigned, Big Endian).

---

## 3. Bảng tra cứu Frame phản hồi (Dành cho Simulator)

Dưới đây là các frame cụ tại mà Simulator cần gửi về PC để cập nhật Dashboard:

| Thông số | Lệnh (Byte 1) | Ví dụ Frame (Dành cho Module ID 1) | Giải thích |
| :--- | :--- | :--- | :--- |
| **Điện áp ra** | `0x00` | `13 00 00 00 00 01 86 A0` | Trả về 100.000 mV (100V) |
| **Dòng điện ra** | `0x01` | `13 01 00 00 00 00 27 10` | Trả về 10.000 mA (10A) |
| **Áp AC vào** | `0x14` | `13 14 00 00 00 03 5B 60` | Trả về 220.000 mV (220V) |
| **Nhiệt độ** | `0x1E` | `13 1E 00 00 00 00 0F A0` | Trả về 4000 m℃ (40°C) |
| **Tốc độ Quạt**| `0x78` | `13 78 00 00 00 00 13 88` | Trả về 5000 RPM |
| **Trạng thái OK**| `0x08` | `13 08 00 00 00 00 00 00` | Module đang ON, không lỗi |

---

## 4. Giả lập Lỗi (Status Bitmask - Command 0x08)

Để App chính hiển thị đèn Đỏ (LED Fault), bạn cần gửi frame `0x13 08 ...` với các bit lỗi được bật trong 4 byte dữ liệu cuối (`Byte 4-7`).

### Cấu trúc Bitmask lỗi (Byte 4-7):
| Bit | Ý nghĩa | Hành động trên App chính |
| :--- | :--- | :--- |
| **Bit 0** | AC Input Fault | Đèn "Lỗi AC Input" chuyển sang Đỏ |
| **Bit 1** | DC Output Fault | Đèn "Lỗi DC Output" chuyển sang Đỏ |
| **Bit 2** | Over Temperature | Đèn "Quá nhiệt (OT)" chuyển sang Đỏ |
| **Bit 9** | Fan Fault | Đèn "Lỗi Quạt (Fan)" chuyển sang Đỏ |
| **Bit 25**| Power Status | 0 = Power ON, 1 = Power OFF |

### Các Frame mẫu giả lập lỗi (Module ID 1):

*   **Lỗi AC Đầu vào**:
    `ID: 0x03214000 | DATA: 13 08 00 00 00 00 00 01`
*   **Lỗi Quạt (Fan Error)**:
    `ID: 0x03214000 | DATA: 13 08 00 00 00 00 02 00` (0x200 = Bit 9)
*   **Lỗi Hệ thống (AC + DC + Quá nhiệt)**:
    `ID: 0x03214000 | DATA: 13 08 00 00 00 00 00 07` (1+2+4 = Bit 0,1,2)
*   **Trạng thái Tắt (Shutdown)**:
    `ID: 0x03214000 | DATA: 13 08 00 00 02 00 00 00` (Bit 25 = 1)

---

## 5. Cách sử dụng Manual Send trên Simulator

Trong App Simulator, bạn có thể nhập các frame này vào phần **Manual Response** để kiểm tra App chính:
1. Nhập ID: `03214000`
2. Nhập Data: `13 08 00 00 00 00 02 01` (Ví dụ: Lỗi AC + Lỗi Quạt)
3. Bấm **Send**: App chính sẽ ngay lập tức cập nhật trạng thái đèn tương ứng.

---

> [!IMPORTANT]
> Lưu ý rằng các giá trị thông số (V, I, AC) đều được tính theo đơn vị cơ bản x1000 (ví dụ 1V = 1000). Giá trị nhiệt độ tính theo m℃.
