"""
觀察者（Observer）API

本模組提供逐輪「觀察 + 辨識」主流程（/observer/run, /observer/stream）

更新重點：
- /observer/run 已改為：前 warmup 回合只蒐集歷史；第 warmup+1 輪起，每輪輸出對「雙邊策略的辨識結果」與 union_loss
- union_loss 以 backend/app/domain/metrics.py 中 CE/Brier/EV 三者平均為準
"""

from fastapi import APIRouter, HTTPException
import os
from fastapi.responses import StreamingResponse
from typing import Optional
from ...schemas.observer import (
    ObserverRunReq, ObserverRunResp, RoundRecord, StrategyProbs
)
from ...services.llm import identify_from_history
from ...domain.strategies import (
    get_all_strategies, get_strategy_names,
    calculate_matchup, beats,
    BASE_STRATEGIES, DYNAMIC_STRATEGIES,
    resolve_dist, iterate_dists
)
from ...core.config import settings
from ...domain.metrics import (
    compute_union_loss,
    normalize_loss,
    compute_all_losses_for_matrix,
    compute_cross_entropy_loss,
    compute_brier_score,
    compute_ev_loss,
)
from dotenv import load_dotenv
load_dotenv()

router = APIRouter(prefix="/observer", tags=["observer"])


# ---- Shared helpers to avoid duplication between /run and /stream ----
def build_strategy_catalog() -> dict:
    strategy_catalog = {}
    for k, v in BASE_STRATEGIES.items():
        strategy_catalog[k] = {
            'type': 'static',
            'name': v['name'],
            'dist': {'rock': v['rock'], 'paper': v['paper'], 'scissors': v['scissors']},
        }
    if settings.USE_DYNAMIC_STRATEGIES:
        for k, v in DYNAMIC_STRATEGIES.items():
            strategy_catalog[k] = {
                'type': 'dynamic',
                'name': v['name'],
                'rule': v['rule'],
            }
    return strategy_catalog


def current_dists_shared(k1: str, k2: str):
    is_base1 = k1 in BASE_STRATEGIES
    is_base2 = k2 in BASE_STRATEGIES
    if is_base1 and is_base2:
        return BASE_STRATEGIES[k1], BASE_STRATEGIES[k2]
    if is_base1 and not is_base2:
        return BASE_STRATEGIES[k1], resolve_dist(k2, BASE_STRATEGIES[k1])
    if not is_base1 and is_base2:
        return resolve_dist(k1, BASE_STRATEGIES[k2]), BASE_STRATEGIES[k2]
    it = iterate_dists(k1, k2, 50)
    return it['s1'], it['s2']


def sample_move_shared(dist):
    import random
    return random.choices([0, 1, 2], weights=[dist['rock'], dist['paper'], dist['scissors']])[0]


def resolve_provider_shared(model: str | None) -> str | None:
    selected = (model or "").lower().strip()
    if selected in ("deepseek-official", "deepseek-reasoner"):
        return "deepseek-official"
    if selected in ("deepseek", "deepseek-r1", "deepseek-r1-free"):
        return "openrouter"
    if selected in ("4o-mini", "40-mini", "gpt-4o-mini", "openai", "o3", "o3-mini"):
        return "openai"
    if selected in ("gemini", "gemini-2.5-pro", "gemini-2.5"):
        return "gemini"
    if selected in ("claude", "claude-3-7-sonnet", "claude-3-7-sonnet-20250219"):
        return "anthropic"
    return None


def ensure_ident_available_for_shared(provider: str | None):
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise HTTPException(status_code=503, detail="LLM unavailable: OPENAI_API_KEY missing")
    elif provider == "openrouter":
        if not os.getenv("OPENROUTER_API_KEY"):
            raise HTTPException(status_code=503, detail="LLM unavailable: OPENROUTER_API_KEY missing")
    elif provider == "deepseek-official":
        if not settings.DEEPSEEK_API_KEY:
            raise HTTPException(status_code=503, detail="LLM unavailable: DEEPSEEK_API_KEY missing")
    elif provider == "gemini":
        if not settings.GEMINI_API_KEY:
            raise HTTPException(status_code=503, detail="LLM unavailable: GEMINI_API_KEY missing")
    elif provider == "anthropic":
        if not settings.ANTHROPIC_API_KEY:
            raise HTTPException(status_code=503, detail="LLM unavailable: ANTHROPIC_API_KEY missing")
    else:
        raise HTTPException(status_code=503, detail="LLM unavailable: no valid provider (set MODEL_PROVIDER or pass model)")


