package main

import (
	"archive/zip"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// ---------- 测试夹具 ----------

// makePluginZip 在 dataDir/plugins/{slug}/{version}.zip 生成一个合法插件包。
func makePluginZip(t *testing.T, dataDir, slug, version, name string, body map[string]string) string {
	t.Helper()
	dir := filepath.Join(dataDir, "plugins", slug)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatalf("创建插件目录失败: %v", err)
	}
	path := filepath.Join(dir, version+".zip")
	f, err := os.Create(path)
	if err != nil {
		t.Fatalf("创建 zip 失败: %v", err)
	}
	defer f.Close()
	zw := zip.NewWriter(f)

	meta := map[string]any{
		"name": name, "slug": slug, "version": version,
		"description": "首行摘要\n第二行不该出现在 summary",
		"author":      "FastBlog Team", "category": "seo", "icon": "🔍",
		"tags": []string{"seo", "meta"}, "license": "MIT",
		"requires":     map[string]string{"fastblog": ">=1.0.0"},
		"capabilities": []string{"read:seo"},
		"dependencies": []map[string]string{{"name": "core", "version": ">=1.0.0"}},
	}
	for k, v := range body {
		meta[k] = v
	}
	rawMeta, _ := json.Marshal(meta)

	write := func(name, content string) {
		w, err := zw.Create(name)
		if err != nil {
			t.Fatalf("写入 zip 成员失败: %v", err)
		}
		if _, err := w.Write([]byte(content)); err != nil {
			t.Fatalf("写入 zip 内容失败: %v", err)
		}
	}
	write("metadata.json", string(rawMeta))
	write("plugin.py", "# plugin")
	write("README.md", "# "+name+" 说明")
	write("CHANGELOG.md", "## "+version)
	if err := zw.Close(); err != nil {
		t.Fatalf("关闭 zip 失败: %v", err)
	}
	return path
}

// newTestAPI 准备一个指向临时数据目录的 API 实例。
func newTestAPI(t *testing.T) (*API, string) {
	t.Helper()
	dataDir := t.TempDir()
	makePluginZip(t, dataDir, "seo", "1.0.0", "SEO Auto", nil)
	makePluginZip(t, dataDir, "seo", "1.2.0", "SEO Auto", nil)
	makePluginZip(t, dataDir, "shop", "2.1.0", "Shop", map[string]string{"category": "marketing"})

	cfg := DefaultConfig()
	cfg.DataDir = dataDir
	cfg.RateLimitPerMin = 0 // 测试不限流
	ix := NewIndex(dataDir)
	if err := ix.Refresh(); err != nil {
		t.Fatalf("索引构建失败: %v", err)
	}
	return NewAPI(cfg, ix), dataDir
}

type envelope struct {
	Code    int             `json:"code"`
	Message string          `json:"message"`
	Data    json.RawMessage `json:"data"`
}

func do(t *testing.T, api *API, method, url string) (*httptest.ResponseRecorder, envelope) {
	t.Helper()
	req := httptest.NewRequest(method, url, nil)
	rec := httptest.NewRecorder()
	api.ServeHTTP(rec, req)
	var env envelope
	if ct := rec.Header().Get("Content-Type"); strings.HasPrefix(ct, "application/json") {
		if err := json.Unmarshal(rec.Body.Bytes(), &env); err != nil {
			t.Fatalf("响应不是合法 JSON（%s %s）: %v\n%s", method, url, err, rec.Body.String())
		}
	}
	return rec, env
}

// ---------- 用例 ----------

func TestHealthAndIndex(t *testing.T) {
	api, _ := newTestAPI(t)
	rec, env := do(t, api, http.MethodGet, "/api/v1/health")
	if rec.Code != http.StatusOK || env.Code != 0 {
		t.Fatalf("health 期望 200/0，实际 %d/%d", rec.Code, env.Code)
	}
	var data struct {
		Status  string `json:"status"`
		Plugins int    `json:"plugins"`
	}
	_ = json.Unmarshal(env.Data, &data)
	if data.Status != "ok" || data.Plugins != 2 {
		t.Fatalf("health 内容异常: %+v", data)
	}
}

