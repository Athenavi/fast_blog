package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net"
	"net/http"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

// apiResponse 是契约里的统一响应体：{"code":0,"data":…} / {"code":40401,"message":"…"}。
type apiResponse struct {
	Code    int         `json:"code"`
	Message string      `json:"message,omitempty"`
	Data    interface{} `json:"data"`
}

type hitWindow struct {
	start time.Time
	count int
}

// API 承载全部端点；路由用手写分发，保证 Go 版与 PHP 版行为逐条对应。
type API struct {
	cfg Config
	ix  *Index

	rlMu   sync.Mutex
	rlHits map[string]*hitWindow
}

func NewAPI(cfg Config, ix *Index) *API {
	return &API{cfg: cfg, ix: ix, rlHits: map[string]*hitWindow{}}
}

func (a *API) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	ip := clientIP(r)
	if !a.allow(ip) {
		writeErr(w, http.StatusTooManyRequests, 42900, "请求过于频繁，请稍后再试")
		return
	}
	if err := a.ix.EnsureFresh(a.cfg.IndexTTL()); err != nil {
		log.Printf("[warn] 刷新插件索引失败: %v", err)
	}

	path := strings.TrimRight(r.URL.Path, "/")
	if path == "" {
		path = "/"
	}

	// 只读市场：非 GET/HEAD 一律拒绝（API.md §6 的 40300 / 40500）
	if r.Method != http.MethodGet && r.Method != http.MethodHead {
		if strings.HasPrefix(path, "/api/") {
			writeErr(w, http.StatusForbidden, 40300,
				"本服务以只读模式运行（PMS_READONLY=true），不接受写操作；插件包请直接放入数据目录")
			return
		}
		writeErr(w, http.StatusMethodNotAllowed, 40500, "仅支持 GET/HEAD 请求")
		return
	}

	switch {
	case path == "/":
		a.pageIndex(w, r)
	case path == "/api/v1/health":
		a.hHealth(w, r)
	case path == "/api/v1/plugins":
		a.hList(w, r)
	case path == "/api/v1/categories":
		a.hCategories(w, r)
	case path == "/api/v1/featured":
		a.hFeatured(w, r)
	case path == "/api/v1/updates":
		a.hUpdates(w, r)
	case strings.HasPrefix(path, "/api/v1/plugins/"):
		a.hPluginRoute(w, r, strings.TrimPrefix(path, "/api/v1/plugins/"))
	default:
		writeErr(w, http.StatusNotFound, 40400, "未知路径: "+path)
	}
}

// ---------- 端点实现 ----------

func (a *API) hHealth(w http.ResponseWriter, r *http.Request) {
	writeOK(w, map[string]any{
		"status":    "ok",
		"version":   a.cfg.Version,
		"site_name": a.cfg.SiteName,
		"readonly":  a.cfg.ReadOnly,
		"plugins":   a.ix.Count(),
		"warnings":  a.ix.Warnings(),
		"time":      time.Now().UTC().Format(time.RFC3339),
	})
}

func (a *API) hList(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	page := atoiDefault(q.Get("page"), 1)
	pageSize := atoiDefault(q.Get("page_size"), 20)
	items, total := a.ix.Query(
		strings.TrimSpace(q.Get("keyword")),
		strings.TrimSpace(q.Get("category")),
		strings.TrimSpace(q.Get("sort")),
		strings.TrimSpace(q.Get("order")),
		page, pageSize,
	)
	out := make([]map[string]any, 0, len(items))
	for _, p := range items {
		out = append(out, a.listItem(r, p))
	}
	writeOK(w, map[string]any{
		"items":     out,
		"total":     total,
		"page":      page,
		"page_size": pageSize,
	})
}

func (a *API) hCategories(w http.ResponseWriter, r *http.Request) {
	counts := a.ix.CategoryCounts()
	slugs := make([]string, 0, len(counts))
	for s := range counts {
		slugs = append(slugs, s)
	}
	sort.Strings(slugs)
	out := make([]map[string]any, 0, len(slugs))
	for _, s := range slugs {
		out = append(out, map[string]any{
			"slug":  s,
			"name":  categoryDisplayName(s),
			"count": counts[s],
		})
	}
	writeOK(w, out)
}

