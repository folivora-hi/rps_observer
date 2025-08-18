"""
策略計算 API 路由模組

功能：
- 提供策略相關的 REST API 端點
- 支援策略對戰結果計算
- 提供完整策略矩陣計算
- 管理策略資訊查詢

API 端點：
- GET /strategies/all - 獲取所有可用策略
- POST /strategies/matchup - 計算兩個策略的對戰結果
- POST /strategies/matrix - 計算完整的策略矩陣

核心功能：
- get_all_strategies_endpoint(): 獲取策略列表
- calculate_strategy_matchup(): 計算策略對戰
- calculate_strategy_matrix(): 計算策略矩陣

資料流程：
1. 接收前端請求
2. 驗證策略存在性
3. 調用 domain 層計算邏輯
4. 返回結構化回應
"""

from fastapi import APIRouter
from ...schemas.simulate import (
    StrategyMatchupRequest, 
    StrategyMatchupResponse, 
    AllStrategiesResponse,
    StrategyMatrixRequest,
    StrategyMatrixResponse
)
from ...domain.strategies import (
    calculate_matchup, 
    get_all_strategies, 
    get_strategy_names,
    BASE_STRATEGIES,
    DYNAMIC_STRATEGIES
)

router = APIRouter(prefix="/strategies", tags=["strategies"])

@router.get("/all", response_model=AllStrategiesResponse)
def get_all_strategies_endpoint():
    """獲取所有可用的策略"""
    strategies = get_strategy_names()
    return AllStrategiesResponse(strategies=strategies)

@router.post("/matchup", response_model=StrategyMatchupResponse)
def calculate_strategy_matchup(req: StrategyMatchupRequest):
    """計算兩個策略的對戰結果"""
    # 驗證策略是否存在
    all_strategies = get_all_strategies()
    if req.strategy1 not in all_strategies:
        raise ValueError(f"策略 {req.strategy1} 不存在")
    if req.strategy2 not in all_strategies:
        raise ValueError(f"策略 {req.strategy2} 不存在")
    
    # 計算對戰結果
    result = calculate_matchup(req.strategy1, req.strategy2)
    
    return StrategyMatchupResponse(
        wins=result['wins'],
        losses=result['losses'],
        draws=result['draws'],
        strategy1_name=all_strategies[req.strategy1]['name'],
        strategy2_name=all_strategies[req.strategy2]['name']
    )

@router.post("/matrix", response_model=StrategyMatrixResponse)
def calculate_strategy_matrix(req: StrategyMatrixRequest):
    """計算完整的策略矩陣"""
    all_strategies = get_all_strategies()
    strategy_names = get_strategy_names()
    
    # 驗證預測策略是否存在
    if req.pred_strategy1 not in all_strategies:
        raise ValueError(f"預測策略 {req.pred_strategy1} 不存在")
    if req.pred_strategy2 not in all_strategies:
        raise ValueError(f"預測策略 {req.pred_strategy2} 不存在")
    
    # 計算預測分佈
    pred_result = calculate_matchup(req.pred_strategy1, req.pred_strategy2)
    pred_distribution = {
        'wins': pred_result['wins'] / 100,
        'losses': pred_result['losses'] / 100,
        'draws': pred_result['draws'] / 100
    }
    
    # 計算完整矩陣
    matrix = {}
    for s1 in all_strategies.keys():
        matrix[s1] = {}
        for s2 in all_strategies.keys():
            result = calculate_matchup(s1, s2)
            matrix[s1][s2] = {
                'wins': result['wins'],
                'losses': result['losses'],
                'draws': result['draws']
            }
    
    return StrategyMatrixResponse(
        matrix=matrix,
        pred_distribution=pred_distribution,
        strategy_names=strategy_names
    )
