"""install 模块的响应模型

只暴露**布尔位与版本号**：不回传连接串、主机名、文件系统路径等细节
（该端点是公开的 —— 未安装的站点还没有管理员可用来鉴权）。
"""

from typing import Optional

from pydantic import Field

from src.api.v3.core.base_schema import SchemaBase


class DatabaseCheck(SchemaBase):
    ok: bool = False
    #: 只给异常**类型名**，不给完整错误信息（后者可能含连接串/主机）
    error: Optional[str] = Field(default=None, description="失败时的异常类型名")


class MigrationCheck(SchemaBase):
    #: 数据库里 ``alembic_version`` 的当前值
    current: Optional[str] = None
    #: 代码里 alembic 脚本目录的 head
    head: Optional[str] = None
    up_to_date: bool = False


class InstallStatusPayload(SchemaBase):
    """安装状态自检结果"""

    database: DatabaseCheck
    migration: MigrationCheck
    #: 是否存在超级管理员（这就是本项目的"已安装"判定）
    has_superuser: bool = False
    installed: bool = False
    #: CRDT / 实时协同依赖是否可用（缺失时协同编辑不可用，其余功能不受影响）
    realtime_available: bool = False
