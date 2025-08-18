"""
LLM 服務整合模組

功能：
- 整合 OpenAI API 進行策略預測
- 提供策略描述分析和特徵提取
- 計算策略對戰結果預測
- 提供備用預測邏輯（當 API 失敗時）
- 支援不同 prompt 風格的預測

核心功能：
- estimate_payoff(): 主要預測函數，整合 OpenAI API
- call_openai_for_prediction(): OpenAI API 調用
- analyze_strategy(): 策略描述分析
- predict_matchup(): 基於特徵的預測計算
- fallback_prediction(): 備用預測邏輯

支援的 prompt 風格：
- analytical: 詳細分析風格
- default: 簡潔預測風格

配置要求：
- OPENAI_API_KEY: OpenAI API 金鑰
- MODEL_PROVIDER: 模型提供商設定
"""

from ..core.config import settings
from typing import Optional
import random
import json
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# 延遲載入 openai 客戶端，避免缺依賴時整體崩潰
_openai_client = None


def _ensure_openai_client(base_url: Optional[str] = None, api_key: Optional[str] = None):
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI
        except Exception as e:
            raise RuntimeError(f"openai 套件未安裝或導入失敗: {e}")
        _openai_client = OpenAI(base_url=base_url, api_key=api_key)
    return _openai_client


def analyze_strategy(description: str) -> dict:
    """分析策略描述，返回策略特徵"""
    description = description.lower()
    
    # 基本策略特徵分析
    features = {
        'rock_freq': 0.33,
        'paper_freq': 0.33, 
        'scissors_freq': 0.33,
        'is_fixed': False,
        'is_random': False,
        'is_reactive': False,
        'aggressive': 0.5
    }
    
    # 檢測固定策略
    if any(word in description for word in ['固定', 'always', 'pure', 'only', '100%']):
        if '石頭' in description or 'rock' in description:
            features.update({'rock_freq': 1.0, 'paper_freq': 0.0, 'scissors_freq': 0.0, 'is_fixed': True})
        elif '布' in description or 'paper' in description:
            features.update({'rock_freq': 0.0, 'paper_freq': 1.0, 'scissors_freq': 0.0, 'is_fixed': True})
        elif '剪刀' in description or 'scissors' in description:
            features.update({'rock_freq': 0.0, 'paper_freq': 0.0, 'scissors_freq': 1.0, 'is_fixed': True})
    
    # 檢測隨機策略
    elif any(word in description for word in ['隨機', 'random', 'randomly']):
        features.update({'is_random': True})
    
    # 檢測反應策略
    elif any(word in description for word in ['反應', 'reactive', 'counter', '回應']):
        features.update({'is_reactive': True, 'aggressive': 0.7})
    
    # 檢測頻率策略
    elif any(word in description for word in ['頻率', 'frequency', 'most', 'common']):
        features.update({'aggressive': 0.6})
    
    # 檢測偏好
    if '偏愛' in description or 'prefer' in description:
        if '石頭' in description or 'rock' in description:
            features.update({'rock_freq': 0.5, 'paper_freq': 0.25, 'scissors_freq': 0.25})
        elif '布' in description or 'paper' in description:
            features.update({'rock_freq': 0.25, 'paper_freq': 0.5, 'scissors_freq': 0.25})
        elif '剪刀' in description or 'scissors' in description:
            features.update({'rock_freq': 0.25, 'paper_freq': 0.25, 'scissors_freq': 0.5})
    
    return features


