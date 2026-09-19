"""ai.config 模块（T5-11 批次 4）：AI 提供商配置管理，表 ``ai_configs``。

API Key 以 AES-256-GCM（SHA256(SECRET_KEY) 派生密钥）加密落库，
响应只回 ``has_api_key`` 布尔位，明文永不回传；更新时留空保持原值。
真实 AI 调用引擎为二期（本模块只管配置档案）。
"""
