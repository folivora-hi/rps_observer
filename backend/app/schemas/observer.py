"""
觀察者預測相關的 Pydantic 模型定義

功能：
- 定義觀察者預測 API 的請求和回應格式
- 支援策略代碼和描述文字輸入
- 提供預測結果和信心度模型
"""

from pydantic import BaseModel
from typing import Dict, List, Optional

# --- 相容保留：單次配對分佈預測用的請求/回應模型（/observer/predict 仍會用到） ---
class ObserverPredictReq(BaseModel):
    """單次配對分佈預測請求模型"""
    description_s1: Optional[str] = None  # 策略1描述
    description_s2: Optional[str] = None  # 策略2描述
    strategy1: Optional[str] = None       # 策略1代碼 (如 'A', 'B', 'X')
    strategy2: Optional[str] = None       # 策略2代碼 (如 'A', 'B', 'X')
    prompt_style: Optional[str] = None    # 提示風格
    model: Optional[str] = None           # 模型名稱（例如 'deepseek', '4o-mini'）

class ObserverPredictResp(BaseModel):
    """單次配對分佈預測回應模型"""
    win: float
    loss: float
    draw: float
    confidence: float
    reasoning: Optional[str] = None  # 推理過程

class StrategyProbs(BaseModel):
    probs: Dict[str, float]   # A..Z 的機率
    top1: str                 # 機率最高的策略代碼

class ObserverRunReq(BaseModel):
    true_strategy1: str
    true_strategy2: str
    rounds: int = 50          # 最高輪次 R
    warmup_rounds: int = 10   # 前 10 輪不辨識，只蒐集歷史
    k_window: Optional[int] = None
    model: Optional[str] = "deepseek"  # 'deepseek' | '4o-mini'

class RoundRecord(BaseModel):
    round: int
    move1: int                # 0/1/2
    move2: int
    result: int               # 1 / 0 / -1 (對 s1 而言)
    # NOTE: 第 11 輪後才會填入模型辨識結果；前 10 輪 warmup 期間為 None
    guess_s1: Optional[StrategyProbs] = None
    guess_s2: Optional[StrategyProbs] = None
    union_loss: Optional[float] = None
    delta: Optional[float] = None      # 相較上一輪 union_loss 的變化（負值=變好）
    confidence: Optional[float] = None
    reasoning: Optional[str] = None    # 可截斷簡短摘要

class ObserverRunResp(BaseModel):
    model: Optional[str]
    true_strategy1: str
    true_strategy2: str
    rounds: int
    warmup_rounds: int
    k_window: Optional[int]
    per_round: List[RoundRecord]
    trend: Dict[str, float]            # 例如 {"last": x, "min": y, "avg_5": z}
    final_guess: Dict[str, str]        # {"s1": "H", "s2": "Z"}
