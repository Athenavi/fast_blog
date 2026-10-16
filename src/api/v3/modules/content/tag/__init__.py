"""tag 模块：标签查询与维护（**不建表**）

路由前缀：``/api/v3/content/tag``

决策背景：fast_blog **没有** Tag 表，标签以 JSON 数组存放在 ``articles.tags_list``。
按既定决策，本次不新建 tags/article_tags 表，v3 只提供：
  - 标签聚合（名称 + 文章数）
  - 按标签查文章
  - 标签重命名 / 删除（批量回写 JSON）

聚合优先用 PostgreSQL 的 ``json_array_elements_text`` 展开，方言不可用时回退到
Python 侧聚合（大库下较慢，但保证可用）。

权限码：``article:view``（查询）/ ``article:edit``（重命名、删除）
"""
