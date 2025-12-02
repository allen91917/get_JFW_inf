#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡易打包腳本 - 一鍵打包成 exe
"""

import os
import shutil
import subprocess
from pathlib import Path

# 設定
EXE_NAME = "JFW資訊抓取工具"
MAIN_SCRIPT = "Get_GFW_Inf.py"

def main():
    base_dir = Path(__file__).parent
    
    print("🚀 開始打包...")
    
    # 1. 清理舊檔案
    print("\n🧹 清理舊檔案...")
    for folder in ["build", "dist", "__pycache__"]:
        if (base_dir / folder).exists():
            shutil.rmtree(base_dir / folder)
    for file in [f"{EXE_NAME}.spec"]:
        if (base_dir / file).exists():
            (base_dir / file).unlink()
    
    # 2. 執行 PyInstaller
    print("\n📦 執行 PyInstaller...")
    cmd = [
        "pyinstaller",
        "--onefile",                    # 單一檔案
        "--clean",                      # 清理暫存
        "--noconfirm",                  # 不詢問
        f"--name={EXE_NAME}",           # exe 名稱
        MAIN_SCRIPT
    ]
    
    subprocess.run(cmd, cwd=str(base_dir), check=True)
    
    # 3. 複製必要檔案到 dist
    print("\n📋 複製檔案...")
    dist_dir = base_dir / "dist"
    for file in ["用戶資訊.txt", "說明.md"]:
        if (base_dir / file).exists():
            shutil.copy2(base_dir / file, dist_dir / file)
            print(f"  ✔ {file}")
    
    # 4. 清理暫存檔案
    print("\n🧹 清理暫存檔案...")
    if (base_dir / "build").exists():
        shutil.rmtree(base_dir / "build")
    if (base_dir / f"{EXE_NAME}.spec").exists():
        (base_dir / f"{EXE_NAME}.spec").unlink()
    
    # 5. 完成
    print("\n" + "=" * 50)
    print("🎉 打包完成！")
    print("=" * 50)
    print(f"\n📦 輸出位置: {dist_dir}")
    print("\n📝 dist 資料夾內容:")
    for item in dist_dir.iterdir():
        print(f"  • {item.name}")
    print("\n⚠️  記得將 Windows 版 chromedriver.exe 放入 dist 資料夾！")

if __name__ == "__main__":
    main()
