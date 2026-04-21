@echo off
echo Đang bắt đầu quá trình đóng gói AcePower Module Simulator thành file EXE...

if exist build rd /s /q build

python -m PyInstaller --noconsole --onefile ^
    --icon="charging-station.png" ^
    --add-data "ControlCAN.dll;." ^
    --add-data "charging-station.png;." ^
    --name "AcePower_Module_Simulator" ^
    module_sim_gui.py

echo.
echo ========================================================
echo Hoàn tất! File EXE: dist\AcePower_Module_Simulator.exe
echo ========================================================
