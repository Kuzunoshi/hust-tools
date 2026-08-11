# bilidown 设计文档

> 创建时间：2026-08-11
> 状态：已获用户批准（2026-08-11）

## 1. 背景与目标

在 `hust-tools` 工具集下新建子项目 `bilidown/`，用于从视频网站下载视频或音频文件。

- **主目标网站**：B 站（bilibili.com）
- **扩展性**：架构预留多站支持，其他网站可零成本接入
- **交互形式**：CLI 命令行

## 2. 范围

### v1.0（本次实现，基础功能）

- 下载单个 B 站视频（BV/av 链接，清晰度 360P~1080P）
- 下载合集/多 P 视频（`--p` 参数指定，或交互式选择）
- 纯音频提取（`--audio`，mp3/m4a）
- 封面下载（`--cover`，可选）
- 弹幕下载（`--danmaku`，可选）
- 非 B 站链接降级为通用下载（yt-dlp 原生能力）
- `--cookies` 透传（基础能力保留，供已有 cookie 的用户使用）

### v1.1（会员高清与登录引导）

**登录流程 `--login`（按用户操作成本递增，默认全自动按序尝试）：**

1. 检查已有 cookie 文件（`~/.bilidown/cookies.txt`）→ 验证有效即结束（0 操作）
2. 从浏览器读取已登录 cookie（yt-dlp cookiesfrombrowser）→ 验证有效后保存（0 操作）
3. 扫码登录：终端显示二维码，B 站 App 扫码（1 次扫码）
4. 打开系统浏览器登录页引导登录（最后回退）

细节约定：
- `--login [scan|browser|file]` 可指定方式，缺省按上述顺序自动尝试
- cookie 验证：B 站 nav API（`/x/web-interface/nav`，`isLogin` 为真）
- cookie 存储：`~/.bilidown/cookies.txt`（Netscape 格式，与 yt-dlp `--cookies` 兼容）
- 自动携带：下载时自动使用已保存的有效 cookie，无需手动 `--cookies`
- 清晰度扩展：`--quality` 支持 360/480/720/1080/1080p60/2160（4K/60fps 需登录）
- 错误提示：会员内容无 cookie 时提示运行 `--login`

实现位置：新增 `bilibili_login.py` 登录模块（独立于下载引擎），CLI 增加 `--login` 与 `--quality` 档位扩展。

## 3. 架构与模块

```
bilidown/
├── bilidown.py        # CLI 入口（参数解析 + 多 P 交互选择 + 调用流程）
├── downloader.py      # 通用下载引擎（封装 yt-dlp，站点无关）
├── bilibili_extra.py  # B 站增强模块（弹幕/封面获取，仅 B 站链接启用）
├── requirements.txt   # yt-dlp
└── README.md          # 使用文档
```

### 模块职责

| 模块 | 职责 | 依赖 |
|------|------|------|
| `downloader.py` | 接收 URL + 选项字典，调用 `yt_dlp.YoutubeDL` 下载；负责进度回调、文件命名、错误翻译 | yt-dlp（唯一硬依赖） |
| `bilibili_extra.py` | 解析 B 站链接中的 BV/av/ep 号；调用 B 站公开 API 获取弹幕（xml）和封面 | requests |
| `bilidown.py` | CLI：参数解析、链接类型识别、多 P 交互选择、组织下载流程 | 上述两个模块 |

### 扩展性设计

- `downloader.py` 完全站点无关，任何 yt-dlp 支持的网站都能下载
- B 站专属功能独立在 `bilibili_extra.py`，通过链接域名判断是否启用
- 新增网站支持时无需改动核心引擎，新增对应增强模块即可

## 4. CLI 接口

```
python bilidown.py <URL> [选项]
```

| 参数 | 说明 |
| `URL` | 视频链接（B 站或其他 yt-dlp 支持网站） |
| `--audio [mp3|m4a]` | 只下载音频；缺省取原生 m4a（无需 ffmpeg），指定 mp3 需 ffmpeg 转码 |
| `--quality N` | 清晰度 360/480/720/1080，默认 1080 |
| `--p 1-3,5` | 选择分 P（支持连字符与逗号） |
| `--danmaku` | 同时下载弹幕 xml（仅 B 站） |
| `--cover` | 同时下载封面（仅 B 站） |
| `--cookies FILE` | 传入 cookie 文件（大会员内容，v1.0 透传保留） |
| `-o DIR` | 输出目录，默认 `./downloads` |
| `--format FMT` | 高级：透传 yt-dlp format 表达式 |

## 5. 行为细节

1. **链接识别**：`bilibili.com` 链接启用 B 站增强；其他网站走纯 yt-dlp 下载
2. **多 P 交互**：合集链接且未指定 `--p` 时，列出各 P 编号+标题+时长，输入 `1-3,5` 选择，回车默认全部
3. **命名规则**：`{标题} [{BV号}].{ext}`（单视频）；合集/多 P 追加 `_P{n}`（如 `标题 [BVxxx]_P2.mp4`）；重名自动追加序号
4. **进度显示**：透传 yt-dlp 进度条
5. **附件命名**：`{同名}.cover.jpg` / `{同名}.danmaku.xml`

## 6. 错误处理

- URL 无效 / 网络失败 → 中文错误提示 + 非零退出码
- 大会员专属内容（无 cookie 时）→ 提示 `--cookies` 用法，并说明 v1.1 将提供完整会员高清支持
- yt-dlp / ffmpeg 缺失 → 给出安装指引

## 7. 测试策略

- **单元测试**：mock yt-dlp，验证选项透传、`--p` 解析、命名规则、链接识别
- **冒烟测试**：下载公开 B 站视频验证端到端（含音频提取路径）

## 8. 依赖

- `yt-dlp`（下载引擎，唯一硬依赖）
- `requests`（B 站增强模块，获取弹幕/封面）
- ffmpeg（系统级，可选：1080P+ 音视频合并需要；纯音频提取不需要）
