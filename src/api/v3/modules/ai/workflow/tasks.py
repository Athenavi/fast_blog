"""AI 任务类型 → 提示词模板（工作流执行引擎的一部分）

每个 ``task_type`` 定义「系统提示词 + 用户提示词模板」；模板里 ``{input}`` 由请求的输入填充，
``{target_lang}`` 只在 ``translate`` 里用（缺省"英文"，原文是英文时模型会自行译为中文）。

新增任务类型就在这里加一条 —— 执行引擎（``service.py``）与前端下拉（``GET /task-types``）
都从这份表读取，不会出现"前端有、后端没有"的漂移。
"""

#: task_type → {"label": 中文名, "system": 系统提示词, "template": 用户提示词模板}
TASK_TEMPLATES: dict[str, dict[str, str]] = {
    "writing_assist": {
        "label": "写作辅助",
        "system": "你是一位中文写作助手：语言凝练准确、不堆砌辞藻，保持作者原意与风格。",
        "template": "请改进以下内容，先给出改进后的正文，再用一句话说明改了什么：\n\n{input}",
    },
    "seo_optimize": {
        "label": "SEO 优化",
        "system": "你是 SEO 专家，只给可落地的建议，不要空泛套话。",
        "template": (
            "为以下内容做 SEO 优化，按小标题输出四项：标题建议、核心关键词（5-8 个）、"
            "meta 描述（不超过 160 字）、结构与内链建议。\n\n{input}"
        ),
    },
    "tag_recommend": {
        "label": "标签推荐",
        "system": "你是内容分类助手，**只输出 JSON 数组**，不要任何解释或代码块标记。",
        "template": '为以下内容推荐 5-8 个中文标签，输出形如 ["标签一", "标签二"] 的 JSON 数组。\n\n{input}',
    },
    "summarize": {
        "label": "内容摘要",
        "system": "你是中文编辑，输出客观、信息密度高的摘要。",
        "template": "用 2-3 句话总结以下内容，不要加入原文没有的信息：\n\n{input}",
    },
    "translate": {
        "label": "翻译",
        "system": "你是专业译者，只输出译文本身。",
        "template": "把以下内容翻译成{target_lang}（若原文已是该语言，则译为中文）：\n\n{input}",
    },
    "custom": {
        "label": "自定义提示词",
        "system": "",
        "template": "{input}",
    },
}

#: 默认任务类型
DEFAULT_TASK_TYPE = "writing_assist"


def render(task_type: str, *, input_text: str, target_lang: str = "英文") -> tuple[str, str]:
    """按任务类型渲染 ``(system, prompt)``；未知类型抛 ``KeyError``（调用方转成 400）"""
    template = TASK_TEMPLATES[task_type]
    prompt = template["template"].format(input=input_text or "", target_lang=target_lang or "英文")
    return template["system"], prompt


def catalogue() -> list[dict]:
    """任务类型清单（前端下拉用）"""
    return [
        {
            "task_type": task_type,
            "label": item["label"],
            "has_system_prompt": bool(item["system"]),
        }
        for task_type, item in TASK_TEMPLATES.items()
    ]
