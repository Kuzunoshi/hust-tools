# 创建时间：2026-08-11 09:38:48
"""B 站增强模块：弹幕、封面下载；仅 B 站链接启用，站点相关代码集中在此。"""
import re

import requests

_BILIBILI_MARKERS = ("bilibili.com", "b23.tv")
_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def is_bilibili_url(url):
    """判断链接是否为 B 站（含 b23.tv 短链）。"""
    return any(m in url for m in _BILIBILI_MARKERS)


def extract_bvid(url):
    """提取 BV/av 号；无则返回 None。"""
    m = re.search(r"BV[0-9A-Za-z]{10}", url)
    if m:
        return m.group(0)
    m = re.search(r"av(\d+)", url)
    if m:
        return "av" + m.group(1)
    return None


def _save(url, out_path):
    """带 UA 下载 URL 内容到 out_path（弹幕 xml 与封面共用）。"""
    resp = requests.get(url, headers={"User-Agent": _UA}, timeout=15)
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(resp.content)
    return out_path


def fetch_danmaku(cid, out_path):
    """下载 B 站弹幕 xml（comment.bilibili.com/{cid}.xml）。"""
    return _save(f"https://comment.bilibili.com/{cid}.xml", out_path)


def fetch_cover(image_url, out_path):
    """下载封面图到 out_path。"""
    return _save(image_url, out_path)
