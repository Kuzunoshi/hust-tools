# 创建时间：2026-08-11 09:38:48
"""通用下载引擎：封装 yt-dlp，站点无关，任何 yt-dlp 支持的网站均可下载。"""
import os

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError


def _format_for_quality(quality):
    """按清晰度档位生成 yt-dlp format 表达式。"""
    if quality == "1080p60":
        return "bestvideo[height<=1080][fps>=60]+bestaudio/best[height<=1080][fps>=60]/best"
    h = int(quality)
    return f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"


def build_opts(out_dir="downloads", quality=1080, audio_codec=None,
               cookies=None, format_expr=None, playlist_items=None, multi=False):
    """构造 yt-dlp 选项字典。

    audio_codec: None=视频；'m4a'=原生音频（无需 ffmpeg）；'mp3'=ffmpeg 转码。
    quality: 360/480/720/1080/1080p60/2160（1080p60 与 2160 需登录）。
    """
    if multi:
        outtmpl = os.path.join(out_dir, "%(title)s [%(id)s]_P%(playlist_index)02d.%(ext)s")
    else:
        outtmpl = os.path.join(out_dir, "%(title)s [%(id)s].%(ext)s")

    opts = {
        "outtmpl": outtmpl,
        "noplaylist": False,  # 单视频也保持 False，便于 extract_info 检测多 P
        "quiet": False,
    }
    if audio_codec == "m4a":
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
    elif audio_codec == "mp3":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
    elif format_expr:
        opts["format"] = format_expr
    else:
        opts["format"] = _format_for_quality(quality)
    if cookies:
        opts["cookiefile"] = cookies
    if playlist_items:
        opts["playlist_items"] = playlist_items
    return opts


def extract_info(url, opts):
    """提取视频信息（不下载），返回 yt-dlp info dict。"""
    with YoutubeDL({**opts, "quiet": True}) as ydl:
        return ydl.extract_info(url, download=False)


def download(url, opts):
    """执行下载；成功返回 True，失败打印中文错误并返回 False。"""
    with YoutubeDL(opts) as ydl:
        try:
            ydl.download([url])
            return True
        except DownloadError as e:
            print(f"[错误] 下载失败：{e}")
            return False


def prepare_paths(info, opts):
    """按 outtmpl 计算输出文件路径列表（单视频返回 1 个元素）。"""
    with YoutubeDL({**opts, "quiet": True}) as ydl:
        entries = info.get("entries") or [info]
        return [ydl.prepare_filename(e) for e in entries]
