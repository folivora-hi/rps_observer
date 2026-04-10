"""
管理員 API 路由

功能：
- API 金鑰狀態監控
- 系統狀態檢查
- 管理員功能
"""

from fastapi import APIRouter, HTTPException
from ...services.api_key_manager import get_key_manager
from ...core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/api-keys/status")
def get_api_key_status():
    """獲取所有 API 金鑰狀態"""
    try:
        openai_manager = get_key_manager("openai")
        deepseek_manager = get_key_manager("deepseek-official")
        openrouter_manager = get_key_manager("openrouter")
        
        status = {
            "openai": openai_manager.get_key_status() if openai_manager else {},
            "deepseek-official": deepseek_manager.get_key_status() if deepseek_manager else {},
            "openrouter": openrouter_manager.get_key_status() if openrouter_manager else {},
        }
        
        return {
            "status": "success",
            "data": status
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get API key status: {str(e)}")


@router.post("/api-keys/reset")
def reset_api_keys():
    """重置所有 API 金鑰狀態"""
    try:
        openai_manager = get_key_manager("openai")
        deepseek_manager = get_key_manager("deepseek-official")
        openrouter_manager = get_key_manager("openrouter")
        
        if openai_manager:
            openai_manager.reset_all_keys()
        if deepseek_manager:
            deepseek_manager.reset_all_keys()
        if openrouter_manager:
            openrouter_manager.reset_all_keys()
        
        return {
            "status": "success",
            "message": "All API keys have been reset"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset API keys: {str(e)}")


@router.get("/system/status")
def get_system_status():
    """獲取系統狀態"""
    try:
        # 檢查各提供者的 API 金鑰可用性
        openai_manager = get_key_manager("openai")
        deepseek_manager = get_key_manager("deepseek-official")
        openrouter_manager = get_key_manager("openrouter")
        
        openai_available = openai_manager and openai_manager.get_available_key() is not None
        deepseek_available = deepseek_manager and deepseek_manager.get_available_key() is not None
        openrouter_available = openrouter_manager and openrouter_manager.get_available_key() is not None
        
        return {
            "status": "success",
            "data": {
                "providers": {
                    "openai": {
                        "available": openai_available,
                        "key_count": len(openai_manager.keys) if openai_manager else 0
                    },
                    "deepseek-official": {
                        "available": deepseek_available,
                        "key_count": len(deepseek_manager.keys) if deepseek_manager else 0
                    },
                    "openrouter": {
                        "available": openrouter_available,
                        "key_count": len(openrouter_manager.keys) if openrouter_manager else 0
                    }
                },
                "model_provider": settings.MODEL_PROVIDER,
                "llm_log_prompt": settings.LLM_LOG_PROMPT,
                "use_dynamic_strategies": settings.USE_DYNAMIC_STRATEGIES
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")