def predict_matchup(s1_features: dict, s2_features: dict) -> dict:
    """根據兩個策略的特徵預測對戰結果"""
    
    # 計算期望勝率
    s1_win = 0.0
    s1_loss = 0.0
    s1_draw = 0.0
    
    # 石頭剪刀布的勝負矩陣
    s1_win += s1_features['rock_freq'] * s2_features['scissors_freq']  # 石頭勝剪刀
    s1_win += s1_features['paper_freq'] * s2_features['rock_freq']     # 布勝石頭
    s1_win += s1_features['scissors_freq'] * s2_features['paper_freq'] # 剪刀勝布
    
    s1_loss += s1_features['rock_freq'] * s2_features['paper_freq']    # 石頭敗布
    s1_loss += s1_features['paper_freq'] * s2_features['scissors_freq'] # 布敗剪刀
    s1_loss += s1_features['scissors_freq'] * s2_features['rock_freq']  # 剪刀敗石頭
    
    s1_draw += s1_features['rock_freq'] * s2_features['rock_freq']     # 石頭平石頭
    s1_draw += s1_features['paper_freq'] * s2_features['paper_freq']   # 布平布
    s1_draw += s1_features['scissors_freq'] * s2_features['scissors_freq'] # 剪刀平剪刀
    
    # 添加一些隨機性來模擬不確定性
    noise = 0.05
    s1_win = max(0.0, min(1.0, s1_win + random.uniform(-noise, noise)))
    s1_loss = max(0.0, min(1.0, s1_loss + random.uniform(-noise, noise)))
    s1_draw = max(0.0, min(1.0, s1_draw + random.uniform(-noise, noise)))
    
    # 正規化
    total = s1_win + s1_loss + s1_draw
    if total > 0:
        s1_win /= total
        s1_loss /= total
        s1_draw /= total
    
    return {
        'win': round(s1_win, 3),
        'loss': round(s1_loss, 3),
        'draw': round(s1_draw, 3)
    }


def estimate_confidence(s1_features: dict, s2_features: dict, prediction: dict) -> float:
    """估計預測的信心度"""
    base_confidence = 0.6
    
    # 如果策略很明確，提高信心度
    if s1_features['is_fixed'] or s2_features['is_fixed']:
        base_confidence += 0.2
    
    # 如果預測很極端（高勝率或高敗率），提高信心度
    max_prob = max(prediction['win'], prediction['loss'], prediction['draw'])
    if max_prob > 0.7:
        base_confidence += 0.1
    
    # 如果兩個策略相似，降低信心度
    if (abs(s1_features['rock_freq'] - s2_features['rock_freq']) < 0.1 and
        abs(s1_features['paper_freq'] - s2_features['paper_freq']) < 0.1):
        base_confidence -= 0.1
    
    return min(0.95, max(0.3, base_confidence))


def _build_prompt(description_s1: str, description_s2: str, prompt_style: Optional[str] = None) -> str:
    if prompt_style == "analytical":
        return f"""
你是一個石頭剪刀布遊戲的專家分析師。請分析以下兩個策略的對戰結果：

策略1: {description_s1}
策略2: {description_s2}

請分析這兩個策略的特徵，並預測策略1對戰策略2的結果。
請以JSON格式回答，包含以下欄位：
- win: 策略1獲勝的機率 (0-1之間的小數)
- loss: 策略1失敗的機率 (0-1之間的小數)  
- draw: 平手的機率 (0-1之間的小數)
- confidence: 你對這個預測的信心度 (0-1之間的小數)
- reasoning: 簡短的推理過程

請確保 win + loss + draw = 1
"""
    else:
        return f"""
在石頭剪刀布遊戲中，策略1是"{description_s1}"，策略2是"{description_s2}"。

請預測策略1對戰策略2的結果，並以JSON格式回答：
{{
  "win": 策略1獲勝機率,
  "loss": 策略1失敗機率,
  "draw": 平手機率,
  "confidence": 預測信心度,
  "reasoning": "推理過程"
}}
"""


def _parse_json_from_text(content: str) -> Optional[dict]:
    try:
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end > start:
            data = json.loads(content[start:end])
            total = data.get('win', 0) + data.get('loss', 0) + data.get('draw', 0)
            if total > 0:
                data['win'] = round(data.get('win', 0) / total, 3)
                data['loss'] = round(data.get('loss', 0) / total, 3)
                data['draw'] = round(data.get('draw', 0) / total, 3)
            data['confidence'] = min(1.0, max(0.0, data.get('confidence', 0.6)))
            return data
    except Exception:
        pass
    return None


