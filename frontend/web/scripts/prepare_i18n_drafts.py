import json
import re
import subprocess
from pathlib import Path

ROOT = Path(r"X:\project\fast_blog\frontend\web")
REPO = ROOT.parent.parent
DRAFTS = ("i18n-system-draft.json", "i18n-content-draft.json", "i18n-admin-draft.json", "i18n-shared-draft.json")


def flatten(node, prefix=""):
    out = {}
    if isinstance(node, dict):
        for key, value in node.items():
            out.update(flatten(value, f"{prefix}.{key}" if prefix else key))
    elif isinstance(node, str):
        out[prefix] = node
    return out


def git_locale(path):
    try:
        raw = subprocess.check_output(
            ["git", "show", "fa2e8f94926bd934e3bf87a1d26fa1da6dc862ea:" + path],
            cwd=REPO,
            stderr=subprocess.DEVNULL,
        )
        return json.loads(raw.decode("utf-8"))
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        return {}


def camel_words(value):
    # Keep keys readable while avoiding Chinese or punctuation in key segments.
    words = re.findall(r"[A-Za-z0-9]+", value)
    if words:
        return words[0].lower() + "".join(word.title() for word in words[1:])
    return "text"


zh_current = flatten(json.loads((ROOT / "i18n/locales/zh-CN.json").read_text(encoding="utf-8")))
en_current = flatten(json.loads((ROOT / "i18n/locales/en.json").read_text(encoding="utf-8")))
zh_old = flatten(git_locale("frontend-astro/src/locales/zh-CN.json"))
en_old = flatten(git_locale("frontend-astro/src/locales/en.json"))

translations = {}
for key, value in zh_old.items():
    if key in en_old and isinstance(value, str) and isinstance(en_old[key], str):
        translations.setdefault(value, en_old[key])
for key, value in zh_current.items():
    if key in en_current and isinstance(value, str) and isinstance(en_current[key], str):
        translations.setdefault(value, en_current[key])

