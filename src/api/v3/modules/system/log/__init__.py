"""log 模块：审计日志与登录安全

路由前缀：``/api/v3/system/log``

数据与能力来源（全部复用既有实现，不重复造）：
  - 审计日志：``shared/services/security/audit_log_service.py``（``audit_logs`` 表）
  - 登录尝试 / 锁定：``shared/services/users/login_security_service.py``（``login_attempts`` 表）

对应 FastApiAdmin 的 ``log`` 模块（``sys_login_log`` + ``sys_operation_log``），
但映射到 fast_blog 已有的表，**不新建** ``sys_*`` 表。

权限码：``settings:view``（查看日志）/ ``settings:edit``（清理日志）
"""
