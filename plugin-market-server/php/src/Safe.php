<?php

declare(strict_types=1);

namespace PMS;

/**
 * 取值校验与安全工具（与 Go 版 safe.go 一一对应）。
 */
final class Safe
{
    public const MAX_SLUG_LEN = 64;
    public const MAX_VERSION_LEN = 32;

    /** slug: ^[a-z0-9-]+$（与 FastBlog 的 PluginManifest 同规则） */
    public static function validSlug(string $s): bool
    {
        return $s !== ''
            && strlen($s) <= self::MAX_SLUG_LEN
            && preg_match('/^[a-z0-9-]+$/', $s) === 1;
    }

    /** version: ^\d+\.\d+\.\d+$ */
    public static function validVersion(string $s): bool
    {
        return $s !== ''
            && strlen($s) <= self::MAX_VERSION_LEN
            && preg_match('/^\d+\.\d+\.\d+$/', $s) === 1;
    }

    /** 常量时间比较（Token 校验用）。 */
    public static function constantTimeEqual(string $a, string $b): bool
    {
        if ($a === '' || $b === '') {
            return false;
        }
        return hash_equals($a, $b);
    }

    /**
     * 解析 /updates?slug=seo:1.0.0&slug=shop:2.1.0
     *
     * @param  list<string> $values
     * @return array<string,string> map[slug]currentVersion
     */
    public static function parseUpdateQuery(array $values): array
    {
        $out = [];
        foreach ($values as $raw) {
            $raw = trim((string) $raw);
            if ($raw === '') {
                continue;
            }
            $slug = $raw;
            $version = '';
            $pos = strrpos($raw, ':');
            if ($pos !== false && $pos > 0) {
                $slug = substr($raw, 0, $pos);
                $version = substr($raw, $pos + 1);
            }
            if (self::validSlug($slug)) {
                $out[$slug] = $version;
            }
        }
        return $out;
    }

    /** 语义化版本比较（仅在格式已校验时调用）。 */
    public static function semverGreater(string $a, string $b): bool
    {
        $pa = array_pad(array_map('intval', explode('.', $a)), 3, 0);
        $pb = array_pad(array_map('intval', explode('.', $b)), 3, 0);
        for ($i = 0; $i < 3; $i++) {
            if ($pa[$i] !== $pb[$i]) {
                return $pa[$i] > $pb[$i];
            }
        }
        return false;
    }

    /** 分类显示名（与 Go 版/FastBlog 的 category_names 同口径）。 */
    public static function categoryDisplayName(string $slug): string
    {
        $names = [
            'seo' => 'SEO优化', 'security' => '安全防护', 'analytics' => '数据分析',
            'social' => '社交分享', 'media' => '媒体处理', 'performance' => '性能优化',
            'backup' => '备份恢复', 'marketing' => '营销工具', 'workflow' => '工作流',
            'search' => '搜索增强', 'cdn' => 'CDN加速', 'email' => '邮件营销',
            'uncategorized' => '未分类',
        ];
        return $names[$slug] ?? $slug;
    }
}
