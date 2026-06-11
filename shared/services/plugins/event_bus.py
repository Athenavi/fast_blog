"""
FastBlog Plugin EventBus
=======================
轻量级事件系统，替代旧的 PluginHook。
插件通过 EventBus 订阅事件，核心服务通过 EventBus 发出事件。
两者完全解耦——核心无需知道有哪些插件，插件无需修改核心代码。

用法
----
插件在 subscribers() 中返回订阅列表：

    class MyPlugin(BasePlugin):
        def subscribers(self) -> list:
            return [
                ("article.published", self.on_article_published),
                ("article.content", self.modify_content, pipeline=True),
            ]

核心代码发出事件：

    from shared.services.plugins.event_bus import event_bus
    await event_bus.emit("article.published", ArticlePublishedPayload(...))
    html = await event_bus.pipeline("article.content", raw_html, article_id=123)
"""

from __future__ import annotations

import asyncio
import inspect
import traceback
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

# ── 预定义事件 Payload ──────────────────────────

@dataclass
class ArticlePublishedPayload:
    """文章发布事件"""
    article_id: int
    slug: str
    title: str
    author_id: int
    excerpt: str = ""
    tags: list[str] = field(default_factory=list)
    category_id: Optional[int] = None


@dataclass
class ArticleUpdatedPayload:
    """文章更新事件"""
    article_id: int
    slug: str
    title: str
    author_id: int
    previous_status: Optional[str] = None


@dataclass
class ArticleDeletedPayload:
    """文章删除事件"""
    article_id: int
    slug: str
    title: str


@dataclass
class CommentCreatedPayload:
    """评论创建事件"""
    comment_id: int
    article_id: int
    user_id: int
    content: str
    parent_id: Optional[int] = None


@dataclass
class UserRegisteredPayload:
    """用户注册事件"""
    user_id: int
    username: str
    email: str


# ── EventBus 核心 ───────────────────────────────

class EventBus:
    """
    事件总线 - 观察者模式实现

    支持两种事件类型：
    1. emit/listen  — 广播通知，无返回值（fire-and-forget）
    2. pipeline     — 数据变换，链式处理（每个 handler 的返回值传给下一个）
    """

    def __init__(self):
        # {event_name: [(priority, callback), ...]}
        self._listeners: Dict[str, list] = {}
        # {pipeline_name: [(priority, callback), ...]}
        self._pipelines: Dict[str, list] = {}

    # ── 订阅（插件端调用） ──

    def listen(self, event_name: str, callback: Callable, priority: int = 10):
        """订阅一个事件（fire-and-forget）"""
        self._listeners.setdefault(event_name, []).append((priority, callback))
        self._listeners[event_name].sort(key=lambda x: x[0])

    def add_pipeline(self, name: str, callback: Callable, priority: int = 10):
        """注册一个数据处理管道"""
        self._pipelines.setdefault(name, []).append((priority, callback))
        self._pipelines[name].sort(key=lambda x: x[0])

    def unlisten(self, event_name: str, callback: Callable):
        """取消订阅"""
        if event_name in self._listeners:
            self._listeners[event_name] = [
                (p, cb) for p, cb in self._listeners[event_name] if cb != callback
            ]

    def remove_pipeline(self, name: str, callback: Callable):
        """移除管道处理器"""
        if name in self._pipelines:
            self._pipelines[name] = [
                (p, cb) for p, cb in self._pipelines[name] if cb != callback
            ]

    # ── 发布（核心端调用） ──

    async def emit(self, event_name: str, payload: Any = None) -> None:
        """
        发出一个事件。
        所有监听器异步执行，互不阻塞。
        任一监听器失败不影响其他监听器。
        """
        listeners = self._listeners.get(event_name, [])
        if not listeners:
            return

        for priority, callback in listeners:
            try:
                result = callback(payload)
                if inspect.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"[EventBus] Error in '{event_name}' listener: {e}")
                traceback.print_exc()

    async def pipeline(self, name: str, value: Any, **context) -> Any:
        """
        运行数据管道。
        每个处理器的返回值作为输入传给下一个处理器。
        context 包含只读的上下文信息（如 article_id）。
        """
        handlers = self._pipelines.get(name, [])
        if not handlers:
            return value

        result = value
        for priority, callback in handlers:
            try:
                if inspect.signature(callback).parameters:
                    # 检查是否接受 context 参数
                    sig = inspect.signature(callback)
                    if any(p.name == "context" for p in sig.parameters.values()):
                        result = callback(result, context=context)
                        if inspect.iscoroutine(result):
                            result = await result
                    else:
                        result = callback(result)
                        if inspect.iscoroutine(result):
                            result = await result
                else:
                    result = callback(result)
                    if inspect.iscoroutine(result):
                        result = await result
            except Exception as e:
                print(f"[EventBus] Error in pipeline '{name}': {e}")
                traceback.print_exc()
                # 管道失败时返回当前值（不阻断整个请求）
        return result

    # ── 批量订阅/退订（插件生命周期用） ──

    def register(self, subscriptions: list[tuple]) -> None:
        """
        批量注册订阅。
        subscriptions 格式:
            ("event.name", callback)                    ← emit/listen
            ("event.name", callback, True)              ← emit/listen (True 无用，表示 listen)
            ("pipeline:name", callback, "pipeline")     ← pipeline
        """
        for item in subscriptions:
            if len(item) == 3 and item[2] == "pipeline":
                name, cb, _ = item
                self.add_pipeline(name, cb)
            elif len(item) >= 2:
                name, cb = item[0], item[1]
                self.listen(name, cb)

    def unregister(self, subscriptions: list[tuple]) -> None:
        """批量取消注册"""
        for item in subscriptions:
            if len(item) == 3 and item[2] == "pipeline":
                self.remove_pipeline(item[0], item[1])
            elif len(item) >= 2:
                self.unlisten(item[0], item[1])

    def clear(self) -> None:
        """清空所有订阅（主要用于测试）"""
        self._listeners.clear()
        self._pipelines.clear()


# 全局单例
event_bus = EventBus()
