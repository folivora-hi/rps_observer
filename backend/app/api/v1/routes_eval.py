"""
評估 API 路由模組

功能：
- 提供策略預測評估 API
- 計算各種損失函數
- 支援矩陣評估功能

API 端點：
- POST /evaluate - 評估單個預測
- POST /evaluate/matrix - 評估完整矩陣
"""

from fastapi import APIRouter
from ...schemas.evaluate import (
    EvaluateRequest, 
    EvaluateResponse,
    MatrixEvaluationRequest,
    MatrixEvaluationResponse
)
from ...domain.metrics import evaluate_prediction, compute_normalized_losses
from ...domain.strategies import calculate_matchup, get_all_strategies, get_strategy_names

router = APIRouter(prefix="/evaluate", tags=["evaluate"])

@router.post("", response_model=EvaluateResponse)
def evaluate_prediction_endpoint(req: EvaluateRequest):
    """評估預測結果"""
    # 驗證策略是否存在
    all_strategies = get_all_strategies()
    strategies = [req.true_strategy1, req.true_strategy2, req.pred_strategy1, req.pred_strategy2]
    
    for strategy in strategies:
        if strategy not in all_strategies:
            raise ValueError(f"策略 {strategy} 不存在")
    
    # 計算完整矩陣（用於標準化）
    matrix = {}
    for s1 in all_strategies.keys():
        matrix[s1] = {}
        for s2 in all_strategies.keys():
            result = calculate_matchup(s1, s2)
            matrix[s1][s2] = result
    
    # 評估預測
    evaluation = evaluate_prediction(
        req.true_strategy1,
        req.true_strategy2,
        req.pred_strategy1,
        req.pred_strategy2,
        matrix
    )
    
    return EvaluateResponse(
        true_distribution=evaluation['true_distribution'],
        pred_distribution=evaluation['pred_distribution'],
        losses=evaluation['losses'],
        normalized_losses=evaluation['normalized_losses']
    )

@router.post("/matrix", response_model=MatrixEvaluationResponse)
def evaluate_matrix_endpoint(req: MatrixEvaluationRequest):
    """評估完整矩陣"""
    # 驗證策略是否存在
    all_strategies = get_all_strategies()
    if req.pred_strategy1 not in all_strategies:
        raise ValueError(f"預測策略 {req.pred_strategy1} 不存在")
    if req.pred_strategy2 not in all_strategies:
        raise ValueError(f"預測策略 {req.pred_strategy2} 不存在")
    
    # 計算完整矩陣
    matrix = {}
    for s1 in all_strategies.keys():
        matrix[s1] = {}
        for s2 in all_strategies.keys():
            result = calculate_matchup(s1, s2)
            matrix[s1][s2] = result
    
    # 計算預測分佈
    pred_result = calculate_matchup(req.pred_strategy1, req.pred_strategy2)
    pred_distribution = {
        'wins': pred_result['wins'],
        'losses': pred_result['losses'],
        'draws': pred_result['draws']
    }
    
    # 計算標準化矩陣
    normalized_matrix = compute_normalized_losses(matrix, pred_distribution)
    
    return MatrixEvaluationResponse(
        matrix=matrix,
        pred_distribution=pred_distribution,
        strategy_names=get_strategy_names(),
        normalized_matrix=normalized_matrix
    )
