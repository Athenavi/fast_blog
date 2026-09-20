"""mobile.feed 模块（T5-11 批次 17）：关注流（personalized feed）。

复用**现成的表**：``user_follows``（批次 11 建立）+ ``articles``（内容域），**不新建表**。

> v2 没有真正的关注流：前台「动态」要么直接列全站文章，要么读一个模块级内存的假关注列表。
> 本模块按登录用户的**真实**关注关系聚合文章——取 ``user_follows`` 里 ``follower == 我``
> 的 ``following`` 集合，交给 ``article_service.public_list`` 的 ``user_ids`` 过滤
> （置顶 → ``sort_order`` → 发布时间倒序，且只含已发布文章）；关注为空则返回空页。
"""
