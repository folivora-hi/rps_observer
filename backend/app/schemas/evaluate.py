"""
評估相關的 Pydantic 模型定義

功能：
- 定義評估 API 的請求和回應格式
- 支援策略預測評估
- 提供損失函數計算的資料模型
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any

class EvaluateRequest(BaseModel):
    """評估請求模型"""
    true_strategy1: str
    true_strategy2: str
    pred_strategy1: str
    pred_strategy2: str

class LossMetrics(BaseModel):
    """損失指標模型"""
    ce_loss: float
    brier_loss: float
    ev_loss: float
    union_loss: float

class NormalizedLosses(BaseModel):
    """標準化損失模型"""
    normalized_ce: float
    normalized_ev: float
    normalized_union: float

class Distribution(BaseModel):
    """分佈模型"""
    wins: float
    losses: float
    draws: float

class EvaluateResponse(BaseModel):
    """評估回應模型"""
    true_distribution: Distribution
    pred_distribution: Distribution
    losses: LossMetrics
    normalized_losses: NormalizedLosses

class MatrixEvaluationRequest(BaseModel):
    """矩陣評估請求模型"""
    pred_strategy1: str
    pred_strategy2: str

class MatrixEvaluationResponse(BaseModel):
    """矩陣評估回應模型"""
    matrix: Dict[str, Dict[str, Dict[str, float]]]
    pred_distribution: Distribution
    strategy_names: Dict[str, str]
    normalized_matrix: Dict[str, Dict[str, Dict[str, float]]]
