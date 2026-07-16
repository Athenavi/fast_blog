# FastBlog Default Theme

FastBlog 默认主题 - 简洁、现代、响应式设计。

**适用版本**: FastBlog V0.3.0+

## 特性

- 响应式设计 · 深色模式 · 可配置侧边栏
- 自定义颜色方案 · 灵活排版 · 评论集成
- 社交分享 · 相关文章 · 目录导航

## 文件结构

```
├── metadata.json        # 主题元数据
├── theme.json           # 运行时配置（颜色、布局、排版）
├── theme.config.js      # 前端构建配置
├── styles.css           # 自定义样式
├── screenshot.svg       # 预览截图
└── templates/           # Astro 组件模板
```

## 自定义

复制本目录为新目录，修改 `metadata.json` 和 `theme.config.js` 中的主题信息与配色，在后台激活即可。

## 许可证

MIT License
