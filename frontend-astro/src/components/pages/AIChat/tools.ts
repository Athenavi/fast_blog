/**
 * AI Chat 工具注册表
 * 映射 MCP 工具名 → 前端 API 调用函数
 * 用于 ReAct 循环：当 LLM 以文本形式输出工具调用时，前端自动执行
 */
import {apiClient} from '@/lib/api/base-client';
import {CATEGORIES, ARTICLES} from '@/lib/api/api-paths';

// ─── 工具执行结果 ────────────────────────────────
export interface ToolResult {
  name: string;
  args: Record<string, any>;
  result: any;
  success: boolean;
  error?: string;
}

// ─── 工具处理函数类型 ────────────────────────────
type ToolHandler = (args: Record<string, any>) => Promise<any>;

// ─── 前端允许的 MCP 工具白名单 ────────────────────
// 只有下列工具可以被 LLM 文本中的 invoke 调用执行
// 危险工具（如 clear_cache, run_migration, ban_user 等）被排除
const ALLOWED_TOOLS: ReadonlySet<string> = new Set([
  // 分类（只读+创建）
  'list_categories', 'create_category',
  // 文章（只读+搜索，delete 和 publish 由后端网关控制）
  'search_articles', 'create_article', 'update_article',
  // 标签（只读）
  'list_tags',
  // 统计（只读）
  'get_system_stats', 'get_analytics',
]);

// ─── 工具注册表 ──────────────────────────────────
const toolRegistry: Record<string, ToolHandler> = {};

/** 注册一个工具 */
function register(name: string, handler: ToolHandler) {
  toolRegistry[name] = handler;
}

// ═══════════════════════════════════════════════
// 分类
// ═══════════════════════════════════════════════
register('list_categories', async () => {
  const r = await apiClient.get(CATEGORIES.LIST);
  return r.success ? (r.data || []) : [];
});

register('create_category', async (args) => {
  const r = await apiClient.post(CATEGORIES.CREATE, {
    name: args.name,
    description: args.description || '',
  });
  return r.success ? (r.data || {}) : {error: r.error || '创建分类失败'};
});

register('update_category', async (args) => {
  const r = await apiClient.put(CATEGORIES.UPDATE(args.id), {
    name: args.name,
    description: args.description,
  });
  return r.success ? (r.data || {}) : {error: r.error || '更新分类失败'};
});

register('delete_category', async (args) => {
  const r = await apiClient.delete(CATEGORIES.DELETE(args.id));
  return r.success ? {deleted: true} : {error: r.error || '删除分类失败'};
});

// ═══════════════════════════════════════════════
// 文章
// ═══════════════════════════════════════════════
register('search_articles', async (args) => {
  const q = args.q || args.query || args.keyword || '';
  const r = await apiClient.get(ARTICLES.SEARCH, {q, per_page: args.per_page || 10});
  return r.success ? (r.data || []) : [];
});

register('create_article', async (args) => {
  const fd = new FormData();
  fd.append('title', args.title || '');
  fd.append('content', args.content || '');
  fd.append('status', String(args.status ?? 1)); // 默认发布
  if (args.category_id) fd.append('category_id', String(args.category_id));
  if (args.excerpt) fd.append('excerpt', args.excerpt);
  if (args.tags) fd.append('tags', JSON.stringify(Array.isArray(args.tags) ? args.tags : [args.tags]));
  const r = await apiClient.request(ARTICLES.CREATE, {method: 'POST', body: fd});
  return r.success ? (r.data || {}) : {error: r.error || '创建文章失败'};
});

register('delete_article', async (args) => {
  const r = await apiClient.delete(ARTICLES.DELETE(args.id));
  return r.success ? {deleted: true} : {error: r.error || '删除文章失败'};
});

register('update_article', async (args) => {
  const fd = new FormData();
  if (args.title) fd.append('title', args.title);
  if (args.content) fd.append('content', args.content);
  if (args.status !== undefined) fd.append('status', String(args.status));
  const r = await apiClient.request(ARTICLES.UPDATE(args.id), {method: 'PUT', body: fd});
  return r.success ? (r.data || {}) : {error: r.error || '更新文章失败'};
});