func TestListAndFilter(t *testing.T) {
	api, _ := newTestAPI(t)

	rec, env := do(t, api, http.MethodGet, "/api/v1/plugins")
	if rec.Code != http.StatusOK {
		t.Fatalf("列表期望 200，实际 %d", rec.Code)
	}
	var page struct {
		Items []map[string]any `json:"items"`
		Total int              `json:"total"`
	}
	_ = json.Unmarshal(env.Data, &page)
	if page.Total != 2 || len(page.Items) != 2 {
		t.Fatalf("期望 2 个插件，实际 total=%d len=%d", page.Total, len(page.Items))
	}

	// 关键词过滤
	_, env = do(t, api, http.MethodGet, "/api/v1/plugins?keyword=shop")
	_ = json.Unmarshal(env.Data, &page)
	if page.Total != 1 || page.Items[0]["slug"] != "shop" {
		t.Fatalf("关键词过滤异常: %+v", page)
	}

	// 分类过滤（category=seo 只应命中 seo）
	_, env = do(t, api, http.MethodGet, "/api/v1/plugins?category=seo")
	_ = json.Unmarshal(env.Data, &page)
	if page.Total != 1 || page.Items[0]["slug"] != "seo" {
		t.Fatalf("分类过滤异常: %+v", page)
	}

	// 分页
	_, env = do(t, api, http.MethodGet, "/api/v1/plugins?page=2&page_size=1")
	_ = json.Unmarshal(env.Data, &page)
	if len(page.Items) != 1 || page.Total != 2 {
		t.Fatalf("分页异常: total=%d len=%d", page.Total, len(page.Items))
	}
}

func TestDetailAndVersions(t *testing.T) {
	api, _ := newTestAPI(t)

	_, env := do(t, api, http.MethodGet, "/api/v1/plugins/seo")
	var detail map[string]any
	_ = json.Unmarshal(env.Data, &detail)
	if detail["version"] != "1.2.0" {
		t.Fatalf("latest 版本应为 1.2.0，实际 %v", detail["version"])
	}
	if detail["summary"] != "首行摘要" {
		t.Fatalf("summary 应只取首行，实际 %q", detail["summary"])
	}
	if detail["readme"] != "# SEO Auto 说明" {
		t.Fatalf("readme 未从包内读取: %v", detail["readme"])
	}
	versions, _ := detail["versions"].([]any)
	if len(versions) != 2 {
		t.Fatalf("期望 2 个版本，实际 %d", len(versions))
	}
	first := versions[0].(map[string]any)
	if first["version"] != "1.2.0" {
		t.Fatalf("版本应倒序，首个为 1.2.0，实际 %v", first["version"])
	}
	if s, _ := first["sha256"].(string); len(s) != 64 {
		t.Fatalf("sha256 期望 64 位十六进制，实际 %q", s)
	}

	_, env = do(t, api, http.MethodGet, "/api/v1/plugins/seo/versions")
	var vinfo struct {
		Latest   string           `json:"latest"`
		Versions []map[string]any `json:"versions"`
	}
	_ = json.Unmarshal(env.Data, &vinfo)
	if vinfo.Latest != "1.2.0" || len(vinfo.Versions) != 2 {
		t.Fatalf("versions 端点异常: %+v", vinfo)
	}
}

func TestDownloadSetsChecksumHeader(t *testing.T) {
	api, _ := newTestAPI(t)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/plugins/seo/download/1.0.0", nil)
	rec := httptest.NewRecorder()
	api.ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("下载期望 200，实际 %d", rec.Code)
	}
	if ct := rec.Header().Get("Content-Type"); ct != "application/zip" {
		t.Fatalf("Content-Type 应为 application/zip，实际 %q", ct)
	}
	sum := rec.Header().Get("X-Checksum-Sha256")
	if len(sum) != 64 {
		t.Fatalf("缺少/非法 X-Checksum-Sha256: %q", sum)
	}
	if cd := rec.Header().Get("Content-Disposition"); !strings.Contains(cd, "seo-1.0.0.zip") {
		t.Fatalf("Content-Disposition 异常: %q", cd)
	}
	if body := rec.Body.Bytes(); len(body) == 0 || string(body[:2]) != "PK" {
		t.Fatalf("响应体不是 zip")
	}
}