# New admin pages need a few phrases that were not present in the old Astro locale.
translations.update({
    "系统总览": "System overview", "已强制下线": "Session terminated", "服务器": "Server",
    "操作系统": "Operating system", "主机名": "Hostname", "启动时间": "Boot time",
    "已运行": "Uptime", "进程": "Process", "内存": "Memory", "挂载点": "Mount point",
    "容量": "Capacity", "使用率": "Usage", "在线用户": "Online users",
    "当前没有活跃会话": "No active sessions", "暂无在线用户": "No online users", "设备": "Device",
    "位置": "Location", "最后活动": "Last activity", "强制下线": "Terminate session",
    "缓存": "Cache", "前往缓存管理 →": "Open cache management →", "缓存管理": "Cache management",
    "最近文章": "Recent articles", "浏览": "Views", "最近评论": "Recent comments",
    "内容": "Content", "审核": "Review", "浏览量排行": "Top views", "点赞": "Likes",
    "文章总数": "Total articles", "用户总数": "Total users", "评论总数": "Total comments",
    "总浏览量": "Total views", "分类数": "Categories", "媒体数": "Media files", "未知": "Unknown",
    "已转为草稿": "Moved to draft", "请先选择要删除的文章": "Select articles to delete first",
    "标题关键词": "Title keyword", "隐藏": "Hidden", "定时发布": "Scheduled publish",
    "转草稿": "Move to draft", "发布": "Publish", "文章标题": "Article title", "别名": "Alias",
    "URL 别名（留空由后端生成）": "URL alias (leave blank to generate)", "封面": "Cover",
    "封面图 URL": "Cover image URL", "请选择": "Please select", "输入后回车添加": "Press Enter to add",
    "正文": "Content", "支持 HTML / Markdown 源码": "HTML / Markdown source supported", "属性": "Properties",
    "仅 VIP": "VIP only", "留空表示立即生效": "Leave blank to publish immediately",
    "请填写分类名称": "Enter a category name", "可见": "Visible", "编辑分类": "Edit category",
    "新建分类": "New category", "父级": "Parent", "顶级分类": "Top-level category", "图标": "Icon",
    "图标名或 URL": "Icon name or URL", "颜色": "Color", "如 #3b82f6": "e.g. #3b82f6",
    "评论内容不能为空": "Comment content is required", "确定删除该评论吗？": "Delete this comment?",
    "请先选择要删除的评论": "Select comments to delete first",
    "按内容或作者过滤当前页": "Filter this page by content or author",
    "编辑评论": "Edit comment", "图片": "Image", "视频": "Video", "音频": "Audio", "文档": "Document",
    "上传完成": "Upload complete", "请先选择要删除的文件": "Select files to delete first",
    "链接已复制": "Link copied", "复制失败，请手动复制": "Copy failed; copy it manually",
    "媒体分类": "Media category", "预览": "Preview", "点击预览": "Click to preview", "文件名": "Filename",
    "复制链接": "Copy link", "大小": "Size", "尺寸": "Dimensions", "上传时间": "Upload time",
    "编辑媒体信息": "Edit media information", "替代文本": "Alt text", "用于无障碍与 SEO": "For accessibility and SEO",
    "用英文逗号分隔": "Separate with commas", "请填写新的标签名": "Enter a new tag name",
    "已合并到同名标签": "Merged into the same-name tag", "已重命名": "Renamed", "标签名包含": "Tag name contains",
    "最少文章数": "Minimum article count", "文章数": "Article count", "重命名标签": "Rename tag",
    "原标签": "Original tag", "新标签": "New tag", "输入新的标签名": "Enter a new tag name",
    "没有发现新插件": "No new plugins found", "安装": "Install", "激活": "Activate", "卸载": "Uninstall",
    "高危操作": "Dangerous operation", "确认卸载": "Confirm uninstall", "必须是 JSON 对象": "Must be a JSON object",
    "配置已保存": "Configuration saved", "扫描插件": "Scan plugins",
    "插件目录中新增的插件需要先扫描才会出现在列表里": "New plugins in the plugin directory must be scanned before they appear in the list",
    "版本": "Version", "已激活": "Active", "未激活": "Inactive",
    "配置项以 JSON 对象提交，字段含义见插件自身文档。": "Submit configuration as a JSON object; see the plugin documentation for field meanings.",
    "设置必须是 JSON 对象": "Settings must be a JSON object",
    "组件槽位必须是 JSON 对象": "Component slots must be a JSON object",
    "主题配置已保存": "Theme configuration saved", "当前主题": "Current theme", "主题截图": "Theme screenshot",
    "无预览图": "No preview image", "使用中": "In use", "无法读取当前主题": "Unable to read the current theme",
    "可用设置项": "Available settings", "键": "Key", "说明": "Description",
    "该主题未声明设置项": "This theme declares no settings",
    "主题配置": "Theme configuration", "设置（JSON）": "Settings (JSON)",
    "组件槽位映射（JSON，可选）": "Component slot mapping (JSON, optional)",
    "主题实现不支持的槽位会被忽略并记录告警，保存不会因此失败。": "Unsupported slots are ignored and logged; saving will still succeed.",
    "组件槽位契约与前台 CSS": "Component slot contract and frontend CSS",
    "组件槽位契约（contract）": "Component slot contract",
    "前台注入的 CSS": "Frontend-injected CSS", "（该主题未提供自定义 CSS）": "(This theme does not provide custom CSS)",
    "请选择部件类型与所属区域": "Select a widget type and region", "区域": "Region", "编辑小部件": "Edit widget",
    "新建小部件": "Create widget", "配置": "Configuration",
    "JSON 对象，如 {&quot;limit&quot;: 5}": "JSON object, e.g. {&quot;limit&quot;: 5}",
    "近 7 天": "Last 7 days", "近 30 天": "Last 30 days", "近 90 天": "Last 90 days", "搜索总次数": "Total searches",
    "不同关键词": "Unique keywords", "无结果搜索": "Searches with no results", "无结果占比": "No-result rate",
    "搜索趋势": "Search trend",
    "该时间段没有搜索记录": "No searches in this period", "热门关键词": "Popular keywords", "次数": "Count",
    "平均结果数": "Average results",
    "——读者想找但站内没有的内容": "— What readers searched for but could not find",
    "请填写标题或正文": "Enter a title or content",
    "综合报告": "Overall report", "平均得分": "Average score", "孤立文章（无入链）": "Orphan articles (no inbound links)",
    "评分分布": "Score distribution", "最常见问题": "Most common issues", "建议": "Recommendation",
    "出现次数": "Occurrences",
    "高频关键词": "Frequent keywords", "刷新报告": "Refresh report", "批量检查": "Bulk check", "得分": "Score",
    "问题数": "Issues",
    "主要问题": "Main issues", "点击上方按钮开始批量检查": "Click the button above to start a bulk check",
    "孤立文章": "Orphan articles",
    "孤立文章指没有任何其它文章链接到它——搜索引擎较难发现，建议在内链中补上引用。": "Orphan articles have no inbound links from other articles, so search engines may miss them. Add internal links to improve discoverability.",
    "入链数": "Inbound links", "内容分析器": "Content analyzer", "待分析的标题": "Title to analyze",
    "粘贴正文内容": "Paste content",
    "改进建议": "Improvement suggestions", "没有发现问题": "No issues found",
    "填写左侧内容后开始分析": "Fill in the content on the left to analyze it",
    "数据库": "Database", "文件": "Files", "完整": "Full",
    "该备份缺少文件名，无法还原": "This backup has no filename and cannot be restored",
    "确认还原": "Confirm restore", "还原指令已提交": "Restore command submitted",
    "保留最近多少天的备份？其余将被删除。": "How many days of backups should be kept? Older backups will be deleted.",
    "清理备份": "Clean backups", "清理完成": "Cleanup complete", "定时策略已保存": "Schedule saved",
    "备份容量": "Backup size", "暂无统计数据": "No statistics available",
    "定时备份": "Scheduled backup", "cron 表达式": "Cron expression", "如 0 3 * * *": "e.g. 0 3 * * *",
    "保留天数": "Retention days",
    "压缩": "Compress", "包含数据库": "Include database", "包含文件": "Include files",
    "无法读取定时策略": "Unable to read backup schedule",
    "确定清理全部已读通知吗？此操作不可撤销。": "Clear all read notifications? This action cannot be undone.",
    "仅未读": "Unread only", "全部标记已读": "Mark all as read",
    "已读": "Read", "未读": "Unread", "标记已读": "Mark as read",
    "请填写名称与回调地址": "Enter a name and callback URL",
    "回调地址需以 http:// 或 https:// 开头": "Callback URL must start with http:// or https://",
    "未触发（可能没有可用事件）": "Not triggered (no available event)",
    "回调地址": "Callback URL", "订阅事件": "Subscribed events", "全部事件": "All events", "密钥": "Secret",
    "已设置": "Set", "无": "None",
    "测试": "Test", "编辑 Webhook": "Edit Webhook", "新建 Webhook": "Create Webhook", "如 同步到 CI": "e.g. Sync to CI",
    "留空表示订阅全部事件": "Leave blank to subscribe to all events", "重置密钥": "Reset secret",
    "用于校验请求签名": "Used to verify request signatures",
    "(未命名)": "(Unnamed)", "复制文件链接": "Copy file link", "编辑图片信息": "Edit image information",
    "关闭 (Esc)": "Close (Esc)",
    "上一个 (←)": "Previous (←)", "PDF 预览": "PDF preview",
    "文件过大或读取失败，暂不支持在线预览": "File is too large or failed to read; online preview is unavailable",
    "该类型暂不支持在线预览": "This type does not support online preview", "下一个 (→)": "Next (→)",
    "性能面板 (Ctrl+Shift+P)": "Performance panel (Ctrl+Shift+P)",
    "性能面板": "Performance panel", "清空": "Clear", "收起": "Collapse", "长任务": "Long tasks", "JS 堆": "JS heap",
    "样本": "Samples", "慢资源（&gt;1s）": "Slow resources (&gt;1s)",
    "顶部导航": "Top navigation", "浮动胶囊（默认）": "Floating pill (default)", "经典顶栏": "Classic header",
    "文章卡片": "Article card", "标准卡片（默认）": "Standard card (default)", "紧凑卡片": "Compact card",
    "页脚": "Footer", "标准（默认）": "Standard (default)", "极简": "Minimal",
    "读取主题配置失败": "Failed to load theme configuration", "组件": "Component",
    "选择该主题下各组件使用的变体": "Choose the variant used by each component in this theme",
    "该页面的业务实现将在后续阶段完成。": "The business implementation for this page will be completed in a later phase.",
    "返回仪表盘": "Back to dashboard", "，位于": ", located at", "未找到该插件页面": "Plugin page not found",
    "操作": "Actions", "提示": "Notice", "状态": "Status", "标题": "Title", "创建时间": "Created at",
    "分类": "Category", "标签": "Tags", "描述": "Description", "名称": "Name", "全部": "All", "查询": "Search",
    "重置": "Reset", "取消": "Cancel", "保存": "Save", "删除": "Delete", "编辑": "Edit", "刷新": "Refresh",
    "启用": "Enabled", "停用": "Disabled", "是": "Yes", "否": "No", "已发布": "Published", "草稿": "Draft",
    "已删除": "Deleted", "待审核": "Pending", "已通过": "Approved", "已拒绝": "Rejected", "文章": "Article",
    "评论": "Comment", "等级": "Level", "类型": "Type", "时间": "Time", "用户": "User", "作者": "Author",
    "审核": "Review", "回复": "Reply", "排序": "Order", "公开": "Public", "大小": "Size", "操作系统": "Operating system"
})

