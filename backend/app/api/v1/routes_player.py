from fastapi import APIRouter
from ...schemas.player import PlayerActReq, PlayerActResp
from ...services.llm import decide_next_move

router = APIRouter(prefix="/player", tags=["player"])

@router.post("/act", response_model=PlayerActResp)
def player_act(req: PlayerActReq):
    move, rationale = decide_next_move(req.history, req.k_window, req.belief)
    return PlayerActResp(move=move, rationale=rationale)
