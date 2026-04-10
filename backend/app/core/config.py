"""
應用程式配置管理模組

功能：
- 載入環境變數
- 定義應用程式設定
- 管理 API 配置
- 處理 CORS 設定
- 管理 LLM 服務配置

配置項目：
- API_PREFIX: API 路徑前綴
- CORS_ALLOW_ORIGINS: 允許的 CORS 來源
- MODEL_PROVIDER: LLM 服務提供商
- OPENAI_API_KEY: OpenAI API 金鑰
"""

import os
from typing import List, Optional
from dotenv import load_dotenv

# 載入 backend/.env 文件
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(backend_dir, '.env')
load_dotenv(env_path)

class Settings:
    API_PREFIX: str = "/api/v1"
    CORS_ALLOW_ORIGINS: List[str] = ["*"]
    
    # LLM 提供商配置
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "fallback")
    
    # OpenAI API 配置 (支援多個金鑰)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_API_KEYS: List[str] = []
    
    # 載入多個 OpenAI API 金鑰
    def _load_openai_keys():
        keys = []
        if os.getenv("OPENAI_API_KEY"):
            keys.append(os.getenv("OPENAI_API_KEY"))
        # 載入額外的金鑰 (OPENAI_API_KEY_2, OPENAI_API_KEY_3, ...)
        i = 2
        while os.getenv(f"OPENAI_API_KEY_{i}"):
            keys.append(os.getenv(f"OPENAI_API_KEY_{i}"))
            i += 1
        return keys
    
    OPENAI_API_KEYS = _load_openai_keys()
    
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")
    
    # OpenRouter / DeepSeek 設定
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_SITE_URL: Optional[str] = os.getenv("OPENROUTER_SITE_URL")
    OPENROUTER_SITE_NAME: Optional[str] = os.getenv("OPENROUTER_SITE_NAME")
    
    # DeepSeek 官方 API 設定
    DEEPSEEK_API_KEY: Optional[str] = os.getenv("DEEPSEEK_API_KEY")
    
    # Gemini API 設定
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")

    # 是否在日誌輸出送往 LLM 的 prompt（預設關閉）
    LLM_LOG_PROMPT: bool = (os.getenv("LLM_LOG_PROMPT", "0").lower() in ("1", "true", "yes", "y"))
    # 送往 LLM 的 prompt 檔案輸出目錄（相對路徑以 backend/ 為基準），預設 backend/logs/llm
    LLM_LOG_DIR: str = os.getenv("LLM_LOG_DIR", "logs/llm")

    # 是否啟用動態策略（X/Y/Z 等）；若關閉，prompt 與候選僅包含靜態策略
    USE_DYNAMIC_STRATEGIES: bool = (os.getenv("USE_DYNAMIC_STRATEGIES", "1").lower() in ("1", "true", "yes", "y"))

settings = Settings()