func TestUpdatesEndpoint(t *testing.T) {
	api, _ := newTestAPI(t)

	// 当前 1.0.0 → 有更新
	_, env := do(t, api, http.MethodGet, "/api/v1/updates?slug=seo:1.0.0&slug=shop:9.9.9")
	var payload struct {
		Updates []map[string]any `json:"updates"`
	}
	_ = json.Unmarshal(env.Data, &payload)
	if len(payload.Updates) != 1 {
		t.Fatalf("期望仅 seo 有更新，实际 %+v", payload.Updates)
	}
	if payload.Updates[0]["latest"] != "1.2.0" {
		t.Fatalf("seo 最新应 1.2.0，实际 %v", payload.Updates[0]["latest"])
	}

	// 已是最新 → 不返回
	_, env = do(t, api, http.MethodGet, "/api/v1/updates?slug=seo:1.2.0")
	_ = json.Unmarshal(env.Data, &payload)
	if len(payload.Updates) != 0 {
		t.Fatalf("已是最新不应返回更新项: %+v", payload.Updates)
	}
}

func TestInvalidInputAndReadOnly(t *testing.T) {
	api, _ := newTestAPI(t)

	cases := []struct {
		name       string
		method     string
		url        string
		wantStatus int
		wantCode   int
	}{
		{"非法 slug", http.MethodGet, "/api/v1/plugins/BAD_SLUG", 400, 40000},
		{"非法版本", http.MethodGet, "/api/v1/plugins/seo/download/1.0", 400, 40000},
		{"路径穿越（slug 段）", http.MethodGet, "/api/v1/plugins/..%2f..%2fetc", 400, 40000},
		{"路径穿越（版本段）", http.MethodGet, "/api/v1/plugins/seo/download/..%2f..%2fpasswd", 400, 40000},
		{"插件不存在", http.MethodGet, "/api/v1/plugins/nope", 404, 40401},
		{"版本不存在", http.MethodGet, "/api/v1/plugins/seo/download/9.9.9", 404, 40401},
		{"未知路径", http.MethodGet, "/api/v1/nope", 404, 40400},
		{"只读拒绝写", http.MethodPost, "/api/v1/plugins", 403, 40300},
		{"只读拒绝删除", http.MethodDelete, "/api/v1/plugins/seo", 403, 40300},
	}
	for _, tc := range cases {
		rec, env := do(t, api, tc.method, tc.url)
		if rec.Code != tc.wantStatus || env.Code != tc.wantCode {
			t.Errorf("%s: 期望 %d/%d，实际 %d/%d (%s)",
				tc.name, tc.wantStatus, tc.wantCode, rec.Code, env.Code, env.Message)
		}
	}
}

