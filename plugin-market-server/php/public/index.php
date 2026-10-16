<?php
/**
 * FastBlog 插件市场服务端（PHP 版）— 单入口。
 *
 * 路由与错误码严格对齐 ../API.md；行为与 Go 版逐条一致。
 * 启动（内置服务器）：
 *   php -S 0.0.0.0:8080 public/index.php
 * FPM/Nginx 部署时把 root 指向 public/，并把所有请求交给 index.php。
 */

declare(strict_types=1);

require __DIR__ . '/../src/Config.php';
require __DIR__ . '/../src/Safe.php';
require __DIR__ . '/../src/Index.php';
require __DIR__ . '/../src/View.php';

use PMS\Config;
use PMS\Index;
use PMS\Safe;
use PMS\View;

// ---------------------------------------------------------------- 响应工具

function respond_json(int $httpStatus, array $body): void
{
    http_response_code($httpStatus);
    header('Content-Type: application/json; charset=utf-8');
    header('X-Content-Type-Options: nosniff');
    echo json_encode($body, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES) . "\n";
}

function respond_ok(mixed $data): void
{
    respond_json(200, ['code' => 0, 'data' => $data]);
}

function respond_err(int $httpStatus, int $code, string $message): void
{
    respond_json($httpStatus, ['code' => $code, 'message' => $message, 'data' => null]);
}

function client_ip(): string
{
    $fwd = trim((string) ($_SERVER['HTTP_X_FORWARDED_FOR'] ?? ''));
    if ($fwd !== '') {
        $pos = strpos($fwd, ',');
        return trim($pos === false ? $fwd : substr($fwd, 0, $pos));
    }
    return (string) ($_SERVER['REMOTE_ADDR'] ?? 'unknown');
}

function base_url(): string
{
    $proto = trim((string) ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? ''));
    if ($proto === '') {
        $proto = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') ? 'https' : 'http';
    }
    $host = trim((string) ($_SERVER['HTTP_X_FORWARDED_HOST'] ?? ''));
    if ($host === '') {
        $host = (string) ($_SERVER['HTTP_HOST'] ?? 'localhost');
    }
    return $proto . '://' . $host;
}

/**
 * 固定窗口限流（PHP-FPM 无跨请求内存，故用带锁的文件计数）。
 * 生产建议同时在前置 nginx 限流；此处保证"默认就有限流"。
 */
function rate_limit_allow(Config $cfg, string $ip): bool
{
    if ($cfg->rateLimitPerMin <= 0) {
        return true;
    }
    $dir = rtrim($cfg->dataDir, "/\\") . '/.cache/rl';
    if (!is_dir($dir) && !@mkdir($dir, 0755, true) && !is_dir($dir)) {
        return true; // 无法建立计数器时不因此阻断服务
    }
    $file = $dir . '/' . md5($ip) . '.json';
    $fh = @fopen($file, 'c+');
    if ($fh === false) {
        return true;
    }
    try {
        if (!flock($fh, LOCK_EX)) {
            return true;
        }
        $raw = stream_get_contents($fh);
        $state = is_string($raw) && $raw !== '' ? json_decode($raw, true) : null;
        $now = time();
        if (!is_array($state) || ($now - (int) ($state['start'] ?? 0)) > 60) {
            $state = ['start' => $now, 'count' => 0];
        }
        $state['count'] = (int) $state['count'] + 1;
        ftruncate($fh, 0);
        rewind($fh);
        fwrite($fh, json_encode($state));
        fflush($fh);
        return $state['count'] <= $cfg->rateLimitPerMin;
    } finally {
        flock($fh, LOCK_UN);
        fclose($fh);
    }
}

// ---------------------------------------------------------------- 视图组装

/** @param array<string,mixed> $p */
function list_item(array $p): array
{
    $base = base_url();
    $slug = (string) $p['slug'];
    $version = (string) $p['version'];
    return [
        'slug' => $slug,
        'name' => $p['name'] ?? $slug,
        'version' => $version,
        'summary' => $p['summary'] ?? '',
        'category' => $p['category'] ?? '',
        'author' => $p['author'] ?? '',
        'icon' => $p['icon'] ?? '',
        'tags' => $p['tags'] ?? [],
        'rating' => $p['rating'] ?? 0,
        'installs' => $p['installs'] ?? 0,
        'updated_at' => $p['updated_at'] ?? '',
        'download_url' => "{$base}/api/v1/plugins/{$slug}/download/{$version}",
        'sha256' => version_sha($p, $version),
    ];
}

