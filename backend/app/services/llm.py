"""
LLM 服務整合模組

功能：
- 整合 OpenAI API 進行策略預測
- 提供策略描述分析和特徵提取
- 計算策略對戰結果預測
- 提供備用預測邏輯（當 API 失敗時）
- 支援不同 prompt 風格的預測

核心功能：
- identify_from_history(): 歷史辨識（identify-only）

支援的 prompt 風格：
- analytical: 詳細分析風格
- default: 簡潔預測風格

配置要求：
- OPENAI_API_KEY: OpenAI API 金鑰
- MODEL_PROVIDER: 模型提供商設定
"""

from ..core.config import settings
from typing import Optional
import json
import os
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



def _build_identify_prompt(strategy_catalog: dict, history: list[dict], include_reasoning: bool = True) -> str:
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

    # 檢查是否有動態策略
    has_dynamic = False
    try:
        for v in (strategy_catalog or {}).values():
            if isinstance(v, dict) and (v.get('type') == 'dynamic'):
                has_dynamic = True
                break
    except Exception:
        pass

    # 根據是否有動態策略決定說明文字
    notes_lines = [
        "Notes:",
        "- Static strategies (type=static): fixed move distribution dist={rock,paper,scissors}.",
    ]
    if has_dynamic:
        notes_lines.append("- Dynamic strategies (type=dynamic): depend on opponent's previous move; field 'rule' describes the behavior.")

    base = (
        "[Strategy Catalog]\n"
        + strategy_def_json + "\n"
        + "\n".join(notes_lines) + "\n\n"
        + "[Match History]\n"
        + history_json + "\n"
        + "Notes: an array, each element contains:\n"
        + "- move1: Player 1 move (0=Rock, 1=Paper, 2=Scissors)\n"
        + "- move2: Player 2 move (0=Rock, 1=Paper, 2=Scissors)\n"
        + "- result: from Player 1 perspective (1=win, 0=draw, -1=loss)\n\n"
        + "Output ONLY the following JSON and nothing else.\n\n"
    )
    if include_reasoning:
        return base + (
            "{\n"
            "  \"guess_s1\": \"<code like 'H'>\",\n"
            "  \"guess_s2\": \"<code like 'Z'>\",\n"
            "  \"confidence\": <decimal between 0 and 1>,\n"
            "  \"reasoning\": \"<3-5 phrases; separated by semicolons>\"\n"
            "}\n"
        )
    else:
        return base + (
            "{\n"
            "  \"guess_s1\": \"<code like 'H'>\",\n"
            "  \"guess_s2\": \"<code like 'Z'>\",\n"
            "  \"confidence\": <decimal between 0 and 1>\n"
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
                'guess_s1': (data.get('guess_s1') or '').strip(),
                'guess_s2': (data.get('guess_s2') or '').strip(),
                'confidence': float(data.get('confidence') or 0.6),
                'reasoning': (data.get('reasoning') or '').strip(),
            }
            # 合法性檢查（至少要有代號）
            if result['guess_s1'] and result['guess_s2']:
                # 夾在 0~1
                result['confidence'] = max(0.0, min(1.0, result['confidence']))
                return result
    except Exception:
        pass
    return None


