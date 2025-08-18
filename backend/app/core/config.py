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
load_dotenv()

class Settings:
    API_PREFIX: str = "/api/v1"
    CORS_ALLOW_ORIGINS: List[str] = ["*"]
    
    # LLM 提供商配置
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "fallback")
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")
    
    # OpenRouter / DeepSeek 設定
    OPENROUTER_API_KEY: Optional[str] = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_SITE_URL: Optional[str] = os.getenv("OPENROUTER_SITE_URL")
    OPENROUTER_SITE_NAME: Optional[str] = os.getenv("OPENROUTER_SITE_NAME")

    # 是否在日誌輸出送往 LLM 的 prompt（預設關閉）
    LLM_LOG_PROMPT: bool = (os.getenv("LLM_LOG_PROMPT", "0").lower() in ("1", "true", "yes", "y"))
    # 送往 LLM 的 prompt 檔案輸出目錄（相對路徑以 backend/ 為基準），預設 backend/logs/llm
    LLM_LOG_DIR: str = os.getenv("LLM_LOG_DIR", "logs/llm")

settings = Settings()
