# AcePower U2T-A030A-AG CAN Protocol Specification (Simulator Guide)

Tài liệu này hướng dẫn các frame CAN cụ thể để mô phỏng một module nguồn AcePower thực thụ, bao gồm cách gửi thông số (Áp, Dòng) và cách giả lập các mã lỗi (Faults) về ứng dụng quản lý.

## 1. Cấu trúc CAN ID (29-bit Extended)

Mọi Frame giao tiếp với AcePower đều sử dụng định dạng **29-Bit Extended ID**.

*   **ID từ PC (Request)**: `0x02200000 | (ModuleAddr << 14)`
*   **ID từ Module (Response)**: `0x03210000 | (ModuleAddr << 14)`

> [!TIP]
> Nếu Module Address là **1**: 
> * ID gửi lệnh từ PC là: `0x02204000`
> * ID phản hồi từ Module là: `0x03214000`

---

## 2. Các lệnh Điều khiển & Cài đặt từ App (PC -> Module)

Đây là các lệnh dùng để thiết lập thông số cho Module hoạt động. Mọi thiết lập cài đặt sử dụng **Byte 0 = `0x10`**. Đơn vị điện áp là **mV** và dòng điện là **mA**.

| Lệnh Điều Khiển | Byte 1 | Ví dụ Frame (Dành cho Module ID 1) | Giải thích chi tiết |
| :--- | :--- | :--- | :--- |
| **Cài đặt Điện áp** | `0x02` | `10 02 00 00 00 07 41 9E` | Cài đặt 475.550 mV (475.55V). Giá trị Hex là `0x0007419E` nằm ở 4 byte cuối. |
| **Cài đặt Dòng giới hạn** | `0x03` | `10 03 00 00 00 00 29 04` | Cài đặt 10.500 mA (10.5A). Giá trị Hex là `0x00002904` nằm ở 4 byte cuối. |
| **Bật Module (Power ON)** | `0x04` | `10 04 00 00 00 00 00 00` | Bật module để cấp phát điện DC. Giá trị `0x00` ở Byte cuối. |
| **Tắt Module (Power OFF)** | `0x04` | `10 04 00 00 00 00 00 01` | Tắt output DC. Giá trị `0x01` ở Byte cuối. |

> [!NOTE]
> ID Frame gửi các lệnh Set này là ID từ PC. Ví dụ với Module 1: `ID = 0x02204000`.

---

## 3. Các lệnh Yêu cầu đọc trạng thái từ App (PC -> Module)

Để Module (hoặc Simulator) biết và gửi trạng thái về, PC sẽ định kỳ gửi các log yêu cầu. Các frame yêu cầu này sử dụng **Byte 0 = `0x12`**.

| Trạng thái cần đọc | Byte 1 | Data (Các byte còn lại = 0x00) |
| :--- | :--- | :--- |
| **Đọc Điện áp ra** | `0x00` | `12 00 00 00 00 00 00 00` |
| **Đọc Dòng điện ra** | `0x01` | `12 01 00 00 00 00 00 00` |
| **Đọc Trạng thái chung/Lỗi** | `0x08` | `12 08 00 00 00 00 00 00` |
| **Đọc Áp AC vào** | `0x14` | `12 14 00 00 00 00 00 00` |
| **Đọc Nhiệt độ** | `0x1E` | `12 1E 00 00 00 00 00 00` |

---

## 4. Phản hồi thông số từ Module (Simulator -> PC)

Đối với phần khai báo định dạng dữ liệu (Payload - 8 Bytes), mọi phản hồi từ Module (Simulator) về PC phải có cấu trúc như sau:
`[Byte 0] [Byte 1] [00] [00] [Data 0] [Data 1] [Data 2] [Data 3]`

*   **Byte 0**: Luôn là `0x13` (Mã phản hồi từ module khi nhận được yêu cầu `0x12`).
*   **Byte 1**: Mã lệnh (Command Type) khớp với cái PC đã yêu cầu.
*   **Byte 4-7**: Giá trị dữ liệu cụ thể (32-bit Signed/Unsigned, Big Endian).

Dưới đây là các frame mà Simulator cần gửi về PC để cập nhật Dashboard:

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
