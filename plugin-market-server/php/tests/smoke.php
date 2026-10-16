<?php
/**
 * PHP 版冒烟测试（无 PHPUnit 依赖）：php tests/smoke.php
 *
 * 覆盖：配置校验、slug/version 校验、索引扫描与坏包容错、
 * 查询过滤/排序/分页、包路径与 sha256、updates 解析。
 * HTTP 层由 docker + curl 在 CI/本地另行验证（见 README）。
 */

declare(strict_types=1);

require __DIR__ . '/../src/Config.php';
require __DIR__ . '/../src/Safe.php';
require __DIR__ . '/../src/Index.php';

use PMS\Config;
use PMS\Index;
use PMS\Safe;

$failures = 0;
$checks = 0;

function check(string $name, bool $ok): void
{
    global $failures, $checks;
    $checks++;
    if ($ok) {
        echo "  ok   {$name}\n";
        return;
    }
    $failures++;
    echo "  FAIL {$name}\n";
}

/** 生成一个合法插件包 */
function make_plugin_zip(string $dataDir, string $slug, string $version, string $name, array $extra = []): void
{
    $dir = $dataDir . '/plugins/' . $slug;
    if (!is_dir($dir)) {
        mkdir($dir, 0755, true);
    }
    $zip = new ZipArchive();
    $path = $dir . '/' . $version . '.zip';
    $zip->open($path, ZipArchive::CREATE | ZipArchive::OVERWRITE);
    $meta = array_merge([
        'name' => $name,
        'slug' => $slug,
        'version' => $version,
        'description' => "首行摘要\n第二行",
        'author' => 'FastBlog Team',
        'category' => 'seo',
        'icon' => '🔍',
        'tags' => ['seo'],
        'license' => 'MIT',
        'requires' => ['fastblog' => '>=1.0.0'],
    ], $extra);
    $zip->addFromString('metadata.json', (string) json_encode($meta, JSON_UNESCAPED_UNICODE));
    $zip->addFromString('plugin.py', '# plugin');
    $zip->addFromString('README.md', "# {$name} 说明");
    $zip->addFromString('CHANGELOG.md', "## {$version}");
    $zip->close();
}

echo "== Safe 校验 ==\n";
check('validSlug 接受合法值', Safe::validSlug('seo') && Safe::validSlug('article-likes'));
check('validSlug 拒绝非法值', !Safe::validSlug('Seo') && !Safe::validSlug('../etc') && !Safe::validSlug('') && !Safe::validSlug('a_b'));
check('validVersion 接受 x.y.z', Safe::validVersion('1.0.0') && Safe::validVersion('10.20.30'));
check('validVersion 拒绝非语义化', !Safe::validVersion('1.0') && !Safe::validVersion('v1.0.0') && !Safe::validVersion('1.0.0-beta'));
check('constantTimeEqual', Safe::constantTimeEqual('a', 'a') && !Safe::constantTimeEqual('a', 'b') && !Safe::constantTimeEqual('', ''));
check('semverGreater 按数字比较', !Safe::semverGreater('1.2.0', '1.10.0') && Safe::semverGreater('1.10.0', '1.2.0'));
check('semverGreater 相同版本', !Safe::semverGreater('1.0.0', '1.0.0'));
$parsed = Safe::parseUpdateQuery(['seo:1.0.0', 'shop', 'BAD!', 'x:1.2']);
check('parseUpdateQuery 过滤非法项', count($parsed) === 3 && $parsed['seo'] === '1.0.0' && $parsed['shop'] === '');

echo "== 配置校验 ==\n";
putenv('PMS_READONLY=false');
putenv('PMS_ADMIN_TOKEN');
$threw = false;
try {
    Config::load(__DIR__ . '/no-such-config.php');
} catch (Throwable $e) {
    $threw = true;
}
check('只读=false 且无 Token 必须报错', $threw);
putenv('PMS_ADMIN_TOKEN=s3cret');
$cfg = Config::load(__DIR__ . '/no-such-config.php');
check('提供 Token 后配置合法且只读=false', $cfg->readOnly === false);
putenv('PMS_READONLY=true');
putenv('PMS_RATE_LIMIT=0');
check('PMS_RATE_LIMIT=0 被接受', (Config::load(__DIR__ . '/no-such-config.php'))->rateLimitPerMin === 0);
putenv('PMS_RATE_LIMIT=abc');
$threw = false;
try {
    Config::load(__DIR__ . '/no-such-config.php');
} catch (Throwable $e) {
    $threw = true;
}
check('非法 PMS_RATE_LIMIT 报错', $threw);
putenv('PMS_RATE_LIMIT');
putenv('PMS_READONLY');

