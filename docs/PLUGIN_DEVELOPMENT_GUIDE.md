# FastBlog 插件开发指南

> **版本**: V0.3.26.0521+ | **插件系统**: WordPress 风格 Hook 机制

---

## 📋 目录

1. [概述](#概述)
2. [快速开始](#快速开始)
3. [插件结构](#插件结构)
4. [Hook 系统](#hook-系统)
5. [常用钩子](#常用钩子)
6. [高级功能](#高级功能)
7. [最佳实践](#最佳实践)

---

## 概述

FastBlog 的插件系统允许开发者在不修改核心代码的情况下扩展功能。通过插件，您可以：

- ✅ 添加新功能（如高级搜索、数据分析）
- ✅ 修改现有行为（如增强搜索、自定义工作流）
- ✅ 集成第三方服务（如 CDN、邮件营销）

### 插件系统架构

```
┌─────────────────────────────────────┐
│         FastBlog Core               │
└──────────┬──────────────────────────┘
           │
           │  Hook System (Actions & Filters)
           │
    ┌──────┴──────┬──────────┬───────┐
    │             │          │       │
┌───▼───┐   ┌────▼────┐  ┌──▼───┐  ┌▼──────┐
│Plugin1│   │Plugin2  │  │ ...  │  │PluginN│
└───────┘   └─────────┘  └──────┘  └───────┘
```

### 核心模块

| 模块               | 路径                                                | 说明                        |
|------------------|---------------------------------------------------|---------------------------|
| `BasePlugin`     | `shared.services.plugins.plugin_manager.core`     | 插件基类                      |
| `PluginHook`     | `shared.services.plugins.plugin_manager.core`     | 钩子系统（`plugin_hooks` 全局实例） |
| `PluginManager`  | `shared.services.plugins.plugin_manager.core`     | 插件管理器                     |
| `PluginManifest` | `shared.services.plugins.plugin_manager.manifest` | 插件清单模型                    |
| `PluginSandbox`  | `shared.services.plugins.sandbox_service`         | 插件沙箱                      |

---

## 快速开始

### 1. 创建插件目录

```bash
mkdir plugins/my-plugin
cd plugins/my-plugin
```

### 2. 创建元数据文件

创建 `metadata.json`：

```json
{
  "name": "我的插件",
  "slug": "my-plugin",
  "version": "1.0.0",
  "description": "这是一个示例插件",
  "author": "您的名字",
  "category": "utility",
  "tags": ["example", "demo"],
  "requires": ">=1.0.0",
  "icon": "🔧",
  "capabilities": [
    "read:articles",
    "write:articles"
  ]
}
```

### 3. 创建插件主文件

创建 `plugin.py`：

```python
"""
我的插件
简短描述插件功能
"""

from typing import Dict, Any
from shared.services.plugins.plugin_manager.core import BasePlugin, plugin_hooks


class MyPlugin(BasePlugin):
    """我的插件类"""

    def __init__(self):
        super().__init__(
            plugin_id=0,
            name="我的插件",
            slug="my-plugin",
            version="1.0.0",
            description="这是一个示例插件",
            author="您的名字",
        )

        self.settings = {
            'enabled': True,
        }

    def register_hooks(self):
        """注册钩子"""
        # 注册动作钩子
        plugin_hooks.add_action(
            "article_published",
            self.on_article_published,
            priority=10
        )

        # 注册过滤器钩子
        plugin_hooks.add_filter(
            "article_content",
            self.enhance_content,
            priority=10
        )

    def on_article_published(self, article_data: Dict[str, Any]):
        """文章发布时的回调"""
        print(f"文章已发布: {article_data.get('title')}")

    def enhance_content(self, content: str) -> str:
        """增强文章内容"""
        return content + "\n\n<!-- 由我的插件增强 -->"

    def get_settings_ui(self) -> Dict[str, Any]:
        """返回设置界面配置"""
        return {
            'fields': [
                {
                    'key': 'enabled',
                    'type': 'boolean',
                    'label': '启用插件',
                },
            ]
        }


# 插件实例（必须命名为 plugin_instance 或 plugin）
plugin_instance = MyPlugin()
```

### 4. 激活插件

1. 重启 FastBlog 服务
2. 进入管理后台 → 插件管理
3. 找到"我的插件"
4. 点击"安装" → "激活"

---

## 插件结构

### 标准目录结构

```
my-plugin/
├── metadata.json          # 插件元数据（必需）
├── plugin.py              # 插件主文件（必需）
├── README.md              # 使用说明（推荐）
├── requirements.txt       # Python 依赖（可选）
└── assets/                # 静态资源（可选）
    ├── css/
    ├── js/
    └── images/
```

### metadata.json 字段说明

| 字段                  | 类型       | 必需 | 说明                             |
|---------------------|----------|----|--------------------------------|
| `name`              | string   | ✅  | 插件显示名称                         |
| `slug`              | string   | ✅  | 插件唯一标识（小写字母+连字符，如 `my-plugin`） |
| `version`           | string   | ✅  | 版本号（语义化版本 `x.y.z`）             |
| `description`       | string   | ✅  | 插件描述（最长 500 字符）                |
| `author`            | string   | ✅  | 作者名称                           |
| `category`          | string   | ❌  | 分类（seo、utility、social 等）       |
| `tags`              | string[] | ❌  | 标签列表                           |
| `requires`          | string   | ❌  | 最低 FastBlog 版本要求               |
| `icon`              | string   | ❌  | 图标（emoji 或 URL）                |
| `requires_database` | boolean  | ❌  | 是否需要数据库表                       |
| `capabilities`      | string[] | ❌  | 所需权限列表                         |

### 权限（Capabilities）格式

权限使用 `<resource>:<action>` 格式声明：

```json
{
  "capabilities": [
    "read:articles",
    "write:articles",
    "read:settings",
    "write:settings",
    "access:filesystem",
    "send:email",
    "manage:seo"
  ]
}
```

未在 `capabilities` 中声明的操作将被拒绝执行（由 `PluginSandbox` 控制）。

---

## Hook 系统

Hook 系统是插件与核心交互的核心机制，分为两种类型：

### Actions（动作钩子）

**特点**：
- 执行某个动作，无返回值
- 可以有多个监听者
- 按优先级顺序执行
- 支持异步（`do_action`）和同步（`do_action_sync`）

**使用场景**：
- 文章发布后发送通知
- 用户注册后执行额外操作

#### 注册 Action

```python
def register_hooks(self):
    plugin_hooks.add_action(
        "article_published",      # 钩子名称
        self.on_article_published, # 回调函数
        priority=10                # 优先级（数字越小越先执行）
    )
```

#### 触发 Action

在核心代码中：

```python
# 异步版本
from shared.services.plugins.plugin_manager.init import trigger_plugin_event

await trigger_plugin_event("article_published", article_data)

# 或直接使用 plugin_hooks
from shared.services.plugins.plugin_manager.core import plugin_hooks
await plugin_hooks.do_action("article_published", article_data)

# 同步版本
plugin_hooks.do_action_sync("article_published", article_data)
```

### Filters（过滤器钩子）

**特点**：
- 修改数据，必须返回值
- 可以有多个过滤器链式处理
- 按优先级顺序应用

**使用场景**：
- 修改文章内容
- 增强搜索结果

#### 注册 Filter

```python
def register_hooks(self):
    plugin_hooks.add_filter(
        "article_content",     # 钩子名称
        self.enhance_content,  # 回调函数
        priority=10            # 优先级
    )
```

#### 应用 Filter

在核心代码中：

```python
from shared.services.plugins.plugin_manager.init import apply_plugin_filter

content = apply_plugin_filter("article_content", original_content)

# 或直接使用 plugin_hooks
content = plugin_hooks.apply_filters("article_content", original_content)
```

### 优先级说明

- **数字越小，优先级越高**（越先执行）
- 默认优先级：`10`
- 建议范围：`1-100`

---

## 常用钩子

### 文章相关

| 钩子名称 | 类型 | 参数 | 说明 |
|---------|------|------|------|
| `article_published` | Action | `article_data: Dict` | 文章发布后 |
| `article_updated` | Action | `article_data: Dict` | 文章更新后 |
| `article_deleted` | Action | `article_data: Dict` | 文章删除后 |
| `article_content` | Filter | `content: str` | 文章内容渲染前 |
| `article_excerpt` | Filter | `excerpt: str` | 文章摘要渲染前 |

### 用户相关

| 钩子名称 | 类型 | 参数 | 说明 |
|---------|------|------|------|
| `user_registered` | Action | `user_data: Dict` | 用户注册后 |
| `user_logged_in` | Action | `user_data: Dict` | 用户登录后 |

### 页面相关

| 钩子名称 | 类型 | 参数 | 说明 |
|---------|------|------|------|
| `page_view` | Action | `view_data: Dict` | 页面访问时 |
| `page_title` | Filter | `title: str` | 页面标题渲染前 |

### 搜索相关

| 钩子名称 | 类型 | 参数 | 说明 |
|---------|------|------|------|
| `search_query` | Filter | `query: str` | 搜索查询处理前 |
| `search_results` | Filter | `results: List` | 搜索结果返回前 |

---

## 高级功能

### 1. 权限检查

```python
# 检查权限（不抛异常）
if not self.has_capability("write:articles"):
    print("[MyPlugin] Permission denied")
    return

# 检查权限（抛异常）
try:
    self.check_capability("write:articles", raise_error=True)
except PermissionError as e:
    print(f"[MyPlugin] {e}")
```

### 2. 数据库操作

使用 SQLAlchemy async 进行数据库操作：

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime


class PluginBase(DeclarativeBase):
    pass


class PluginData(PluginBase):
    __tablename__ = 'plugin_my_data'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


def activate(self):
    """激活插件时初始化数据库"""
    super().activate()
    if self.metadata.get('requires_database', False):
        self._init_plugin_database()
```

### 3. 定时任务

使用 APScheduler 进行定时任务：

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

def activate(self):
    """激活插件时启动定时任务"""
    super().activate()

    self.scheduler = AsyncIOScheduler()
    self.scheduler.add_job(
        self.cleanup_old_data,
        'interval',
        hours=24
    )
    self.scheduler.start()

async def cleanup_old_data(self):
    """清理旧数据"""
    pass


def deactivate(self):
    """停用插件时停止定时任务"""
    if hasattr(self, 'scheduler'):
        self.scheduler.shutdown()
    super().deactivate()
```

### 4. 插件间通信

通过钩子系统或共享数据库表实现插件间通信：

```python
# 插件 A 发布事件
plugin_hooks.do_action_sync("my_custom_event", data={"key": "value"})

# 插件 B 监听事件
plugin_hooks.add_action("my_custom_event", self.handle_custom_event)
```

---

## 最佳实践

### 1. 错误处理

妥善处理异常，避免影响其他插件：

```python
def on_article_published(self, article_data):
    try:
        result = self.do_something()
    except Exception as e:
        print(f"[MyPlugin] Error: {e}")
        return None
```

### 2. 日志记录

使用 Python 标准 logging 模块：

```python
import logging

logger = logging.getLogger("plugin.my-plugin")

def on_article_published(self, article_data):
    logger.info(f"Article published: {article_data.get('title')}")
```

### 3. 性能优化

- 避免在钩子中执行耗时操作
- 使用异步操作处理 I/O
- 缓存频繁访问的数据

### 4. 兼容性

- 始终检查 FastBlog 版本（通过 `metadata.json` 的 `requires` 字段）
- 优雅降级处理缺失的功能
- 提供清晰的错误提示

### 5. 安全

- 声明所需的 `capabilities`，不要请求不必要的权限
- 验证所有用户输入
- 使用 `PluginSandbox` 提供的隔离环境

---

## 常见问题

### Q: 如何调试插件？

A: 使用 Python 的 logging 模块：

```python
import logging

logger = logging.getLogger("plugin.my-plugin")
logger.debug("Debug message")
```

### Q: 插件之间如何通信？

A: 通过钩子系统（`plugin_hooks.add_action` / `do_action`）或共享数据库表。

### Q: 插件主文件必须命名为 `plugin.py` 吗？

A: 是的，`PluginManager` 会自动查找 `plugins/<slug>/plugin.py` 文件，并从中获取 `plugin_instance` 或 `plugin` 变量。

### Q: 如何处理插件升级？

A: 在 `install()` 方法中检查版本并执行迁移：

```python
def install(self):
    super().install()
    if self.needs_upgrade():
        self.run_migrations()
```

---

## 现有插件参考

项目内置了 18 个插件，可作为开发参考：

| 插件               | 说明                           |
|------------------|------------------------------|
| `seo`            | SEO 优化中心（元标签、Sitemap、Schema） |
| `cloud-backup`   | 云备份                          |
| `cloud-cdn`      | CDN 集成                       |
| `email`          | 邮件服务                         |
| `security`       | 安全增强                         |
| `social`         | 社交媒体集成                       |
| `ab-testing`     | A/B 测试                       |
| `article-rating` | 文章评分                         |
| `contact-forms`  | 联系表单                         |

详见 [`plugins/`](../plugins/) 目录。

---

## 总结

- ✅ 继承 `BasePlugin` 类（从 `shared.services.plugins.plugin_manager.core` 导入）
- ✅ 实现 `register_hooks()` 方法注册钩子
- ✅ 使用 `plugin_hooks` 的 `add_action` / `add_filter` 与核心交互
- ✅ 在 `metadata.json` 中声明权限和元数据
- ✅ 导出 `plugin_instance` 或 `plugin` 变量
- ✅ 遵循最佳实践确保稳定性和性能
