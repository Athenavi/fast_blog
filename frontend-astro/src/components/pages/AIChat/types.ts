/** AI Chat 类型定义与常量 */

// ─── Types ──────────────────────────────────────

export interface ChatMessage {
  role: 'user' | 'assistant' | 'tool';
  content: string;
  tool_calls?: {id: string; type: string; function: {name: string; arguments: string}}[];
  tool_call_id?: string;
  name?: string;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
}

export interface LLMConfig {
  endpoint: string;
  apiKey: string;
  model: string;
  systemPrompt: string;
}

// ─── Defaults & Constants ───────────────────────

export const DEFAULT_CONFIG: LLMConfig = {
  endpoint: '',
  apiKey: '',
  model: '',
  systemPrompt: `你是 FastBlog 的 AI 助手，可以通过 MCP 工具管理博客内容。

可用操作：
1. 创建文章 — 提供标题和内容
2. 更新文章 — 指定文章 ID
3. 删除文章 — 指定文章 ID
4. 搜索文章 — 提供关键词
5. 查看/创建分类
6. 查看系统统计

请使用中文回复。`,
};

export const CFG_KEY = 'fastblog-aichat-config';
export const CONS_KEY = 'fastblog-aichat-conversations';

export const PRESETS = [
  {endpoint: 'https://api.deepseek.com/v1', apiKey: '', model: 'deepseek-chat', label: 'DeepSeek'},
  {endpoint: 'https://api.openai.com/v1', apiKey: '', model: 'gpt-4o-mini', label: 'OpenAI'},
  {endpoint: 'https://api.openai.com/v1', apiKey: '', model: 'gpt-4o', label: 'GPT-4o'},
];

export const SUGGESTIONS = [
  {icon: '✍️', title: '写文章', text: '帮我写一篇关于 AI 趋势的文章'},
  {icon: '🔍', title: '找文章', text: '搜索标题包含 Python 的文章'},
  {icon: '📊', title: '看统计', text: '博客现有多少篇文章？'},
  {icon: '📂', title: '看分类', text: '列出所有文章分类'},
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