# Prefer stable existing admin keys for common phrases; otherwise create a page-local key.
preferred = {
    "提示": "admin.common.notice", "操作": "admin.common.actions", "状态": "admin.common.status",
    "名称": "admin.common.name",
    "描述": "admin.common.description", "全部": "admin.common.all", "查询": "admin.common.search",
    "重置": "admin.common.reset",
    "取消": "admin.common.cancel", "保存": "admin.common.save", "删除": "admin.common.delete",
    "编辑": "admin.common.edit",
    "刷新": "admin.common.refresh", "启用": "admin.common.enabled", "停用": "admin.common.disabled",
    "是": "admin.common.yes", "否": "admin.common.no",
    "创建时间": "admin.common.createdAt", "更新时间": "admin.common.updatedAt", "已发布": "common.published",
    "草稿": "common.draft",
    "待审核": "common.pending", "已通过": "common.approved", "已拒绝": "common.rejected", "文章": "article.title",
    "评论": "comment.title",
    "作者": "article.author", "分类": "article.category", "标签": "article.tags", "浏览": "article.views",
    "点赞": "article.likes",
    "回复": "comment.reply", "公开": "admin.setting.publicLabel", "等级": "vip.level", "用户": "user.title",
    "类型": "admin.cache.level",
    "时间": "admin.system.log.time", "排序": "admin.widget.order", "标题": "admin.system.menu.itemTitle",
    "内容": "article.content",
}

