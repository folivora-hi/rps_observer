# 🪨📄✂️ RPS Calculator - 剪刀石頭布策略分析系統

這是一個完整的剪刀石頭布策略分析系統，包含前端（React + Vite）和後端（FastAPI + Python），用於分析不同策略的長期勝率、LLM 預測能力評估等。

## 📋 環境需求

### 必要套件
- **Python 3.9+** - 後端運行環境 (3.9.6)
- **Node.js 18+** - 前端運行環境 (v24.4.1)
- **npm 9+** - 前端套件管理 (11.4.2)

### 檢查環境
```bash
# 檢查 Python 版本
python3 --version

# 檢查 Node.js 版本
node --version

# 檢查 npm 版本
npm --version
```

## 🚀 快速開始

### 1. 克隆專案
```bash
git clone https://github.com/pen9rum/rps.git
cd rps
```

### 2. 設置 Python 虛擬環境
```bash
# 創建虛擬環境
python3 -m venv rps

# 激活虛擬環境
source rps/bin/activate  # macOS/Linux
# 或
rps\Scripts\activate     # Windows
```

### 3. 安裝後端依賴
```bash
cd backend
pip install -r requirements.txt
```

### 4. 安裝前端依賴
```bash
# 回到專案根目錄
cd ..
npm install
```

### 5. 啟動服務

#### 啟動後端（終端 1）
```bash
# 確保虛擬環境已激活
source rps/bin/activate

# 啟動後端服務
cd backend
uvicorn app.main:app --reload --port 8002
```

#### 啟動前端（終端 2）
```bash
# 在專案根目錄
npm run dev
```

### 6. 訪問應用
- 🌐 **前端界面**: http://localhost:5173
- 🔧 **後端 API**: http://127.0.0.1:8002
- 📚 **API 文檔**: http://127.0.0.1:8002/docs

## 🛑 停止服務

### 停止後端
```bash
# 在後端終端按 Ctrl+C
```

### 停止前端
```bash
# 在前端終端按 Ctrl+C
```

## 🔍 故障排除

### 後端問題
```bash
# 檢查端口是否被佔用
lsof -i :8002

# 殺死佔用端口的進程
pkill -f uvicorn

# 重新安裝依賴
cd backend
pip install -r requirements.txt --force-reinstall
```

### 前端問題
```bash
# 清除 node_modules 重新安裝
rm -rf node_modules package-lock.json
npm install

# 檢查端口是否被佔用
lsof -i :5173
```

### 虛擬環境問題
```bash
# 重新創建虛擬環境
rm -rf rps
python3 -m venv rps
source rps/bin/activate
cd backend
pip install -r requirements.txt
```

## 📊 驗證安裝

### 測試後端
```bash
# 健康檢查
curl http://127.0.0.1:8002/health

# 測試模擬 API
curl -X POST http://127.0.0.1:8002/api/v1/simulate \
  -H "Content-Type: application/json" \
  -d '{"s1":{"kind":"frequency"},"s2":{"kind":"random"},"rounds":1000}'
```

### 測試前端
```bash
# 檢查前端是否運行
curl http://localhost:5173

# 測試前端代理到後端
curl http://localhost:5173/api/v1/health
```

## 📚 更多資訊

- 📂 **專案結構**: 詳見 [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)
- 🚀 **快速啟動**: 詳見 [QUICK_START.md](./QUICK_START.md)
- 🔧 **API 文檔**: http://127.0.0.1:8002/docs

## 🤝 支援

如果遇到問題，請檢查：
1. 環境版本是否符合要求
2. 虛擬環境是否正確激活
3. 所有依賴是否正確安裝
4. 端口是否被其他程序佔用
