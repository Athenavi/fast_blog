"""
会员订阅服务

功能：
1. 会员等级管理
2. 内容访问控制
3. 订阅管理
4. 权限检查
"""
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession


class MembershipService:
    """
    会员订阅服务
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_vip_status(self, user_id: int) -> Dict:
        """
        获取用户 VIP 状态

        Args:
            user_id: 用户ID

        Returns:
            VIP 状态信息
        """
        from shared.models.vip.vip_subscription import VIPSubscription
        from shared.models.vip.vip_plan import VIPPlan

        # 查询当前有效的订阅
        now = datetime.now(timezone.utc)
        stmt = select(VIPSubscription, VIPPlan).join(
            VIPPlan, VIPSubscription.plan == VIPPlan.id
        ).where(
            VIPSubscription.user == user_id,
            VIPSubscription.status == 1,
            VIPSubscription.expires_at > now
        ).order_by(
            VIPSubscription.expires_at.desc()
        ).limit(1)

        result = await self.db.execute(stmt)
        row = result.one_or_none()

        if not row:
            return {
                'is_vip': False,
                'level': 0,
                'expires_at': None,
                'plan_name': None,
            }

        subscription, plan = row
        return {
            'is_vip': True,
            'level': plan.level,
            'expires_at': subscription.expires_at.isoformat(),
            'plan_name': plan.name,
            'subscription_id': subscription.id,
        }

    async def check_content_access(
            self,
            user_id: int,
            article_id: int,
            required_level: int = 0
    ) -> Dict:
        """
        检查用户是否有权限访问内容

        Args:
            user_id: 用户ID
            article_id: 文章ID
            required_level: 所需VIP等级（0表示无需VIP）

        Returns:
            访问权限结果
        """
        if required_level == 0:
            return {
                'has_access': True,
                'reason': '公开内容',
            }

        vip_status = await self.get_user_vip_status(user_id)

        if not vip_status['is_vip']:
            return {
                'has_access': False,
                'reason': '需要VIP会员',
                'required_level': required_level,
            }

        if vip_status['level'] < required_level:
            return {
                'has_access': False,
                'reason': f'需要VIP等级{required_level}',
                'current_level': vip_status['level'],
                'required_level': required_level,
            }

        return {
            'has_access': True,
            'reason': '权限验证通过',
            'level': vip_status['level'],
        }

    async def create_subscription(
            self,
            user_id: int,
            plan_id: int,
            payment_amount: float,
            transaction_id: Optional[str] = None
    ) -> Dict:
        """
        创建订阅

        Args:
            user_id: 用户ID
            plan_id: 套餐ID
            payment_amount: 支付金额
            transaction_id: 交易ID

        Returns:
            订阅结果
        """
        from shared.models.vip.vip_subscription import VIPSubscription
        from shared.models.vip.vip_plan import VIPPlan
        from shared.models.user import User

        # 获取套餐信息
        plan = await self.db.get(VIPPlan, plan_id)
        if not plan:
            return {'success': False, 'message': '套餐不存在'}

        if not plan.is_active:
            return {'success': False, 'message': '套餐已停用'}

        # 创建订阅
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=plan.duration_days)

        # 验证支付金额（仅当 price > 0 时检查不足支付）
        if plan.price is not None and float(plan.price) > 0 and (not payment_amount or float(payment_amount) < float(plan.price)):
            return {'success': False, 'message': '支付金额不足'}

        subscription = VIPSubscription(
            user=user_id,
            plan=plan_id,
            starts_at=now,
            expires_at=expires_at,
            status=1,
            payment_amount=payment_amount,
            transaction_id=transaction_id,
            created_at=now,
        )

        self.db.add(subscription)
        await self.db.commit()
        await self.db.refresh(subscription)

        # 同步 VIP 信息到 User 模型（不降级，只升级）
        user = await self.db.get(User, user_id)
        if user:
            # 仅当新套餐等级高于当前等级时才升级，防止低等级覆盖高等级
            if plan.level > user.vip_level:
                user.vip_level = plan.level
            # 延长过期时间：新过期时间比现有时间长才更新
            if not user.vip_expires_at or expires_at > user.vip_expires_at:
                user.vip_expires_at = expires_at
            await self.db.commit()

        return {
            'success': True,
            'subscription_id': subscription.id,
            'expires_at': expires_at.isoformat(),
            'plan_name': plan.name,
            'level': plan.level,
        }

    async def cancel_subscription(self, subscription_id: int, user_id: int) -> Dict:
        """
        取消订阅

        Args:
            subscription_id: 订阅ID
            user_id: 用户ID

        Returns:
            操作结果
        """
        from shared.models.vip.vip_subscription import VIPSubscription
        from shared.models.user import User

        subscription = await self.db.get(VIPSubscription, subscription_id)

        if not subscription:
            return {'success': False, 'message': '订阅不存在'}

        if subscription.user != user_id:
            return {'success': False, 'message': '无权操作此订阅'}

        subscription.status = 0

        # 取消订阅后检查用户是否有其他有效订阅
        now = datetime.now(timezone.utc)
        other_stmt = select(VIPSubscription).where(
            VIPSubscription.user == user_id,
            VIPSubscription.status == 1,
            VIPSubscription.expires_at > now,
            VIPSubscription.id != subscription_id
        ).order_by(VIPSubscription.expires_at.desc()).limit(1)
        other_result = await self.db.execute(other_stmt)
        other_active = other_result.scalar_one_or_none()

        user = await self.db.get(User, user_id)
        if user:
            if other_active:
                # 有其他有效订阅，沿用最高等级
                from shared.models.vip.vip_plan import VIPPlan
                other_plan = await self.db.get(VIPPlan, other_active.plan)
                if other_plan:
                    user.vip_level = other_plan.level
                    user.vip_expires_at = other_active.expires_at
                else:
                    user.vip_level = 0
                    user.vip_expires_at = None
            else:
                # 没有其他有效订阅，重置 VIP 等级
                user.vip_level = 0
                user.vip_expires_at = None

        await self.db.commit()

        return {
            'success': True,
            'message': '订阅已取消',
        }

    async def get_available_plans(self) -> List[Dict]:
        """
        获取可用套餐列表

        Returns:
            套餐列表
        """
        from shared.models.vip.vip_plan import VIPPlan

        stmt = select(VIPPlan).where(
            VIPPlan.is_active == True
        ).order_by(
            VIPPlan.level.asc(),
            VIPPlan.price.asc()
        )

        result = await self.db.execute(stmt)
        plans = result.scalars().all()

        return [
            {
                'id': plan.id,
                'name': plan.name,
                'description': plan.description,
                'price': plan.price,
                'original_price': plan.original_price,
                'duration_days': plan.duration_days,
                'level': plan.level,
                'features': plan.features,
                'is_active': plan.is_active,
                'created_at': plan.created_at.isoformat() if plan.created_at else None,
                'updated_at': plan.updated_at.isoformat() if plan.updated_at else None,
            }
            for plan in plans
        ]

    async def get_all_features(self) -> List[Dict]:
        """
        获取所有 VIP 功能特权列表

        Returns:
            功能特权列表
        """
        from shared.models.vip.vip_feature import VIPFeature

        stmt = select(VIPFeature).where(
            VIPFeature.is_active == True
        ).order_by(
            VIPFeature.required_level.asc(),
            VIPFeature.id.asc()
        )

        result = await self.db.execute(stmt)
        features = result.scalars().all()

        return [f.to_dict() for f in features]

    async def get_features_by_level(self) -> Dict[int, List[Dict]]:
        """
        按等级分组的 VIP 功能特权

        Returns:
            {level: [feature_dict, ...]}
        """
        features = await self.get_all_features()
        grouped: Dict[int, List[Dict]] = {}
        for f in features:
            level = f.get('required_level', 1)
            grouped.setdefault(level, []).append(f)
        return grouped

    async def get_user_subscriptions(self, user_id: int) -> List[Dict]:
        """
        获取用户订阅历史

        Args:
            user_id: 用户ID

        Returns:
            订阅列表
        """
        from shared.models.vip.vip_subscription import VIPSubscription
        from shared.models.vip.vip_plan import VIPPlan

        stmt = select(VIPSubscription, VIPPlan).join(
            VIPPlan, VIPSubscription.plan == VIPPlan.id
        ).where(
            VIPSubscription.user == user_id
        ).order_by(
            VIPSubscription.created_at.desc()
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        return [
            {
                'id': sub.id,
                'user_id': sub.user,
                'plan_id': sub.plan,
                'plan_name': plan.name,
                'level': plan.level,
                'starts_at': sub.starts_at.isoformat() if sub.starts_at else None,
                'expires_at': sub.expires_at.isoformat() if sub.expires_at else None,
                'status': sub.status,
                'payment_amount': sub.payment_amount,
                'transaction_id': sub.transaction_id,
                'created_at': sub.created_at.isoformat() if sub.created_at else None,
            }
            for sub, plan in rows
        ]

    async def get_premium_content(self, user_id: int, page: int = 1, page_size: int = 20) -> Dict:
        """
        获取需要 VIP 访问的文章列表

        Args:
            user_id: 用户ID
            page: 页码
            page_size: 每页数量

        Returns:
            VIP 文章列表及当前用户 VIP 状态
        """
        from shared.models.article import Article

        # 获取用户 VIP 状态
        vip_status = await self.get_user_vip_status(user_id)
        user_level = vip_status.get('level', 0) if vip_status.get('is_vip') else 0

        # 查询所有需要 VIP 的文章
        conditions = [
            Article.is_vip_only == True,
            Article.status == 1,
        ]

        # 标记用户可访问的文章（等级 <= 用户等级）
        # 一次性返回所有 VIP 文章，前端可区分可访问/不可访问
        stmt = select(Article).where(
            *conditions
        ).order_by(
            Article.created_at.desc()
        )

        # 总数量
        count_stmt = select(func.count()).select_from(
            select(Article).where(*conditions).subquery()
        )
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # 分页
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)
        result = await self.db.execute(stmt)
        articles = result.scalars().all()

        return {
            'active_status': vip_status,
            'current_vip_level': vip_status.get('level', 0),
            'user_level': user_level,
            'articles': [
                {
                    'id': a.id,
                    'title': a.title,
                    'slug': a.slug,
                    'excerpt': a.excerpt,
                    'cover_image': a.cover_image,
                    'views': a.views,
                    'likes': a.likes,
                    'required_vip_level': a.required_vip_level,
                    'accessible': user_level >= a.required_vip_level if a.required_vip_level else False,
                    'created_at': a.created_at.isoformat() if a.created_at else None,
                    'updated_at': a.updated_at.isoformat() if a.updated_at else None,
                    'user_id': a.user,
                    'category_id': a.category,
                }
                for a in articles
            ],
            'total': total,
            'page': page,
            'page_size': page_size,
        }

    async def renew_subscription(self, user_id: int, plan_id: int) -> Dict:
        """
        续费订阅（延长有效期）

        Args:
            user_id: 用户ID
            plan_id: 套餐ID

        Returns:
            续费结果
        """
        from shared.models.vip.vip_subscription import VIPSubscription
        from shared.models.vip.vip_plan import VIPPlan
        from shared.models.user import User

        # 获取套餐
        plan = await self.db.get(VIPPlan, plan_id)
        if not plan or not plan.is_active:
            return {'success': False, 'message': '套餐不存在或已停用'}

        # 查找当前有效订阅
        now = datetime.now(timezone.utc)
        stmt = select(VIPSubscription).where(
            VIPSubscription.user == user_id,
            VIPSubscription.status == 1,
        ).order_by(VIPSubscription.expires_at.desc()).limit(1)

        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # 延长有效期（从当前到期日往后加）
            new_expires = existing.expires_at + timedelta(days=plan.duration_days)
            existing.expires_at = new_expires
            await self.db.commit()
            await self.db.refresh(existing)

            # 更新用户 VIP 信息
            user = await self.db.get(User, user_id)
            if user:
                user.vip_level = plan.level
                user.vip_expires_at = new_expires
                await self.db.commit()

            return {
                'success': True,
                'subscription_id': existing.id,
                'expires_at': new_expires.isoformat(),
                'plan_name': plan.name,
                'level': plan.level,
            }
        else:
            # 无有效订阅，直接创建新订阅
            return await self.create_subscription(user_id, plan_id, float(plan.price) if plan.price else 0)

    async def check_expired_subscriptions(self) -> int:
        """
        检查并处理所有过期订阅（定时任务用）

        Returns:
            处理的过期订阅数量
        """
        from shared.models.vip.vip_subscription import VIPSubscription
        from shared.models.user import User

        now = datetime.now(timezone.utc)
        stmt = select(VIPSubscription).where(
            VIPSubscription.status == 1,
            VIPSubscription.expires_at <= now
        )
        result = await self.db.execute(stmt)
        expired = result.scalars().all()

        count = 0
        for sub in expired:
            sub.status = 0  # 标记为过期
            # 检查用户是否有其他有效订阅
            other_stmt = select(VIPSubscription).where(
                VIPSubscription.user == sub.user,
                VIPSubscription.status == 1,
                VIPSubscription.expires_at > now,
                VIPSubscription.id != sub.id
            )
            other_result = await self.db.execute(other_stmt)
            other_active = other_result.scalar_one_or_none()

            if not other_active:
                # 没有其他有效订阅，重置用户 VIP 等级
                user = await self.db.get(User, sub.user)
                if user:
                    user.vip_level = 0
                    user.vip_expires_at = None

            count += 1

        if count > 0:
            await self.db.commit()

        return count


def create_membership_service(db: AsyncSession) -> MembershipService:
    return MembershipService(db)