used_generated = {}
for draft_name in DRAFTS:
    path = ROOT / draft_name
    draft = json.loads(path.read_text(encoding="utf-8"))
    for item in draft["entries"]:
        raw = item["raw"]
        if raw.startswith("[\\n") and "示例值" in raw:
            item["key"] = ""
            continue
        if item.get("interpolation"):
            continue
        key = preferred.get(raw)
        if not key:
            # Derive a stable key from the source file and English label.
            rel = item["file"]
            if rel.startswith("src/pages/"):
                prefix = "admin." + rel[len("src/pages/"): -4].replace("\\", "/").replace("/index", "").replace("/",
                                                                                                                ".")
            elif rel.startswith("src/components/"):
                stem = rel[len("src/components/"): -4].replace("\\", "/").replace("/", ".")
                prefix = "admin.shared." + stem
            else:
                prefix = "admin.shared.misc"
            slug = camel_words(translations.get(raw, "text"))
            base = f"{prefix}.{slug}"
            count = used_generated.get(base, 0)
            used_generated[base] = count + 1
            key = base if count == 0 else f"{base}{count + 1}"
        item["key"] = key
        item["en"] = translations.get(raw, "Admin text")
        if item.get("occurrences", 1) > 1:
            item["all"] = True
    path.write_text(json.dumps(draft, ensure_ascii=False, indent=2), encoding="utf-8")
print("prepared", ", ".join(DRAFTS), "generated", len(used_generated), "keys")
