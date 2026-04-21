# Tài liệu Tham khảo Lệnh Điều khiển Mở rộng - AcePower U2T-A030A-AG (và U2T-A040B)

Tài liệu này bổ trợ các cụm frame điều khiển (Control Frames) nâng cao và chi tiết định dạng gói tin điều khiển module chỉnh lưu AcePower (Rectifier module) chuẩn xác nhất dựa trên tài liệu Protocol chính thức của hãng (tích hợp từ hệ thống NotebookLM).

Thông thường các tài liệu CAN module công nghiệp chuyên dụng không có sẵn phổ biến trên Internet vì nó thuộc tài liệu kỹ thuật bảo mật của hãng sản xuất AcePower, do đó tôi đã trích xuất từ hệ thống NotebookLM để cung cấp cho bạn cấu trúc lệnh tốt nhất.

**Cấu trúc CAN ID Chung (Baudrate 125kbps):**
*   **ID Broadcast (Gửi tất cả module)**: `0x02000000`
*   **ID Gửi cụ thể (VD cho Module 1)**: `0x02204000` *(Protocol=1, Monitor=1, Module=1)*

---

## 1. Lệnh Đa thông số tối ưu (AllSetData Command)

Trong thực tế thi công trạm EVSE lớn, đôi khi cần tiết kiệm băng thông CAN. Lệnh `AllSetData` cho phép bạn gửi **dòng điện, điện áp ắc quy, điện áp đầu ra và điều khiển trạng thái bật/tắt chỉ trong 1 frame duy nhất**.

*   **Byte 0**: `0x1B` *(Giải thích: Group 1 [0x10] + Message Type AllSetData [0x0B])*
*   **Byte 1 (Bật/Tắt & Hi/Lo Mode)**:
    *   `0x00`: Turn On DC (Bật thiết bị bình thường)
    *   `0x01`: Shut Down DC (Tắt thiết bị)
    *   `0x02`: Turn On DC & PFC
    *   `0x03`: Shut Down DC & PFC
*   **Byte 2-3**: Dòng điện giới hạn (Đơn vị tính: **0.1A**).
*   **Byte 4-5**: Điện áp pin/ắc quy tham chiếu (Đơn vị tính: **0.1V**).
*   **Byte 6-7**: Điện áp khởi tạo đầu ra (Đơn vị tính: **0.1V**).

**👉 Ví dụ Frame (Bật Module chạy 10.5A, 475.5V):**
Bật phát DC (Byte 1 = `00`).
Cài đặt dòng 10.5A (10.5 * 10 = 105 = `0x0069`).
Cài điện áp pin 470.5V (470.5 * 10 = 4705 = `0x1261`).
Cài điện áp đầu ra 475.5V (475.5 * 10 = 4755 = `0x1293`).
> **ID Frame**: `0x02204000`
> **Data (Hex)**: `1B 00 00 69 12 61 12 93`

---

## 2. Các Lệnh Cấu hình Nâng cao Đơn lẻ (Byte 0 = 0x10)

Đây là các lệnh cài đặt đơn lẻ, gửi bằng Byte 0 = `0x10`. Đối với các lệnh này, phần Payload chính sẽ là một chuỗi 32-bit (4 Byte phần cuối) tính bằng đơn vị **mV / mA**.

### 2.1. Lệnh Tắt Tuyến Tính làm mềm (Linear-Off)
Khác với việc ngắt DC đột ngột (`10 04 ... 01`), bạn có thể ra lệnh tắt dòng từ từ (linear-off @ 150A/s) nhằm bảo vệ tuổi thọ relay tải.
*   **Byte 1 (Command)**: `0x04`
*   **Byte 4-7 (Dữ liệu)**: `0x11` (Decimal 17).

**👉 Ví dụ Frame Linear-Off:**
> **ID Frame**: `0x02204000`
> **Data (Hex)**: `10 04 00 00 00 00 00 11`

### 2.2. Điều khiển Mức độ Ồn Nhẹ của Quạt (Fan Silent Level)
Hãng chặn việc người dùng fix cứng số vòng xoay RPM. Thay vào đó cấu hình quạt chỉ Read-only (Mã đọc tốc độ 120, 121, 122). Nếu trạm đặt gần khu dân cư cần tối ưu chống ồn, bạn phải truyền cài đặt chế độ tiếng ồn.
*   **Byte 1 (Command)**: `0x3E` (Command Dec: 62).
*   **Thang đo (Byte 4-7)**:
    *   `0` (`00 00 00 00`): Standard Mode (Cơ bản chạy Max tốc)
    *   `10` (`00 00 00 0A`): Silent mode (Ngưỡng 60dB)
    *   `30` (`00 00 00 1E`): Silent mode (Ngưỡng 50dB)
    *   `50` (`00 00 00 32`): Super Silent mode (Ngưỡng 40dB)

**👉 Ví dụ SET Quạt chạy siêu êm 40dB:**
> **ID Frame**: `0x02204000`
> **Data (Hex)**: `10 3E 00 00 00 00 00 32`

---

## 3. Bản lưu tóm tắt Frame Chạy chuẩn cho Code
Khi bạn lập trình C/C++ (STM32) hoặc Python để bắn bản tin ra trạm ngoài đời thực, hãy sử dụng chính xác luồng này:

1. **Khởi tạo trạm (`Broadcast Voltage`)**: `ID: 0x02000000 | DATA: 10 02 00 00 00 07 41 9E` (Set all module 475.5V)
2. **Khởi tạo dòng (`Broadcast Current`)**: `ID: 0x02000000 | DATA: 10 03 00 00 00 00 29 04` (Set all module 10.5A)
3. **Bắn lệnh mở nguồn (`Power ON`)**: `ID: 0x02204000 | DATA: 10 04 00 00 00 00 00 00` (Turn ON Module 1)
4. **Vòng lặp đọc trạng thái (`Read loop`)**: Bắn `12 08 00 00 00 00 00 00` định kỳ (mỗi 500ms) để nhận mã trạng thái `13 08...` từ Module.
