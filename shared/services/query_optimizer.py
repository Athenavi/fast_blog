"""
查询优化工具

提供SQLAlchemy查询优化功能：
- 自动检测N+1查询问题
- 智能预加载建议
- 批量查询优化
- 查询性能分析
"""

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload


class QueryOptimizer:
    """
    查询优化器
    
    分析和优化数据库查询，解决N+1问题
    """

    def __init__(self):
        self.query_log = []
        self.n_plus_one_threshold = 5  # N+1检测阈值

    def analyze_queries(self, queries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析查询列表，检测性能问题
        
        Args:
            queries: 查询日志列表，每项包含 {'sql': ..., 'time': ..., 'params': ...}
        
        Returns:
            分析报告
        """
        analysis = {
            'total_queries': len(queries),
            'total_time': sum(q.get('time', 0) for q in queries),
            'slow_queries': [],
            'n_plus_one_issues': [],
            'optimization_suggestions': [],
        }

        # 检测慢查询 (>100ms)
        slow_threshold = 0.1  # 100ms
        for query in queries:
            if query.get('time', 0) > slow_threshold:
                analysis['slow_queries'].append({
                    'sql': query.get('sql', '')[:200],
                    'time': query.get('time', 0),
                    'params': query.get('params', {}),
                })

        # 检测N+1查询模式
        n_plus_one_issues = self._detect_n_plus_one(queries)
        analysis['n_plus_one_issues'] = n_plus_one_issues

        # 生成优化建议
        analysis['optimization_suggestions'] = self._generate_suggestions(
            queries, n_plus_one_issues
        )

        return analysis

    def _detect_n_plus_one(self, queries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        检测N+1查询问题
        
        Args:
            queries: 查询日志列表
        
        Returns:
            N+1问题列表
        """
        issues = []

        # 按SQL模式分组
        pattern_counts = defaultdict(list)
        for i, query in enumerate(queries):
            sql = query.get('sql', '')
            pattern = self._normalize_sql(sql)
            pattern_counts[pattern].append({
                'index': i,
                'sql': sql,
                'time': query.get('time', 0),
                'params': query.get('params', {}),
            })

        # 检测重复的查询模式
        for pattern, occurrences in pattern_counts.items():
            if len(occurrences) >= self.n_plus_one_threshold:
                # 检查是否是相似的参数（典型的N+1模式）
                if self._is_n_plus_one_pattern(occurrences):
                    issues.append({
                        'pattern': pattern[:200],
                        'count': len(occurrences),
                        'total_time': sum(o['time'] for o in occurrences),
                        'examples': [o['sql'][:150] for o in occurrences[:3]],
                        'suggestion': self._suggest_eager_loading(pattern),
                    })

        return issues

    def _normalize_sql(self, sql: str) -> str:
        """
        标准化SQL语句，移除具体值以便模式匹配
        
        Args:
            sql: 原始SQL
        
        Returns:
            标准化的SQL模式
        """
        import re

        # 替换数字为占位符
        normalized = re.sub(r'\b\d+\b', '?', sql)

        # 替换字符串值为占位符
        normalized = re.sub(r"'[^']*'", '?', normalized)

        # 移除多余空格
        normalized = ' '.join(normalized.split())

        return normalized

    def _is_n_plus_one_pattern(self, occurrences: List[Dict]) -> bool:
        """
        判断是否为N+1查询模式
        
        Args:
            occurrences: 相同模式的查询出现列表
        
        Returns:
            是否为N+1模式
        """
        if len(occurrences) < self.n_plus_one_threshold:
            return False

        # 检查参数是否不同但结构相似
        params_list = [occ.get('params', {}) for occ in occurrences]

        # 如果所有查询的参数键相同但值不同，很可能是N+1
        if params_list:
            keys_set = set()
            for params in params_list:
                keys_set.add(frozenset(params.keys()))

            # 如果参数键一致，说明是同一查询的不同实例
            if len(keys_set) == 1:
                return True

        return False

    def _suggest_eager_loading(self, sql_pattern: str) -> str:
        """
        根据SQL模式建议使用预加载
        
        Args:
            sql_pattern: SQL模式
        
        Returns:
            优化建议
        """
        import re

        # 检测WHERE子句中的ID条件
        where_match = re.search(r'WHERE.*?(\w+)\.id\s*=', sql_pattern, re.IGNORECASE)
        if where_match:
            table_name = where_match.group(1)
            return (
                f"考虑使用 eager loading 预加载 '{table_name}' 相关数据:\n"
                f"  - 对于外键关联: options(joinedload(Model.{table_name}))\n"
                f"  - 对于一对多关联: options(selectinload(Model.{table_name}s))"
            )

        return "考虑使用批量查询或缓存来减少数据库访问次数"

    def _generate_suggestions(
            self,
            queries: List[Dict[str, Any]],
            n_plus_one_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        生成优化建议
        
        Args:
            queries: 查询列表
            n_plus_one_issues: N+1问题列表
        
        Returns:
            优化建议列表
        """
        suggestions = []

        # N+1问题建议
        if n_plus_one_issues:
            suggestions.append({
                'type': 'critical',
                'title': f'发现 {len(n_plus_one_issues)} 个N+1查询问题',
                'description': 'N+1查询会显著降低性能，建议使用eager loading优化',
                'issues': n_plus_one_issues[:5],  # 只显示前5个
            })

        # 慢查询建议
        slow_queries = [q for q in queries if q.get('time', 0) > 0.1]
        if slow_queries:
            suggestions.append({
                'type': 'warning',
                'title': f'发现 {len(slow_queries)} 个慢查询 (>100ms)',
                'description': '这些查询可能需要添加索引或优化SQL',
                'queries': [
                    {
                        'sql': q.get('sql', '')[:200],
                        'time': q.get('time', 0),
                    }
                    for q in slow_queries[:5]
                ],
            })

        # 查询总数建议
        if len(queries) > 50:
            suggestions.append({
                'type': 'info',
                'title': '单次请求查询数量过多',
                'description': f'本次请求执行了 {len(queries)} 次查询，建议优化到20次以内',
                'recommendation': '考虑使用批量查询、缓存或预加载',
            })

        return suggestions

    def optimize_article_query(
            self,
            db: AsyncSession,
            page: int = 1,
            per_page: int = 10,
            **filters
    ) -> Tuple[List[Any], int]:
        """
        优化的文章查询示例
        
        演示如何使用预加载避免N+1问题
        
        Args:
            db: 数据库会话
            page: 页码
            per_page: 每页数量
            **filters: 过滤条件
        
        Returns:
            (文章列表, 总数)
        """
        from shared.models.article import Article
        from sqlalchemy import func, desc

        # 基础查询
        query = select(Article)

        # 应用过滤条件
        for key, value in filters.items():
            if value is not None and hasattr(Article, key):
                query = query.where(getattr(Article, key) == value)

        # 获取总数
        count_query = select(func.count()).select_from(Article)
        for key, value in filters.items():
            if value is not None and hasattr(Article, key):
                count_query = count_query.where(getattr(Article, key) == value)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 使用预加载避免N+1问题
        query = query.options(
            joinedload(Article.author),  # 预加载作者
            joinedload(Article.category),  # 预加载分类
        )

        # 排序和分页
        offset = (page - 1) * per_page
        query = query.order_by(desc(Article.created_at)).offset(offset).limit(per_page)

        result = await db.execute(query)
        articles = result.scalars().all()

        return list(articles), total

    def batch_load_related(
            self,
            items: List[Any],
            relation_attr: str,
            related_model,
            foreign_key: str,
            local_key: str = 'id'
    ) -> Dict[int, Any]:
        """
        批量加载关联数据
        
        Args:
            items: 主对象列表
            relation_attr: 关联属性名
            related_model: 关联模型类
            foreign_key: 外键字段名
            local_key: 本地键字段名
        
        Returns:
            {local_key_value: related_object} 字典
        """
        if not items:
            return {}

        # 收集所有需要加载的ID
        ids = [getattr(item, local_key) for item in items if hasattr(item, local_key)]

        if not ids:
            return {}

        # 批量查询
        from sqlalchemy import select
        stmt = select(related_model).where(
            getattr(related_model, foreign_key).in_(ids)
        )

        # 这里需要在实际使用时传入db session
        # 返回构建的查询语句，由调用者执行
        return {'query': stmt, 'ids': ids}


# 全局实例
query_optimizer = QueryOptimizer()

# 导出
__all__ = ['QueryOptimizer', 'query_optimizer']
