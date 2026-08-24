# FastBlog Capacitor 混合应用开发指南

将 Astro PWA 应用打包为 iOS/Android 原生应用，复用 100% 的 Web 代码。

## 快速开始

### 前置要求

- Node.js 16+
- FastBlog Astro 项目已完成 PWA 配置

### 初始化

```bash
cd mobile-app
npm install @capacitor/core @capacitor/cli
npx cap init FastBlog com.fastblog.app --web-dir=../frontend-astro/dist
npm install @capacitor/android @capacitor/ios  # iOS 需要 macOS
npx cap add android
npx cap add ios
```

### 构建 + 同步

```bash
cd frontend-astro && npm run build
cd ../mobile-app && npx cap sync
```

### 运行

```bash
npx cap open android   # Android Studio
npx cap run android    # 直接运行设备
npx cap open ios       # Xcode（需 macOS）
npx cap run ios        # 模拟器（需 macOS）
```

## 常用 Capacitor 插件

```bash
npm install @capacitor/push-notifications   # 推送通知
npm install @capacitor/camera               # 相机
npm install @capacitor/filesystem            # 文件系统
npm install @capacitor/geolocation           # 地理位置
npm install @capacitor/share                 # 分享
```

## 配置文件

`mobile-app/capacitor.config.ts`:

```typescript
import {CapacitorConfig} from '@capacitor/cli';

const config: CapacitorConfig = {
    appId: 'com.fastblog.app',
    appName: 'FastBlog',
    webDir: '../frontend-astro/dist',
    server: {cleartext: false},
    plugins: {
        SplashScreen: {launchShowDuration: 2000, backgroundColor: '#3b82f6'},
        StatusBar: {style: 'light', backgroundColor: '#3b82f6'},
    },
};
export default config;
```

## 打包发布

### Android

```bash
keytool -genkey -v -keystore fastblog-release-key.jks -keyalg RSA -keysize 2048 -validity 10000 -alias fastblog
# 在 android/app/build.gradle 配置签名后：
cd android
./gradlew bundleRelease   # AAB (Google Play)
./gradlew assembleRelease # APK
```

### iOS

在 Xcode 中配置签名证书后：Product → Archive → Distribute App。

## 调试

- Android: `chrome://inspect/#devices` 或 `adb logcat`
- iOS: Safari → 开发 → 设备名称
- 热重载: `capacitor.config.ts` 中设置 `server.url = 'http://localhost:4321'`

## 注意事项

- **纯 Web 内容**更新通过服务端即时生效，**原生功能**更新需重新提交审核
- 生产环境使用 HTTPS，不在代码中硬编码 API 密钥
- 上传文件限制：普通图片 10MB，封面图片 5MB

> 完整文档详见 [Capacitor 官方文档](https://capacitorjs.com/docs)