def call_openai_o3_for_identify(strategy_catalog: dict, history: list[dict], include_reasoning: bool = True) -> Optional[dict]:
    """使用 OpenAI o3（Responses API）進行策略辨識（返回解析後 dict 或 None）。"""
    if not settings.OPENAI_API_KEY:
        return None
    prompt = _build_identify_prompt(strategy_catalog, history, include_reasoning=include_reasoning)
    if settings.LLM_LOG_PROMPT:
        try:
            print("[LLM PROMPT - OpenAI o3 IDENT]".ljust(28, ' '), "\n" + prompt)
            _write_prompt_file(prompt, provider="openai_o3_ident")
        except Exception:
            pass
    client = _ensure_openai_client(api_key=settings.OPENAI_API_KEY)
    try:
        # 使用 Responses API 呼叫 o3
        resp = client.chat.completions.create(
            model="o3",
            messages=[
                {"role": "system", "content": "You are an RPS observer. Infer the most likely strategies for P1 and P2 from the catalog and history. Respond with JSON only."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        # 原始 JSON 回應
        print(resp)
        # 嘗試多種方式取回純文字內容
        content = getattr(resp.choices[0].message, "content", None)
        if not content:
            try:
                outputs = getattr(resp, "output", None) or getattr(resp, "outputs", None)
                if outputs:
                    # 常見結構：outputs[0].content[0].text
                    first = outputs[0]
                    cont_list = getattr(first, "content", None)
                    if cont_list and len(cont_list) > 0:
                        content = getattr(cont_list[0], "text", None) or content
            except Exception:
                pass
        if settings.LLM_LOG_PROMPT:
            try:
                print("[LLM RESPONSE - OpenAI o3 IDENT]".ljust(30, ' '), "\n" + (content or "<empty>"))
                _write_prompt_file(content or "", provider="openai_o3_ident_resp")
            except Exception:
                pass
        parsed = _parse_identify_json(content or "")
        if settings.LLM_LOG_PROMPT:
            try:
                print("[LLM PARSED   - OpenAI o3 IDENT]".ljust(30, ' '), parsed)
            except Exception:
                pass
        return parsed
    except Exception as e:
        # 若 o3 失敗，不做跨提供者回退；維持嚴格提供者
        import traceback
        print("OpenAI o3 call failed:", e)
        traceback.print_exc()
        return None


def call_openai_for_identify(strategy_catalog: dict, history: list[dict], include_reasoning: bool = True) -> Optional[dict]:
    """使用 OpenAI 進行策略辨識（返回解析後 dict 或 None）。"""
    if not settings.OPENAI_API_KEY:
        return None
    prompt = _build_identify_prompt(strategy_catalog, history, include_reasoning=include_reasoning)
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
                {
                    "role": "system",
                    "content": (
                        "You are an RPS observer. Infer the most likely strategies for P1 and P2 from the catalog and history. Respond with JSON only."
                    )
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        # 原始 JSON 回應
        print(resp)
        content = getattr(resp.choices[0].message, "content", None)
        if settings.LLM_LOG_PROMPT:
            try:
                print("[LLM RESPONSE - OpenAI IDENT]".ljust(28, ' '), "\n" + (content or "<empty>"))
                _write_prompt_file(content or "", provider="openai_ident_resp")
            except Exception:
                pass
        # 補充列印 finish_reason / usage
        if settings.LLM_LOG_PROMPT:
            try:
                fr = getattr(resp.choices[0], "finish_reason", None)
                usage = getattr(resp, "usage", None)
                print("[LLM META     - OpenAI IDENT]".ljust(28, ' '), {"finish_reason": fr, "usage": getattr(usage, "model_dump", lambda: usage)() if hasattr(usage, "model_dump") else usage})
            except Exception:
                pass
        parsed = _parse_identify_json(content or "")
        if settings.LLM_LOG_PROMPT:
            try:
                print("[LLM PARSED   - OpenAI IDENT]".ljust(28, ' '), parsed)
            except Exception:
                pass
        return parsed
    except Exception as e:
        import traceback
        print("OpenAI call failed:", e)
        traceback.print_exc()
        return None



def call_openrouter_for_identify(strategy_catalog: dict, history: list[dict], include_reasoning: bool = True) -> Optional[dict]:
    """使用 OpenRouter 的 DeepSeek 進行策略辨識（返回解析後 dict 或 None）。"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    print("api_key", api_key is not None)
    if not api_key:
        return None
    
    prompt = _build_identify_prompt(strategy_catalog, history, include_reasoning=include_reasoning)
    if settings.LLM_LOG_PROMPT:
        try:
            print("[LLM PROMPT - OpenRouter IDENT]".ljust(24, ' '), "\n" + prompt)
            _write_prompt_file(prompt, provider="openrouter_ident")
        except Exception:
            pass
    try:
        print("call_openrouter_for_identify - try")
        from openai import OpenAI
        client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        resp = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            # model="deepseek/deepseek-chat-v3-0324:free",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an RPS observer. Infer the most likely strategies for P1 and P2 from the catalog and history. Respond with JSON only."
                    )
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=800,
            extra_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", ""),
                "X-Title": os.getenv("OPENROUTER_SITE_NAME", "RPS Observer"),
            },
        )
        # 原始 JSON 回應
        # 某些模型的 content 可能為 None，嘗試從 raw_json 再解析
        print("resp", resp)
        content = getattr(resp.choices[0].message, "content", None)
        print("content", content)
        if settings.LLM_LOG_PROMPT:
            try:
                print("[LLM RESPONSE - OpenRouter IDENT]".ljust(28, ' '), "\n" + (content or "<empty>"))
                _write_prompt_file(content or "", provider="openrouter_ident_resp")
            except Exception:
                pass
        # 補充列印 finish_reason / usage
        if settings.LLM_LOG_PROMPT:
            try:
                fr = getattr(resp.choices[0], "finish_reason", None)
                usage = getattr(resp, "usage", None)
                print("[LLM META     - OpenRouter IDENT]".ljust(28, ' '), {"finish_reason": fr, "usage": getattr(usage, "model_dump", lambda: usage)() if hasattr(usage, "model_dump") else usage})
            except Exception:
                pass
        parsed = _parse_identify_json(content or "")
        if settings.LLM_LOG_PROMPT:
            try:
                print("[LLM PARSED   - OpenRouter IDENT]".ljust(28, ' '), parsed)
            except Exception:
                pass
        return parsed
    except Exception as e:
        import traceback
        print("OpenRouter call failed:", e)
        traceback.print_exc()
        return None


def identify_from_history(strategy_catalog: dict, history: list[dict], model: Optional[str] = None, include_reasoning: bool = True) -> Optional[dict]:
    """對歷史進行 LLM 辨識，並統一輸出格式。
    返回 dict：
    {
        s1_code, s2_code, s1_name, s2_name,
        confidence, reasoning,
        s1_probs: {code: prob}, s2_probs: {code: prob}
    }
    失敗時返回 None。
    """
    selected = (model or '').lower().strip()
    parsed: Optional[dict] = None

    # 嚴格模式：只使用前端指定，或只使用環境指定，不做跨提供者嘗試
    if selected in ("deepseek", "deepseek-r1", "deepseek-r1-free", "openrouter"):
        print("call_openrouter_for_identify")
        parsed = call_openrouter_for_identify(strategy_catalog, history, include_reasoning=include_reasoning)
    elif selected in ("o3", "o3-mini"):
        parsed = call_openai_o3_for_identify(strategy_catalog, history, include_reasoning=include_reasoning)
    elif selected in ("4o-mini", "gpt-4o-mini", "openai", "gpt"):
        parsed = call_openai_for_identify(strategy_catalog, history, include_reasoning=include_reasoning)
    else:
        provider = (settings.MODEL_PROVIDER or "").lower().strip()
        if provider in ("openai", "gpt-4o-mini"):
            parsed = call_openai_for_identify(strategy_catalog, history, include_reasoning=include_reasoning)
        elif provider in ("openrouter", "deepseek"):
            parsed = call_openrouter_for_identify(strategy_catalog, history, include_reasoning=include_reasoning)

    if not parsed:
        return None

    # 將 {guess_s1, guess_s2, confidence, reasoning} 正規化為最終輸出
    s1_code = (parsed.get('guess_s1') or '').strip()
    s2_code = (parsed.get('guess_s2') or '').strip()
    confidence = float(parsed.get('confidence') or 0.6)
    reasoning = (parsed.get('reasoning') or '').strip() or None

    codes = list(strategy_catalog.keys())
    s1_probs = {c: (1.0 if c == s1_code else 0.0) for c in codes} if s1_code else {c: 0.0 for c in codes}
    s2_probs = {c: (1.0 if c == s2_code else 0.0) for c in codes} if s2_code else {c: 0.0 for c in codes}

    result = {
        's1_code': s1_code or None,
        's2_code': s2_code or None,
        's1_name': (strategy_catalog.get(s1_code, {}) or {}).get('name') if s1_code else None,
        's2_name': (strategy_catalog.get(s2_code, {}) or {}).get('name') if s2_code else None,
        'confidence': max(0.0, min(1.0, confidence)),
        'reasoning': reasoning,
        's1_probs': s1_probs,
        's2_probs': s2_probs,
    }
    return result

def decide_next_move(history, k_window=5, belief=None):
    # Simple heuristic placeholder; replace with real LLM policy
    if not history: return 0, "No history; default ROCK."
    opp_moves = [opp for _, opp in history[-(k_window or len(history)):]]
    top = max(set(opp_moves), key=opp_moves.count)
    move = (top + 1) % 3
    return move, "Counter most frequent opponent move."

# --- debug：將 prompt 輸出到檔案，集中在 backend/logs/llm 目錄 ---
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


