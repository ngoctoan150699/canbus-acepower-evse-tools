import os
import subprocess
import sys

def build():
    print("--- Starting Build Process ---")
    
    # 1. Install PyInstaller if not present
    try:
        import PyInstaller
        print("PyInstaller is already installed.")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Base commands for PyInstaller
    common_args = [
        "--onefile",
        "--windowed",
        "--add-data", "ControlCAN.dll;.",
        "--add-data", "charging-station.png;.",
        "--icon", "charging-station.png",
        "--clean"
    ]

    # 2. Build Controller
    print("\n--- Building AcePower Ultimate Controller ---")
    cmd_ctrl = [sys.executable, "-m", "PyInstaller"] + common_args + [
        "--name", "AcePower_Ultimate_Controller",
        "main_gui.py"
    ]
    subprocess.check_call(cmd_ctrl)

    # 3. Build Simulator
    print("\n--- Building AcePower Simulator ---")
    cmd_sim = [sys.executable, "-m", "PyInstaller"] + common_args + [
        "--name", "AcePower_Simulator",
        "module_sim_gui.py"
    ]
    subprocess.check_call(cmd_sim)
    
    print("\n--- Build Successful! ---")
    print(f"Output files in 'dist' folder:")
    print(f"1. dist/AcePower_Ultimate_Controller.exe")
    print(f"2. dist/AcePower_Simulator.exe")

if __name__ == "__main__":
    build()
