# Hướng dẫn Điều khiển Module Sạc Fiverevse (Protocol V2.6)

Tài liệu này trình bày quy trình và các khung lệnh CAN cụ thể để điều khiển module sạc ra điện áp, trích xuất duy nhất từ tài liệu `Fiverevse EV Charger Module CAN BUS Communication Protocol-V2.6.pdf`.

---

## 1. Thông số Kỹ thuật CAN
*   **Baudrate**: 125 kbps.
*   **Định dạng ID**: CAN 2.0B Extended (29-bit).
*   **Cấu trúc CAN ID**:
    *   **Protocol Code (bit 28-22)**: `0x60` (Cố định).
    *   **Destination Address (bit 21-11)**: Địa chỉ Module (VD: `0x001`).
    *   **Source Address (bit 10-0)**: Địa chỉ Controller (Group ID + Subaddress).
    
> [!TIP]
> **Cách tính ID đơn giản**: Nếu bạn dùng ID nguồn mặc định và điều khiển Module 1, bạn có thể thử các ID sau:
> * Gửi từ Controller: `0x1802F001` (hoặc tùy biến theo cấu trúc 0x60 ở đầu).

---

## 2. Quy trình điều khiển ra điện áp (Step-by-Step)

Để module bắt đầu xuất điện áp ra đầu DC, bạn cần thực hiện theo đúng thứ tự 3 bước sau:

### Bước 1: Cài đặt Điện áp đầu ra (Set Output Voltage)
Bạn phải thiết lập mức áp mong muốn trước khi bật nguồn.
*   **Message Type**: `0x03`
*   **Message ID**: `0x0021`
*   **Công thức**: `Giá trị gửi = Điện áp (V) * 10`.
*   **Ví dụ**: Muốn ra **400.0V** -> 4000 (`0x0FA0`).

**👉 Frame Data (Hex)**:
`03 F0 00 21 00 00 0F A0`

---

### Bước 2: Cài đặt Giới hạn Dòng điện (Set Current Limit)
Thiết lập mức dòng tối đa mà module được phép xuất ra.
*   **Message Type**: `0x03`
*   **Message ID**: `0x0022`
*   **Công thức**: `Giá trị gửi = (Dòng yêu cầu / 20A) * 1024`.
*   **Ví dụ**: Muốn giới hạn **20A** (100%) -> 1024 (`0x0400`).

**👉 Frame Data (Hex)**:
`03 F0 00 22 00 00 04 00`

---

### Bước 3: Lệnh Bật nguồn (Boot Command)
Sau khi đã set Áp và Dòng, gửi lệnh Boot để module đóng Relay và xuất điện.
*   **Message Type**: `0x03`
*   **Message ID**: `0x0230` (Dành cho module địa chỉ 1-31).
*   **Logic**: Sử dụng Bitmask. Module 1 tương ứng với Bit 1 của nội dung gửi.
*   **Ví dụ**: Bật duy nhất **Module 1**.

**👉 Frame Data (Hex)**:
`03 F0 02 30 00 00 00 02`

---

## 3. Kiểm tra trạng thái & Mã lỗi (Monitoring)

Khi bạn gửi lệnh truy vấn `50 F0 02 02 00 00 00 00`, module sẽ phản hồi các bản tin trạng thái (Message ID `0x0203` cho DC và `0x0204` cho AC).

### A. Mã lỗi chung (Byte 1 của phản hồi)
*   **`0xF0`**: Bình thường (No error).
*   **`0xF1`**: Sai địa chỉ node.
*   **`0xF2`**: Lệnh không hợp lệ (Invalid command).
*   **`0xF3`**: Lỗi xác thực dữ liệu (Checksum/Verification error).

### B. Các Bit trạng thái quan trọng (Message 0x0203 - DC Status)
Dưới đây là các bit lỗi phổ biến bạn cần kiểm tra ở phần Payload phản hồi:

| Bit | Ý nghĩa (1 = Lỗi / Hoạt động) | Lưu ý |
| :--- | :--- | :--- |
| **Bit 0** | Quá áp đầu ra (Output Overvoltage) | |
| **Bit 1** | Quá nhiệt (Over Temperature) | |
| **Bit 2** | Lỗi phần cứng (Hardware Failure) | |
| **Bit 4** | Lỗi quạt (Fan Failure) | |
| **Bit 9** | Trạng thái ON/OFF | **1 = Đang Tắt**, 0 = Đang Bật |
| **Bit F** | Lỗi giao tiếp CAN | |

### C. Bit sẳn sàng khởi động (DC Status 2 - Message 0x0203)
*   **Bit D (Bit 13)** của Status 2: **Ready to boot**. 
*   Nếu bit này bằng `1`, module đã sẵn sàng để nhận lệnh Boot.

---

## 4. Lệnh Tắt nguồn (Shutdown)
Để ngắt điện áp đầu ra ngay lập tức:
*   Gửi lại lệnh ở Bước 3 nhưng đặt Bit tương ứng về `0`.
*   **Ví dụ Tắt Module 1**: `03 F0 02 30 00 00 00 00`

> [!CAUTION]
> **Quy trình chuyên nghiệp**: Trước khi gửi lệnh Boot (Bước 3), bạn nên gửi lệnh Query và kiểm tra **Bit 13 (Ready to boot)**. Chỉ khi module báo sẵn sàng mới thực hiện bật nguồn để tránh hỏng hóc hoặc báo lỗi giả.
