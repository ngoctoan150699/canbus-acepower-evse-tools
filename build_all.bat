@echo off
echo Đang đóng gói tất cả 3 ứng dụng...

:: Đóng gói Fiverevse Controller
call build_fiverevse_exe.bat

:: Đóng gói AcePower Main Controller
call build_acepower_main_exe.bat

:: Đóng gói AcePower Simulator
call build_acepower_sim_exe.bat

echo.
echo ========================================================
echo Tất cả các ứng dụng đã được đóng gói vào thư mục dist!
echo 1. Fiverevse_CAN_Controller.exe
echo 2. AcePower_Main_Controller.exe
echo 3. AcePower_Module_Simulator.exe
echo ========================================================
pause
