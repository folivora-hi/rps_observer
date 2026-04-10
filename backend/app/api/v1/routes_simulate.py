from fastapi import APIRouter
from ...schemas.simulate import SimulateRequest, SimulateResponse
from ...domain.strategies import FixedStrategy, RandomStrategy, ReactiveStrategy, FrequencyStrategy
from ...domain.simulator import simulate

router = APIRouter(tags=["simulate"])

def build_strategy(spec):
    if spec.kind == "fixed": return FixedStrategy(spec.param or 0)
    if spec.kind == "random": return RandomStrategy()
    if spec.kind == "reactive": return ReactiveStrategy()
    if spec.kind == "frequency": return FrequencyStrategy()
    raise ValueError("unknown strategy")

@router.post("/simulate", response_model=SimulateResponse)
def simulate_endpoint(req: SimulateRequest):
    s1 = build_strategy(req.s1)
    s2 = build_strategy(req.s2)
    res = simulate(s1, s2, rounds=req.rounds)
    return SimulateResponse(**res)
