"""
自定义块模式服务
允许用户保存和管理自己的块模式
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional


class CustomBlockPatternService:
    """
    自定义块模式服务
    
    功能:
    1. 保存自定义块模式
    2. 加载用户的块模式
    3. 编辑和删除
    4. 分类管理
    """
    
    def __init__(self, patterns_dir: str = "custom-patterns"):
        self.patterns_dir = Path(patterns_dir)
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
    
    def save_pattern(
        self,
        user_id: int,
        title: str,
        description: str,
        blocks: List[Dict[str, Any]],
        category: str = "custom",
        tags: Optional[List[str]] = None,
        pattern_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        保存自定义块模式
        
        Args:
            user_id: 用户ID
            title: 模式标题
            description: 描述
            blocks: 区块数据
            category: 分类
            tags: 标签
            pattern_id: 模式ID（编辑时使用）
            
        Returns:
            保存结果
        """
        try:
            # 生成文件名
            if pattern_id:
                pattern_file = self.patterns_dir / f"user_{user_id}_pattern_{pattern_id}.json"
            else:
                # 生成新ID
                existing_files = list(self.patterns_dir.glob(f"user_{user_id}_pattern_*.json"))
                pattern_id = len(existing_files) + 1
                pattern_file = self.patterns_dir / f"user_{user_id}_pattern_{pattern_id}.json"
            
            # 构建模式数据
            pattern_data = {
                "id": pattern_id,
                "user_id": user_id,
                "title": title,
                "description": description,
                "category": category,
                "tags": tags or [],
                "blocks": blocks,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "is_custom": True
            }
            
            # 保存到文件
            with open(pattern_file, 'w', encoding='utf-8') as f:
                json.dump(pattern_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "message": "块模式已保存",
                "pattern_id": pattern_id,
                "pattern": pattern_data
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"保存失败: {str(e)}"
            }
    
    def get_user_patterns(self, user_id: int, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取用户的自定义块模式
        
        Args:
            user_id: 用户ID
            category: 可选的分类过滤
            
        Returns:
            块模式列表
        """
        patterns = []
        
        # 查找用户的所有模式文件
        pattern_files = self.patterns_dir.glob(f"user_{user_id}_pattern_*.json")
        
        for pattern_file in pattern_files:
            try:
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    pattern_data = json.load(f)
                
                # 分类过滤
                if category and pattern_data.get("category") != category:
                    continue
                
                patterns.append(pattern_data)
                
            except Exception as e:
                print(f"加载模式文件失败 {pattern_file}: {e}")
                continue
        
        # 按创建时间排序
        patterns.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return patterns
    
    def get_pattern_by_id(self, user_id: int, pattern_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取块模式
        
        Args:
            user_id: 用户ID
            pattern_id: 模式ID
            
        Returns:
            块模式数据，不存在返回None
        """
        pattern_file = self.patterns_dir / f"user_{user_id}_pattern_{pattern_id}.json"
        
        if not pattern_file.exists():
            return None
        
        try:
            with open(pattern_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return None
    
    def update_pattern(
        self,
        user_id: int,
        pattern_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None,
        category: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        更新块模式
        
        Args:
            user_id: 用户ID
            pattern_id: 模式ID
            其他参数为可选更新字段
            
        Returns:
            更新结果
        """
        pattern = self.get_pattern_by_id(user_id, pattern_id)
        
        if not pattern:
            return {
                "success": False,
                "error": "块模式不存在"
            }
        
        # 检查权限
        if pattern["user_id"] != user_id:
            return {
                "success": False,
                "error": "无权修改此块模式"
            }
        
        # 更新字段
        if title is not None:
            pattern["title"] = title
        if description is not None:
            pattern["description"] = description
        if blocks is not None:
            pattern["blocks"] = blocks
        if category is not None:
            pattern["category"] = category
        if tags is not None:
            pattern["tags"] = tags
        
        pattern["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        # 保存
        pattern_file = self.patterns_dir / f"user_{user_id}_pattern_{pattern_id}.json"
        try:
            with open(pattern_file, 'w', encoding='utf-8') as f:
                json.dump(pattern, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "message": "块模式已更新",
                "pattern": pattern
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"更新失败: {str(e)}"
            }
    
    def delete_pattern(self, user_id: int, pattern_id: int) -> Dict[str, Any]:
        """
        删除块模式
        
        Args:
            user_id: 用户ID
            pattern_id: 模式ID
            
        Returns:
            删除结果
        """
        pattern = self.get_pattern_by_id(user_id, pattern_id)
        
        if not pattern:
            return {
                "success": False,
                "error": "块模式不存在"
            }
        
        # 检查权限
        if pattern["user_id"] != user_id:
            return {
                "success": False,
                "error": "无权删除此块模式"
            }
        
        # 删除文件
        pattern_file = self.patterns_dir / f"user_{user_id}_pattern_{pattern_id}.json"
        try:
            pattern_file.unlink()
            return {
                "success": True,
                "message": "块模式已删除"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"删除失败: {str(e)}"
            }
    
    def get_categories(self, user_id: int) -> List[str]:
        """获取用户的所有分类"""
        patterns = self.get_user_patterns(user_id)
        categories = set(p.get("category", "custom") for p in patterns)
        return sorted(list(categories))


# 全局实例
custom_block_pattern_service = CustomBlockPatternService()
