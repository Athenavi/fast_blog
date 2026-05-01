"""
批量操作服务

功能：
1. 批量删除文章/评论/用户
2. 批量更新状态（发布/草稿）
3. 批量移动分类
4. 批量添加标签
5. 操作日志记录
"""
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update, delete


class BatchOperationService:
    """
    批量操作服务
    
    参考 WordPress 和 Django Admin 的设计模式
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.operation_log = []

    async def batch_delete_articles(
            self,
            article_ids: List[int],
            operator_id: Optional[int] = None
    ) -> Dict:
        """
        批量删除文章
        
        Args:
            article_ids: 文章ID列表
            operator_id: 操作者ID
            
        Returns:
            操作结果
        """
        from shared.models.article import Article
        from shared.models.comment import Comment
        from shared.models.article_view import ArticleView

        if not article_ids:
            return {'success': False, 'message': '没有选择任何文章'}

        try:
            # 先删除相关文章的评论
            await self.db.execute(
                delete(Comment).where(
                    Comment.article_id.in_(article_ids)
                )
            )

            # 删除文章浏览记录
            await self.db.execute(
                delete(ArticleView).where(
                    ArticleView.article_id.in_(article_ids)
                )
            )

            # 删除文章
            result = await self.db.execute(
                delete(Article).where(
                    Article.id.in_(article_ids)
                )
            )

            deleted_count = result.rowcount
            await self.db.commit()

            # 记录操作日志
            self._log_operation(
                'batch_delete_articles',
                {'article_ids': article_ids, 'count': deleted_count},
                operator_id
            )

            return {
                'success': True,
                'message': f'成功删除 {deleted_count} 篇文章',
                'deleted_count': deleted_count,
            }
        except Exception as e:
            await self.db.rollback()
            return {
                'success': False,
                'message': f'删除失败: {str(e)}',
            }

    async def batch_update_article_status(
            self,
            article_ids: List[int],
            status: str,
            operator_id: Optional[int] = None
    ) -> Dict:
        """
        批量更新文章状态
        
        Args:
            article_ids: 文章ID列表
            status: 新状态 (published, draft, archived)
            operator_id: 操作者ID
            
        Returns:
            操作结果
        """
        from shared.models.article import Article

        if not article_ids:
            return {'success': False, 'message': '没有选择任何文章'}

        valid_statuses = ['published', 'draft', 'archived']
        if status not in valid_statuses:
            return {'success': False, 'message': f'无效的状态: {status}'}

        try:
            result = await self.db.execute(
                update(Article)
                .where(Article.id.in_(article_ids))
                .values(
                    status=status,
                    updated_at=datetime.now()
                )
            )

            updated_count = result.rowcount
            await self.db.commit()

            # 记录操作日志
            self._log_operation(
                'batch_update_status',
                {'article_ids': article_ids, 'status': status, 'count': updated_count},
                operator_id
            )

            return {
                'success': True,
                'message': f'成功更新 {updated_count} 篇文章状态为 {status}',
                'updated_count': updated_count,
            }
        except Exception as e:
            await self.db.rollback()
            return {
                'success': False,
                'message': f'更新失败: {str(e)}',
            }

    async def batch_move_to_category(
            self,
            article_ids: List[int],
            category_id: int,
            operator_id: Optional[int] = None
    ) -> Dict:
        """
        批量移动文章到指定分类
        
        Args:
            article_ids: 文章ID列表
            category_id: 目标分类ID
            operator_id: 操作者ID
            
        Returns:
            操作结果
        """
        from shared.models.article import Article
        from shared.models.category import Category

        if not article_ids:
            return {'success': False, 'message': '没有选择任何文章'}

        # 验证分类是否存在
        category = await self.db.get(Category, category_id)
        if not category:
            return {'success': False, 'message': '分类不存在'}

        try:
            result = await self.db.execute(
                update(Article)
                .where(Article.id.in_(article_ids))
                .values(
                    category_id=category_id,
                    updated_at=datetime.now()
                )
            )

            updated_count = result.rowcount
            await self.db.commit()

            # 记录操作日志
            self._log_operation(
                'batch_move_category',
                {'article_ids': article_ids, 'category_id': category_id, 'count': updated_count},
                operator_id
            )

            return {
                'success': True,
                'message': f'成功移动 {updated_count} 篇文章到分类 "{category.name}"',
                'updated_count': updated_count,
            }
        except Exception as e:
            await self.db.rollback()
            return {
                'success': False,
                'message': f'移动失败: {str(e)}',
            }

    async def batch_add_tags(
            self,
            article_ids: List[int],
            tags: List[str],
            operator_id: Optional[int] = None
    ) -> Dict:
        """
        批量添加标签
        
        Args:
            article_ids: 文章ID列表
            tags: 标签列表
            operator_id: 操作者ID
            
        Returns:
            操作结果
        """
        from shared.models.article import Article
        import json

        if not article_ids:
            return {'success': False, 'message': '没有选择任何文章'}

        if not tags:
            return {'success': False, 'message': '没有提供标签'}

        try:
            # 获取所有文章
            result = await self.db.execute(
                Article.id, Article.tags
            ).where(
                Article.id.in_(article_ids)
            )

            articles = result.all()
            updated_count = 0

            for article_id, current_tags_json in articles:
                # 解析现有标签
                current_tags = json.loads(current_tags_json) if current_tags_json else []

                # 添加新标签（去重）
                for tag in tags:
                    if tag not in current_tags:
                        current_tags.append(tag)

                # 更新文章
                await self.db.execute(
                    update(Article)
                    .where(Article.id == article_id)
                    .values(
                        tags=json.dumps(current_tags, ensure_ascii=False),
                        updated_at=datetime.now()
                    )
                )
                updated_count += 1

            await self.db.commit()

            # 记录操作日志
            self._log_operation(
                'batch_add_tags',
                {'article_ids': article_ids, 'tags': tags, 'count': updated_count},
                operator_id
            )

            return {
                'success': True,
                'message': f'成功为 {updated_count} 篇文章添加标签',
                'updated_count': updated_count,
            }
        except Exception as e:
            await self.db.rollback()
            return {
                'success': False,
                'message': f'添加标签失败: {str(e)}',
            }

    async def batch_delete_comments(
            self,
            comment_ids: List[int],
            operator_id: Optional[int] = None
    ) -> Dict:
        """
        批量删除评论
        
        Args:
            comment_ids: 评论ID列表
            operator_id: 操作者ID
            
        Returns:
            操作结果
        """
        from shared.models.comment import Comment

        if not comment_ids:
            return {'success': False, 'message': '没有选择任何评论'}

        try:
            result = await self.db.execute(
                delete(Comment).where(
                    Comment.id.in_(comment_ids)
                )
            )

            deleted_count = result.rowcount
            await self.db.commit()

            # 记录操作日志
            self._log_operation(
                'batch_delete_comments',
                {'comment_ids': comment_ids, 'count': deleted_count},
                operator_id
            )

            return {
                'success': True,
                'message': f'成功删除 {deleted_count} 条评论',
                'deleted_count': deleted_count,
            }
        except Exception as e:
            await self.db.rollback()
            return {
                'success': False,
                'message': f'删除失败: {str(e)}',
            }

    async def batch_update_comment_status(
            self,
            comment_ids: List[int],
            status: str,
            operator_id: Optional[int] = None
    ) -> Dict:
        """
        批量更新评论状态
        
        Args:
            comment_ids: 评论ID列表
            status: 新状态 (approved, pending, spam)
            operator_id: 操作者ID
            
        Returns:
            操作结果
        """
        from shared.models.comment import Comment

        if not comment_ids:
            return {'success': False, 'message': '没有选择任何评论'}

        valid_statuses = ['approved', 'pending', 'spam']
        if status not in valid_statuses:
            return {'success': False, 'message': f'无效的状态: {status}'}

        try:
            result = await self.db.execute(
                update(Comment)
                .where(Comment.id.in_(comment_ids))
                .values(
                    status=status,
                    updated_at=datetime.now()
                )
            )

            updated_count = result.rowcount
            await self.db.commit()

            # 记录操作日志
            self._log_operation(
                'batch_update_comment_status',
                {'comment_ids': comment_ids, 'status': status, 'count': updated_count},
                operator_id
            )

            return {
                'success': True,
                'message': f'成功更新 {updated_count} 条评论状态为 {status}',
                'updated_count': updated_count,
            }
        except Exception as e:
            await self.db.rollback()
            return {
                'success': False,
                'message': f'更新失败: {str(e)}',
            }

    def _log_operation(
            self,
            operation_type: str,
            details: Dict,
            operator_id: Optional[int] = None
    ):
        """
        记录操作日志
        
        Args:
            operation_type: 操作类型
            details: 操作详情
            operator_id: 操作者ID
        """
        log_entry = {
            'operation': operation_type,
            'details': details,
            'operator_id': operator_id,
            'timestamp': datetime.now().isoformat(),
        }

        self.operation_log.append(log_entry)

        # TODO: 实际项目中应该写入数据库或日志文件
        print(f"[Batch Operation] {log_entry}")

    def get_operation_log(self) -> List[Dict]:
        """
        获取操作日志
        
        Returns:
            操作日志列表
        """
        return self.operation_log.copy()


# 工厂函数
def create_batch_service(db: AsyncSession) -> BatchOperationService:
    return BatchOperationService(db)
