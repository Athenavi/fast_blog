package main

import (
	"archive/zip"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

// ---------- 数据模型（与 API.md §3 对齐） ----------

// VersionInfo 是某个插件的一个可下载版本。
type VersionInfo struct {
	Version     string    `json:"version"`
	PublishedAt time.Time `json:"published_at"`
	Changelog   string    `json:"changelog,omitempty"`
	DownloadURL string    `json:"download_url,omitempty"`
	SHA256      string    `json:"sha256"`
	Size        int64     `json:"size"`

	// 内部字段：不序列化
	path string
}

// PluginInfo 是一个插件（含其全部版本）。
type PluginInfo struct {
	Slug    string `json:"slug"`
	Name    string `json:"name"`
	Version string `json:"version"` // 最新版本
	Summary string `json:"summary"`

	Description  string            `json:"description,omitempty"`
	Category     string            `json:"category,omitempty"`
	Author       string            `json:"author,omitempty"`
	Icon         string            `json:"icon,omitempty"`
	Tags         []string          `json:"tags,omitempty"`
	License      string            `json:"license,omitempty"`
	Rating       float64           `json:"rating,omitempty"`
	Installs     int64             `json:"installs,omitempty"`
	UpdatedAt    time.Time         `json:"updated_at"`
	Requires     map[string]string `json:"requires,omitempty"`
	Dependencies []string          `json:"dependencies,omitempty"`
	Capabilities []string          `json:"capabilities,omitempty"`

	// 仅详情返回
	Readme      string        `json:"readme,omitempty"`
	Changelog   string        `json:"changelog,omitempty"`
	Screenshots []string      `json:"screenshots,omitempty"`
	Versions    []VersionInfo `json:"versions,omitempty"`
}

// manifest 是插件包内 metadata.json 中本服务端关心的字段
// （与 FastBlog 的 PluginManifest 对齐，未列出的字段忽略）。
type manifest struct {
	Name         string            `json:"name"`
	Slug         string            `json:"slug"`
	Version      string            `json:"version"`
	Description  string            `json:"description"`
	Author       string            `json:"author"`
	Category     string            `json:"category"`
	Icon         string            `json:"icon"`
	Tags         []string          `json:"tags"`
	License      string            `json:"license"`
	Requires     map[string]string `json:"requires"`
	Capabilities []string          `json:"capabilities"`
	Rating       float64           `json:"rating"`
	Installs     int64             `json:"installs"`
	Screenshots  []string          `json:"screenshots"`
	// dependencies 可能是 ["a"] 或 [{"name":"a"}]，用 RawMessage 兼容两种
	RawDependencies []json.RawMessage `json:"dependencies"`
}

// ---------- 索引 ----------

type shaEntry struct {
	Size int64  `json:"size"`
	Mod  int64  `json:"mod"`
	Sum  string `json:"sum"`
}

// Index 只读索引：扫描 {dataDir}/plugins/{slug}/{version}.zip 并缓存解析结果。
// sha256 结果会持久化到 {dataDir}/.cache/checksums.json，重启后按 size+mtime 复用。
type Index struct {
	dataDir string

	mu       sync.RWMutex
	plugins  map[string]*PluginInfo
	loadedAt time.Time
	warnings []string

	shaMu    sync.Mutex
	shaCache map[string]shaEntry
	shaDirty bool
}

// NewIndex 创建索引并载入 sha 缓存（失败不致命）。
func NewIndex(dataDir string) *Index {
	ix := &Index{
		dataDir:  dataDir,
		plugins:  map[string]*PluginInfo{},
		shaCache: map[string]shaEntry{},
	}
	ix.loadChecksumCache()
	return ix
}

func (ix *Index) checksumCachePath() string {
	return filepath.Join(ix.dataDir, ".cache", "checksums.json")
}

func (ix *Index) loadChecksumCache() {
	raw, err := os.ReadFile(ix.checksumCachePath())
	if err != nil {
		return
	}
	var m map[string]shaEntry
	if err := json.Unmarshal(raw, &m); err == nil {
		ix.shaCache = m
	}
}

// FlushChecksumCache 落盘 sha 缓存（有变化时）。
func (ix *Index) FlushChecksumCache() {
	ix.shaMu.Lock()
	defer ix.shaMu.Unlock()
	if !ix.shaDirty {
		return
	}
	path := ix.checksumCachePath()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return
	}
	raw, err := json.Marshal(ix.shaCache)
	if err != nil {
		return
	}
	_ = os.WriteFile(path, raw, 0o644)
	ix.shaDirty = false
}

