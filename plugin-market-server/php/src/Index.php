<?php

declare(strict_types=1);

namespace PMS;

use RuntimeException;
use Throwable;
use ZipArchive;

/**
 * 只读插件索引：扫描 {dataDir}/plugins/{slug}/{version}.zip，
 * 从包内 metadata.json 读取展示字段（与 Go 版 index.go 行为一致）。
 *
 * sha256 结果缓存于 {dataDir}/.cache/checksums.json，按 size+mtime 复用。
 */
final class Index
{
    /** @var array<string, array<string,mixed>> slug => 插件（含 versions） */
    private array $plugins = [];

    /** @var list<string> */
    private array $warnings = [];

    private int $loadedAt = 0;

    /** @var array<string, array{size:int,mod:int,sum:string}> */
    private array $shaCache = [];

    private bool $shaDirty = false;

    public function __construct(private readonly string $dataDir)
    {
        $this->loadChecksumCache();
    }

    // ---------------------------------------------------------------- 校验和缓存

    private function checksumCachePath(): string
    {
        return rtrim($this->dataDir, "/\\") . '/.cache/checksums.json';
    }

    private function loadChecksumCache(): void
    {
        $path = $this->checksumCachePath();
        if (!is_file($path)) {
            return;
        }
        $raw = @file_get_contents($path);
        if ($raw === false) {
            return;
        }
        $decoded = json_decode($raw, true);
        if (is_array($decoded)) {
            $this->shaCache = $decoded;
        }
    }

    public function flushChecksumCache(): void
    {
        if (!$this->shaDirty) {
            return;
        }
        $path = $this->checksumCachePath();
        $dir = dirname($path);
        if (!is_dir($dir) && !@mkdir($dir, 0755, true) && !is_dir($dir)) {
            return;
        }
        $json = json_encode($this->shaCache);
        if ($json !== false) {
            @file_put_contents($path, $json);
            $this->shaDirty = false;
        }
    }

    /** 计算文件 sha256（size+mtime 命中缓存则直接复用）。 */
    public function checksum(string $path, int $size, int $mtime): string
    {
        $key = $path;
        $cached = $this->shaCache[$key] ?? null;
        if (is_array($cached) && ($cached['size'] ?? null) === $size && ($cached['mod'] ?? null) === $mtime) {
            return (string) $cached['sum'];
        }
        $sum = hash_file('sha256', $path);
        if ($sum === false) {
            throw new RuntimeException("计算校验和失败: {$path}");
        }
        $this->shaCache[$key] = ['size' => $size, 'mod' => $mtime, 'sum' => $sum];
        $this->shaDirty = true;
        return $sum;
    }

    // ---------------------------------------------------------------- 构建索引

    /** 重建索引；插件目录不存在时视为空市场。 */
    public function refresh(): void
    {
        $pluginsDir = rtrim($this->dataDir, "/\\") . '/plugins';
        $found = [];
        $this->warnings = [];

        if (!is_dir($pluginsDir)) {
            $this->plugins = $found;
            $this->loadedAt = time();
            return;
        }

        foreach (scandir($pluginsDir) ?: [] as $slug) {
            if ($slug === '.' || $slug === '..') {
                continue;
            }
            $slugDir = $pluginsDir . '/' . $slug;
            if (!is_dir($slugDir)) {
                continue;
            }
            if (!Safe::validSlug($slug)) {
                $this->warnings[] = "跳过非法 slug 目录: {$slug}";
                continue;
            }

            $plugin = ['slug' => $slug, 'versions' => []];
            foreach (scandir($slugDir) ?: [] as $file) {
                if ($file === '.' || $file === '..') {
                    continue;
                }
                $zipPath = $slugDir . '/' . $file;
                if (!is_file($zipPath) || strtolower(pathinfo($file, PATHINFO_EXTENSION)) !== 'zip') {
                    continue;
                }
                $version = pathinfo($file, PATHINFO_FILENAME);
                if (!Safe::validVersion($version)) {
                    $this->warnings[] = "跳过非法版本文件名: {$slug}/{$file}";
                    continue;
                }

                $size = (int) filesize($zipPath);
                $mtime = (int) filemtime($zipPath);
                try {
                    $pkg = $this->readPackage($zipPath);
                } catch (Throwable $e) {
                    $this->warnings[] = "解析插件包失败 {$slug}/{$file}: " . $e->getMessage();
                    continue;
                }
                if (($pkg['meta']['slug'] ?? '') !== $slug) {
                    $this->warnings[] = "包内 slug 与目录不一致，已跳过: {$slug}/{$file}";
                    continue;
                }
                if (($pkg['meta']['version'] ?? '') !== $version) {
                    $this->warnings[] = "包内 version 与文件名不一致，已跳过: {$slug}/{$file}";
                    continue;
                }
                try {
                    $sum = $this->checksum($zipPath, $size, $mtime);
                } catch (Throwable $e) {
                    $this->warnings[] = "{$slug}/{$file}: " . $e->getMessage();
                    continue;
                }

                $plugin['versions'][] = [
                    'version' => $version,
                    'published_at' => gmdate('c', $mtime),
                    'changelog' => (string) ($pkg['changelog'] ?? ''),
                    'sha256' => $sum,
                    'size' => $size,
                    '_path' => $zipPath,
                ];

                $currentLatest = (string) ($plugin['version'] ?? '');
                if ($currentLatest === '' || Safe::semverGreater($version, $currentLatest)) {
                    $this->applyManifest($plugin, $pkg['meta'], $version, gmdate('c', $mtime));
                    $plugin['readme'] = (string) ($pkg['readme'] ?? '');
                    $plugin['changelog'] = (string) ($pkg['changelog'] ?? '');
                    $plugin['screenshots'] = (array) ($pkg['meta']['screenshots'] ?? []);
                }
            }

            if ($plugin['versions'] === []) {
                continue;
            }
            usort($plugin['versions'], static function (array $a, array $b): int {
                if ($a['version'] === $b['version']) {
                    return 0;
                }
                return Safe::semverGreater($a['version'], $b['version']) ? -1 : 1;
            });
            if (($plugin['changelog'] ?? '') === '' && ($plugin['versions'][0]['changelog'] ?? '') !== '') {
                $plugin['changelog'] = $plugin['versions'][0]['changelog'];
            }
            $found[$slug] = $plugin;
        }

        $this->plugins = $found;
        $this->loadedAt = time();
        $this->flushChecksumCache();
    }