func (a *API) hFeatured(w http.ResponseWriter, r *http.Request) {
	limit := atoiDefault(r.URL.Query().Get("limit"), 6)
	if limit < 1 || limit > 50 {
		limit = 6
	}
	items, _ := a.ix.Query("", "", "installs", "desc", 1, limit)
	out := make([]map[string]any, 0, len(items))
	for _, p := range items {
		out = append(out, a.listItem(r, p))
	}
	writeOK(w, out)
}

func (a *API) hUpdates(w http.ResponseWriter, r *http.Request) {
	wanted := parseUpdateQuery(r.URL.Query()["slug"])
	updates := []map[string]any{}
	for slug, current := range wanted {
		p := a.ix.Get(slug)
		if p == nil {
			continue
		}
		if current != "" && !semverGreater(p.Version, current) {
			continue // 已是最新
		}
		updates = append(updates, map[string]any{
			"slug":         p.Slug,
			"current":      current,
			"latest":       p.Version,
			"download_url": a.downloadURL(r, p.Slug, p.Version),
			"changelog":    p.Changelog,
			"sha256":       a.versionSHA(p, p.Version),
		})
	}
	sort.Slice(updates, func(i, j int) bool {
		return updates[i]["slug"].(string) < updates[j]["slug"].(string)
	})
	writeOK(w, map[string]any{"updates": updates})
}

