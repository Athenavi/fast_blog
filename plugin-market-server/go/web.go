package main

import (
	"html/template"
	"net/http"
)

// indexHTML 是极简浏览页：无任何外部资源（不引 CDN），只用原生 fetch 调本服务的 API。
// 目的不是做完整前端，而是让站长部署完能立刻自检"包放对了没、能不能下载"。
const indexHTML = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{.SiteName}}</title>
<style>
  :root { color-scheme: light dark; }
  body { font: 15px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0; padding: 24px; max-width: 1080px; margin-inline: auto; }
  h1 { font-size: 22px; margin: 0 0 4px; }
  .meta { color: #6b7280; font-size: 13px; margin-bottom: 18px; }
  .bar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }
  input, select, button { font: inherit; padding: 7px 10px; border: 1px solid #d1d5db; border-radius: 6px; background: transparent; }
  button { cursor: pointer; }
  .grid { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
  .card { border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; }
  .card h2 { font-size: 16px; margin: 0 0 6px; display: flex; gap: 8px; align-items: center; }
  .card p { margin: 0 0 8px; color: #4b5563; font-size: 13px; }
  .tag { font-size: 12px; padding: 1px 7px; border: 1px solid #d1d5db; border-radius: 999px; color: #6b7280; }
  code { font-size: 12px; background: #f3f4f6; padding: 1px 5px; border-radius: 4px; }
  .warn { border-left: 3px solid #f59e0b; padding-left: 10px; color: #92400e; font-size: 13px; }
  .empty { color: #6b7280; padding: 24px 0; }
  a { color: #2563eb; }
</style>
</head>
<body>
<h1>{{.SiteName}}</h1>
<div class="meta">
  只读插件市场 · 插件 {{.Count}} 个 · 服务端版本 {{.Version}} ·
  <a href="/api/v1/health">/api/v1/health</a>
</div>
{{if .Warnings}}
<div class="warn">
  <strong>索引告警（{{len .Warnings}}）</strong>
  <ul>{{range .Warnings}}<li>{{.}}</li>{{end}}</ul>
</div>
{{end}}
<div class="bar">
  <input id="kw" placeholder="搜索名称 / slug / 作者" size="28">
  <select id="cat"><option value="">全部分类</option></select>
  <select id="sort">
    <option value="name">按名称</option>
    <option value="updated">按更新时间</option>
    <option value="installs">按安装量</option>
    <option value="rating">按评分</option>
  </select>
  <button onclick="load()">查询</button>
</div>
<div id="list" class="grid"></div>

<script>
async function load() {
  const kw = document.getElementById('kw').value.trim();
  const cat = document.getElementById('cat').value;
  const sort = document.getElementById('sort').value;
  const url = '/api/v1/plugins?keyword=' + encodeURIComponent(kw) +
              '&category=' + encodeURIComponent(cat) +
              '&sort=' + encodeURIComponent(sort) + '&order=desc&page_size=60';
  const el = document.getElementById('list');
  el.innerHTML = '<div class="empty">加载中…</div>';
  try {
    const res = await fetch(url);
    const body = await res.json();
    if (body.code !== 0) { el.innerHTML = '<div class="empty">接口返回错误：' + body.message + '</div>'; return; }
    const items = body.data.items || [];
    if (!items.length) { el.innerHTML = '<div class="empty">还没有插件。把插件包放到 data/plugins/{slug}/{version}.zip 即可。</div>'; return; }
    el.innerHTML = items.map(function (p) {
      const tags = (p.tags || []).map(function (t) { return '<span class="tag">' + t + '</span>'; }).join(' ');
      return '<div class="card"><h2>' + (p.icon || '🧩') + ' ' + p.name + ' <span class="tag">v' + p.version + '</span></h2>' +
        '<p>' + (p.summary || '') + '</p>' +
        '<div>' + tags + '</div>' +
        '<p style="margin-top:8px">作者：' + (p.author || '未知') + ' · 分类：' + (p.category || '未分类') + '</p>' +
        '<p><a href="' + p.download_url + '">下载 ZIP</a> · <code>' + (p.sha256 || '').slice(0, 16) + '…</code></p></div>';
    }).join('');
  } catch (e) {
    el.innerHTML = '<div class="empty">请求失败：' + e + '</div>';
  }
}
async function loadCategories() {
  try {
    const res = await fetch('/api/v1/categories');
    const body = await res.json();
    if (body.code !== 0) return;
    const sel = document.getElementById('cat');
    (body.data || []).forEach(function (c) {
      const o = document.createElement('option');
      o.value = c.slug; o.textContent = c.name + ' (' + c.count + ')';
      sel.appendChild(o);
    });
  } catch (e) { /* 分类失败不影响主列表 */ }
}
loadCategories();
load();
document.getElementById('kw').addEventListener('keydown', function (e) { if (e.key === 'Enter') load(); });
</script>
</body>
</html>
`

var indexTmpl = template.Must(template.New("index").Parse(indexHTML))

func (a *API) pageIndex(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	_ = indexTmpl.Execute(w, map[string]any{
		"SiteName": a.cfg.SiteName,
		"Version":  a.cfg.Version,
		"Count":    a.ix.Count(),
		"Warnings": a.ix.Warnings(),
	})
}