def _build_identify_prompt(strategy_catalog: dict, history: list[dict]) -> str:
    """構建用於策略辨識的提示，包含：
    - 完整的策略定義（靜態策略：出拳分佈；動態策略：規則說明）
    - 每輪玩家1/2的出拳與結果（history）
    - 要求模型回覆玩家1/2各自的策略判斷
    """
    try:
        strategy_def_json = json.dumps(strategy_catalog, ensure_ascii=False)
    except Exception:
        strategy_def_json = str(strategy_catalog)
    try:
        history_json = json.dumps(history, ensure_ascii=False)
    except Exception:
        history_json = str(history)

    return (
        "你是一位石頭剪刀布觀察者，你的任務是根據策略定義表與對戰歷史，判斷玩家1與玩家2最可能使用的策略。\n\n"
        "[策略定義表]\n"
        + strategy_def_json + "\n"
        "# 說明：\n"
        "# - 靜態策略 (type=static)：固定出拳分佈 dist={rock,paper,scissors}。\n"
        "# - 動態策略 (type=dynamic)：根據對手上一輪行為決定，rule 描述規則。\n\n"
        "[對戰歷史]\n"
        + history_json + "\n"
        "# 說明：陣列，每一元素包含：\n"
        "#   move1 = 玩家1出拳 (0=石頭,1=布,2=剪刀)\n"
        "#   move2 = 玩家2出拳 (0=石頭,1=布,2=剪刀)\n"
        "#   result = 從玩家1視角：1=勝,0=平,-1=敗\n\n"
        "請你：\n"
        "1) 判斷玩家1、玩家2各自最可能的策略代號（從策略定義表中選）。\n"
        "2) 給出 3~5 個關鍵推理短語（不超過100字，用分號隔開）。\n"
        "3) 僅輸出下列 JSON，勿輸出其它文字。\n\n"
        "{\n"
        "  \"guess_s1_code\": \"<代號，如 'H'>\",\n"
        "  \"guess_s1_name\": \"<策略名稱，如 'H (偏愛石頭)'>\",\n"
        "  \"guess_s2_code\": \"<代號，如 'Z'>\",\n"
        "  \"guess_s2_name\": \"<策略名稱，如 'Z (跟前一拳)'>\",\n"
        "  \"confidence\": <0~1的小數>,\n"
        "  \"reasoning\": \"<3~5個短語，用分號隔開>\"\n"
        "}\n"
    )


def _parse_identify_json(content: str) -> Optional[dict]:
    """從模型輸出文字中抽取辨識 JSON。"""
    try:
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end > start:
            data = json.loads(content[start:end])
            result = {
                's1_code': (data.get('guess_s1_code') or '').strip(),
                's2_code': (data.get('guess_s2_code') or '').strip(),
                's1_name': (data.get('guess_s1_name') or '').strip(),
                's2_name': (data.get('guess_s2_name') or '').strip(),
                'confidence': float(data.get('confidence') or 0.6),
                'reasoning': (data.get('reasoning') or '').strip(),
            }
            # 合法性檢查（至少要有代號）
            if result['s1_code'] and result['s2_code']:
                # 夾在 0~1
                result['confidence'] = max(0.0, min(1.0, result['confidence']))
                return result
    except Exception:
        pass
    return None


def call_openai_for_identify(strategy_catalog: dict, history: list[dict]) -> Optional[dict]:
    """使用 OpenAI 進行策略辨識（返回解析後 dict 或 None）。"""
    if not settings.OPENAI_API_KEY:
        return None
    prompt = _build_identify_prompt(strategy_catalog, history)
    if settings.LLM_LOG_PROMPT:
        try:
            print("[LLM PROMPT - OpenAI IDENT]".ljust(24, ' '), "\n" + prompt)
            _write_prompt_file(prompt, provider="openai_ident")
        except Exception:
            pass
    client = _ensure_openai_client(api_key=settings.OPENAI_API_KEY)
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一個石頭剪刀布遊戲的觀察與辨識專家。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        content = resp.choices[0].message.content
        return _parse_identify_json(content)
    except Exception:
        return None


