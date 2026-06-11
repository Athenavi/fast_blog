/**
 * AudioPlayer — 全屏音频播放器
 *
 * 模块结构:
 *   AudioPlayer/            ← (this file re-exports AudioLayer)
 *     AudioLayer.tsx        持久音频层（持有 <audio>、播放状态、ESC 切换最小化）
 *     PlayerView.tsx        全屏播放器视图（组装 VinylRecord + LyricsPanel + ControlsBar）
 *     MiniPlayer.tsx        MiniPlayer（最小化卡片）+ MiniPlayerWrapper
 *     ControlsBar.tsx       底部控制栏（进度条 + 播放控制 + 音量/循环/收藏）
 *     LyricsPanel.tsx       歌词面板（逐字卡拉 OK 高亮）
 *     VinylRecord.tsx       黑胶唱片 + 唱臂可视化
 *     helpers.ts            工具函数 + 类型
 */

export {default as AudioLayer} from './AudioPlayer/AudioLayer';
export {default} from './AudioPlayer/AudioLayer';