    private function applyManifest(array &$plugin, array $meta, string $version, string $updatedAt): void
    {
        $plugin['name'] = (string) ($meta['name'] ?? '') !== '' ? (string) $meta['name'] : $plugin['slug'];
        $plugin['version'] = $version;
        $description = (string) ($meta['description'] ?? '');
        $plugin['summary'] = $this->firstLine($description);
        $plugin['description'] = $description;
        $plugin['category'] = (string) ($meta['category'] ?? '');
        $plugin['author'] = (string) ($meta['author'] ?? '');
        $plugin['icon'] = (string) ($meta['icon'] ?? '');
        $plugin['tags'] = array_values((array) ($meta['tags'] ?? []));
        $plugin['license'] = (string) ($meta['license'] ?? 'MIT');
        $plugin['rating'] = (float) ($meta['rating'] ?? 0);
        $plugin['installs'] = (int) ($meta['installs'] ?? 0);
        $plugin['updated_at'] = $updatedAt;
        $plugin['requires'] = (array) ($meta['requires'] ?? []);
        $plugin['capabilities'] = array_values((array) ($meta['capabilities'] ?? []));
        $plugin['dependencies'] = $this->normalizeDependencies((array) ($meta['dependencies'] ?? []));
    }

    /** @param list<mixed> $raw */
    private function normalizeDependencies(array $raw): array
    {
        $out = [];
        foreach ($raw as $item) {
            if (is_string($item) && $item !== '') {
                $out[] = $item;
                continue;
            }
            if (is_array($item)) {
                $name = (string) ($item['slug'] ?? $item['name'] ?? '');
                if ($name !== '') {
                    $out[] = $name;
                }
            }
        }
        return $out;
    }

    private function firstLine(string $s): string
    {
        $s = trim($s);
        $pos = strcspn($s, "\r\n");
        $s = substr($s, 0, $pos);
        return strlen($s) > 200 ? substr($s, 0, 200) : $s;
    }

    /**
     * 从 zip 中读 metadata.json（根或一级子目录）+ README.md / CHANGELOG.md。
     *
     * @return array{meta:array<string,mixed>, readme:string, changelog:string}
     */
    private function readPackage(string $zipPath): array
    {
        $zip = new ZipArchive();
        if ($zip->open($zipPath) !== true) {
            throw new RuntimeException('无法打开 zip');
        }
        try {
            $metaName = null;
            for ($i = 0; $i < $zip->numFiles; $i++) {
                $name = (string) $zip->getNameIndex($i);
                $clean = ltrim(str_replace('\\', '/', $name), './');
                if ($clean === 'metadata.json' || preg_match('#^[^/]+/metadata\.json$#', $clean) === 1) {
                    $metaName = $name;
                    break;
                }
            }
            if ($metaName === null) {
                throw new RuntimeException('包内缺少 metadata.json');
            }
            $rawMeta = $zip->getFromName($metaName);
            if ($rawMeta === false) {
                throw new RuntimeException('读取 metadata.json 失败');
            }
            $meta = json_decode($rawMeta, true);
            if (!is_array($meta)) {
                throw new RuntimeException('metadata.json 不是合法 JSON');
            }
            foreach (['name', 'slug', 'version'] as $field) {
                if (empty($meta[$field]) || !is_string($meta[$field])) {
                    throw new RuntimeException("metadata.json 缺少必需字段 {$field}");
                }
            }
            $prefix = '';
            $slash = strrpos($metaName, '/');
            if ($slash !== false) {
                $prefix = substr($metaName, 0, $slash + 1);
            }
            $readme = $this->readMember($zip, $prefix . 'README.md');
            $changelog = $this->readMember($zip, $prefix . 'CHANGELOG.md');

            return ['meta' => $meta, 'readme' => $readme, 'changelog' => $changelog];
        } finally {
            $zip->close();
        }
    }