// Checksum 返回文件 sha256（带 size+mtime 缓存）。
func (ix *Index) Checksum(path string, info os.FileInfo) (string, error) {
	key := path
	ix.shaMu.Lock()
	if e, ok := ix.shaCache[key]; ok && e.Size == info.Size() && e.Mod == info.ModTime().UnixNano() {
		ix.shaMu.Unlock()
		return e.Sum, nil
	}
	ix.shaMu.Unlock()

	f, err := os.Open(path)
	if err != nil {
		return "", err
	}
	defer f.Close()
	h := sha256.New()
	if _, err := io.Copy(h, f); err != nil {
		return "", err
	}
	sum := hex.EncodeToString(h.Sum(nil))

	ix.shaMu.Lock()
	ix.shaCache[key] = shaEntry{Size: info.Size(), Mod: info.ModTime().UnixNano(), Sum: sum}
	ix.shaDirty = true
	ix.shaMu.Unlock()
	return sum, nil
}

// Refresh 重建索引。
func (ix *Index) Refresh() error {
	pluginsDir := filepath.Join(ix.dataDir, "plugins")
	found := map[string]*PluginInfo{}
	warnings := []string{}

	entries, err := os.ReadDir(pluginsDir)
	if err != nil {
		if os.IsNotExist(err) {
			// 目录不存在视为空市场（不报错，方便首次启动）
			ix.replace(found, warnings)
			return nil
		}
		return fmt.Errorf("读取插件目录失败: %w", err)
	}

	for _, dirEntry := range entries {
		if !dirEntry.IsDir() {
			continue
		}
		slug := dirEntry.Name()
		if !validSlug(slug) {
			warnings = append(warnings, fmt.Sprintf("跳过非法 slug 目录: %s", slug))
			continue
		}
		slugDir := filepath.Join(pluginsDir, slug)
		files, err := os.ReadDir(slugDir)
		if err != nil {
			warnings = append(warnings, fmt.Sprintf("读取 %s 失败: %v", slug, err))
			continue
		}

		plugin := &PluginInfo{Slug: slug}
		for _, f := range files {
			name := f.Name()
			if f.IsDir() || !strings.HasSuffix(strings.ToLower(name), ".zip") {
				continue
			}
			version := strings.TrimSuffix(name, filepath.Ext(name))
			if !validVersion(version) {
				warnings = append(warnings, fmt.Sprintf("跳过非法版本文件名: %s/%s", slug, name))
				continue
			}
			zipPath := filepath.Join(slugDir, name)
			info, err := f.Info()
			if err != nil {
				warnings = append(warnings, fmt.Sprintf("读取文件信息失败 %s: %v", zipPath, err))
				continue
			}
			mf, readme, changelog, err := readPackage(zipPath)
			if err != nil {
				warnings = append(warnings, fmt.Sprintf("解析插件包失败 %s: %v", zipPath, err))
				continue
			}
			// 包内 slug 与目录名必须一致，避免"挂羊头卖狗肉"
			if mf.Slug != "" && mf.Slug != slug {
				warnings = append(warnings, fmt.Sprintf("包内 slug(%s) 与目录(%s) 不一致，已跳过: %s", mf.Slug, slug, name))
				continue
			}
			if mf.Version != "" && mf.Version != version {
				warnings = append(warnings, fmt.Sprintf("包内 version(%s) 与文件名(%s) 不一致，已跳过: %s", mf.Version, version, name))
				continue
			}
			sum, err := ix.Checksum(zipPath, info)
			if err != nil {
				warnings = append(warnings, fmt.Sprintf("计算校验和失败 %s: %v", zipPath, err))
				continue
			}

			vi := VersionInfo{
				Version:     version,
				PublishedAt: info.ModTime().UTC(),
				Changelog:   changelog,
				SHA256:      sum,
				Size:        info.Size(),
				path:        zipPath,
			}
			plugin.Versions = append(plugin.Versions, vi)
			// 最新版本决定展示字段
			if plugin.Name == "" || semverGreater(version, plugin.Version) {
				applyManifest(plugin, mf, version, info.ModTime().UTC())
				plugin.Readme = readme
				plugin.Changelog = changelog
				plugin.Screenshots = mf.Screenshots
			}
		}

		if len(plugin.Versions) == 0 {
			continue
		}
		sort.Slice(plugin.Versions, func(i, j int) bool {
			return semverGreater(plugin.Versions[i].Version, plugin.Versions[j].Version)
		})
		if plugin.Versions[0].Changelog != "" && plugin.Changelog == "" {
			plugin.Changelog = plugin.Versions[0].Changelog
		}
		found[slug] = plugin
	}

	ix.replace(found, warnings)
	ix.FlushChecksumCache()
	return nil
}

