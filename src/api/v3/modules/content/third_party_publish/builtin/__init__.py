"""内置平台适配器包（**导入即注册**）

每个平台一个模块，模块底部调用 ``register_adapter(...)``；这里把它们导入一遍即可完成注册
（``adapters.load_builtin_adapters()`` 在进程启动时导入本包）。

新增平台 = 加一个模块 + 在下面加一行导入；前端下拉与 ``adapter_ready`` 标注会自动跟上
（`GET /publish/platforms` 读的是注册表）。

已接入（2026-09-21 批次 21）：

  - ``cnblogs``  博客园 —— MetaWeblog / XML-RPC（配置最简单，可立即真实验证）
  - ``wechat_mp`` 微信公众号 —— 草稿箱 ``draft/add``（+ 可选 ``freepublish/submit`` 发布）
  - ``medium``   Medium —— Integration Token API
  - ``weibo``    微博 —— OAuth 2.0 + ``statuses/share``（分享链接）
  - ``twitter``  X / Twitter —— API v2 ``POST /2/tweets``

**未接入的平台（知乎 / 百家号 / 网易号 / 搜狐号 / B站专栏 / 小红书 / 豆瓣 / CSDN / 掘金 /
51CTO / 思否 / InfoQ / 简书 等）保持"如实失败"**：它们没有公开的发布 API，接非官方接口等于
随时失效的假实现 —— 任务会在 ``last_error`` 里写明"未实现该平台的发布适配器（platform=xxx）"。
"""

from src.api.v3.modules.content.third_party_publish.builtin import (  # noqa: F401
    cnblogs,
    medium,
    wechat_mp,
    weibo,
    x_twitter,
)
