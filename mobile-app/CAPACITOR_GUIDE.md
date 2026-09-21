# FastBlog 移动端（Capacitor）

把 Nuxt 前端打包为 Android / iOS 原生外壳，Web 代码 100% 复用。当前外壳配置为 **Capacitor 5**，`android/` 与 `ios/`
平台目录都已生成。

## 目录

```
mobile-app/
├── capacitor.config.json   Capacitor 配置（appId / webDir / 原生插件 / 平台选项）
├── package.json            依赖与构建脚本（@capacitor/* 5.x）
├── init-capacitor.ps1      首次初始化：npm install + 校验配置
├── build-and-deploy.ps1    构建流水线：frontend/web 静态导出 → cap sync → 平台构建
├── test-config.ps1         配置自检（webDir / build:web / 产物文件数）
├── android/                Android 工程（Gradle）
└── ios/                    iOS 工程（Xcode）
```

## 前置要求

- Node ≥ 22 与 `mobile-app`、`frontend/web` 两处的 `npm install`
- Android：Android Studio + JDK；iOS：macOS + Xcode
- 前端必须能静态导出（`frontend/web` 的 `npm run generate`），产物落在 `frontend/web/.output/public` —— 这正是
  `capacitor.config.json` 的 `webDir`

## 构建与运行

```bash
# 在 mobile-app 目录下
npm run build:web      # = cd ../frontend/web && npm run generate
npm run sync           # npx cap sync（把 webDir 产物与插件同步进原生工程）
npm run android        # 打开 Android Studio
npm run run:android    # 直接跑到设备/模拟器
npm run ios            # 打开 Xcode（需 macOS）
npm run run:ios        # 模拟器（需 macOS）

# 直接出包
npm run build:android  # generate + cap sync + gradlew assembleRelease
npm run build:ios      # generate + cap sync + xcodebuild archive
```

PowerShell 用户也可以走脚本：`./init-capacitor.ps1`（初始化）、`./test-config.ps1`（自检）、`./build-and-deploy.ps1`（构建）。

## 配置说明（`capacitor.config.json`）

| 项                                                                            | 值                                | 说明                          |
|------------------------------------------------------------------------------|----------------------------------|-----------------------------|
| `appId` / `appName`                                                          | `com.fastblog.app` / `FastBlog`  | 原生应用标识                      |
| `webDir`                                                                     | `../frontend/web/.output/public` | Nuxt `generate` 的静态产物目录     |
| `server.androidScheme` / `iosScheme`                                         | `https`                          | WebView 使用 https scheme     |
| `plugins.SplashScreen`                                                       | 2s、`#3b82f6`、全屏                  | 启动画面                        |
| `plugins.StatusBar`                                                          | light、`#3b82f6`                  | 状态栏                         |
| `android.allowMixedContent` / `captureInput` / `webContentsDebuggingEnabled` | `false` / `true` / `false`       | 禁混合内容、允许输入捕获、默认关 WebView 调试 |
| `ios.contentInset` / `allowsLinkPreview`                                     | `automatic` / `false`            | 安全区内边距、禁链接预览                |

已安装的原生依赖（`package.json`）：`@capacitor/core`、`@capacitor/android`、`@capacitor/ios`、
`@capacitor/push-notifications`（+ `@capacitor/cli` 开发依赖）。

## 与后端联调

外壳里的页面与浏览器端一致：请求同源 `/api`，因此需要把 `webDir` 产物部署到与后端同域的站点，或在 `capacitor.config.json` 的
`server` 段指向开发/测试服务器地址后重新 `cap sync`。后端侧的跨域白名单当前包含 `http://localhost`（Android 模拟器），见
`src/app.py::register_middleware`。

## 发布注意事项

- **纯 Web 内容**改动只需重新 `generate` + `cap sync` + 平台构建；**原生能力**（新增插件、权限、签名）改动需要重新提交审核。
- 生产必须 HTTPS，不要在代码里硬编码密钥。
- 后端上传限制见 `UPLOAD_LIMIT`（默认 60MB）。

## 已知偏差

- `capacitor.config.json` 里配置了 `SplashScreen` 与 `StatusBar` 插件，但 `package.json` **没有安装**
  `@capacitor/splash-screen` 与 `@capacitor/status-bar`，这两段配置当前不生效。
- `test-config.ps1` 的输出文案仍在说"Astro 前端"（实际工程是 Nuxt），校验逻辑本身有效。

> Capacitor 官方文档：<https://capacitorjs.com/docs>
