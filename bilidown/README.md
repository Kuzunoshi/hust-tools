# bilidown — 视频/音频下载工具

从 B 站（bilibili.com）下载视频、音频，支持多 P 合集选择、弹幕与封面附件；架构预留多站支持，非 B 站链接自动降级为通用下载（yt-dlp 原生支持上千网站）。

## 调用方法

```bash
# 基本用法：下载视频（默认 1080P）
python bilidown.py <视频链接>

# 只下载音频（原生 m4a，无需 ffmpeg）
python bilidown.py <视频链接> --audio

# 转码为 mp3（需要 ffmpeg）
python bilidown.py <视频链接> --audio mp3

# 指定清晰度 + 输出目录
python bilidown.py <视频链接> --quality 720 -o D:\下载

# 多 P 合集：指定分 P 下载
python bilidown.py <合集链接> --p 1-3,5

# 附带下载弹幕与封面
python bilidown.py <视频链接> --danmaku --cover

# 大会员内容（1080P60/4K 等，需登录 cookie）
python bilidown.py <视频链接> --cookies cookies.txt
```

## 参数说明

| 参数 | 说明 |
|------|------|
| `URL` | 视频链接（B 站或其他 yt-dlp 支持网站） |
| `--audio [mp3\|m4a]` | 只下载音频；缺省取原生 m4a（无需 ffmpeg），指定 mp3 需 ffmpeg 转码 |
| `--quality N` | 视频清晰度 360/480/720/1080，默认 1080 |
| `--p SPEC` | 选择分 P（如 `1-3,5`，仅合集/多 P）；不指定时交互式选择 |
| `--danmaku` | 同时下载弹幕 xml（仅 B 站） |
| `--cover` | 同时下载封面 |
| `--cookies FILE` | cookie 文件（大会员内容） |
| `-o DIR` | 输出目录，默认 `downloads/` |
| `--format FMT` | 高级：透传 yt-dlp format 表达式 |

## 输出文件

- 单视频：`{标题} [{BV号}].mp4`（或 `.m4a`）
- 多 P：`{标题} [{BV号}]_P{编号}.mp4`
- 附件：`{同名}.cover.jpg` / `{同名}.danmaku.xml`

## 依赖安装

```bash
pip install -r requirements.txt   # yt-dlp + requests
```

音频/视频分离流合并需要系统级 **ffmpeg**（纯音频 m4a 提取不需要）：

- **Windows**: `winget install ffmpeg` 或下载加入 PATH
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

## 项目结构

```
bilidown/
├── bilidown.py        # CLI 入口（参数解析 + 多 P 交互选择 + 流程编排）
├── downloader.py      # 通用下载引擎（封装 yt-dlp，站点无关）
├── bilibili_extra.py  # B 站增强（弹幕/封面/cid 获取，仅 B 站链接启用）
├── requirements.txt   # 依赖
├── test_downloader.py # 引擎单元测试
├── test_bilibili_extra.py  # 增强模块单元测试
├── test_bilidown.py   # CLI 单元测试
└── README.md
```

## 常见示例

```bash
# 下载 1080P 视频到默认 downloads/ 目录
python bilidown.py "https://www.bilibili.com/video/BV1xx411c7mD"

# 只提取音频（m4a）
python bilidown.py "https://www.bilibili.com/video/BV1xx411c7mD" --audio

# 下载合集第 1-3 和 5 集
python bilidown.py "https://www.bilibili.com/video/BV1xx411c7mD" --p 1-3,5

# 视频 + 弹幕 + 封面一套带走
python bilidown.py "https://www.bilibili.com/video/BV1xx411c7mD" --danmaku --cover

# 非 B 站网站（如 YouTube）直接下载
python bilidown.py "https://www.youtube.com/watch?v=xxxx"
```

## 规划

- **v1.0（当前）**：基础下载功能（单视频/多 P/音频/弹幕/封面）
- **v1.1（规划中）**：会员高清支持（1080P60/4K），含 cookie 获取引导与清晰度选项扩展。`--cookies` 已在 v1.0 预留透传，升级无需改动核心引擎。
