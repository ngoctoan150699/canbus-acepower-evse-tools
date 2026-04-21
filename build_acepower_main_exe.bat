@echo off
echo Đang bắt đầu quá trình đóng gói AcePower Main GUI thành file EXE...

if exist build rd /s /q build

python -m PyInstaller --noconsole --onefile ^
    --icon="charging-station.png" ^
    --add-data "ControlCAN.dll;." ^
    --add-data "charging-station.png;." ^
    --name "AcePower_Main_Controller" ^
    main_gui.py

echo.
echo ========================================================
echo Hoàn tất! File EXE: dist\AcePower_Main_Controller.exe
echo ========================================================