    /** 单成员读取上限 4MB，避免异常包拖垮内存。 */
    private function readMember(ZipArchive $zip, string $name): string
    {
        $stat = $zip->statName($name);
        if ($stat === false || (int) $stat['size'] > 4 * 1024 * 1024) {
            return '';
        }
        $content = $zip->getFromName($name);
        return $content === false ? '' : $content;
    }

    // ---------------------------------------------------------------- 查询

    public function ensureFresh(int $ttl): void
    {
        if ($ttl <= 0 || (time() - $this->loadedAt) > $ttl || $this->loadedAt === 0) {
            $this->refresh();
        }
    }

    public function count(): int
    {
        return count($this->plugins);
    }

    /** @return list<string> */
    public function warnings(): array
    {
        return $this->warnings;
    }

    /** @return array<string,mixed>|null */
    public function get(string $slug): ?array
    {
        return $this->plugins[$slug] ?? null;
    }

    /**
     * @return array{items:list<array<string,mixed>>, total:int}
     */
    public function query(string $keyword, string $category, string $sort, string $order, int $page, int $pageSize): array
    {
        $items = array_values($this->plugins);

        if ($keyword !== '') {
            $kw = mb_strtolower($keyword);
            $items = array_values(array_filter($items, static function (array $p) use ($kw): bool {
                foreach (['name', 'slug', 'description', 'author'] as $field) {
                    if (str_contains(mb_strtolower((string) ($p[$field] ?? '')), $kw)) {
                        return true;
                    }
                }
                return false;
            }));
        }
        if ($category !== '') {
            $items = array_values(array_filter($items, static fn (array $p): bool => ($p['category'] ?? '') === $category));
        }

        $desc = strcasecmp($order, 'desc') === 0;
        usort($items, static function (array $a, array $b) use ($sort, $desc): int {
            $cmp = match ($sort) {
                'rating' => ($a['rating'] ?? 0) <=> ($b['rating'] ?? 0),
                'installs' => ($a['installs'] ?? 0) <=> ($b['installs'] ?? 0),
                'updated' => strcmp((string) ($a['updated_at'] ?? ''), (string) ($b['updated_at'] ?? '')),
                default => strcasecmp((string) ($a['name'] ?? ''), (string) ($b['name'] ?? '')),
            };
            return $desc ? -$cmp : $cmp;
        });

        $total = count($items);
        $page = max(1, $page);
        $pageSize = min(100, max(1, $pageSize));
        $offset = ($page - 1) * $pageSize;
        if ($offset >= $total) {
            return ['items' => [], 'total' => $total];
        }
        return ['items' => array_slice($items, $offset, $pageSize), 'total' => $total];
    }

    /** @return array<string,int> */
    public function categoryCounts(): array
    {
        $out = [];
        foreach ($this->plugins as $p) {
            $cat = (string) ($p['category'] ?? '');
            if ($cat === '') {
                $cat = 'uncategorized';
            }
            $out[$cat] = ($out[$cat] ?? 0) + 1;
        }
        return $out;
    }

    /** 某版本的磁盘路径（slug/version 必须合法且存在）。 */
    public function packagePath(string $slug, string $version): ?string
    {
        if (!Safe::validSlug($slug) || !Safe::validVersion($version)) {
            return null;
        }
        $plugin = $this->get($slug);
        if ($plugin === null) {
            return null;
        }
        foreach ($plugin['versions'] as $v) {
            if ($v['version'] === $version) {
                return (string) $v['_path'];
            }
        }
        return null;
    }

    /** 取某版本的 sha256（用于下载响应头与 updates）。 */
    public function versionSha(string $slug, string $version): string
    {
        $plugin = $this->get($slug);
        if ($plugin === null) {
            return '';
        }
        foreach ($plugin['versions'] as $v) {
            if ($v['version'] === $version) {
                return (string) $v['sha256'];
            }
        }
        return '';
    }
}
