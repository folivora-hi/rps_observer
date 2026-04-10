# RPS Observer：透過遊戲觀察模擬大型語言模型的心智理論

[![arXiv](https://img.shields.io/badge/arXiv-2512.19210-b31b1b.svg)](https://arxiv.org/abs/2512.19210)
[![NeurIPS 2025 Workshop](https://img.shields.io/badge/NeurIPS_2025-Workshop-purple)](https://arxiv.org/abs/2512.19210)

本論文 **"Observer, Not Player: Simulating Theory of Mind in LLMs through Game Observation"** 的官方實作，發表於 NeurIPS 2025 Workshop on *Foundations of Reasoning in Language Models* 以及 *Bridging Language, Agent, and World Model*。

---

## 摘要

我們提出一個互動框架，用於評估 LLM 是否能展現真正的策略理解能力。以剪刀石頭布（RPS）為受控實驗環境，LLM 扮演**觀察者**角色——觀看一連串的對戰記錄，並必須辨識每位玩家所使用的隱藏策略及其信心度。此框架將策略「理解」與策略「執行」分離，使心智理論的探測更加純粹。我們引入三種互補指標（Cross-Entropy、Brier Score、EV Loss）並整合為 **Union Loss**，並使用 **Strategy Identification Rate（SIR）** 評估穩定的策略辨識率，在 GPT-4o-mini、o3 以及 Claude 3.7 Sonnet 上進行實驗。

---

## 系統概覽

### 觀察者框架

```
對戰記錄（第 1..t 輪）
        │
        ▼
  ┌─────────────┐        ┌───────────────────────────┐
  │  RPS 引擎   │──────▶ │  LLM 觀察者               │
  │  (19 種策略) │        │  - 辨識玩家 1 的策略       │
  └─────────────┘        │  - 辨識玩家 2 的策略       │
                         │  - 回報信心度             │
                         └───────────────────────────┘
                                      │
                                      ▼
                              評估指標計算
                         (CE / Brier / EV / Union Loss)
```

### 策略空間

| 類型 | 代碼 | 說明 |
|------|------|------|
| 靜態策略 | A–P（16 種）| 固定的 {石頭、布、剪刀} 機率分布 |
| 動態策略 | X、Y、Z（3 種）| 根據對手上一輪出拳做出反應 |

靜態策略涵蓋純策略（A=純剪刀、B=純石頭、C=純布）、隨機（D）、二元混合（E–G）、偏好型（H–J）、有序混合（K–P）。動態策略：**X**（贏對手上一手）、**Y**（輸給對手上一手）、**Z**（複製對手上一手）。

### 評估指標

| 指標 | 公式 | 意涵 |
|------|------|------|
| Cross-Entropy Loss | −∑ p_true · log(p_pred) | 預測分布的校準品質 |
| Brier Score | ∑ (p_true − p_pred)² | 對機率誤差的敏感度 |
| EV Loss | (EV_true − EV_pred)² | 賽局理論期望值對齊 |
| **Union Loss** | mean(CE, Brier, EV) | 統一評分 |
| SIR | 正確辨識策略的回合百分比 | 離散辨識準確率 |

---

## 實驗結果

實驗在三種策略對戰情境下執行。每個資料夾中包含各模型的損失比較圖及跨模型比較圖。

| 情境 | 玩家 1 | 玩家 2 |
|------|--------|--------|
| [DY](experiments/results/DY/) | D — 隨機（均勻 1/3）| Y — 輸給對手上一手 |
| [HC](experiments/results/HC/) | H — 石頭偏好（0.5, 0.25, 0.25）| C — 純布 |
| [NG](experiments/results/NG/) | N — 布>剪刀（0.167, 0.5, 0.333）| G — 布+剪刀（0, 0.5, 0.5）|

**測試模型**：`gpt-4o-mini`、`o3`、`claude-3-7-sonnet`

---

## 快速開始

### 環境需求

- Python 3.9+
- Node.js 18+、npm 9+
- 至少一個 LLM 服務提供商的 API 金鑰

### 1. 克隆與設定

```bash
git clone https://github.com/folivora-hi/rps_observer.git
cd rps_observer
cp backend/env.example backend/.env
# 編輯 backend/.env，填入 API 金鑰
```

**支援的 LLM 服務提供商**（`backend/.env` 中的 `MODEL_PROVIDER`）：

| 值 | 提供商 | 所需 Key |
|----|--------|---------|
| `openai` | OpenAI (gpt-4o, gpt-4o-mini) | `OPENAI_API_KEY` |
| `deepseek-official` | DeepSeek Chat | `DEEPSEEK_API_KEY` |
| `deepseek-reasoner` | DeepSeek Reasoner | `DEEPSEEK_API_KEY` |
| `gemini-2.5-pro` | Google Gemini | `GEMINI_API_KEY` |
| `claude-3-7-sonnet-20250219` | Anthropic Claude | `ANTHROPIC_API_KEY` |
| `openrouter` | OpenRouter | `OPENROUTER_API_KEY` |

### 2. 後端啟動

```bash
python3 -m venv rps
source rps/bin/activate        # Windows: rps\Scripts\activate
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
```

後端 API：http://127.0.0.1:8002  
Swagger 文件：http://127.0.0.1:8002/docs

### 3. 前端啟動

```bash
# 在專案根目錄（新終端機）
npm install
npm run dev
```

前端介面：http://localhost:5173

### 4. 存取應用程式

- 前端介面：http://localhost:5173
- 後端 API：http://127.0.0.1:8002
- API 文件：http://127.0.0.1:8002/docs

---

## 執行實驗

使用 `scripts/observer_auto_test.py` 批次執行觀察者實驗並匯出 Excel 結果：

```bash
source rps/bin/activate
python scripts/observer_auto_test.py \
  --server http://localhost:8002 \
  --true-s1 D --true-s2 Y \
  --rounds 30 \
  --warmup 5 \
  --history-limit 10 \
  --reasoning-interval 3 \
  --model 4o-mini \
  --repeats 5 \
  --out-dir ./output
```

主要參數說明：

| 參數 | 說明 |
|------|------|
| `--true-s1/s2` | 兩位玩家的真實策略代碼（如 `D`、`Y`） |
| `--rounds` | 每次執行的遊戲輪數 |
| `--warmup` | LLM 開始預測前先觀看的熱身輪數 |
| `--history-limit` | 提供給 LLM 的最大歷史輪數（-1 為無限制） |
| `--reasoning-interval` | 每隔 N 輪請求 LLM 提供推理說明 |
| `--model` | LLM 模型識別碼 |
| `--repeats` | 每個參數組合的重複次數 |

---

## 故障排除

```bash
# 後端端口被佔用
lsof -i :8002
pkill -f uvicorn

# 前端端口被佔用
lsof -i :5173

# 重新安裝後端依賴
cd backend && pip install -r requirements.txt --force-reinstall

# 重新安裝前端依賴
rm -rf node_modules package-lock.json && npm install
```

---

## 引用

如果本研究對您有幫助，請引用：

```bibtex
@article{wang2025observer,
  title={Observer, Not Player: Simulating Theory of Mind in LLMs through Game Observation},
  author={Wang, Jerry and Liu, Ting Yiu},
  journal={arXiv preprint arXiv:2512.19210},
  year={2025},
  url={https://arxiv.org/abs/2512.19210}
}
```

---

## 架構說明

詳細的後端與前端架構說明請參見 [ARCHITECTURE.md](ARCHITECTURE.md)。

---

[English README](README.md)
