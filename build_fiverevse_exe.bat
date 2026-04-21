@echo off
echo Đang bắt đầu quá trình đóng gói Fiverevse GUI thành file EXE...

:: Xóa các thư mục cũ nếu có
if exist build rd /s /q build

:: Chạy PyInstaller
:: --onefile: Đóng gói thành 1 file duy nhất
:: --noconsole: Không hiện cửa sổ terminal
:: --icon: Sử dụng icon cho file exe
:: --add-data: Đính kèm các file cần thiết (DLL và Hình ảnh)
python -m PyInstaller --noconsole --onefile ^
    --icon="charging-station (1).png" ^
    --add-data "ControlCAN.dll;." ^
    --add-data "charging-station (1).png;." ^
    --name "Fiverevse_CAN_Controller" ^
    fiverevse_gui.py

echo.
echo ========================================================
echo Quá trình đóng gói hoàn tất!
echo File EXE nằm trong thư mục: dist\Fiverevse_CAN_Controller.exe
echo ========================================================
