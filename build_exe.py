import os
import shutil
import subprocess
import sys
import time

def install_requirements():
    print("📦 Installing build requirements...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

def build_exe():
    print("🚀 Starting build process...")
    
    # Define main script and name
    main_script = "main.py"
    app_name = "TradingBot_GeminiX2"
    
    # PyInstaller command
    # --onedir: Create a directory (easier for config updates)
    # --console: Keep console open for logs
    # --name: Executable name
    # --clean: Clean cache
    # --hidden-import: Add necessary hidden imports (pandas, numpy often need help)
    
    cmd = [
        sys.executable, "-m", "PyInstaller",
        main_script,
        "--name", app_name,
        "--onedir", 
        "--console", 
        "--clean",
        "--noconfirm",
        # Hidden imports often missed by PyInstaller
        "--hidden-import", "pandas",
        "--hidden-import", "numpy",
        "--hidden-import", "requests",
        "--hidden-import", "telebot",
        "--hidden-import", "binance",
        "--hidden-import", "ta", 
        "--collect-all", "certifi", # SSL certs
        "--add-data", "vietnamese_messages.py;.",
        "--add-data", "indicators.py;.",
        "--add-data", "database.py;.",
        "--add-data", "binance_client.py;.",
        "--add-data", "telegram_bot.py;.",
        "--add-data", "telegram_commands.py;.",
        "--add-data", "watchlist.py;.",
        "--add-data", "watchlist_monitor.py;.",
        "--add-data", "market_scanner.py;.",
        "--add-data", "bot_detector.py;.",
        "--add-data", "pump_detector_realtime.py;.",
        "--add-data", "gemini_analyzer.py;.",
        "--add-data", "advanced_pump_detector.py;.",
        "--add-data", "volume_profile.py;.",
        "--add-data", "fair_value_gaps.py;.",
        "--add-data", "order_blocks.py;.",
        "--add-data", "support_resistance.py;.",
        "--add-data", "smart_money_concepts.py;.",
        "--add-data", "volume_detector.py;.",
        "--add-data", "bot_monitor.py;.",
        "--add-data", "stoch_rsi_analyzer.py;.",
        "--hidden-import", "babel.numbers"
    ]
    
    print(f"🔨 Running: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    
    print("✅ Build complete.")
    
    # Copy external files to dist folder
    dist_dir = os.path.join("dist", app_name)
    
    files_to_copy = [
        ".env",
        ".env.example",
        "prompt_v3.txt",
        "jsonAi.txt",
        "requirements.txt",
        "gemini_analyzer.py", # Just in case dynamic loading needs it, but usually not for exe
        "vietnamese_messages.py" # Usually bundled, but good for reference
    ]
    
    print("\n📂 Copying config files to output directory...")
    for file in files_to_copy:
        if os.path.exists(file):
            target = os.path.join(dist_dir, file)
            shutil.copy2(file, target)
            print(f"  - Copied {file}")
        else:
            print(f"  ⚠️ Warning: {file} not found")
            
    # Create a simple launcher bat for convenience
    launcher_content = f"""@echo off
echo Starting Trading Bot...
cd /d "%~dp0"
{app_name}.exe
pause
"""
    with open(os.path.join(dist_dir, "Run_Bot.bat"), "w") as f:
        f.write(launcher_content)
    print("  - Created Run_Bot.bat")

    print(f"\n✨ SUCCESS! App located at: {os.path.abspath(dist_dir)}")
    print(f"👉 You can move this '{app_name}' folder anywhere on your desktop.")

if __name__ == "__main__":
    try:
        # Check if pyinstaller is installed
        try:
            import PyInstaller
        except ImportError:
            install_requirements()
            
        build_exe()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        input("Press Enter to exit...")
