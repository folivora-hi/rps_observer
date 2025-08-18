# 🚀 RPS Calculator 快速啟動指令

## 📋 前置需求

### 檢查環境
```bash
# 檢查 Python 版本 (需要 3.9+)
python3 --version

# 檢查 Node.js 版本 (需要 18+)
node --version

# 檢查 npm 版本
npm --version
```

## 🔧 後端啟動

### 1. 激活虛擬環境
```bash
source rps/bin/activate
```

### 2. 安裝後端依賴
```bash
cd backend
pip install -r requirements.txt
```

### 3. 啟動後端服務
```bash
# 開發模式 (自動重載)
uvicorn app.main:app --reload --port 8002

# 生產模式
uvicorn app.main:app --host 0.0.0.0 --port 8002
```

### 4. 驗證後端
```bash
# 健康檢查
curl http://127.0.0.1:8002/health

# 測試模擬 API
curl -X POST http://127.0.0.1:8002/api/v1/simulate \
  -H "Content-Type: application/json" \
  -d '{"s1":{"kind":"frequency"},"s2":{"kind":"random"},"rounds":1000}'
```

## 🟢 前端啟動

### 1. 安裝前端依賴
```bash
# 回到專案根目錄
cd ..
npm install
```

### 2. 啟動前端開發服務器
```bash
npm run dev
```

### 3. 驗證前端
```bash
# 檢查前端是否運行
curl http://localhost:5173

# 測試前端代理到後端
curl http://localhost:5173/api/v1/health
```

## 🎯 完整啟動流程

### 終端 1 - 後端
```bash
# 激活虛擬環境
source rps/bin/activate

# 啟動後端
cd backend
uvicorn app.main:app --reload --port 8002
```

### 終端 2 - 前端
```bash
# 啟動前端
npm run dev
```

### 訪問應用
- 🌐 前端界面: http://localhost:5173
- 🔧 後端 API: http://127.0.0.1:8002
- 📚 API 文檔: http://127.0.0.1:8002/docs

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

# 檢查 Python 依賴
pip list | grep fastapi
```

### 前端問題
```bash
# 清除 node_modules 重新安裝
rm -rf node_modules package-lock.json
npm install

# 檢查端口是否被佔用
lsof -i :5173
```

### 代理問題
```bash
# 檢查 vite.config.js 中的代理配置
cat vite.config.js

# 測試代理是否工作
curl http://localhost:5173/api/v1/health
```

## 📊 常用 API 測試

### 策略模擬
```bash
curl -X POST http://127.0.0.1:8002/api/v1/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "s1": {"kind": "frequency"},
    "s2": {"kind": "random"},
    "rounds": 1000
  }'
```

### LLM 預測
```bash
curl -X POST http://127.0.0.1:8002/api/v1/observer/predict \
  -H "Content-Type: application/json" \
  -d '{
    "description_s1": "頻率策略",
    "description_s2": "隨機策略"
  }'
```

### 玩家決策
```bash
curl -X POST http://127.0.0.1:8002/api/v1/player/act \
  -H "Content-Type: application/json" \
  -d '{
    "history": [[0, 1], [1, 2], [2, 0]],
    "k_window": 3
  }'
```

### 評估指標
```bash
curl -X POST http://127.0.0.1:8002/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "pred": [0.3, 0.4, 0.3],
    "gt": [0.35, 0.35, 0.3]
  }'
```