func TestIndexSkipsBrokenPackages(t *testing.T) {
	dataDir := t.TempDir()
	makePluginZip(t, dataDir, "seo", "1.0.0", "SEO Auto", nil)

	// 1) 非法 slug 目录 2) 非法版本文件名 3) 包内 slug 不一致 4) 不是 zip
	if err := os.MkdirAll(filepath.Join(dataDir, "plugins", "Bad_Slug"), 0o755); err != nil {
		t.Fatal(err)
	}
	brokenDir := filepath.Join(dataDir, "plugins", "shop")
	if err := os.MkdirAll(brokenDir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(brokenDir, "notaversion.zip"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(brokenDir, "3.0.0.zip"), []byte("not a zip"), 0o644); err != nil {
		t.Fatal(err)
	}
	makePluginZip(t, dataDir, "mismatch", "1.0.0", "Mismatch", map[string]string{"slug": "other"})

	ix := NewIndex(dataDir)
	if err := ix.Refresh(); err != nil {
		t.Fatalf("索引失败: %v", err)
	}
	if ix.Count() != 1 {
		t.Fatalf("只应保留 1 个合法插件，实际 %d", ix.Count())
	}
	if len(ix.Warnings()) == 0 {
		t.Fatalf("应产生索引告警（非法 slug/版本/坏包/不一致）")
	}
}

func TestConfigValidation(t *testing.T) {
	t.Setenv("PMS_READONLY", "false")
	t.Setenv("PMS_ADMIN_TOKEN", "")
	if _, err := LoadConfig(); err == nil {
		t.Fatalf("PMS_READONLY=false 且无 Token 时必须报错")
	}
	t.Setenv("PMS_ADMIN_TOKEN", "s3cret")
	cfg, err := LoadConfig()
	if err != nil {
		t.Fatalf("配置应合法: %v", err)
	}
	if cfg.ReadOnly {
		t.Fatalf("PMS_READONLY=false 未生效")
	}

	t.Setenv("PMS_READONLY", "true")
	t.Setenv("PMS_RATE_LIMIT", "0")
	if _, err := LoadConfig(); err != nil {
		t.Fatalf("PMS_RATE_LIMIT=0 应被接受: %v", err)
	}
	t.Setenv("PMS_RATE_LIMIT", "abc")
	if _, err := LoadConfig(); err == nil {
		t.Fatalf("非法 PMS_RATE_LIMIT 应报错")
	}
}

func TestValidators(t *testing.T) {
	for _, ok := range []string{"seo", "article-likes", "a1"} {
		if !validSlug(ok) {
			t.Errorf("validSlug(%q) 应为 true", ok)
		}
	}
	for _, bad := range []string{"", "Seo", "a_b", "../etc", "a/b", strings.Repeat("a", 65)} {
		if validSlug(bad) {
			t.Errorf("validSlug(%q) 应为 false", bad)
		}
	}
	for _, ok := range []string{"1.0.0", "10.20.30"} {
		if !validVersion(ok) {
			t.Errorf("validVersion(%q) 应为 true", ok)
		}
	}
	for _, bad := range []string{"1.0", "v1.0.0", "1.0.0.0", "1.0.0-beta", ""} {
		if validVersion(bad) {
			t.Errorf("validVersion(%q) 应为 false", bad)
		}
	}
	if !constantTimeEqual("abc", "abc") || constantTimeEqual("abc", "abd") || constantTimeEqual("", "") {
		t.Errorf("constantTimeEqual 行为异常")
	}
}

func TestParseUpdateQuery(t *testing.T) {
	got := parseUpdateQuery([]string{"seo:1.0.0", "shop", "BAD!", "x:1.2"})
	if len(got) != 3 {
		t.Fatalf("期望 3 条合法项，实际 %+v", got)
	}
	if got["seo"] != "1.0.0" || got["shop"] != "" || got["x"] != "1.2" {
		t.Fatalf("解析结果异常: %+v", got)
	}
}

func TestIndexPageRenders(t *testing.T) {
	api, _ := newTestAPI(t)
	rec, _ := do(t, api, http.MethodGet, "/")
	if rec.Code != http.StatusOK {
		t.Fatalf("首页期望 200，实际 %d", rec.Code)
	}
	body := rec.Body.String()
	for _, want := range []string{"<title>", "/api/v1/health", "data/plugins/"} {
		if !strings.Contains(body, want) {
			t.Errorf("首页 HTML 缺少 %q", want)
		}
	}
}

func TestSemverGreater(t *testing.T) {
	if semverGreater("1.2.0", "1.10.0") {
		t.Fatal("1.2.0 不应大于 1.10.0（应按数字而非字符串比较）")
	}
	if !semverGreater("1.10.0", "1.2.0") {
		t.Fatal("1.10.0 应大于 1.2.0")
	}
	if semverGreater("1.0.0", "1.0.0") {
		t.Fatal("相同版本不应判定为更大")
	}
	if !semverGreater("2.0.0", "1.9.9") {
		t.Fatal("2.0.0 应大于 1.9.9")
	}
}