/** @param array<string,mixed> $p */
function version_sha(array $p, string $version): string
{
    foreach ($p['versions'] as $v) {
        if ($v['version'] === $version) {
            return (string) $v['sha256'];
        }
    }
    return '';
}

/** @param array<string,mixed> $p */
function version_view(array $p, array $v): array
{
    $base = base_url();
    $slug = (string) $p['slug'];
    return [
        'version' => $v['version'],
        'published_at' => $v['published_at'],
        'changelog' => $v['changelog'] ?? '',
        'download_url' => "{$base}/api/v1/plugins/{$slug}/download/{$v['version']}",
        'sha256' => $v['sha256'],
        'size' => $v['size'],
    ];
}

// ---------------------------------------------------------------- 启动

try {
    $cfg = Config::load();
} catch (Throwable $e) {
    respond_json(500, ['code' => 50000, 'message' => '配置错误：' . $e->getMessage(), 'data' => null]);
    exit(1);
}

$ix = new Index($cfg->dataDir);
try {
    $ix->ensureFresh($cfg->indexTtl());
} catch (Throwable $e) {
    error_log('[pms] 索引刷新失败: ' . $e->getMessage());
}

$method = strtoupper((string) ($_SERVER['REQUEST_METHOD'] ?? 'GET'));
$path = parse_url((string) ($_SERVER['REQUEST_URI'] ?? '/'), PHP_URL_PATH);
$path = is_string($path) && $path !== '' ? rtrim($path, '/') : '/';
if ($path === '') {
    $path = '/';
}

if (!rate_limit_allow($cfg, client_ip())) {
    respond_err(429, 42900, '请求过于频繁，请稍后再试');
    exit;
}

// 只读市场：非 GET/HEAD 一律拒绝（与 Go 版同一错误码）
if ($method !== 'GET' && $method !== 'HEAD') {
    if (str_starts_with($path, '/api/')) {
        respond_err(403, 40300, '本服务以只读模式运行（PMS_READONLY=true），不接受写操作；插件包请直接放入数据目录');
    } else {
        respond_err(405, 40500, '仅支持 GET/HEAD 请求');
    }
    exit;
}

// ---------------------------------------------------------------- 路由

if ($path === '/') {
    header('Content-Type: text/html; charset=utf-8');
    header('X-Content-Type-Options: nosniff');
    echo View::indexPage($cfg, $ix);
    exit;
}

if ($path === '/api/v1/health') {
    respond_ok([
        'status' => 'ok',
        'version' => $cfg->version,
        'site_name' => $cfg->siteName,
        'readonly' => $cfg->readOnly,
        'plugins' => $ix->count(),
        'warnings' => $ix->warnings(),
        'time' => gmdate('c'),
    ]);
    exit;
}

if ($path === '/api/v1/plugins') {
    $page = max(1, (int) ($_GET['page'] ?? 1));
    $pageSize = (int) ($_GET['page_size'] ?? 20);
    $result = $ix->query(
        trim((string) ($_GET['keyword'] ?? '')),
        trim((string) ($_GET['category'] ?? '')),
        trim((string) ($_GET['sort'] ?? '')),
        trim((string) ($_GET['order'] ?? '')),
        $page,
        $pageSize,
    );
    respond_ok([
        'items' => array_map('list_item', $result['items']),
        'total' => $result['total'],
        'page' => $page,
        'page_size' => min(100, max(1, $pageSize)),
    ]);
    exit;
}

if ($path === '/api/v1/categories') {
    $counts = $ix->categoryCounts();
    ksort($counts);
    $out = [];
    foreach ($counts as $slug => $count) {
        $out[] = ['slug' => $slug, 'name' => Safe::categoryDisplayName((string) $slug), 'count' => $count];
    }
    respond_ok($out);
    exit;
}

