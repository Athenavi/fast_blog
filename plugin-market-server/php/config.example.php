<?php
/**
 * FastBlog 插件市场服务端 — 配置示例（PHP 版）
 *
 * 用法：复制为 config.php 放在项目根目录（与 src/ 同级），按需修改。
 * 优先级：环境变量 > config.php > 内置默认值（与 Go 版完全一致）。
 */

declare(strict_types=1);

return [
    // 监听地址（内置服务器/CLI 用；FPM 下由 Web 服务器决定，此项不生效）
    'listen'             => ':8080',

    // 数据目录：插件包放在 {data_dir}/plugins/{slug}/{version}.zip
    'data_dir'           => __DIR__ . '/data',

    // 站点名（出现在 /api/v1/health 与浏览页标题）
    'site_name'          => 'FastBlog Plugin Market',

    // 只读市场（推荐 true）：插件包由站长自行放入目录
    'readonly'           => true,

    // 仅在 readonly=false 时使用；留空则拒绝启动
    'admin_token'        => '',

    // 上游镜像（预留）
    'upstream_url'       => '',

    // 每 IP 每分钟请求上限（0 = 不限流）
    'rate_limit_per_min' => 60,

    // 索引缓存秒数
    'index_ttl_seconds'  => 60,

    // 下载签名（预留；需要 admin_token 作为签名密钥）
    'sign_download'      => false,

    // 上传上限（只读模式下不生效，保留给未来的写能力）
    'max_upload_bytes'   => 32 * 1024 * 1024,
];
