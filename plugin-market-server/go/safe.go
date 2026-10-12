package main

import (
	"crypto/subtle"
	"regexp"
	"strings"
)

// slug 与 version 的取值规则必须与 FastBlog 的 PluginManifest 一致：
// slug: ^[a-z0-9-]+$ ； version: ^\d+\.\d+\.\d+$
var (
	slugRe    = regexp.MustCompile(`^[a-z0-9-]+$`)
	versionRe = regexp.MustCompile(`^\d+\.\d+\.\d+$`)
)

const maxSlugLen = 64
const maxVersionLen = 32

// validSlug 校验插件标识；长度上限另算，避免超长目录名。
func validSlug(s string) bool {
	return s != "" && len(s) <= maxSlugLen && slugRe.MatchString(s)
}

// validVersion 校验版本号。
func validVersion(s string) bool {
	return s != "" && len(s) <= maxVersionLen && versionRe.MatchString(s)
}

// constantTimeEqual 常量时间比较（用于 Token 校验，避免时序侧信道）。
func constantTimeEqual(a, b string) bool {
	if a == "" || b == "" {
		return false
	}
	return subtle.ConstantTimeCompare([]byte(a), []byte(b)) == 1
}

// parseUpdateQuery 解析 /updates?slug=seo:1.0.0&slug=shop:2.1.0
// 返回 map[slug]currentVersion；非法项被忽略（不因此让整个请求失败）。
func parseUpdateQuery(values []string) map[string]string {
	out := map[string]string{}
	for _, raw := range values {
		raw = strings.TrimSpace(raw)
		if raw == "" {
			continue
		}
		slug, version := raw, ""
		if idx := strings.LastIndex(raw, ":"); idx > 0 {
			slug, version = raw[:idx], raw[idx+1:]
		}
		if validSlug(slug) {
			out[slug] = version
		}
	}
	return out
}