def build_hist_json(history: list[tuple[int, int, int]], history_limit: int | None):
    base_round = len(history) - len(history) + 1
    # history 是 (m1, m2, res)
    hist_json = [
        {"round": base_round + i, "move1": mm1, "move2": mm2, "result": rr}
        for i, (mm1, mm2, rr) in enumerate(history)
    ]
    if history_limit and history_limit > 0:
        hist_json = hist_json[-int(history_limit):]
    return hist_json


def compute_losses(true_dist: dict, pred_dist: dict, matrix: dict):
    ce_loss = compute_cross_entropy_loss(true_dist, pred_dist)
    brier_loss = compute_brier_score(true_dist, pred_dist)
    ev_loss = compute_ev_loss(true_dist, pred_dist)
    union_loss = compute_union_loss(true_dist, pred_dist)

    all_losses = compute_all_losses_for_matrix(matrix, pred_dist)
    normalized_ce_loss = normalize_loss(ce_loss, all_losses['ce_losses'])
    normalized_ev_loss = ev_loss / 1.0
    normalized_union_loss = (float(normalized_ce_loss) + float(brier_loss) + float(normalized_ev_loss)) / 3.0

    return {
        'ce_loss': ce_loss,
        'brier_loss': brier_loss,
        'ev_loss': ev_loss,
        'union_loss': union_loss,
        'normalized_ce_loss': normalized_ce_loss,
        'normalized_ev_loss': normalized_ev_loss,
        'normalized_union_loss': normalized_union_loss,
    }