def call_openrouter_for_identify(strategy_catalog: dict, history: list[dict]) -> Optional[dict]:
    """使用 OpenRouter 的 DeepSeek 進行策略辨識（返回解析後 dict 或 None）。"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None
    prompt = _build_identify_prompt(strategy_catalog, history)
    if settings.LLM_LOG_PROMPT:
        try:
            print("[LLM PROMPT - OpenRouter IDENT]".ljust(24, ' '), "\n" + prompt)
            _write_prompt_file(prompt, provider="openrouter_ident")
        except Exception:
            pass
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        resp = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=400,
            extra_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
                "X-Title": os.getenv("OPENROUTER_SITE_NAME", "RPS Observer"),
            },
        )
        content = resp.choices[0].message.content
        return _parse_identify_json(content)
    except Exception:
        return None


def identify_from_history(strategy_catalog: dict, history: list[dict], model: Optional[str] = None) -> Optional[dict]:
    """對歷史進行 LLM 辨識。
    返回 dict: {s1_code, s2_code, s1_name, s2_name, confidence, reasoning} 或 None（失敗）。
    """
    selected = (model or '').lower().strip()
    # 指定模型
    if selected in ("deepseek", "deepseek-r1", "deepseek-r1-free"):
        res = call_openrouter_for_identify(strategy_catalog, history)
        if res:
            return res
        return call_openai_for_identify(strategy_catalog, history)
    if selected in ("4o-mini", "gpt-4o-mini", "openai"):
        res = call_openai_for_identify(strategy_catalog, history)
        if res:
            return res
        return call_openrouter_for_identify(strategy_catalog, history)

    # 未指定時，依環境設定嘗試
    provider = (settings.MODEL_PROVIDER or "").lower()
    if provider in ("openai", "gpt-4o-mini"):
        res = call_openai_for_identify(strategy_catalog, history)
        if res:
            return res
        return call_openrouter_for_identify(strategy_catalog, history)
    if provider in ("openrouter", "deepseek"):
        res = call_openrouter_for_identify(strategy_catalog, history)
        if res:
            return res
        return call_openai_for_identify(strategy_catalog, history)

    # 沒有任何可用提供者
    return None

def call_openai_for_prediction(description_s1: str, description_s2: str, prompt_style: Optional[str] = None) -> dict:
    """使用 OpenAI (官方) chat.completions 進行預測"""
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API key not configured")

    prompt = _build_prompt(description_s1, description_s2, prompt_style)
    # 依環境變數決定是否輸出 prompt 到日誌
    if settings.LLM_LOG_PROMPT:
        try:
            print("[LLM PROMPT - OpenAI]".ljust(24, ' '), "\n" + prompt)
            # 檔案輸出
            _write_prompt_file(prompt, provider="openai")
        except Exception:
            pass
    client = _ensure_openai_client(api_key=settings.OPENAI_API_KEY)
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "你是一個石頭剪刀布遊戲分析專家。請提供準確的預測和清晰的推理。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=500,
    )
    content = resp.choices[0].message.content
    parsed = _parse_json_from_text(content)
    if parsed:
        return parsed
    return fallback_prediction(description_s1, description_s2)


def call_openrouter_deepseek(description_s1: str, description_s2: str, prompt_style: Optional[str] = None) -> dict:
    """使用 OpenRouter 調用 DeepSeek 模型（.env 版）"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("⚠️ OpenRouter API key 未設定，改用備用預測邏輯")
        return fallback_prediction(description_s1, description_s2)

    site_url = os.getenv("OPENROUTER_SITE_URL", "")  # 可留空
    site_name = os.getenv("OPENROUTER_SITE_NAME", "RPS Observer")

    prompt = _build_prompt(description_s1, description_s2, prompt_style)
    if settings.LLM_LOG_PROMPT:
        try:
            print("[LLM PROMPT - OpenRouter]".ljust(24, ' '), "\n" + prompt)
            _write_prompt_file(prompt, provider="openrouter")
        except Exception:
            pass

    # 實際呼叫 OpenRouter DeepSeek（使用 OpenAI SDK 並指定 base_url）
    try:
        from openai import OpenAI
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        resp = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            messages=[
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
            extra_headers={
                "HTTP-Referer": site_url,
                "X-Title": site_name,
            },
        )
        content = resp.choices[0].message.content
        parsed = _parse_json_from_text(content)
        if parsed:
            return parsed
        return fallback_prediction(description_s1, description_s2)
    except Exception as e:
        print(f"❌ OpenRouter 調用失敗，使用備用邏輯: {e}")
        return fallback_prediction(description_s1, description_s2)

