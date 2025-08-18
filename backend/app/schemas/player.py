from pydantic import BaseModel
from typing import List, Tuple, Optional, Dict, Any

class PlayerActReq(BaseModel):
    history: List[Tuple[int,int]] = []
    k_window: Optional[int] = 5
    belief: Optional[Dict[str, Any]] = None

class PlayerActResp(BaseModel):
    move: int
    rationale: Optional[str] = None
