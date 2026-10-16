"""gamification.certification 模块（T5-11 批次 13）：专家认证。

表：``expert_certifications`` / ``certification_documents`` / ``certification_reviews``（本批次新建）。

> v2 的同名能力是**进程内内存单例**：重启即失、多 worker 各一份、没有审核记录、没有有效期。
> 本模块是重写：真表 + 状态机（pending → approved / rejected → revoked）+ 两年有效期 +
> 审核流水，且公开列表**排除已过期的认证**。
"""
