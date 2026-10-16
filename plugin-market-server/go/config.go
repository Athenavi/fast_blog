package main

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// Config 是服务端的全部可自定义配置。
// 优先级：环境变量 > {dataDir}/config.json > 内置默认值。
type Config struct {
	// Listen 监听地址，如 ":8080" 或 "127.0.0.1:8080"
	Listen string `json:"listen"`
	// DataDir 数据目录：插件包放 {DataDir}/plugins/{slug}/{version}.zip
	DataDir string `json:"data_dir"`
	// SiteName 出现在 /health 与浏览页标题
	SiteName string `json:"site_name"`
	// ReadOnly 为 true 时只提供浏览/下载/查更新（本项目的默认与推荐形态）
	ReadOnly bool `json:"readonly"`
	// AdminToken 仅在 ReadOnly=false 时使用；为空则拒绝启动
	AdminToken string `json:"admin_token"`
	// UpstreamURL 非空时作为上游镜像站点（预留：代理上游目录）
	UpstreamURL string `json:"upstream_url"`
	// RateLimitPerMin 每 IP 每分钟请求上限（0 = 不限流）
	RateLimitPerMin int `json:"rate_limit_per_min"`
	// IndexTTL 索引缓存秒数
	IndexTTLSeconds int `json:"index_ttl_seconds"`
	// SignDownload 开启后下载 URL 需带 expires+sig（预留，需 AdminToken 作签名密钥）
	SignDownload bool `json:"sign_download"`
	// MaxUploadBytes 上传上限（只读模式下不生效，保留给未来的写能力）
	MaxUploadBytes int64 `json:"max_upload_bytes"`
	// Version 服务端自身版本，写入 /health
	Version string `json:"-"`
}

// DefaultConfig 返回内置默认值（与 API.md §4 的表格一致）。
func DefaultConfig() Config {
	return Config{
		Listen:          ":8080",
		DataDir:         "./data",
		SiteName:        "FastBlog Plugin Market",
		ReadOnly:        true,
		AdminToken:      "",
		UpstreamURL:     "",
		RateLimitPerMin: 60,
		IndexTTLSeconds: 60,
		SignDownload:    false,
		MaxUploadBytes:  32 << 20, // 32MB
		Version:         "1.0.0",
	}
}

// IndexTTL 返回索引缓存时长。
func (c Config) IndexTTL() time.Duration {
	return time.Duration(c.IndexTTLSeconds) * time.Second
}

// PluginsDir 返回插件包目录。
func (c Config) PluginsDir() string {
	return filepath.Join(c.DataDir, "plugins")
}

// LoadConfig 读取配置文件并用环境变量覆盖，最后做合法性校验。
func LoadConfig() (Config, error) {
	cfg := DefaultConfig()

	// 1) 配置文件：优先 {PMS_DATA_DIR}/config.json，其次 ./config.json
	candidates := []string{}
	if dir := strings.TrimSpace(os.Getenv("PMS_DATA_DIR")); dir != "" {
		candidates = append(candidates, filepath.Join(dir, "config.json"))
	}
	candidates = append(candidates, "config.json")
	for _, path := range candidates {
		raw, err := os.ReadFile(path)
		if err != nil {
			continue
		}
		if err := json.Unmarshal(raw, &cfg); err != nil {
			return cfg, fmt.Errorf("解析配置文件 %s 失败: %w", path, err)
		}
		break
	}

	// 2) 环境变量覆盖（API.md §4）
	if v := strings.TrimSpace(os.Getenv("PMS_LISTEN")); v != "" {
		cfg.Listen = v
	}
	if v := strings.TrimSpace(os.Getenv("PMS_DATA_DIR")); v != "" {
		cfg.DataDir = v
	}
	if v := strings.TrimSpace(os.Getenv("PMS_SITE_NAME")); v != "" {
		cfg.SiteName = v
	}
	if v, ok := os.LookupEnv("PMS_READONLY"); ok {
		b, err := parseBool(v)
		if err != nil {
			return cfg, fmt.Errorf("PMS_READONLY 取值非法: %q", v)
		}
		cfg.ReadOnly = b
	}
	if v := strings.TrimSpace(os.Getenv("PMS_ADMIN_TOKEN")); v != "" {
		cfg.AdminToken = v
	}
	if v := strings.TrimSpace(os.Getenv("PMS_UPSTREAM_URL")); v != "" {
		cfg.UpstreamURL = v
	}
	if v := strings.TrimSpace(os.Getenv("PMS_RATE_LIMIT")); v != "" {
		n, err := parseRateLimit(v)
		if err != nil {
			return cfg, err
		}
		cfg.RateLimitPerMin = n
	}
	if v := strings.TrimSpace(os.Getenv("PMS_INDEX_TTL")); v != "" {
		n, err := strconv.Atoi(v)
		if err != nil || n < 0 {
			return cfg, fmt.Errorf("PMS_INDEX_TTL 取值非法: %q", v)
		}
		cfg.IndexTTLSeconds = n
	}
	if v, ok := os.LookupEnv("PMS_SIGN_DOWNLOAD"); ok {
		b, err := parseBool(v)
		if err != nil {
			return cfg, fmt.Errorf("PMS_SIGN_DOWNLOAD 取值非法: %q", v)
		}
		cfg.SignDownload = b
	}
	if v := strings.TrimSpace(os.Getenv("PMS_MAX_UPLOAD")); v != "" {
		n, err := strconv.ParseInt(v, 10, 64)
		if err != nil || n <= 0 {
			return cfg, fmt.Errorf("PMS_MAX_UPLOAD 取值非法: %q", v)
		}
		cfg.MaxUploadBytes = n
	}

	// 3) 校验：写模式必须有 Token，否则等于裸奔
	if !cfg.ReadOnly && cfg.AdminToken == "" {
		return cfg, fmt.Errorf("PMS_READONLY=false 时必须设置 PMS_ADMIN_TOKEN（否则任何人都能发布插件）")
	}
	if cfg.SignDownload && cfg.AdminToken == "" {
		return cfg, fmt.Errorf("PMS_SIGN_DOWNLOAD=true 时必须设置 PMS_ADMIN_TOKEN（用作下载签名密钥）")
	}
	return cfg, nil
}

func parseBool(v string) (bool, error) {
	switch strings.ToLower(strings.TrimSpace(v)) {
	case "1", "true", "yes", "on":
		return true, nil
	case "0", "false", "no", "off":
		return false, nil
	}
	return false, fmt.Errorf("非法布尔值 %q", v)
}

// parseRateLimit 接受 "60"、"60/min"、"0"（关闭）三种写法。
func parseRateLimit(v string) (int, error) {
	s := strings.ToLower(strings.TrimSpace(v))
	s = strings.TrimSuffix(s, "/min")
	s = strings.TrimSuffix(s, "/minute")
	n, err := strconv.Atoi(strings.TrimSpace(s))
	if err != nil || n < 0 {
		return 0, fmt.Errorf("PMS_RATE_LIMIT 取值非法: %q", v)
	}
	return n, nil
}