// ═══════════════════════════════════════════════
// 统计
// ═══════════════════════════════════════════════
register('get_system_stats', async () => {
  const r = await apiClient.get('/dashboard/stats');
  return r.success ? (r.data || {}) : {};
});

register('get_analytics', async (args) => {
  const r = await apiClient.get('/dashboard/analytics/overview', {days: args.days || 7});
  return r.success ? (r.data || {}) : {};
});

// ═══════════════════════════════════════════════
// 标签
// ═══════════════════════════════════════════════
register('list_tags', async () => {
  const r = await apiClient.get('/cms/tags/');
  return r.success ? (r.data || []) : [];
});

// ═══════════════════════════════════════════════
// 通用工具执行入口
// ═══════════════════════════════════════════════

/** 检查文本中是否包含工具调用，如存在则执行并返回结果 */
export function parseToolCalls(text: string): Array<{name: string; args: Record<string, any>}> {
  const calls: Array<{name: string; args: Record<string, any>}> = [];

  // 格式1: XML <tool_calls><invoke name="xxx">...</invoke></tool_calls>
  const xmlRegex = /<invoke\s+name=["']([^"']+)["'][^>]*>([\s\S]*?)<\/invoke>/g;
  let match: RegExpExecArray | null;
  while ((match = xmlRegex.exec(text)) !== null) {
    const name = match[1].trim();
    const body = match[2];
    const args: Record<string, any> = {};
    const paramRegex = /<parameter\s+name=["']([^"']+)["'](?:\s+string=["']true["'])?>([^<]*)<\/parameter>/g;
    let pm: RegExpExecArray | null;
    while ((pm = paramRegex.exec(body)) !== null) {
      args[pm[1].trim()] = pm[2].trim();
    }
    if (name) calls.push({name, args});
  }

  // 格式2: JSON 格式 { "function": "xxx", "arguments": { ... } } 或 JSON 代码块
  const jsonBlockRegex = /```(?:json)?\s*({[\s\S]*?})\s*```/g;
  while ((match = jsonBlockRegex.exec(text)) !== null) {
    try {
      const parsed = JSON.parse(match[1]);
      const name = parsed.function || parsed.name || parsed.tool;
      if (name) calls.push({name, args: parsed.arguments || parsed.args || parsed.parameters || {}});
    } catch { /* not valid JSON, skip */ }
  }

  // 格式3: 行内 JSON 工具调用 (单个花括号对象)
  const inlineJsonRegex = /\{\s*"(?:function|name|tool)"\s*:\s*"([^"]+)"[\s\S]*?"(?:arguments|args|parameters)"\s*:\s*(\{[\s\S]*?\})\s*\}/g;
  while ((match = inlineJsonRegex.exec(text)) !== null) {
    try {
      const args = JSON.parse(match[2]);
      calls.push({name: match[1], args});
    } catch { /* skip */ }
  }

  return calls;
}

/** 执行一个已解析的工具调用（受 ALLOWED_TOOLS 白名单限制） */
export async function executeToolCall(name: string, args: Record<string, any>): Promise<ToolResult> {
  // 白名单检查：拒绝不在 ALLOWED_TOOLS 中的工具
  if (!ALLOWED_TOOLS.has(name)) {
    return {name, args, result: null, success: false, error: `工具 "${name}" 不在前端允许的白名单中`};
  }
  const handler = toolRegistry[name];
  if (!handler) {
    return {name, args, result: null, success: false, error: `未知工具: ${name}`};
  }
  try {
    const result = await handler(args);
    return {name, args, result, success: true};
  } catch (err: any) {
    return {name, args, result: null, success: false, error: err?.message || String(err)};
  }
}

/** 格式化工具结果为文字描述（用于喂回 LLM） */
export function formatToolResult(r: ToolResult): string {
  const status = r.success ? '✅' : '❌';
  const body = r.success
    ? JSON.stringify(r.result, null, 2)
    : r.error || '执行失败';
  return `${status} ${r.name} 结果:\n${body}`;
}