// hPluginRoute 处理 /plugins/{slug}、/plugins/{slug}/versions、/plugins/{slug}/download/{version}
func (a *API) hPluginRoute(w http.ResponseWriter, r *http.Request, seg string) {
	parts := strings.Split(strings.Trim(seg, "/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		writeErr(w, http.StatusNotFound, 40401, "缺少插件标识")
		return
	}
	slug := parts[0]
	if !validSlug(slug) {
		writeErr(w, http.StatusBadRequest, 40000, "非法的插件标识（须匹配 ^[a-z0-9-]+$）")
		return
	}
	plugin := a.ix.Get(slug)
	if plugin == nil {
		writeErr(w, http.StatusNotFound, 40401, "plugin not found: "+slug)
		return
	}

	switch {
	case len(parts) == 1:
		writeOK(w, a.detail(r, plugin))
	case len(parts) == 2 && parts[1] == "versions":
		writeOK(w, a.versions(r, plugin))
	case len(parts) >= 2 && parts[1] == "download":
		// 结构必须是 {slug}/download/{version}；多段（含路径穿越尝试）或版本非法一律 400，
		// 避免把"非法输入"和"资源不存在"混为一谈。
		if len(parts) != 3 {
			writeErr(w, http.StatusBadRequest, 40000,
				"下载路径格式应为 /api/v1/plugins/{slug}/download/{version}")
			return
		}
		a.download(w, r, plugin, parts[2])
	default:
		writeErr(w, http.StatusNotFound, 40400, "未知子路径: "+seg)
	}
}

func (a *API) download(w http.ResponseWriter, r *http.Request, plugin *PluginInfo, version string) {
	if !validVersion(version) {
		writeErr(w, http.StatusBadRequest, 40000, "非法的版本号（须匹配 ^\\d+\\.\\d+\\.\\d+$）")
		return
	}
	path, ok := a.ix.PackagePath(plugin.Slug, version)
	if !ok {
		writeErr(w, http.StatusNotFound, 40401, fmt.Sprintf("版本不存在: %s@%s", plugin.Slug, version))
		return
	}
	w.Header().Set("Content-Type", "application/zip")
	w.Header().Set("Content-Disposition",
		fmt.Sprintf("attachment; filename=%q", fmt.Sprintf("%s-%s.zip", plugin.Slug, version)))
	w.Header().Set("X-Checksum-Sha256", a.versionSHA(plugin, version))
	w.Header().Set("Cache-Control", "public, max-age=300")
	http.ServeFile(w, r, path)
}

// ---------- 视图组装 ----------

func (a *API) listItem(r *http.Request, p *PluginInfo) map[string]any {
	return map[string]any{
		"slug":         p.Slug,
		"name":         p.Name,
		"version":      p.Version,
		"summary":      p.Summary,
		"category":     p.Category,
		"author":       p.Author,
		"icon":         p.Icon,
		"tags":         p.Tags,
		"rating":       p.Rating,
		"installs":     p.Installs,
		"updated_at":   p.UpdatedAt,
		"download_url": a.downloadURL(r, p.Slug, p.Version),
		"sha256":       a.versionSHA(p, p.Version),
	}
}

func (a *API) detail(r *http.Request, p *PluginInfo) map[string]any {
	versions := make([]map[string]any, 0, len(p.Versions))
	for _, v := range p.Versions {
		versions = append(versions, a.versionView(r, p.Slug, v))
	}
	out := a.listItem(r, p)
	out["description"] = p.Description
	out["license"] = p.License
	out["requires"] = p.Requires
	out["dependencies"] = p.Dependencies
	out["capabilities"] = p.Capabilities
	out["readme"] = p.Readme
	out["changelog"] = p.Changelog
	out["screenshots"] = p.Screenshots
	out["versions"] = versions
	return out
}

func (a *API) versions(r *http.Request, p *PluginInfo) map[string]any {
	versions := make([]map[string]any, 0, len(p.Versions))
	for _, v := range p.Versions {
		versions = append(versions, a.versionView(r, p.Slug, v))
	}
	return map[string]any{
		"slug":     p.Slug,
		"latest":   p.Version,
		"versions": versions,
	}
}

func (a *API) versionView(r *http.Request, slug string, v VersionInfo) map[string]any {
	return map[string]any{
		"version":      v.Version,
		"published_at": v.PublishedAt,
		"changelog":    v.Changelog,
		"download_url": a.downloadURL(r, slug, v.Version),
		"sha256":       v.SHA256,
		"size":         v.Size,
	}
}

func (a *API) versionSHA(p *PluginInfo, version string) string {
	for _, v := range p.Versions {
		if v.Version == version {
			return v.SHA256
		}
	}
	return ""
}

// downloadURL 生成绝对下载地址：优先采用反向代理传来的协议与 Host。
func (a *API) downloadURL(r *http.Request, slug, version string) string {
	scheme := "http"
	if r.TLS != nil {
		scheme = "https"
	}
	if proto := strings.TrimSpace(r.Header.Get("X-Forwarded-Proto")); proto != "" {
		scheme = proto
	}
	host := r.Host
	if fwd := strings.TrimSpace(r.Header.Get("X-Forwarded-Host")); fwd != "" {
		host = fwd
	}
	return fmt.Sprintf("%s://%s/api/v1/plugins/%s/download/%s", scheme, host, slug, version)
}

// ---------- 限流 / 工具 ----------

func (a *API) allow(ip string) bool {
	limit := a.cfg.RateLimitPerMin
	if limit <= 0 {
		return true
	}
	now := time.Now()
	a.rlMu.Lock()
	defer a.rlMu.Unlock()
	// 简单清理：窗口对象过多时回收过期的，避免内存无界增长
	if len(a.rlHits) > 4096 {
		for k, v := range a.rlHits {
			if now.Sub(v.start) > time.Minute {
				delete(a.rlHits, k)
			}
		}
	}
	hw := a.rlHits[ip]
	if hw == nil || now.Sub(hw.start) > time.Minute {
		a.rlHits[ip] = &hitWindow{start: now, count: 1}
		return true
	}
	hw.count++
	return hw.count <= limit
}

func clientIP(r *http.Request) string {
	if fwd := strings.TrimSpace(r.Header.Get("X-Forwarded-For")); fwd != "" {
		if idx := strings.Index(fwd, ","); idx > 0 {
			return strings.TrimSpace(fwd[:idx])
		}
		return fwd
	}
	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

func writeOK(w http.ResponseWriter, data any) {
	writeJSON(w, http.StatusOK, apiResponse{Code: 0, Data: data})
}

func writeErr(w http.ResponseWriter, status, code int, msg string) {
	writeJSON(w, status, apiResponse{Code: code, Message: msg, Data: nil})
}

func writeJSON(w http.ResponseWriter, status int, body apiResponse) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.WriteHeader(status)
	enc := json.NewEncoder(w)
	enc.SetEscapeHTML(false)
	_ = enc.Encode(body)
}

func atoiDefault(s string, def int) int {
	s = strings.TrimSpace(s)
	if s == "" {
		return def
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return def
	}
	return n
}

// categoryDisplayName 与 FastBlog 的 market category_names 保持同一口径。
func categoryDisplayName(slug string) string {
	names := map[string]string{
		"seo": "SEO优化", "security": "安全防护", "analytics": "数据分析",
		"social": "社交分享", "media": "媒体处理", "performance": "性能优化",
		"backup": "备份恢复", "marketing": "营销工具", "workflow": "工作流",
		"search": "搜索增强", "cdn": "CDN加速", "email": "邮件营销",
		"uncategorized": "未分类",
	}
	if n, ok := names[slug]; ok {
		return n
	}
	return slug
}