@router.post("/run", response_model=ObserverRunResp)
def observer_run(req: ObserverRunReq):
    all_strategies = get_all_strategies()
    if req.true_strategy1 not in all_strategies or req.true_strategy2 not in all_strategies:
        raise HTTPException(status_code=400, detail="真實策略不存在")

    strategy_names = get_strategy_names()
    codes = list(all_strategies.keys())
    matrix = {s1: {s2: calculate_matchup(s1, s2) for s2 in codes} for s1 in codes}

    strategy_catalog = build_strategy_catalog()

    k1_true, k2_true = req.true_strategy1, req.true_strategy2
    history = []
    per_round: list[RoundRecord] = []
    last_union_loss: float = 0.0
    losses_series: list[float] = []

    for r in range(1, int(req.rounds) + 1):
        dist1, dist2 = current_dists_shared(k1_true, k2_true)
        m1 = sample_move_shared(dist1)
        m2 = sample_move_shared(dist2)
        res = beats(m1, m2)
        history.append((m1, m2, res))

        guess_s1_code = None
        guess_s2_code = None
        union_loss = None
        normalized_union_loss = None  # 初始化正規化 loss
        # 其他損失初始化
        ce_loss = None
        brier_loss = None
        ev_loss = None
        normalized_ce_loss = None
        # 不提供 Brier 的 normalized
        normalized_ev_loss = None
        delta = None
        extra_conf = None
        extra_reason = None
        hist_used = None

        if r > (req.warmup_rounds or 0):
            print("round", r)
            hw = history
            try:
                base_round = len(history) - len(hw) + 1
                hist_json = build_hist_json(hw, req.history_limit)
                hist_used = len(hist_json)
                include_reason = (r % (req.reasoning_interval or 10) == 0 or r == req.rounds)
                provider = resolve_provider_shared(req.model)
                print(f"model: {req.model}, provider: {provider}")
                ensure_ident_available_for_shared(provider)
                ident = identify_from_history(strategy_catalog, hist_json, req.model, include_reasoning=include_reason)
                # print("ident1", ident)
            except Exception as e:
                print("error", e)
                ident = None
                err_msg = str(e)
            # print("ident2", ident)

            if ident:
                # 兼容：s1_probs/s2_probs 可能是 dict，也可能是單一代碼（字串）。
                s1_code = ident.get("s1_code") or None
                s2_code = ident.get("s2_code") or None
                s1_probs_raw = ident.get("s1_probs")
                s2_probs_raw = ident.get("s2_probs")
                if not s1_code:
                    if isinstance(s1_probs_raw, dict) and s1_probs_raw:
                        s1_code = max(s1_probs_raw.items(), key=lambda x: x[1])[0]
                    elif isinstance(s1_probs_raw, str) and s1_probs_raw:
                        s1_code = s1_probs_raw
                if not s2_code:
                    if isinstance(s2_probs_raw, dict) and s2_probs_raw:
                        s2_code = max(s2_probs_raw.items(), key=lambda x: x[1])[0]
                    elif isinstance(s2_probs_raw, str) and s2_probs_raw:
                        s2_code = s2_probs_raw

                # 只回傳單一代碼（不再輸出 probs 至前端）
                guess_s1_code = s1_code or None
                guess_s2_code = s2_code or None
                extra_conf = float(ident.get("confidence") or 0.6)
                extra_reason = (
                    (ident.get("reasoning") or None)
                    if (r % (req.reasoning_interval or 50) == 0 or r == req.rounds)
                    else None
                )
            else:
                # 輕量降級：無辨識結果時，當輪不報錯，僅回傳空猜測
                guess_s1_code = None
                guess_s2_code = None
                extra_conf = None
                extra_reason = None

            # 計算 loss 和 delta（移到這裡，確保每次都會計算）
            true_dist = matrix[k1_true][k2_true]
            best_pair = (guess_s1_code, guess_s2_code)
            if best_pair[0] and best_pair[1]:
                pred_dist = matrix[best_pair[0]][best_pair[1]]
                # 計算四種損失與 normalized（共用）
                losses = compute_losses(true_dist, pred_dist, matrix)
                ce_loss = losses['ce_loss']
                brier_loss = losses['brier_loss']
                ev_loss = losses['ev_loss']
                union_loss = losses['union_loss']
                normalized_ce_loss = losses['normalized_ce_loss']
                normalized_ev_loss = losses['normalized_ev_loss']
                normalized_union_loss = losses['normalized_union_loss']
                
                delta = None if r == (req.warmup_rounds or 0) + 1 else (union_loss - last_union_loss)
                last_union_loss = union_loss
                try:
                    losses_series.append(float(union_loss))
                except Exception:
                    pass
            else:
                union_loss = None
                normalized_union_loss = None
                ce_loss = None
                brier_loss = None
                ev_loss = None
                normalized_ce_loss = None
                # 不提供 Brier 的 normalized
                normalized_ev_loss = None
                delta = None

        per_round.append(RoundRecord(
            round=r,
            move1=m1,
            move2=m2,
            result=res,
            guess_s1=guess_s1_code,
            guess_s2=guess_s2_code,
            ce_loss=ce_loss,
            brier_loss=brier_loss,
            ev_loss=ev_loss,
            union_loss=union_loss,
            normalized_ce_loss=normalized_ce_loss,
            normalized_ev_loss=normalized_ev_loss,
            normalized_union_loss=normalized_union_loss,  # 新增正規化 loss
            delta=delta,
            confidence=extra_conf,
            reasoning=extra_reason,
            history_used=(len(hist_json) if (r > (req.warmup_rounds or 0)) else None)
        ))

    # 獲取最後一輪的猜測
    last_guess_s1 = None
    last_guess_s2 = None
    for record in reversed(per_round):
        if record.guess_s1 is not None or record.guess_s2 is not None:
            last_guess_s1 = record.guess_s1
            last_guess_s2 = record.guess_s2
            break
    
    final_guess = {'s1': (last_guess_s1 or ''), 's2': (last_guess_s2 or '')}
    trend = {}
    if losses_series:
        trend['last'] = losses_series[-1]
        trend['min'] = min(losses_series)
        trend['avg_5'] = sum(losses_series[-5:]) / min(5, len(losses_series))
        
        # 添加最後一輪的正規化 loss
        if per_round:
            last_record = per_round[-1]
            if last_record.normalized_union_loss is not None:
                trend['last_normalized'] = last_record.normalized_union_loss

    return ObserverRunResp(
        model=req.model,
        true_strategy1=k1_true,
        true_strategy2=k2_true,
        rounds=req.rounds,
        warmup_rounds=req.warmup_rounds,
        history_limit=req.history_limit,
        reasoning_interval=req.reasoning_interval,
        per_round=per_round,
        trend=trend,
        final_guess=final_guess,
    )


