# FastBlog 插件开发指南

> **版本**: V0.6.26.0611+ | **插件系统**: EventBus 事件驱动

---

## 概述

FastBlog 的插件系统基于 **EventBus（观察者模式）**，插件通过订阅事件与核心交互，完全解耦。插件拥有自己的 SQLite 数据库、前端页面和管理菜单，无需修改核心代码。

### 架构

```
核心（Core）                   插件（Plugin）
─────────                   ──────────────
event_bus.emit("article.published", payload)
    │                              │
    └─────────────────────────────►│  subscribers() 监听事件
                                   │  → 发送 newsletter 等

event_bus.pipeline("article.content", html)
    ◄─────────────────────────────┤  subscribers() 注册管道
                                   │  → 替换 [snippet:123] 为嵌入代码
```

### 当前插件

| 插件 | 功能 | 后端 | 前端管理页 |
|------|------|------|-----------|
| code-snippets | 代码片段收藏与嵌入 | SQLite + EventBus | `/admin/plugin-pages/code-snippets` |
| newsletter | 邮件订阅与推送 | SQLite + EventBus | `/admin/plugin-pages/newsletter` |

---

## 快速开始

### 插件目录结构

```
plugins/<your-plugin>/
├── metadata.json        ← 插件元数据（必选）
├── plugin.py            ← Python 代码（必选）
└── frontend/            ← 前端代码（可选）
    ├── manifest.json    ← 前端声明（自动发现）
    ├── admin/
    │   └── Page.tsx     ← 管理页面 React 组件
    └── api.ts           ← API 服务
```

### 最小插件示例

**metadata.json:**
```json
{
  "name": "My Plugin",
  "slug": "my-plugin",
  "version": "1.0.0",
  "description": "Plugin description",
  "icon": "🔌",
  "price": "free"
}
```

**plugin.py:**
```python
from shared.services.plugins.plugin_manager.core import BasePlugin
from shared.services.plugins.event_bus import event_bus

class MyPlugin(BasePlugin):
    def __init__(self):
        super().__init__(plugin_id=0, name="My Plugin", slug="my-plugin", version="1.0.0")

    def subscribers(self) -> list:
        return [
            ("article.published", self.on_article_published),
        ]

    def activate(self):
        super().activate()
        self.init_db(MyBase)  # 如果使用 SQLite
        print("[MyPlugin] Activated")

    def on_article_published(self, payload):
        print(f"Article published: {payload.title}")

plugin_instance = MyPlugin()
```

---

## EventBus 事件系统

### 核心概念

| 概念 | 说明 |
|------|------|
| **EventBus** | 全局单例，管理所有事件的订阅与发布 |
| **emit** | 广播事件（fire-and-forget），订阅者异步处理 |
| **pipeline** | 数据管道，每个处理器的输出传给下一个 |
| **Payload** | 预定义的数据类，确保事件数据格式一致 |

### 预定义事件

| 事件名 | Payload 类型 | 触发时机 | 用途 |
|--------|-------------|---------|------|
| `article.published` | `ArticlePublishedPayload` | 文章创建 | Newsletter 推送 |
| `article.updated` | `ArticleUpdatedPayload` | 文章更新 | 缓存刷新 |
| `article.deleted` | `ArticleDeletedPayload` | 文章删除 | 索引清理 |
| `comment.created` | `CommentCreatedPayload` | 评论创建 | 通知 |
| `article.content` (pipeline) | `{"html": str}` | 文章详情返回 | 内容嵌入 |

### 订阅事件（插件端）

```python
def subscribers(self) -> list:
    return [
        ("article.published", self.on_article_published),   # emit 事件
        ("article.content", self.modify_content, "pipeline"), # pipeline
    ]
```

### 触发事件（核心端）

```python
from shared.services.plugins.event_bus import event_bus, ArticlePublishedPayload

# 广播
await event_bus.emit("article.published", ArticlePublishedPayload(
    article_id=1, slug="hello", title="Hello", author_id=1,
))

# 管道
html = await event_bus.pipeline("article.content", {"html": raw_html}, article_id=1)
```

---

## SQLite 持久化

插件使用本地 SQLite 数据库（`storage/plugins/<slug>/data.db`），不依赖主 PostgreSQL 数据库。

```python
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.orm import declarative_base

MyBase = declarative_base()

class MyModel(MyBase):
    __tablename__ = "my_data"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))

def activate(self):
    super().activate()
    self.init_db(MyBase)  # 自动创建表

def _get_session(self):
    engine = self.get_db_engine()
    return sessionmaker(bind=engine)()
```

---

## 前端页面

### manifest.json 声明

```json
{
  "name": "My Plugin",
  "slug": "my-plugin",
  "routes": [
    {
      "path": "/admin/plugin-pages/my-plugin",
      "component": "./admin/Page.tsx",
      "title": "My Plugin"
    }
  ],
  "navItems": [
    {
      "label": "My Plugin",
      "href": "/admin/plugin-pages/my-plugin",
      "icon": "Star"
    }
  ]
}
```

构建时运行 `npm run prescan`，扫描 `plugins/*/frontend/manifest.json`，自动：
1. 复制前端代码到 `src/.plugin-pages/<slug>/`
2. 生成 Astro 代理页面（`/admin/plugin-pages/<slug>/`）
3. 生成 `.plugin-registry.ts`（侧边栏菜单项）

### 管理页面组件模式

```tsx
'use client';
import {AuthGuard} from '@/components/AuthGuard';
import {QueryProvider} from '@/components/QueryProvider';
import {AdminShell} from '@/components/admin/AdminShell';

function MyManager() {
  return <AdminShell title="My Plugin">{/* content */}</AdminShell>;
}

export default function AdminMyPlugin() {
  return <AuthGuard><QueryProvider><MyManager/></QueryProvider></AuthGuard>;
}
```

### API 服务

通过插件 action 端点调用插件方法：

```typescript
import {apiClient} from '@/lib/api/base-client';
await apiClient.post('/plugins/my-plugin/action', {
  action: 'my_method',
  params: {key: 'value'},
});
```

---

## 插件 Action API

后端自动暴露 `POST /api/v2/plugins/{slug}/action`，动态调用插件上的任何方法：

```python
# 插件中的方法
def my_method(self, key: str) -> dict:
    return {'success': True, 'result': key}

# 前端调用
POST /api/v2/plugins/my-plugin/action
{"action": "my_method", "params": {"key": "hello"}}
# → {"success": true, "data": {"success": true, "result": "hello"}}
```

---

## 更新日志

| 版本 | 变更 |
|------|------|
| V0.6 | 废弃旧 PluginHook，迁移到 EventBus |
| V0.5 | 初始插件系统（PluginHook 钩子系统） |
