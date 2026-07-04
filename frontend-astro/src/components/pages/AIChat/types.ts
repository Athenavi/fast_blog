/** AI Chat 类型定义与常量 */

// ─── 智能代理模式 ──────────────────────────────
export type AgentMode = 'react' | 'plan-execute' | 'reflexion';

export const AGENT_MODES: {id: AgentMode; label: string; icon: string; desc: string}[] = [
  {id: 'react',         label: 'ReAct',          icon: '🧠', desc: '思考→行动→观察，迭代推理'},
  {id: 'plan-execute',  label: 'Plan & Execute', icon: '📋', desc: '先制定计划，再逐步执行'},
  {id: 'reflexion',     label: 'Reflexion',      icon: '🪞', desc: '执行后自我评估并优化结果'},
];

// ─── ChatMessage ────────────────────────────────
export interface ChatMessage {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  /** 前端渲染类型（非 API 字段，仅用于 UI 展示） */
  displayType?: 'normal' | 'reasoning' | 'plan' | 'evaluation';
  tool_calls?: {id: string; type: string; function: {name: string; arguments: string}}[];
  tool_call_id?: string;
  name?: string;
}

// ─── 计划 ───────────────────────────────────────
export interface PlanStep {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
}

export interface Plan {
  title: string;
  steps: PlanStep[];
}

// ─── 评估（Reflexion） ──────────────────────────
export interface Evaluation {
  score: number;           // 1-10
  summary: string;
  issues: string[];
  suggestions: string[];
}

// ─── 对话 ──────────────────────────────────────
export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  mode?: AgentMode;        // 每条对话记录使用的模式
}

// ─── LLM 配置 ──────────────────────────────────
export interface LLMConfig {
  endpoint: string;
  apiKey: string;
  model: string;
  systemPrompt: string;
}

// ─── 默认配置 & 常量 ───────────────────────────

const BASE_SYSTEM_PROMPT = `你是 FastBlog 的 AI 助手，可通过工具管理博客的全部内容。

## 可用工具（按类别）

**内容管理：**
- 文章：search_articles, create_article, update_article, delete_article
- 分类：list_categories, create_category, update_category, delete_category
- 评论：list_comments, approve_comment, reject_comment, delete_comment
- 标签：list_tags
- 媒体：list_media, delete_media

**系统管理：**
- 设置：get_settings, update_settings
- 备份：list_backups, create_backup
- 用户：list_users, create_user, update_user_role, ban_user
- 安全：query_audit_log, scan_sensitive_words, get_security_report
- 缓存：clear_cache, get_cache_status, get_performance_metrics
- 工作流：list_pending_reviews, approve_content, reject_content
- Webhook：list_webhooks
- 维护：get_maintenance_mode, set_maintenance_mode, run_migration

**数据与分析：**
- 统计：get_system_stats, get_analytics, get_trending_articles
- 通知：list_notifications, mark_notification_read
- SEO：generate_seo_description

**高级（需超级管理员权限）：**
- send_test_email, send_bulk_notification, batch_publish_articles
- export_audit_log, manage_sensitive_word, list_rate_limits
- list_collaborators, get_user_stats, list_user_activity
- get_system_info

请使用中文回复。工具调用由系统自动处理，你只需思考并输出最终回复。`;

/** ReAct 模式 — 推理-行动-观察循环 */
export const REACT_SYSTEM_PROMPT = `${BASE_SYSTEM_PROMPT}

## 工作方式：ReAct（推理-行动-观察循环）

按照以下步骤工作：
1. **思考 (Thought):** 分析情况，确定需要做什么
2. **行动 (Action):** 系统会自动调用所需的工具
3. **观察 (Observation):** 工具结果会自动返回

重复以上步骤直到任务完成，然后用中文给出最终回复。`;

/** Plan-and-Execute 模式 — 先计划后执行 */
export const PLAN_EXECUTE_SYSTEM_PROMPT = `${BASE_SYSTEM_PROMPT}

## 工作方式：Plan & Execute（计划 + 逐步执行）

### 阶段一：制定计划
分析用户请求并用 <plan> 标签制定执行计划。

### 阶段二：逐步执行
按计划依次执行，系统会自动调用工具。

### 阶段三：总结
所有步骤完成后，给出最终结果总结。`;

/** Reflexion 模式 — 执行后自我评估 */
export const REFLEXION_SYSTEM_PROMPT = `${BASE_SYSTEM_PROMPT}

## 工作方式：Reflexion（执行 + 自我评估 + 优化）

### 第一轮：执行
按 ReAct 方式完成用户的请求（思考→行动→观察）。

### 第二轮：评估
完成执行后，使用以下格式评估自己的输出：

<evaluation>
  <score>1-10 的评分</score>
  <summary>整体评价</summary>
  <issues>
    <issue>问题1</issue>
    <issue>问题2</issue>
  </issues>
  <suggestions>
    <suggestion>改进建议1</suggestion>
  </suggestions>
</evaluation>

### 第三轮：优化
根据评估结果，如果有改进空间（评分 < 9），生成优化后的最终回复。
如果评分 >= 9，直接总结完成。`;