@router.get("/stream")
def observer_run_stream(true_strategy1: str, true_strategy2: str, rounds: int = 50, warmup_rounds: int = 10, history_limit: Optional[int] = None, reasoning_interval: Optional[int] = 10, model: Optional[str] = "deepseek"):
    """以 SSE 逐輪推送辨識與結果，便於前端即時展示。GET 參數對應 /observer/run。"""
    all_strategies = get_all_strategies()
    if true_strategy1 not in all_strategies or true_strategy2 not in all_strategies:
        raise HTTPException(status_code=400, detail="真實策略不存在")

    # 準備策略定義與對戰矩陣
    strategy_names = get_strategy_names()
    codes = list(all_strategies.keys())
    matrix = {s1: {s2: calculate_matchup(s1, s2) for s2 in codes} for s1 in codes}

    strategy_catalog = {}
    for k, v in BASE_STRATEGIES.items():
        strategy_catalog[k] = {
            'type': 'static',
            'name': v['name'],
            'dist': {'rock': v['rock'], 'paper': v['paper'], 'scissors': v['scissors']},
        }
    if settings.USE_DYNAMIC_STRATEGIES:
        for k, v in DYNAMIC_STRATEGIES.items():
            strategy_catalog[k] = {
                'type': 'dynamic',
                'name': v['name'],
                'rule': v['rule'],
            }

    def current_dists(k1: str, k2: str):
        is_base1 = k1 in BASE_STRATEGIES
        is_base2 = k2 in BASE_STRATEGIES
        if is_base1 and is_base2:
            return BASE_STRATEGIES[k1], BASE_STRATEGIES[k2]
        if is_base1 and not is_base2:
            return BASE_STRATEGIES[k1], resolve_dist(k2, BASE_STRATEGIES[k1])
        if not is_base1 and is_base2:
            return resolve_dist(k1, BASE_STRATEGIES[k2]), BASE_STRATEGIES[k2]
        it = iterate_dists(k1, k2, 50)
        return it['s1'], it['s2']

    import random, json

    def sample_move(dist):
        return random.choices([0,1,2], weights=[dist['rock'], dist['paper'], dist['scissors']])[0]

    def resolve_provider(model: str | None) -> str | None:
        selected = (model or "").lower().strip()
        print(f"stream resolve_provider: model='{model}', selected='{selected}'")
        if selected in ("deepseek-official", "deepseek-reasoner"): 
            print(f"  -> returning deepseek-official")
            return "deepseek-official"
        if selected in ("deepseek", "deepseek-r1", "deepseek-r1-free"): 
            print(f"  -> returning openrouter")
            return "openrouter"
        if selected in ("4o-mini", "gpt-4o-mini", "openai", "o3", "o3-mini"): 
            print(f"  -> returning openai")
            return "openai"
        if selected in ("gemini", "gemini-2.5-pro", "gemini-2.5"): 
            print(f"  -> returning gemini")
            return "gemini"
        if selected in ("claude", "claude-3-7-sonnet", "claude-3-7-sonnet-20250219"): 
            print(f"  -> returning anthropic")
            return "anthropic"
        print(f"  -> returning None (no match)")
        return None

    def ensure_ident_available_for(provider: str | None):
        from ...core.config import settings
        if provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise HTTPException(status_code=503, detail="LLM unavailable: OPENAI_API_KEY missing")
        elif provider == "openrouter":
            if not os.getenv("OPENROUTER_API_KEY"):
                raise HTTPException(status_code=503, detail="LLM unavailable: OPENROUTER_API_KEY missing")
        elif provider == "deepseek-official":
            if not settings.DEEPSEEK_API_KEY:
                raise HTTPException(status_code=503, detail="LLM unavailable: DEEPSEEK_API_KEY missing")
        elif provider == "gemini":
            if not settings.GEMINI_API_KEY:
                raise HTTPException(status_code=503, detail="LLM unavailable: GEMINI_API_KEY missing")
        elif provider == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise HTTPException(status_code=503, detail="LLM unavailable: ANTHROPIC_API_KEY missing")
        else:
            raise HTTPException(status_code=503, detail="LLM unavailable: no valid provider (set MODEL_PROVIDER or pass model)")

    k1_true, k2_true = true_strategy1, true_strategy2
    history = []
    last_union_loss: float = 0.0

    def sse_gen():
        nonlocal last_union_loss
        last_guess_s1 = None
        last_guess_s2 = None
        # 早停統計
        consecutive_same = 0
        prev_guess_s1 = None
        prev_guess_s2 = None
        losses_series: list[float] = []
        normalized_losses_series: list[float] = []  # 新增：追蹤正規化 loss
        EARLY_STOP_N = 15

        for r in range(1, int(rounds) + 1):
            dist1, dist2 = current_dists(k1_true, k2_true)
            m1 = sample_move(dist1)
            m2 = sample_move(dist2)
            res = beats(m1, m2)
            history.append((m1, m2, res))

            guess_s1 = None
            guess_s2 = None
            union_loss = None
            normalized_union_loss = None  # 初始化正規化 loss
            # 其他損失初始化
            ce_loss = None
            brier_loss = None
            ev_loss = None
            normalized_ce_loss = None
            # 不提供 Brier 的 normalized
            normalized_ev_loss = None
            delta = None
            extra_conf = None
            extra_reason = None
            if r > (warmup_rounds or 0):
                print(r)
                hw = history
                try:
                    base_round = len(history) - len(hw) + 1
                    hist_json = [
                        {"round": base_round + i, "move1": mm1, "move2": mm2, "result": rr}
                        for i, (mm1, mm2, rr) in enumerate(hw)
                    ]
                    # 應用 history_limit（若設定），只保留最近 N 筆
                    if history_limit and history_limit > 0:
                        hist_json = hist_json[-int(history_limit):]
                    print("hist_json", hist_json)
                    from ...services.llm import identify_from_history
                    include_reason = (r % (reasoning_interval or 10) == 0 or r == rounds)
                    provider = resolve_provider(model)
                    print("provider", provider)
                    ensure_ident_available_for(provider)
                    print("model", model)
                    ident = identify_from_history(strategy_catalog, hist_json, model, include_reasoning=include_reason)
                    print("ident1", ident)
                except Exception as e:
                    print("error", e)
                    ident = None
                    err_msg = str(e)
                print("ident2", ident)
                if ident:
                    # 兼容：s1_probs/s2_probs 可能是 dict，也可能是單一代碼（字串）。
                    s1_code = ident.get("s1_code") or None
                    s2_code = ident.get("s2_code") or None
                    s1_probs_raw = ident.get("s1_probs")
                    s2_probs_raw = ident.get("s2_probs")
                    if not s1_code:
                        if isinstance(s1_probs_raw, dict) and s1_probs_raw:
                            s1_code = max(s1_probs_raw.items(), key=lambda x: x[1])[0]
                        elif isinstance(s1_probs_raw, str) and s1_probs_raw:
                            s1_code = s1_probs_raw
                    if not s2_code:
                        if isinstance(s2_probs_raw, dict) and s2_probs_raw:
                            s2_code = max(s2_probs_raw.items(), key=lambda x: x[1])[0]
                        elif isinstance(s2_probs_raw, str) and s2_probs_raw:
                            s2_code = s2_probs_raw

                    # 只回傳單一代碼（不再輸出 probs 至前端）
                    guess_s1_code = s1_code or None
                    guess_s2_code = s2_code or None

                    best_pair = (s1_code, s2_code)
                    extra_conf = float(ident.get("confidence") or 0.6)
                    extra_reason = (
                        (ident.get("reasoning") or None)
                        if (r % (reasoning_interval or 50) == 0 or r == rounds)
                        else None
                    )
                else:
                    # 輕量降級：無辨識結果時，當輪不報錯，僅回傳空猜測
                    guess_s1_code = None
                    guess_s2_code = None
                    best_pair = (None, None)
                    extra_conf = None
                    extra_reason = None

                # 計算 loss 和 delta（移到這裡，確保每次都會計算）
                true_dist = matrix[k1_true][k2_true]
                if best_pair[0] and best_pair[1]:
                    pred_dist = matrix[best_pair[0]][best_pair[1]]
                    # 計算四種損失
                    ce_loss = compute_cross_entropy_loss(true_dist, pred_dist)
                    brier_loss = compute_brier_score(true_dist, pred_dist)
                    ev_loss = compute_ev_loss(true_dist, pred_dist)
                    union_loss = compute_union_loss(true_dist, pred_dist)

                    # 計算四種損失與 normalized（共用）
                    losses = compute_losses(true_dist, pred_dist, matrix)
                    ce_loss = losses['ce_loss']
                    brier_loss = losses['brier_loss']
                    ev_loss = losses['ev_loss']
                    union_loss = losses['union_loss']
                    normalized_ce_loss = losses['normalized_ce_loss']
                    normalized_ev_loss = losses['normalized_ev_loss']
                    normalized_union_loss = losses['normalized_union_loss']
                    
                    delta = None if r == (warmup_rounds or 0) + 1 else (union_loss - last_union_loss)
                    last_union_loss = union_loss
                    try:
                        losses_series.append(float(union_loss))
                        normalized_losses_series.append(float(normalized_union_loss)) # 新增：追蹤正規化 loss
                    except Exception:
                        pass
                else:
                    union_loss = None
                    normalized_union_loss = None
                    ce_loss = None
                    brier_loss = None
                    ev_loss = None
                    normalized_ce_loss = None
                    # 不提供 Brier 的 normalized
                    normalized_ev_loss = None
                    delta = None

            # 紀錄本輪最後的猜測（以單一代碼字串；即使在 warmup，也保留 None）
            curr_guess_s1 = locals().get('guess_s1_code')
            curr_guess_s2 = locals().get('guess_s2_code')
            last_guess_s1 = curr_guess_s1
            last_guess_s2 = curr_guess_s2

            rr_payload = {
                'round': r,
                'move1': m1,
                'move2': m2,
                'result': res,
                'guess_s1': last_guess_s1,
                'guess_s2': last_guess_s2,
                'ce_loss': ce_loss,
                'brier_loss': brier_loss,
                'ev_loss': ev_loss,
                'union_loss': union_loss,
                'normalized_ce_loss': normalized_ce_loss,
                # 不輸出 normalized_brier_loss
                'normalized_ev_loss': normalized_ev_loss,
                'normalized_union_loss': normalized_union_loss,  # 新增正規化 loss
                'delta': delta,
                'confidence': extra_conf,
                'reasoning': extra_reason,
                'history_used': (len(hist_json) if (r > (warmup_rounds or 0)) else None),
            }
            yield "event: round\n" + "data: " + json.dumps(rr_payload, ensure_ascii=False) + "\n\n"

            # 早停：在 warmup 之後，若連續 EARLY_STOP_N 輪猜測相同（s1、s2 皆相同），提前結束
            early_stop = False
            if r > (warmup_rounds or 0) and curr_guess_s1 and curr_guess_s2:
                if prev_guess_s1 == curr_guess_s1 and prev_guess_s2 == curr_guess_s2:
                    consecutive_same += 1
                else:
                    consecutive_same = 1
                prev_guess_s1 = curr_guess_s1
                prev_guess_s2 = curr_guess_s2
                if consecutive_same >= EARLY_STOP_N:
                    early_stop = True
            else:
                # 尚未開始辨識或沒有猜測時重置
                consecutive_same = 0 if r <= (warmup_rounds or 0) else consecutive_same

            if early_stop:
                trend = {}
                if losses_series:
                    trend['last'] = losses_series[-1]
                    trend['min'] = min(losses_series)
                    trend['avg_5'] = sum(losses_series[-5:]) / min(5, len(losses_series))
                    # 添加最後一輪的正規化 loss
                    if normalized_losses_series:
                        trend['last_normalized'] = normalized_losses_series[-1]
                final_guess = {'s1': curr_guess_s1 or '', 's2': curr_guess_s2 or ''}
                final_payload = {
                    'model': model,
                    'true_strategy1': k1_true,
                    'true_strategy2': k2_true,
                    'rounds': r,
                    'warmup_rounds': warmup_rounds,
                    'history_limit': history_limit,
                    'reasoning_interval': reasoning_interval,
                    'final_guess': final_guess,
                    'trend': trend,
                    'early_stop': True,
                    'early_stop_round': r,
                }
                yield "event: final\n" + "data: " + json.dumps(final_payload, ensure_ascii=False) + "\n\n"
                return

        # 最終彙總（常規結束）
        final_guess = {'s1': (last_guess_s1 or ''), 's2': (last_guess_s2 or '')}
        trend = {}
        if losses_series:
            trend['last'] = losses_series[-1]
            trend['min'] = min(losses_series)
            trend['avg_5'] = sum(losses_series[-5:]) / min(5, len(losses_series))
            # 添加最後一輪的正規化 loss
            if normalized_losses_series:
                trend['last_normalized'] = normalized_losses_series[-1]
        yield "event: final\n" + "data: " + json.dumps({
            'model': model,
            'true_strategy1': k1_true,
            'true_strategy2': k2_true,
            'rounds': rounds,
            'warmup_rounds': warmup_rounds,
            'history_limit': history_limit,
            'reasoning_interval': reasoning_interval,
            'final_guess': final_guess,
            'trend': trend,
        }, ensure_ascii=False) + "\n\n"

    return StreamingResponse(sse_gen(), media_type="text/event-stream")
