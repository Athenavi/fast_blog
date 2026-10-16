"""seo 模块：SEO 分析与内链优化（**真实实现**）

路由前缀：``/api/v3/analytics/seo``

背景：v2 的 ``/api/v2/seo/*`` 里 keywords / backlinks / report / bulk-check 基本都是
硬编码占位数据，只有 ``SEOAnalyzer`` 是真实计算。按既定决策，v3 **完整实现**这些能力，
数据来自真实分析：

  - 单篇 / 批量分析 → 复用 ``shared/services/seo/seo_analyzer.py`` 的 ``SEOAnalyzer.analyze_seo``
    （标题长度、描述质量、关键词密度、可读性、内容长度、标题层级、内链、图片 alt 共 8 项加权）
  - 内链建议 / 孤立文章 / 链接分布 → 复用 ``shared/services/seo/internal_link_service.py``
    （其 ``extract_keywords`` 提供无分词依赖的中文关键词提取）
  - 入链统计 → 用 BeautifulSoup 解析文章正文里的 ``<a href>``（内链指向站内文章的 slug 或 id）

``article_seo`` 表可覆盖标题/描述/关键词：分析时优先用该表的 SEO 字段，回退到文章本身字段。

权限码：``settings:view``（分析与报告）/ ``article:view``（文章维度）
"""
