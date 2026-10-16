"""theme 模块：当前主题与主题配置

路由前缀：``/api/v3/extension/theme``

重要事实：``themes`` 表在**整个后端没有任何读写代码**（grep ``models.theme import Theme``
只命中 GlobalStyle 这类无关模型）。v2 的主题数据实际来自 ``plugins/`` 目录扫描
（``plugin_state.json``）+ ``PluginManager`` 内存态。因此 v3 的主题能力**以
``PluginManager.get_active_theme_plugin()`` 为唯一数据源**，不去读那张空表。

本次范围（按既定决策）：当前主题信息 / 配置读写 / 配置 schema / 主题契约 /
前台公开的 CSS 与配置。主题市场、安装、卸载、切换留给二期。

权限码：``theme:view`` / ``theme:customize``；``/public/**`` 无鉴权。
"""
