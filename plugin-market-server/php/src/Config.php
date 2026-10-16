<?php

declare(strict_types=1);

namespace PMS;

use RuntimeException;

/**
 * 服务端配置：优先级 环境变量 > config.php > 默认值（与 Go 版逐项一致）。
 */
final class Config
{
    public function __construct(
        public readonly string $listen = ':8080',
        public readonly string $dataDir = './data',
        public readonly string $siteName = 'FastBlog Plugin Market',
        public readonly bool $readOnly = true,
        public readonly string $adminToken = '',
        public readonly string $upstreamUrl = '',
        public readonly int $rateLimitPerMin = 60,
        public readonly int $indexTtlSeconds = 60,
        public readonly bool $signDownload = false,
        public readonly int $maxUploadBytes = 33554432,
        public readonly string $version = '1.0.0',
    ) {
    }

    public function pluginsDir(): string
    {
        return rtrim($this->dataDir, "/\\") . DIRECTORY_SEPARATOR . 'plugins';
    }

    public function indexTtl(): int
    {
        return max(0, $this->indexTtlSeconds);
    }

    /**
     * 载入配置：先读 config.php，再由环境变量覆盖，最后做强制校验。
     */
    public static function load(?string $configPath = null): self
    {
        $file = $configPath ?? dirname(__DIR__) . '/config.php';
        $raw = [];
        if (is_file($file)) {
            /** @var mixed $loaded */
            $loaded = require $file;
            if (!is_array($loaded)) {
                throw new RuntimeException("配置文件 {$file} 必须返回数组");
            }
            $raw = $loaded;
        }

        $pick = static function (string $key, mixed $default) use ($raw): mixed {
            return array_key_exists($key, $raw) ? $raw[$key] : $default;
        };

        $cfg = new self(
            listen: (string) env_str('PMS_LISTEN', (string) $pick('listen', ':8080')),
            dataDir: (string) env_str('PMS_DATA_DIR', (string) $pick('data_dir', './data')),
            siteName: (string) env_str('PMS_SITE_NAME', (string) $pick('site_name', 'FastBlog Plugin Market')),
            readOnly: env_bool('PMS_READONLY', (bool) $pick('readonly', true)),
            adminToken: (string) env_str('PMS_ADMIN_TOKEN', (string) $pick('admin_token', '')),
            upstreamUrl: (string) env_str('PMS_UPSTREAM_URL', (string) $pick('upstream_url', '')),
            rateLimitPerMin: env_rate_limit('PMS_RATE_LIMIT', (int) $pick('rate_limit_per_min', 60)),
            indexTtlSeconds: env_int('PMS_INDEX_TTL', (int) $pick('index_ttl_seconds', 60), 0),
            signDownload: env_bool('PMS_SIGN_DOWNLOAD', (bool) $pick('sign_download', false)),
            maxUploadBytes: env_int('PMS_MAX_UPLOAD', (int) $pick('max_upload_bytes', 33554432), 1),
        );

        if (!$cfg->readOnly && $cfg->adminToken === '') {
            throw new RuntimeException('PMS_READONLY=false 时必须设置 PMS_ADMIN_TOKEN（否则任何人都能发布插件）');
        }
        if ($cfg->signDownload && $cfg->adminToken === '') {
            throw new RuntimeException('PMS_SIGN_DOWNLOAD=true 时必须设置 PMS_ADMIN_TOKEN（用作下载签名密钥）');
        }
        return $cfg;
    }
}

/**
 * 读取字符串型环境变量；未设置（含空串）时用默认值。
 */
function env_str(string $name, string $default): string
{
    $v = getenv($name);
    if ($v === false || trim($v) === '') {
        return $default;
    }
    return trim($v);
}

function env_bool(string $name, bool $default): bool
{
    $v = getenv($name);
    if ($v === false || trim($v) === '') {
        return $default;
    }
    return match (strtolower(trim($v))) {
        '1', 'true', 'yes', 'on' => true,
        '0', 'false', 'no', 'off' => false,
        default => throw new RuntimeException("环境变量 {$name} 取值非法: " . $v),
    };
}

function env_int(string $name, int $default, int $min): int
{
    $v = getenv($name);
    if ($v === false || trim($v) === '') {
        return $default;
    }
    if (!preg_match('/^-?\d+$/', trim($v))) {
        throw new RuntimeException("环境变量 {$name} 取值非法: " . $v);
    }
    $n = (int) trim($v);
    if ($n < $min) {
        throw new RuntimeException("环境变量 {$name} 不能小于 {$min}");
    }
    return $n;
}

/** 接受 "60"、"60/min"、"0"（关闭）三种写法。 */
function env_rate_limit(string $name, int $default): int
{
    $v = getenv($name);
    if ($v === false || trim($v) === '') {
        return $default;
    }
    $s = strtolower(trim($v));
    $s = preg_replace('#/min(ute)?$#', '', $s) ?? $s;
    $s = trim($s);
    if (!preg_match('/^\d+$/', $s)) {
        throw new RuntimeException("环境变量 {$name} 取值非法: " . $v);
    }
    return (int) $s;
}