if ($path === '/api/v1/featured') {
    $limit = (int) ($_GET['limit'] ?? 6);
    if ($limit < 1 || $limit > 50) {
        $limit = 6;
    }
    $result = $ix->query('', '', 'installs', 'desc', 1, $limit);
    respond_ok(array_map('list_item', $result['items']));
    exit;
}

if ($path === '/api/v1/updates') {
    $wanted = Safe::parseUpdateQuery((array) ($_GET['slug'] ?? []));
    $updates = [];
    foreach ($wanted as $slug => $current) {
        $p = $ix->get((string) $slug);
        if ($p === null) {
            continue;
        }
        $latest = (string) $p['version'];
        if ($current !== '' && !Safe::semverGreater($latest, $current)) {
            continue;
        }
        $updates[] = [
            'slug' => $slug,
            'current' => $current,
            'latest' => $latest,
            'download_url' => base_url() . "/api/v1/plugins/{$slug}/download/{$latest}",
            'changelog' => $p['changelog'] ?? '',
            'sha256' => version_sha($p, $latest),
        ];
    }
    usort($updates, static fn (array $a, array $b): int => strcmp((string) $a['slug'], (string) $b['slug']));
    respond_ok(['updates' => $updates]);
    exit;
}

if (str_starts_with($path, '/api/v1/plugins/')) {
    $seg = substr($path, strlen('/api/v1/plugins/'));
    $parts = array_values(array_filter(explode('/', trim($seg, '/')), static fn (string $s): bool => $s !== ''));
    if ($parts === []) {
        respond_err(404, 40401, '缺少插件标识');
        exit;
    }
    $slug = $parts[0];
    if (!Safe::validSlug($slug)) {
        respond_err(400, 40000, '非法的插件标识（须匹配 ^[a-z0-9-]+$）');
        exit;
    }
    $plugin = $ix->get($slug);
    if ($plugin === null) {
        respond_err(404, 40401, "plugin not found: {$slug}");
        exit;
    }

    if (count($parts) === 1) {
        $detail = list_item($plugin);
        $detail['description'] = $plugin['description'] ?? '';
        $detail['license'] = $plugin['license'] ?? 'MIT';
        $detail['requires'] = $plugin['requires'] ?? [];
        $detail['dependencies'] = $plugin['dependencies'] ?? [];
        $detail['capabilities'] = $plugin['capabilities'] ?? [];
        $detail['readme'] = $plugin['readme'] ?? '';
        $detail['changelog'] = $plugin['changelog'] ?? '';
        $detail['screenshots'] = $plugin['screenshots'] ?? [];
        $detail['versions'] = array_map(static fn (array $v): array => version_view($plugin, $v), $plugin['versions']);
        respond_ok($detail);
        exit;
    }

    if (count($parts) === 2 && $parts[1] === 'versions') {
        respond_ok([
            'slug' => $slug,
            'latest' => (string) $plugin['version'],
            'versions' => array_map(static fn (array $v): array => version_view($plugin, $v), $plugin['versions']),
        ]);
        exit;
    }

    if (count($parts) >= 2 && $parts[1] === 'download') {
        if (count($parts) !== 3) {
            respond_err(400, 40000, '下载路径格式应为 /api/v1/plugins/{slug}/download/{version}');
            exit;
        }
        $version = $parts[2];
        if (!Safe::validVersion($version)) {
            respond_err(400, 40000, '非法的版本号（须匹配 ^\d+\.\d+\.\d+$）');
            exit;
        }
        $file = $ix->packagePath($slug, $version);
        if ($file === null || !is_file($file)) {
            respond_err(404, 40401, "版本不存在: {$slug}@{$version}");
            exit;
        }
        header('Content-Type: application/zip');
        header('Content-Disposition: attachment; filename="' . $slug . '-' . $version . '.zip"');
        header('X-Checksum-Sha256: ' . $ix->versionSha($slug, $version));
        header('Cache-Control: public, max-age=300');
        header('Content-Length: ' . (string) filesize($file));
        readfile($file);
        exit;
    }

    respond_err(404, 40400, "未知子路径: {$seg}");
    exit;
}

respond_err(404, 40400, "未知路径: {$path}");