echo "== 索引与查询 ==\n";
$dataDir = sys_get_temp_dir() . '/pms-smoke-' . getmypid();
@mkdir($dataDir, 0755, true);
make_plugin_zip($dataDir, 'seo', '1.0.0', 'SEO Auto');
make_plugin_zip($dataDir, 'seo', '1.2.0', 'SEO Auto');
make_plugin_zip($dataDir, 'shop', '2.1.0', 'Shop', ['category' => 'marketing']);

$ix = new Index($dataDir);
$ix->refresh();
check('索引到 2 个插件', $ix->count() === 2);

$seo = $ix->get('seo');
check('latest 取最高版本', $seo !== null && $seo['version'] === '1.2.0');
check('版本倒序', $seo['versions'][0]['version'] === '1.2.0' && count($seo['versions']) === 2);
check('summary 只取首行', ($seo['summary'] ?? '') === '首行摘要');
check('readme 从包内读取', ($seo['readme'] ?? '') === '# SEO Auto 说明');
check('sha256 为 64 位十六进制', preg_match('/^[0-9a-f]{64}$/', (string) $seo['versions'][0]['sha256']) === 1);

$byKeyword = $ix->query('shop', '', '', '', 1, 20);
check('关键词过滤', $byKeyword['total'] === 1 && $byKeyword['items'][0]['slug'] === 'shop');
$byCategory = $ix->query('', 'seo', '', '', 1, 20);
check('分类过滤', $byCategory['total'] === 1 && $byCategory['items'][0]['slug'] === 'seo');
$paged = $ix->query('', '', 'name', 'asc', 2, 1);
check('分页', $paged['total'] === 2 && count($paged['items']) === 1);
check('分类统计', $ix->categoryCounts() === ['seo' => 1, 'marketing' => 1]);

$path = $ix->packagePath('seo', '1.0.0');
check('包路径可获取', is_string($path) && is_file($path));
check('非法 slug 取不到路径', $ix->packagePath('../etc', '1.0.0') === null);
check('非法版本取不到路径', $ix->packagePath('seo', '1.0') === null);
check('versionSha 可获取', preg_match('/^[0-9a-f]{64}$/', $ix->versionSha('seo', '1.2.0')) === 1);

echo "== 坏包容错 ==\n";
$badDir = sys_get_temp_dir() . '/pms-smoke-bad-' . getmypid();
@mkdir($badDir . '/plugins/Bad_Slug', 0755, true);
@mkdir($badDir . '/plugins/shop', 0755, true);
file_put_contents($badDir . '/plugins/shop/notaversion.zip', 'x');
file_put_contents($badDir . '/plugins/shop/3.0.0.zip', 'not a zip');
make_plugin_zip($badDir, 'mismatch', '1.0.0', 'Mismatch', ['slug' => 'other']);
$ixBad = new Index($badDir);
$ixBad->refresh();
check('坏包全部被跳过', $ixBad->count() === 0);
check('产生索引告警', count($ixBad->warnings()) >= 3);

// 清理临时目录
$cleanup = static function (string $dir): void {
    if (!is_dir($dir)) {
        return;
    }
    $items = new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator($dir, FilesystemIterator::SKIP_DOTS),
        RecursiveIteratorIterator::CHILD_FIRST
    );
    foreach ($items as $item) {
        $item->isDir() ? @rmdir($item->getPathname()) : @unlink($item->getPathname());
    }
    @rmdir($dir);
};
$cleanup($dataDir);
$cleanup($badDir);

echo "\n共 {$checks} 项，失败 {$failures} 项\n";
exit($failures === 0 ? 0 : 1);
