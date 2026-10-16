"""plugin 模块：插件管理

路由前缀：``/api/v3/extension/plugin``

数据与能力来源：``shared/services/plugins/plugin_manager``（``PluginManager`` 单例）——
插件的"已安装 / 已激活"状态由它管理（目录扫描 + ``storage/plugin_state.json``），
``plugins`` 表只是同步出来的副本，因此读写都走 manager，不直接写表。

**危险操作二次确认**（按既定决策）：``install`` / ``activate`` / ``deactivate`` /
``uninstall`` 会动态加载或卸载运行中的 Python 代码，必须显式传 ``confirm=true``，
否则返回 400 并说明原因。

与 v2 的差异：v2 的 ``/api/v2/plugins/*`` 全部要求 ``admin_required``，且存在
"``GET /{slug}`` 注册在 ``/active``、``/scan-new`` 之前"的遮蔽问题；v3 改用细粒度权限码，
并把静态路径统一前置。

权限码：``plugin:view`` / ``plugin:install`` / ``plugin:activate`` /
``plugin:delete`` / ``plugin:configure``
"""
