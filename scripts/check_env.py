#!/usr/bin/env python3
"""
環境檢查腳本
用於檢查 RPS Calculator 專案的環境設置是否正確
"""

import sys
import subprocess
import importlib
from pathlib import Path

def check_python_version():
    """檢查 Python 版本"""
    print("🐍 檢查 Python 版本...")
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - 符合要求")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - 需要 Python 3.9+")
        return False

def check_pip():
    """檢查 pip 是否可用"""
    print("\n📦 檢查 pip...")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ pip 可用: {result.stdout.strip()}")
            return True
        else:
            print("❌ pip 不可用")
            return False
    except Exception as e:
        print(f"❌ 檢查 pip 時發生錯誤: {e}")
        return False

def check_backend_dependencies():
    """檢查後端依賴"""
    print("\n🔧 檢查後端依賴...")
    dependencies = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "numpy",
        "scipy",
        "python-dotenv"
    ]
    
    missing = []
    for dep in dependencies:
        try:
            importlib.import_module(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} - 未安裝")
            missing.append(dep)
    
    if missing:
        print(f"\n⚠️  缺少依賴: {', '.join(missing)}")
        print("請執行: pip install -r backend/requirements.txt")
        return False
    else:
        print("✅ 所有後端依賴都已安裝")
        return True

def check_backend_structure():
    """檢查後端目錄結構"""
    print("\n📁 檢查後端目錄結構...")
    backend_path = Path("backend")
    required_files = [
        "app/main.py",
        "app/core/config.py",
        "app/api/v1/routes_simulate.py",
        "app/domain/strategies.py",
        "requirements.txt"
    ]
    
    missing = []
    for file_path in required_files:
        full_path = backend_path / file_path
        if full_path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 不存在")
            missing.append(file_path)
    
    if missing:
        print(f"\n⚠️  缺少文件: {', '.join(missing)}")
        return False
    else:
        print("✅ 後端目錄結構完整")
        return True

def check_frontend_structure():
    """檢查前端目錄結構"""
    print("\n📁 檢查前端目錄結構...")
    required_files = [
        "package.json",
        "vite.config.js",
        "src/App.jsx",
        "src/lib/api.js"
    ]
    
    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - 不存在")
            missing.append(file_path)
    
    if missing:
        print(f"\n⚠️  缺少文件: {', '.join(missing)}")
        return False
    else:
        print("✅ 前端目錄結構完整")
        return True

def check_node_npm():
    """檢查 Node.js 和 npm"""
    print("\n🟢 檢查 Node.js 和 npm...")
    
    # 檢查 Node.js
    try:
        result = subprocess.run(["node", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js {version}")
        else:
            print("❌ Node.js 未安裝或不可用")
            return False
    except FileNotFoundError:
        print("❌ Node.js 未安裝")
        return False
    
    # 檢查 npm
    try:
        result = subprocess.run(["npm", "--version"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ npm {version}")
        else:
            print("❌ npm 未安裝或不可用")
            return False
    except FileNotFoundError:
        print("❌ npm 未安裝")
        return False
    
    return True

def check_virtual_environment():
    """檢查虛擬環境"""
    print("\n🔒 檢查虛擬環境...")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 正在使用虛擬環境")
        return True
    else:
        print("⚠️  未檢測到虛擬環境（建議使用虛擬環境）")
        return True  # 不強制要求

def main():
    """主函數"""
    print("🔍 RPS Calculator 環境檢查")
    print("=" * 50)
    
    checks = [
        check_python_version(),
        check_pip(),
        check_virtual_environment(),
        check_backend_dependencies(),
        check_backend_structure(),
        check_node_npm(),
        check_frontend_structure()
    ]
    
    print("\n" + "=" * 50)
    print("📊 檢查結果總結")
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"🎉 所有檢查都通過了！({passed}/{total})")
        print("\n🚀 您可以開始使用專案了：")
        print("1. 啟動後端: cd backend && uvicorn app.main:app --reload --port 8002")
        print("2. 啟動前端: npm run dev")
        print("3. 訪問: http://localhost:5173")
    else:
        print(f"⚠️  有 {total - passed} 項檢查未通過 ({passed}/{total})")
        print("\n🔧 請根據上述提示修復問題後重新運行檢查")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
