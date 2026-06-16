"""
草稿预览链接生成器
为未发布的文章生成临时预览链接

修复: 添加文件持久化支持，避免服务重启后所有预览令牌失效
"""

import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from src.unified_logger import default_logger as logger


# 预览令牌持久化文件路径
_PREVIEW_DATA_DIR = Path(os.environ.get('FASTBLOG_DATA_DIR', 'data'))
_PREVIEW_DATA_FILE = _PREVIEW_DATA_DIR / 'preview_tokens.json'


def _load_tokens() -> Dict[str, Dict[str, Any]]:
    """从磁盘加载预览令牌"""
    try:
        if _PREVIEW_DATA_FILE.exists():
            raw = _PREVIEW_DATA_FILE.read_text('utf-8')
            data = json.loads(raw)
            # 恢复 datetime 对象
            for token, info in data.items():
                for key in ('created_at', 'expires_at'):
                    if key in info and isinstance(info[key], str):
                        try:
                            info[key] = datetime.fromisoformat(info[key])
                        except (ValueError, TypeError):
                            info[key] = None
            return data
    except Exception as e:
        logger.warning(f"加载预览令牌持久化文件失败: {e}")
    return {}


def _save_tokens(tokens: Dict[str, Dict[str, Any]]) -> None:
    """保存预览令牌到磁盘"""
    try:
        _PREVIEW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        serializable = {}
        for token, info in tokens.items():
            entry = dict(info)
            for key in ('created_at', 'expires_at'):
                if isinstance(entry.get(key), datetime):
                    entry[key] = entry[key].isoformat()
            serializable[token] = entry
        _PREVIEW_DATA_FILE.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), 'utf-8')
    except Exception as e:
        logger.warning(f"保存预览令牌持久化文件失败: {e}")


class DraftPreviewService:
    """
    草稿预览服务
    
    功能:
    1. 生成唯一的预览URL
    2. 设置过期时间
    3. 支持密码保护
    4. 记录访问统计
    """

    def __init__(self):
        # 从磁盘加载预览令牌（持久化存储，避免重启丢失）
        self.preview_tokens: Dict[str, Dict[str, Any]] = _load_tokens()
        logger.info(f"已加载 {len(self.preview_tokens)} 个预览令牌")

    def generate_preview_token(
            self,
            article_id: int,
            expires_hours: int = 24,
            password: Optional[str] = None,
            max_views: Optional[int] = None
    ) -> str:
        """
        生成草稿预览令牌
        
        Args:
            article_id: 文章ID
            expires_hours: 过期时间(小时)
            password: 可选的访问密码
            max_views: 最大访问次数
            
        Returns:
            预览令牌字符串
        """
        # 生成随机令牌
        token = secrets.token_urlsafe(32)

        # 计算过期时间
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expires_hours)

        # 如果有密码，使用带 salt 的 SHA256 哈希
        password_hash = None
        if password:
            salt = secrets.token_hex(16)
            pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
            password_hash = f"{salt}:{pwd_hash}"

        # 存储令牌信息
        self.preview_tokens[token] = {
            'article_id': article_id,
            'created_at': datetime.now(timezone.utc),
            'expires_at': expires_at,
            'password_hash': password_hash,
            'max_views': max_views,
            'view_count': 0,
            'is_active': True,
        }

        logger.info(f"生成预览令牌: {token[:8]}... for article {article_id}")

        # 持久化保存
        _save_tokens(self.preview_tokens)

        return token

    def validate_preview_token(
            self,
            token: str,
            password: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        验证预览令牌
        
        Args:
            token: 预览令牌
            password: 提供的密码(如果需要)
            
        Returns:
            令牌信息字典,如果无效则返回None
        """
        # 检查令牌是否存在
        if token not in self.preview_tokens:
            logger.warning(f"无效的预览令牌: {token[:8]}...")
            return None

        token_info = self.preview_tokens[token]

        # 检查是否激活
        if not token_info['is_active']:
            logger.warning(f"预览令牌已停用: {token[:8]}...")
            return None

        # 检查是否过期
        if datetime.now(timezone.utc) > token_info['expires_at']:
            logger.warning(f"预览令牌已过期: {token[:8]}...")
            token_info['is_active'] = False
            return None

        # 检查访问次数限制
        if token_info['max_views'] and token_info['view_count'] >= token_info['max_views']:
            logger.warning(f"预览令牌已达最大访问次数: {token[:8]}...")
            token_info['is_active'] = False
            return None

        # 验证密码(如果需要)
        if token_info['password_hash']:
            if not password:
                logger.warning(f"预览令牌需要密码: {token[:8]}...")
                return None

            stored = token_info['password_hash']
            if ':' in stored:
                salt, expected_hash = stored.split(':', 1)
                provided_hash = hashlib.sha256((salt + password).encode()).hexdigest()
                if provided_hash != expected_hash:
                    logger.warning(f"预览令牌密码错误: {token[:8]}...")
                    return None
            else:
                # 兼容旧格式（无 salt）
                if hashlib.sha256(password.encode()).hexdigest() != stored:
                    logger.warning(f"预览令牌密码错误: {token[:8]}...")
                    return None

        # 增加访问计数
        token_info['view_count'] += 1
        # 持久化保存（异步场景下同步写文件可能阻塞，但预览访问频率低可以接受）
        _save_tokens(self.preview_tokens)

        return token_info

    def get_preview_url(self, token: str, base_url: str = "") -> str:
        """
        获取完整的预览URL
        
        Args:
            token: 预览令牌
            base_url: 网站基础URL（由调用者从请求中提取）
            
        Returns:
            完整的预览URL
        """
        if not base_url:
            return f"/api/v2/articles/preview/{token}"
        return f"{base_url}/api/v2/articles/preview/{token}"

    def revoke_token(self, token: str) -> bool:
        """
        撤销预览令牌
        
        Args:
            token: 预览令牌
            
        Returns:
            是否成功撤销
        """
        if token in self.preview_tokens:
            self.preview_tokens[token]['is_active'] = False
            logger.info(f"预览令牌已撤销: {token[:8]}...")
            _save_tokens(self.preview_tokens)
            return True
        return False

    def cleanup_expired_tokens(self) -> int:
        """
        清理过期的令牌
        
        Returns:
            清理的令牌数量
        """
        now = datetime.now(timezone.utc)
        expired_tokens = [
            token for token, info in self.preview_tokens.items()
            if not info['is_active'] or now > info['expires_at']
        ]

        for token in expired_tokens:
            del self.preview_tokens[token]

        if expired_tokens:
            _save_tokens(self.preview_tokens)

        logger.info(f"清理了 {len(expired_tokens)} 个过期预览令牌")
        return len(expired_tokens)

    def get_token_stats(self, token: str) -> Optional[Dict[str, Any]]:
        """
        获取令牌的统计信息
        
        Args:
            token: 预览令牌
            
        Returns:
            统计信息字典
        """
        if token not in self.preview_tokens:
            return None

        info = self.preview_tokens[token]

        return {
            'article_id': info['article_id'],
            'created_at': info['created_at'].isoformat(),
            'expires_at': info['expires_at'].isoformat(),
            'view_count': info['view_count'],
            'max_views': info['max_views'],
            'is_active': info['is_active'],
            'has_password': info['password_hash'] is not None,
        }


# 全局实例
draft_preview_service = DraftPreviewService()