func (ix *Index) replace(found map[string]*PluginInfo, warnings []string) {
	ix.mu.Lock()
	defer ix.mu.Unlock()
	ix.plugins = found
	ix.loadedAt = time.Now()
	ix.warnings = warnings
}

func applyManifest(p *PluginInfo, mf manifest, version string, updated time.Time) {
	p.Name = mf.Name
	if p.Name == "" {
		p.Name = p.Slug
	}
	p.Version = version
	p.Summary = firstLine(mf.Description)
	p.Description = mf.Description
	p.Category = mf.Category
	p.Author = mf.Author
	p.Icon = mf.Icon
	p.Tags = mf.Tags
	p.License = mf.License
	if p.License == "" {
		p.License = "MIT"
	}
	p.Rating = mf.Rating
	p.Installs = mf.Installs
	p.UpdatedAt = updated
	p.Requires = mf.Requires
	p.Capabilities = mf.Capabilities
	p.Dependencies = normalizeDependencies(mf.RawDependencies)
}

func normalizeDependencies(raw []json.RawMessage) []string {
	out := []string{}
	for _, item := range raw {
		var s string
		if err := json.Unmarshal(item, &s); err == nil {
			if s != "" {
				out = append(out, s)
			}
			continue
		}
		var obj struct {
			Name string `json:"name"`
			Slug string `json:"slug"`
		}
		if err := json.Unmarshal(item, &obj); err == nil {
			if obj.Slug != "" {
				out = append(out, obj.Slug)
			} else if obj.Name != "" {
				out = append(out, obj.Name)
			}
		}
	}
	return out
}

// readPackage 从 zip 内读 metadata.json（根或一级子目录）+ README/CHANGELOG。
func readPackage(zipPath string) (manifest, string, string, error) {
	var mf manifest
	zr, err := zip.OpenReader(zipPath)
	if err != nil {
		return mf, "", "", err
	}
	defer zr.Close()

	var metaName string
	for _, f := range zr.File {
		clean := strings.TrimPrefix(filepath.ToSlash(f.Name), "./")
		parts := strings.Split(clean, "/")
		switch {
		case clean == "metadata.json" || (len(parts) == 2 && parts[1] == "metadata.json"):
			if metaName == "" {
				metaName = f.Name
			}
		}
	}
	if metaName == "" {
		return mf, "", "", fmt.Errorf("包内缺少 metadata.json")
	}

	read := func(name string) ([]byte, error) {
		f, err := zr.Open(name)
		if err != nil {
			return nil, err
		}
		defer f.Close()
		return io.ReadAll(io.LimitReader(f, 4<<20)) // 单文件上限 4MB，避免异常包拖垮内存
	}

	raw, err := read(metaName)
	if err != nil {
		return mf, "", "", fmt.Errorf("读取 metadata.json 失败: %w", err)
	}
	if err := json.Unmarshal(raw, &mf); err != nil {
		return mf, "", "", fmt.Errorf("metadata.json 不是合法 JSON: %w", err)
	}
	if mf.Name == "" || mf.Slug == "" || mf.Version == "" {
		return mf, "", "", fmt.Errorf("metadata.json 缺少必需字段（name/slug/version）")
	}

	prefix := ""
	if idx := strings.LastIndex(metaName, "/"); idx >= 0 {
		prefix = metaName[:idx+1]
	}
	readme := ""
	if b, err := read(prefix + "README.md"); err == nil {
		readme = string(b)
	}
	changelog := mf.changelogFromPackage(read, prefix)
	return mf, readme, changelog, nil
}

func (m manifest) changelogFromPackage(read func(string) ([]byte, error), prefix string) string {
	if b, err := read(prefix + "CHANGELOG.md"); err == nil {
		return string(b)
	}
	return ""
}

// ---------- 查询 ----------

// EnsureFresh 按 TTL 决定是否重建索引。
func (ix *Index) EnsureFresh(ttl time.Duration) error {
	ix.mu.RLock()
	stale := ttl <= 0 || time.Since(ix.loadedAt) > ttl
	ix.mu.RUnlock()
	if !stale {
		return nil
	}
	return ix.Refresh()
}

