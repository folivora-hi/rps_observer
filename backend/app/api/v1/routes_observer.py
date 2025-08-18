"""
觀察者（Observer）API

本模組現在同時承擔：
- 單次配對分佈預測（/observer/predict）
- 逐輪「觀察 + 辨識」主流程（/observer/run）

更新重點：
- /observer/run 已改為：前 warmup 回合只蒐集歷史；第 11 輪起，每輪輸出對「雙邊策略的辨識結果」與 union_loss
- union_loss 以 backend/app/domain/metrics.py 中 CE/Brier/EV 三者平均為準
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from ...schemas.observer import (
    ObserverPredictReq, ObserverPredictResp,
    ObserverRunReq, ObserverRunResp, RoundRecord, StrategyProbs
)
from ...services.llm import estimate_payoff, identify_from_history
from ...domain.strategies import (
    get_all_strategies, get_strategy_names,
    calculate_matchup, beats,
    BASE_STRATEGIES, DYNAMIC_STRATEGIES,
    resolve_dist, iterate_dists
)
from ...domain.metrics import compute_union_loss

router = APIRouter(prefix="/observer", tags=["observer"])

@router.post("/predict", response_model=ObserverPredictResp)
def observer_predict(req: ObserverPredictReq):
    """觀察者預測端點"""
    # 驗證輸入
    if req.strategy1 and req.strategy2:
        # 使用策略代碼
        all_strategies = get_all_strategies()
        if req.strategy1 not in all_strategies:
            raise HTTPException(status_code=400, detail=f"策略 {req.strategy1} 不存在")
        if req.strategy2 not in all_strategies:
            raise HTTPException(status_code=400, detail=f"策略 {req.strategy2} 不存在")
        
        # 將策略代碼轉換為描述
        description_s1 = all_strategies[req.strategy1]['name']
        description_s2 = all_strategies[req.strategy2]['name']
    elif req.description_s1 and req.description_s2:
        # 使用描述文字
        description_s1 = req.description_s1
        description_s2 = req.description_s2
    else:
        raise HTTPException(
            status_code=400, 
            detail="必須提供策略代碼 (strategy1, strategy2) 或描述文字 (description_s1, description_s2)"
        )
    
    # 調用 LLM 服務進行預測
    try:
        result = estimate_payoff(description_s1, description_s2, req.prompt_style, req.model)
        return ObserverPredictResp(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"預測失敗: {str(e)}")


@router.post("/run", response_model=ObserverRunResp)
def observer_run(req: ObserverRunReq):
    """
    逐輪觀察 + 辨識：
    - 前 warmup 回合：只依真實策略進行對戰，蒐集歷史
    - 第 warmup+1 輪起：每輪根據歷史辨識雙邊最可能策略，並計算 union_loss（以真實(A/B) 對「猜測 top-1 組合」的分佈）

    註：目前辨識預設使用 fallback（根據歷史勝負平與全空間對戰分佈比對），若環境提供 LLM 金鑰，
        可在 services/llm.py 擴充 identify 函式改為 LLM 推理。
    """
    all_strategies = get_all_strategies()
    if req.true_strategy1 not in all_strategies or req.true_strategy2 not in all_strategies:
        raise HTTPException(status_code=400, detail="真實策略不存在")

    # 準備策略名稱、完整策略定義，以及完整對戰矩陣（供 union_loss 計算與辨識比對）
    strategy_names = get_strategy_names()
    # 完整策略定義表（靜態含分佈、動態含規則文字）
    dynamic_rules = {
        'X': '出剋制對手上一輪的拳（若對手上一輪偏剪刀，則我偏石頭；依此類推）',
        'Y': '出會被對手上一輪剋制的拳（若對手上一輪偏剪刀，則我偏布；依此類推）',
        'Z': '出與對手上一輪相同的拳（跟隨對手上一輪分佈）',
    }
    strategy_catalog = {}
    for k, v in BASE_STRATEGIES.items():
        strategy_catalog[k] = {
            'type': 'static',
            'name': v['name'],
            'dist': {'rock': v['rock'], 'paper': v['paper'], 'scissors': v['scissors']},
        }
    for k, v in DYNAMIC_STRATEGIES.items():
        strategy_catalog[k] = {
            'type': 'dynamic',
            'name': v['name'],
            'rule': dynamic_rules.get(k, ''),
        }
    codes = list(all_strategies.keys())
    matrix = {s1: {s2: calculate_matchup(s1, s2) for s2 in codes} for s1 in codes}

    # 便捷：根據真實策略生成當回合出拳分佈
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

    # 便捷：抽樣出拳
    import random
    def sample_move(dist):
        return random.choices([0,1,2], weights=[dist['rock'], dist['paper'], dist['scissors']])[0]

    # 便捷：由一段歷史估計「經驗勝負平分佈」（百分比，與矩陣格式一致）
    def empirical_dist(hist):
        if not hist:
            return {'wins': 33.3, 'losses': 33.3, 'draws': 33.4}
        wins = sum(1 for _,_,r in hist if r == 1)
        losses = sum(1 for _,_,r in hist if r == -1)
        draws = sum(1 for _,_,r in hist if r == 0)
        total = max(1, wins + losses + draws)
        return {
            'wins': wins * 100.0 / total,
            'losses': losses * 100.0 / total,
            'draws': draws * 100.0 / total,
        }

    # 便捷：根據歷史用「loss 加權」產生雙邊機率並選擇最可能的組合
    def fallback_identify(hist_window):
        ed = empirical_dist(hist_window)
        # 對所有 (s1,s2) 計算 union_loss，分數越小越好
        pair_losses = {}
        for s1 in codes:
            for s2 in codes:
                loss = compute_union_loss(ed, matrix[s1][s2])
                pair_losses[(s1, s2)] = loss
        # 轉為權重（softmax on -loss）
        tau = 0.5
        import math
        weights = {p: math.exp(-pair_losses[p]/tau) for p in pair_losses}
        z = sum(weights.values()) or 1.0
        weights = {p: w/z for p, w in weights.items()}
        # 邊際化為左右機率
        s1_probs = {c: 0.0 for c in codes}
        s2_probs = {c: 0.0 for c in codes}
        for (s1, s2), w in weights.items():
            s1_probs[s1] += w
            s2_probs[s2] += w
        # 取最可能的成對（直接用最小 loss 的組合作為 top-1）
        best_pair = min(pair_losses, key=pair_losses.get)
        top_s1, top_s2 = best_pair
        # 正規化（保險）
        sum1 = sum(s1_probs.values()) or 1.0
        sum2 = sum(s2_probs.values()) or 1.0
        s1_probs = {k: v/sum1 for k, v in s1_probs.items()}
        s2_probs = {k: v/sum2 for k, v in s2_probs.items()}
        return (
            StrategyProbs(probs=s1_probs, top1=top_s1),
            StrategyProbs(probs=s2_probs, top1=top_s2),
            best_pair
        )

    k1_true, k2_true = req.true_strategy1, req.true_strategy2
    history = []  # [(move1, move2, result)]
    per_round: list[RoundRecord] = []
    last_union_loss: float = 0.0

    for r in range(1, int(req.rounds) + 1):
        # 1) 先用真實策略打一輪，蒐集歷史
        dist1, dist2 = current_dists(k1_true, k2_true)
        m1 = sample_move(dist1)
        m2 = sample_move(dist2)
        res = beats(m1, m2)
        history.append((m1, m2, res))

        # 2) warmup 期間不辨識
        if r <= (req.warmup_rounds or 0):
            per_round.append(RoundRecord(round=r, move1=m1, move2=m2, result=res))
            continue

        # 3) 取 k-window 歷史做辨識（含本輪）
        hw = history[-req.k_window:] if req.k_window else history
        # 嘗試 LLM 辨識（包含策略代號表與逐輪出拳/結果）
        try:
            # 構建 JSON 歷史，使 LLM 明確知悉每輪數據
            base_round = len(history) - len(hw) + 1
            hist_json = [
                {"round": base_round + i, "move1": m1, "move2": m2, "result": res}
                for i, (m1, m2, res) in enumerate(hw)
            ]
            ident = identify_from_history(strategy_catalog, hist_json, req.model)
        except Exception:
            ident = None

        if ident and ident.get('s1_code') in codes and ident.get('s2_code') in codes:
            # 以 LLM 結果建立一熱分佈（便於前端顯示百分比）
            s1_probs = {c: 0.0 for c in codes}; s1_probs[ident['s1_code']] = 1.0
            s2_probs = {c: 0.0 for c in codes}; s2_probs[ident['s2_code']] = 1.0
            guess_s1 = StrategyProbs(probs=s1_probs, top1=ident['s1_code'])
            guess_s2 = StrategyProbs(probs=s2_probs, top1=ident['s2_code'])
            best_pair = (ident['s1_code'], ident['s2_code'])
            extra_conf = float(ident.get('confidence') or 0.6)
            extra_reason = ident.get('reasoning') or None
        else:
            # LLM 無法辨識或失敗，回退本地辨識
            guess_s1, guess_s2, best_pair = fallback_identify(hw)
            extra_conf = None
            extra_reason = None

        # 4) 以真實 vs 猜測 top-1 組合計 union_loss
        true_dist = matrix[k1_true][k2_true]
        pred_dist = matrix[best_pair[0]][best_pair[1]]
        union_loss = compute_union_loss(true_dist, pred_dist)
        delta = None if r == (req.warmup_rounds or 0) + 1 else (union_loss - last_union_loss)
        last_union_loss = union_loss

        per_round.append(RoundRecord(
            round=r,
            move1=m1,
            move2=m2,
            result=res,
            guess_s1=guess_s1,
            guess_s2=guess_s2,
            union_loss=union_loss,
            delta=delta,
            confidence=extra_conf,
            reasoning=extra_reason,
        ))

    # 趨勢摘要
    losses = [r.union_loss for r in per_round if r.union_loss is not None]
    trend = {}
    if losses:
        trend['last'] = losses[-1]
        trend['min'] = min(losses)
        trend['avg_5'] = sum(losses[-5:]) / min(5, len(losses))

    final_guess = {'s1': per_round[-1].guess_s1.top1 if per_round[-1].guess_s1 else '',
                   's2': per_round[-1].guess_s2.top1 if per_round[-1].guess_s2 else ''}

    return ObserverRunResp(
        model=req.model,
        true_strategy1=k1_true,
        true_strategy2=k2_true,
        rounds=req.rounds,
        warmup_rounds=req.warmup_rounds,
        k_window=req.k_window,
        per_round=per_round,
        trend=trend,
        final_guess=final_guess,
    )


@router.get("/stream")
def observer_run_stream(true_strategy1: str, true_strategy2: str, rounds: int = 50, warmup_rounds: int = 10, k_window: int | None = None, model: str | None = "deepseek"):
    """以 SSE 逐輪推送辨識與結果，便於前端即時展示。GET 參數對應 /observer/run。"""
    all_strategies = get_all_strategies()
    if true_strategy1 not in all_strategies or true_strategy2 not in all_strategies:
        raise HTTPException(status_code=400, detail="真實策略不存在")

    # 準備策略定義與對戰矩陣
    strategy_names = get_strategy_names()
    codes = list(all_strategies.keys())
    matrix = {s1: {s2: calculate_matchup(s1, s2) for s2 in codes} for s1 in codes}

    dynamic_rules = {
        'X': '出剋制對手上一輪的拳（若對手上一輪偏剪刀，則我偏石頭；依此類推）',
        'Y': '出會被對手上一輪剋制的拳（若對手上一輪偏剪刀，則我偏布；依此類推）',
        'Z': '出與對手上一輪相同的拳（跟隨對手上一輪分佈）',
    }
    strategy_catalog = {}
    for k, v in BASE_STRATEGIES.items():
        strategy_catalog[k] = {
            'type': 'static',
            'name': v['name'],
            'dist': {'rock': v['rock'], 'paper': v['paper'], 'scissors': v['scissors']},
        }
    for k, v in DYNAMIC_STRATEGIES.items():
        strategy_catalog[k] = {
            'type': 'dynamic',
            'name': v['name'],
            'rule': dynamic_rules.get(k, ''),
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

    def empirical_dist(hist):
        if not hist:
            return {'wins': 33.3, 'losses': 33.3, 'draws': 33.4}
        wins = sum(1 for _,_,r in hist if r == 1)
        losses = sum(1 for _,_,r in hist if r == -1)
        draws = sum(1 for _,_,r in hist if r == 0)
        total = max(1, wins + losses + draws)
        return {
            'wins': wins * 100.0 / total,
            'losses': losses * 100.0 / total,
            'draws': draws * 100.0 / total,
        }

    def fallback_identify(hist_window):
        ed = empirical_dist(hist_window)
        pair_losses = {}
        for s1 in codes:
            for s2 in codes:
                loss = compute_union_loss(ed, matrix[s1][s2])
                pair_losses[(s1, s2)] = loss
        # softmax on -loss
        tau = 0.5
        import math
        weights = {p: math.exp(-pair_losses[p]/tau) for p in pair_losses}
        z = sum(weights.values()) or 1.0
        weights = {p: w/z for p, w in weights.items()}
        s1_probs = {c: 0.0 for c in codes}
        s2_probs = {c: 0.0 for c in codes}
        for (s1, s2), w in weights.items():
            s1_probs[s1] += w
            s2_probs[s2] += w
        best_pair = min(pair_losses, key=pair_losses.get)
        top_s1, top_s2 = best_pair
        sum1 = sum(s1_probs.values()) or 1.0
        sum2 = sum(s2_probs.values()) or 1.0
        s1_probs = {k: v/sum1 for k, v in s1_probs.items()}
        s2_probs = {k: v/sum2 for k, v in s2_probs.items()}
        return (
            StrategyProbs(probs=s1_probs, top1=top_s1),
            StrategyProbs(probs=s2_probs, top1=top_s2),
            best_pair
        )

    k1_true, k2_true = true_strategy1, true_strategy2
    history = []
    last_union_loss: float = 0.0

    def sse_gen():
        nonlocal last_union_loss
        last_guess_s1 = None
        last_guess_s2 = None
        # 初始事件：提供策略名稱對照，便於前端顯示（可選）
        init_payload = {"strategy_names": strategy_names}
        yield "event: init\n" + "data: " + json.dumps(init_payload, ensure_ascii=False) + "\n\n"

        for r in range(1, int(rounds) + 1):
            dist1, dist2 = current_dists(k1_true, k2_true)
            m1 = sample_move(dist1)
            m2 = sample_move(dist2)
            res = beats(m1, m2)
            history.append((m1, m2, res))

            guess_s1 = None
            guess_s2 = None
            union_loss = None
            delta = None
            extra_conf = None
            extra_reason = None

            if r > (warmup_rounds or 0):
                hw = history[-k_window:] if k_window else history
                try:
                    base_round = len(history) - len(hw) + 1
                    hist_json = [
                        {"round": base_round + i, "move1": mm1, "move2": mm2, "result": rr}
                        for i, (mm1, mm2, rr) in enumerate(hw)
                    ]
                    from ...services.llm import identify_from_history
                    ident = identify_from_history(strategy_catalog, hist_json, model)
                except Exception:
                    ident = None

                if ident and ident.get('s1_code') in codes and ident.get('s2_code') in codes:
                    s1_probs = {c: 0.0 for c in codes}; s1_probs[ident['s1_code']] = 1.0
                    s2_probs = {c: 0.0 for c in codes}; s2_probs[ident['s2_code']] = 1.0
                    guess_s1 = StrategyProbs(probs=s1_probs, top1=ident['s1_code'])
                    guess_s2 = StrategyProbs(probs=s2_probs, top1=ident['s2_code'])
                    best_pair = (ident['s1_code'], ident['s2_code'])
                    extra_conf = float(ident.get('confidence') or 0.6)
                    extra_reason = ident.get('reasoning') or None
                else:
                    guess_s1, guess_s2, best_pair = fallback_identify(hw)
                    extra_conf = None
                    extra_reason = None

                true_dist = matrix[k1_true][k2_true]
                pred_dist = matrix[best_pair[0]][best_pair[1]]
                union_loss = compute_union_loss(true_dist, pred_dist)
                delta = None if r == (warmup_rounds or 0) + 1 else (union_loss - last_union_loss)
                last_union_loss = union_loss

            # 紀錄本輪最後的猜測（即使在 warmup，也保留 None）
            last_guess_s1 = guess_s1
            last_guess_s2 = guess_s2

            rr_payload = {
                'round': r,
                'move1': m1,
                'move2': m2,
                'result': res,
                'guess_s1': guess_s1.dict() if guess_s1 else None,
                'guess_s2': guess_s2.dict() if guess_s2 else None,
                'union_loss': union_loss,
                'delta': delta,
                'confidence': extra_conf,
                'reasoning': extra_reason,
            }
            yield "event: round\n" + "data: " + json.dumps(rr_payload, ensure_ascii=False) + "\n\n"

        # 最終彙總
        final_guess = {'s1': last_guess_s1.top1 if last_guess_s1 else '', 's2': last_guess_s2.top1 if last_guess_s2 else ''}
        trend = {}
        if last_union_loss:
            trend['last'] = last_union_loss
        yield "event: final\n" + "data: " + json.dumps({
            'model': model,
            'true_strategy1': k1_true,
            'true_strategy2': k2_true,
            'rounds': rounds,
            'warmup_rounds': warmup_rounds,
            'k_window': k_window,
            'final_guess': final_guess,
            'trend': trend,
        }, ensure_ascii=False) + "\n\n"

    return StreamingResponse(sse_gen(), media_type="text/event-stream")
