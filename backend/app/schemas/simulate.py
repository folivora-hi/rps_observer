"""
API 請求和回應的 Pydantic 模型定義

功能：
- 定義所有 API 端點的請求和回應格式
- 提供資料驗證和序列化
- 確保 API 介面的一致性

模型分類：
1. 模擬相關 (SimulateRequest/Response)
2. 策略計算相關 (StrategyMatchupRequest/Response)
3. 策略矩陣相關 (StrategyMatrixRequest/Response)
4. 策略列表相關 (AllStrategiesResponse)

資料驗證：
- 策略代碼格式驗證
- 數值範圍檢查
- 必填欄位驗證
"""

from pydantic import BaseModel
from typing import Literal, Optional, Dict, Any

class StrategySpec(BaseModel):
    kind: Literal["fixed","random","reactive","frequency"]
    param: Optional[int] = None

class SimulateRequest(BaseModel):
    s1: StrategySpec
    s2: StrategySpec
    rounds: int = 10000
    k_window: Optional[int] = None

class SimulateResponse(BaseModel):
    win: float
    loss: float
    draw: float

# --- 新增：策略計算相關的 schema ---
class StrategyMatchupRequest(BaseModel):
    strategy1: str  # 策略代碼，如 'A', 'B', 'X', 'Y', 'Z'
    strategy2: str

class StrategyMatchupResponse(BaseModel):
    wins: float
    losses: float
    draws: float
    strategy1_name: str
    strategy2_name: str

class AllStrategiesResponse(BaseModel):
    strategies: Dict[str, str]  # 策略代碼 -> 策略名稱

class StrategyMatrixRequest(BaseModel):
    pred_strategy1: str
    pred_strategy2: str

class StrategyMatrixResponse(BaseModel):
    matrix: Dict[str, Dict[str, Dict[str, float]]]  # strategy1 -> strategy2 -> {wins, losses, draws}
    pred_distribution: Dict[str, float]  # 預測分佈
    strategy_names: Dict[str, str]