// Count 返回插件数。
func (ix *Index) Count() int {
	ix.mu.RLock()
	defer ix.mu.RUnlock()
	return len(ix.plugins)
}

// Warnings 返回最近一次索引的告警（暴露在 /health，便于站长发现放错的包）。
func (ix *Index) Warnings() []string {
	ix.mu.RLock()
	defer ix.mu.RUnlock()
	out := make([]string, len(ix.warnings))
	copy(out, ix.warnings)
	return out
}

// Get 取单个插件。
func (ix *Index) Get(slug string) *PluginInfo {
	ix.mu.RLock()
	defer ix.mu.RUnlock()
	return ix.plugins[slug]
}

// Query 列表查询（关键词 / 分类 / 排序 / 分页）。
func (ix *Index) Query(keyword, category, sortBy, order string, page, pageSize int) ([]*PluginInfo, int) {
	ix.mu.RLock()
	items := make([]*PluginInfo, 0, len(ix.plugins))
	for _, p := range ix.plugins {
		items = append(items, p)
	}
	ix.mu.RUnlock()

	if keyword != "" {
		kw := strings.ToLower(keyword)
		filtered := items[:0]
		for _, p := range items {
			if strings.Contains(strings.ToLower(p.Name), kw) ||
				strings.Contains(strings.ToLower(p.Slug), kw) ||
				strings.Contains(strings.ToLower(p.Description), kw) ||
				strings.Contains(strings.ToLower(p.Author), kw) {
				filtered = append(filtered, p)
			}
		}
		items = filtered
	}
	if category != "" {
		filtered := items[:0]
		for _, p := range items {
			if p.Category == category {
				filtered = append(filtered, p)
			}
		}
		items = filtered
	}

	desc := strings.EqualFold(order, "desc")
	less := func(i, j int) bool { return strings.ToLower(items[i].Name) < strings.ToLower(items[j].Name) }
	switch sortBy {
	case "rating":
		less = func(i, j int) bool { return items[i].Rating < items[j].Rating }
	case "installs":
		less = func(i, j int) bool { return items[i].Installs < items[j].Installs }
	case "updated":
		less = func(i, j int) bool { return items[i].UpdatedAt.Before(items[j].UpdatedAt) }
	}
	sort.SliceStable(items, func(i, j int) bool {
		if desc {
			return less(j, i)
		}
		return less(i, j)
	})

	total := len(items)
	if page < 1 {
		page = 1
	}
	if pageSize < 1 {
		pageSize = 20
	}
	if pageSize > 100 {
		pageSize = 100
	}
	start := (page - 1) * pageSize
	if start >= total {
		return []*PluginInfo{}, total
	}
	end := start + pageSize
	if end > total {
		end = total
	}
	return items[start:end], total
}

// CategoryCounts 返回分类统计。
func (ix *Index) CategoryCounts() map[string]int {
	ix.mu.RLock()
	defer ix.mu.RUnlock()
	out := map[string]int{}
	for _, p := range ix.plugins {
		cat := p.Category
		if cat == "" {
			cat = "uncategorized"
		}
		out[cat]++
	}
	return out
}

// PackagePath 返回某版本的 zip 路径（要求 slug/version 合法且存在）。
func (ix *Index) PackagePath(slug, version string) (string, bool) {
	if !validSlug(slug) || !validVersion(version) {
		return "", false
	}
	p := ix.Get(slug)
	if p == nil {
		return "", false
	}
	for _, v := range p.Versions {
		if v.Version == version {
			return v.path, true
		}
	}
	return "", false
}

// ---------- 小工具 ----------

func firstLine(s string) string {
	s = strings.TrimSpace(s)
	if idx := strings.IndexAny(s, "\r\n"); idx >= 0 {
		s = s[:idx]
	}
	if len(s) > 200 {
		s = s[:200]
	}
	return s
}

// semverGreater 比较两个语义化版本（仅在按文件名已知格式合法时调用）。
func semverGreater(a, b string) bool {
	parse := func(v string) [3]int {
		var out [3]int
		for i, part := range strings.Split(v, ".") {
			if i > 2 {
				break
			}
			n, _ := strconv.Atoi(part)
			out[i] = n
		}
		return out
	}
	av, bv := parse(a), parse(b)
	for i := 0; i < 3; i++ {
		if av[i] != bv[i] {
			return av[i] > bv[i]
		}
	}
	return false
}