export const DEFAULT_CONFIG: LLMConfig = {
  endpoint: '',
  apiKey: '',
  model: '',
  systemPrompt: REACT_SYSTEM_PROMPT,
};

export const CFG_KEY = 'fastblog-aichat-config';
export const CONS_KEY = 'fastblog-aichat-conversations';

export const PRESETS = [
  {endpoint: 'https://api.deepseek.com/v1', apiKey: '', model: 'deepseek-chat', label: 'DeepSeek'},
  {endpoint: 'https://api.openai.com/v1', apiKey: '', model: 'gpt-4o-mini', label: 'OpenAI'},
  {endpoint: 'https://api.openai.com/v1', apiKey: '', model: 'gpt-4o', label: 'GPT-4o'},
];

export const SUGGESTIONS = [
  {icon: '✍️', title: '写文章', text: '帮我写一篇关于 AI 趋势的文章并发布'},
  {icon: '🔍', title: '找文章', text: '搜索标题包含 Python 的文章'},
  {icon: '📊', title: '看统计', text: '博客现有多少篇文章？'},
  {icon: '📂', title: '看分类', text: '列出所有文章分类'},
  {icon: '👥', title: '管理用户', text: '列出所有用户'},
  {icon: '💬', title: '评论审核', text: '查看待审核的评论'},
  {icon: '🖼️', title: '查看媒体', text: '列出最近的媒体文件'},
  {icon: '📋', title: '工作流', text: '查看待审批的内容'},
  {icon: '⚙️', title: '系统信息', text: '查看系统版本和运行状态'},
  {icon: '🔐', title: '安全检查', text: '查看最近的安全事件'},
];

// ─── Helpers ─────────────────────────────────────

export function genId(): string {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export function trunc(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + '…' : s;
}

export function ago(ts: number): string {
  const d = new Date(ts);
  const diff = Date.now() - d.getTime();
  if (diff < 60_000) return '刚刚';
  if (diff < 3600_000) return `${Math.floor(diff / 60_000)} 分钟前`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3600_000)} 小时前`;
  return d.toLocaleDateString('zh-CN', {month: 'short', day: 'numeric'});
}

// ─── 文本解析 ───────────────────────────────────

/** 从 assistant 回复中提取计划 */
export function parsePlan(text: string): Plan | null {
  const planRegex = /<plan>([\s\S]*?)<\/plan>/;
  const match = planRegex.exec(text);
  if (!match) return null;

  const body = match[1];
  const stepRegex = /<step\s+id=["']?([^"'>]+)["']?>(.*?)<\/step>/g;
  const steps: PlanStep[] = [];
  let sm: RegExpExecArray | null;

  while ((sm = stepRegex.exec(body)) !== null) {
    steps.push({
      id: sm[1].trim(),
      title: sm[2].trim(),
      status: 'pending',
    });
  }

  return steps.length > 0 ? {title: '', steps} : null;
}

/** 从 assistant 回复中提取评估（Reflexion） */
export function parseEvaluation(text: string): Evaluation | null {
  const evalRegex = /<evaluation>([\s\S]*?)<\/evaluation>/;
  const match = evalRegex.exec(text);
  if (!match) return null;

  const body = match[1];

  const scoreMatch = /<score>\s*(\d+)\s*<\/score>/.exec(body);
  const summaryMatch = /<summary>([\s\S]*?)<\/summary>/.exec(body);

  const issues: string[] = [];
  const issueRegex = /<issue>([\s\S]*?)<\/issue>/g;
  let im: RegExpExecArray | null;
  while ((im = issueRegex.exec(body)) !== null) {
    issues.push(im[1].trim());
  }

  const suggestions: string[] = [];
  const sugRegex = /<suggestion>([\s\S]*?)<\/suggestion>/g;
  let sm: RegExpExecArray | null;
  while ((sm = sugRegex.exec(body)) !== null) {
    suggestions.push(sm[1].trim());
  }

  return {
    score: scoreMatch ? parseInt(scoreMatch[1]) : 5,
    summary: summaryMatch ? summaryMatch[1].trim() : '',
    issues,
    suggestions,
  };
}

/** 从文本中移除 XML 标签 */
export function stripXmlTags(text: string, tag: string): string {
  const regex = new RegExp(`<${tag}>[\\s\\S]*?<\\/${tag}>`, 'g');
  return text.replace(regex, '').trim();
}
