"""
觀察者預測相關的 Pydantic 模型定義

功能：
- 定義觀察者預測 API 的請求和回應格式
- 支援策略代碼和描述文字輸入
- 提供預測結果和信心度模型
"""

from pydantic import BaseModel
from typing import Dict, List, Optional

class StrategyProbs(BaseModel):
    # 若後端改為只回傳單一代碼，前端 SSE 直接傳字串，不再用此模型於串流欄位
    probs: Dict[str, float]
    top1: str

class ObserverRunReq(BaseModel):
    true_strategy1: str
    true_strategy2: str
    rounds: int = 50          # 最高輪次 R
    warmup_rounds: int = 10   # 前 10 輪不辨識，只蒐集歷史
    history_limit: Optional[int] = None  # 僅將最近 N 輪送入 LLM 辨識
    reasoning_interval: Optional[int] = 50  # 每隔多少輪攜帶 reasoning
    model: Optional[str] = "deepseek"  # 'deepseek' | '4o-mini'

class RoundRecord(BaseModel):
    round: int
    move1: int                # 0/1/2
    move2: int
    result: int               # 1 / 0 / -1 (對 s1 而言)
    # NOTE: 第 11 輪後才會填入模型辨識結果；前 10 輪 warmup 期間為 None
    # 串流輸出現改為單一代碼字串
    guess_s1: Optional[str] = None
    guess_s2: Optional[str] = None

    # 各種損失
    ce_loss: Optional[float] = None
    brier_loss: Optional[float] = None
    ev_loss: Optional[float] = None
    union_loss: Optional[float] = None

    # 各種損失（標準化）
    normalized_ce_loss: Optional[float] = None
    normalized_ev_loss: Optional[float] = None
    normalized_union_loss: Optional[float] = None  # 新增：正規化的 union_loss
    delta: Optional[float] = None      # 相較上一輪 union_loss 的變化（負值=變好）
    confidence: Optional[float] = None
    reasoning: Optional[str] = None    # 可截斷簡短摘要
    history_used: Optional[int] = None # 本輪送入 LLM 的歷史筆數

class ObserverRunResp(BaseModel):
    model: Optional[str]
    true_strategy1: str
    true_strategy2: str
    rounds: int
    warmup_rounds: int
    history_limit: Optional[int]
    reasoning_interval: Optional[int]
    per_round: List[RoundRecord]
    trend: Dict[str, float]            # 例如 {"last": x, "min": y, "avg_5": z}
    final_guess: Dict[str, str]        # {"s1": "H", "s2": "Z"}
