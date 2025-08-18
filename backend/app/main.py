"""
FastAPI 主應用程式入口點

功能：
- 設定 FastAPI 應用程式和 CORS 中間件
- 註冊所有 API 路由
- 提供健康檢查端點
- 整合所有模組：simulate, observer, player, eval, strategies

API 端點：
- GET /health - 健康檢查
- POST /api/v1/simulate - 策略模擬
- POST /api/v1/observer/predict - 觀察者預測
- POST /api/v1/player/act - 玩家行動
- POST /api/v1/evaluate - 評估指標
- GET /api/v1/strategies/all - 獲取所有策略
- POST /api/v1/strategies/matchup - 計算策略對戰
- POST /api/v1/strategies/matrix - 計算策略矩陣
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api.v1.routes_simulate import router as simulate_router
from .api.v1.routes_observer import router as observer_router
from .api.v1.routes_player import router as player_router
from .api.v1.routes_eval import router as eval_router
from .api.v1.routes_strategies import router as strategies_router

app = FastAPI(title="RPS Belief API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(simulate_router, prefix=settings.API_PREFIX)
app.include_router(observer_router, prefix=settings.API_PREFIX)
app.include_router(player_router, prefix=settings.API_PREFIX)
app.include_router(eval_router, prefix=settings.API_PREFIX)
app.include_router(strategies_router, prefix=settings.API_PREFIX)
