// Plugin Frontend Scanner — Nuxt 版
//
// 构建 / 开发 / 类型检查前运行（见 frontend/web/package.json 的 prescan / prebuild / predev）。
// 把 plugins/*/frontend/ 的插件前端源码与清单同步给 frontend/web，
// 供后台「插件页面」宿主 src/pages/admin/plugin-pages/[slug].vue 按 slug 加载。
//
// 产出（都在 frontend/web/src 内，已被 .gitignore 忽略）：
//   .plugin-pages/<slug>/**   插件前端源码副本
//   .plugin-pages/_loader.ts  Vue 组件加载表（import.meta.glob）
//   .plugin-registry.ts       导航项 + 页面路由登记
//
// 迁移状态：manifest.routes[].component 目前多为 React（.tsx）。
// 加载表只收录同名 .vue 组件；尚未重写为 Vue 的插件，宿主页显示「待迁移」占位，
// 原 React 实现保留在 plugins/<slug>/frontend/ 下（不随 frontend-astro 移除而丢失）。

import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(__dirname, '..');
const FRONTEND_DIR = path.join(PROJECT_ROOT, 'frontend', 'web');
const PLUGINS_DIR = path.join(PROJECT_ROOT, 'plugins');
const SRC_DIR = path.join(FRONTEND_DIR, 'src');
const GENERATED_SRC = path.join(SRC_DIR, '.plugin-pages');
const LOADER_FILE = path.join(GENERATED_SRC, '_loader.ts');
const REGISTRY_FILE = path.join(SRC_DIR, '.plugin-registry.ts');

function log(msg) {
  console.log(`[plugin-scanner] ${msg}`);
}

function scanPlugins() {
  if (!fs.existsSync(PLUGINS_DIR)) {
    log('No plugins/ directory found.');
    return [];
  }

    const entries = fs.readdirSync(PLUGINS_DIR, {withFileTypes: true});
  const plugins = [];

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const manifestPath = path.join(PLUGINS_DIR, entry.name, 'frontend', 'manifest.json');
    if (!fs.existsSync(manifestPath)) continue;

    try {
      const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
        plugins.push({slug: entry.name, manifest});
      log(`Found plugin frontend: ${entry.name}`);
    } catch (e) {
      log(`Warning: Failed to parse manifest for ${entry.name}: ${e.message}`);
    }
  }

  return plugins;
}

function copyPluginSource(slug) {
  const srcDir = path.join(PLUGINS_DIR, slug, 'frontend');
  const destDir = path.join(GENERATED_SRC, slug);

  // Clean and recreate
    fs.rmSync(destDir, {recursive: true, force: true});

  function copyRecursive(src, dest) {
      fs.mkdirSync(dest, {recursive: true});
      const items = fs.readdirSync(src, {withFileTypes: true});
    for (const item of items) {
      const srcPath = path.join(src, item.name);
      const destPath = path.join(dest, item.name);
      if (item.isDirectory()) {
        if (item.name !== 'node_modules') copyRecursive(srcPath, destPath);
      } else {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  }

  if (fs.existsSync(srcDir)) {
    copyRecursive(srcDir, destDir);
      log(`Copied frontend source: ${slug} -> .plugin-pages/${slug}/`);
  }
}

/** manifest 登记的组件是否已有同名 Vue 实现（决定宿主页能否渲染） */
function isMigrated(slug, component) {
    const rel = String(component || '')
        .replace(/^\.\//, '')
        .replace(/\.tsx?$/, '.vue');
    if (!rel) return false;
    return fs.existsSync(path.join(PLUGINS_DIR, slug, 'frontend', rel));
}

function writeLoader() {
    // 内容固定（不含时间戳等易变量），便于作为稳定生成物比对
    const content = `// 由 scripts/scan-plugin-frontend.mjs 生成，请勿手改。
// 只收录已迁移为 Vue 的插件页面组件（.vue）。

import type {Component} from 'vue'

export const pluginPageModules = import.meta.glob<Component>('./**/*.vue', {import: 'default'})
`;
    fs.mkdirSync(GENERATED_SRC, {recursive: true});
    fs.writeFileSync(LOADER_FILE, content, 'utf-8');
    log('Generated .plugin-pages/_loader.ts');
}

function generateRegistry(plugins) {
  const navItems = [];
    const routes = [];

    for (const {slug, manifest} of plugins) {
        for (const item of manifest.navItems || []) {
            navItems.push({
                label: item.label,
                href: item.href,
                icon: item.icon || 'Puzzle',
                slug,
            });
    }

        for (const route of manifest.routes || []) {
            routes.push({
                path: route.path,
                slug,
                title: route.title || manifest.name || slug,
                component: route.component,
                migrated: isMigrated(slug, route.component),
            });
    }
  }

    const content = `// 由 scripts/scan-plugin-frontend.mjs 生成，请勿手改。

export interface PluginNavItem {
  label: string
  href: string
  icon: string
  slug: string
}

export interface PluginPageRoute {
  path: string
  slug: string
  title: string
  /** manifest 登记的原组件路径（当前多为 React 的 .tsx） */
  component: string
  /** 是否已有同名 Vue 实现（.vue）；仅 migrated 为 true 时宿主页能渲染 */
  migrated: boolean
}

export const pluginNavItems: PluginNavItem[] = ${JSON.stringify(navItems, null, 2)}

export const pluginPageRoutes: PluginPageRoute[] = ${JSON.stringify(routes, null, 2)}
`;

    fs.writeFileSync(REGISTRY_FILE, content, 'utf-8');
    log(`Generated .plugin-registry.ts (${navItems.length} nav items, ${routes.length} routes)`);
}

// ─── Main ────────────────────────────────────────────────────────────────────
export function scanPluginFrontend() {
  log('Scanning for plugin frontend sources...');
  const plugins = scanPlugins();

  if (plugins.length === 0) {
    log('No plugin frontends found. Cleaning up generated files.');
      fs.rmSync(GENERATED_SRC, {recursive: true, force: true});
      fs.rmSync(REGISTRY_FILE, {force: true});
      writeLoader();
    generateRegistry([]);
    return;
  }

    for (const {slug} of plugins) {
    copyPluginSource(slug);
  }
    writeLoader();
  generateRegistry(plugins);

    const migrated = generateMigratedCount(plugins);
    log(`Done. Processed ${plugins.length} plugin(s); Vue 页面已迁移 ${migrated} 个。`);
}

function generateMigratedCount(plugins) {
    let count = 0;
    for (const {slug, manifest} of plugins) {
        for (const route of manifest.routes || []) {
            if (isMigrated(slug, route.component)) count += 1;
        }
    }
    return count;
}

// Run directly (Windows-safe check)
const isMain = process.argv[1] && (
  process.argv[1].replace(/\\/g, '/').endsWith('scan-plugin-frontend.mjs')
);
if (isMain) {
  scanPluginFrontend();
}