# --- 新增：將 prompt 輸出到檔案，集中在 backend/logs/llm 目錄 ---
def _write_prompt_file(prompt: str, provider: str = "unknown") -> None:
    try:
        base_dir = settings.LLM_LOG_DIR or "logs/llm"
        # 以 backend/ 為工作目錄假設。保證目錄存在
        os.makedirs(base_dir, exist_ok=True)
        import datetime, uuid
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        fid = uuid.uuid4().hex[:8]
        path = os.path.join(base_dir, f"{ts}_{provider}_{fid}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(prompt)
    except Exception as _:
        # 文件寫入失敗不影響流程
        pass



# 主要的預測函數，加入 model 參數以切換

def estimate_payoff(description_s1: str, description_s2: str, prompt_style: Optional[str] = None, model: Optional[str] = None):
    """根據策略描述預測對戰結果，支援 model 選擇（'deepseek' 或 '4o-mini'），預設遵循環境設定。"""
    # 沒有任何外部金鑰時，直接 fallback
    has_openai = bool(settings.OPENAI_API_KEY)
    has_openrouter = bool(settings.OPENROUTER_API_KEY)
    if not (has_openai or has_openrouter):
        print("⚠️ 警告: 未設定任何 API 金鑰，使用備用預測邏輯")
        return fallback_prediction(description_s1, description_s2)

    # 依使用者指定或預設提供商選擇
    selected = (model or '').lower().strip()
    try:
        if selected in ("deepseek", "deepseek-r1", "deepseek-r1-free"):
            return call_openrouter_deepseek(description_s1, description_s2, prompt_style)
        if selected in ("4o-mini", "gpt-4o-mini", "openai"):
            return call_openai_for_prediction(description_s1, description_s2, prompt_style)

        # 未指定時，依環境走
        provider = (settings.MODEL_PROVIDER or "").lower()
        if provider in ("openai", "gpt-4o-mini") and has_openai:
            return call_openai_for_prediction(description_s1, description_s2, prompt_style)
        if provider in ("openrouter", "deepseek") and has_openrouter:
            return call_openrouter_deepseek(description_s1, description_s2, prompt_style)

        # 任何情況不可用則 fallback
        return fallback_prediction(description_s1, description_s2)
    except Exception as e:
        print(f"❌ LLM 調用失敗，使用備用邏輯: {e}")
        return fallback_prediction(description_s1, description_s2)


def fallback_prediction(description_s1: str, description_s2: str) -> dict:
    """當 OpenAI API 失敗時的備用預測"""
    # 使用原有的邏輯作為備用
    s1_features = analyze_strategy(description_s1)
    s2_features = analyze_strategy(description_s2)
    prediction = predict_matchup(s1_features, s2_features)
    confidence = estimate_confidence(s1_features, s2_features, prediction)
    
    return {
        "win": prediction['win'],
        "loss": prediction['loss'], 
        "draw": prediction['draw'],
        "confidence": round(confidence, 3),
        "reasoning": "使用備用分析邏輯"
    }


def decide_next_move(history, k_window=5, belief=None):
    # Simple heuristic placeholder; replace with real LLM policy
    if not history: return 0, "No history; default ROCK."
    opp_moves = [opp for _, opp in history[-(k_window or len(history)):]]
    top = max(set(opp_moves), key=opp_moves.count)
    move = (top + 1) % 3
    return move, "Counter most frequent opponent move."

# for test
if __name__ == "__main__":
    result = call_openrouter_deepseek("固定出石頭", "隨機出拳")
    print(result)
