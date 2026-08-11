# 创建时间：2026-08-11 09:52:00
"""B 站登录模块：cookie 检查、浏览器读取、扫码登录、浏览器引导。

登录流程按用户操作成本递增：已有 cookie → 浏览器 cookie → 扫码 → 打开登录页。
"""
import os
import time
import webbrowser

import qrcode
import requests

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
_HEADERS = {"User-Agent": _UA, "Referer": "https://www.bilibili.com/"}
NAV_URL = "https://api.bilibili.com/x/web-interface/nav"
GENERATE_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
POLL_URL = "https://passport.bilibili.com/x/passport-login/web/qrcode/poll"
LOGIN_PAGE_URL = "https://passport.bilibili.com/login"
COOKIE_FILE = os.path.join(os.path.expanduser("~"), ".bilidown", "cookies.txt")


def validate_cookie(session):
    """验证 session 携带的 cookie 是否为有效 B 站登录态。"""
    resp = session.get(NAV_URL, timeout=15)
    return resp.json().get("data", {}).get("isLogin") is True


def load_cookie_file(path=COOKIE_FILE):
    """读取 Netscape 格式 cookie 文件，验证有效则返回 session，否则返回 None。"""
    if not os.path.exists(path):
        return None
    s = requests.Session()
    s.headers.update(_HEADERS)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 7:
                continue
            domain, _, path_part, _, _, name, value = parts[:7]
            s.cookies.set(name, value, domain=domain, path=path_part)
    return s if validate_cookie(s) else None


def save_cookie_file(session, path=COOKIE_FILE):
    """把 session 的 cookie 序列化为 Netscape 格式保存，返回路径。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    lines = ["# Netscape HTTP Cookie File"]
    for c in session.cookies:
        secure = "TRUE" if getattr(c, "secure", False) else "FALSE"
        expires = int(c.expires) if getattr(c, "expires", None) else 0
        lines.append(f"{c.domain}\tTRUE\t{c.path}\t{secure}\t{expires}\t{c.name}\t{c.value}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return path


def login_scan():
    """扫码登录：生成二维码 → 终端显示 → 轮询确认，返回已登录 session。"""
    s = requests.Session()
    s.headers.update(_HEADERS)
    resp = s.get(GENERATE_URL, timeout=15)
    data = resp.json().get("data", {})
    qr_url, qrcode_key = data.get("url"), data.get("qrcode_key")
    if not qrcode_key:
        raise RuntimeError("获取登录二维码失败")
    qr = qrcode.QRCode(border=1)
    qr.add_data(qr_url)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    print("请使用 B 站 App 扫描上方二维码登录")
    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(2)
        resp = s.get(f"{POLL_URL}?qrcode_key={qrcode_key}&source=main-fe-header", timeout=15)
        code = resp.json().get("data", {}).get("code")
        if code == 0:
            if not validate_cookie(s):
                raise RuntimeError("扫码成功但 cookie 验证失败，请重试")
            return s
        if code == 86038:
            raise RuntimeError("二维码已失效，请重新运行 --login")
        if code == 86090:
            print("已扫码，请在手机上确认登录…")
        elif code == 86101:
            print("等待扫码…")
        else:
            print(f"扫码状态异常（code={code}），继续等待…")
    raise RuntimeError("扫码超时（180 秒），请重新运行 --login")


def login_browser(browsers=None):
    """从已登录的浏览器读取 B 站 cookie 并验证，返回 session。"""
    from yt_dlp.cookies import extract_cookies_from_browser
    for name in (browsers or ("chrome", "edge", "firefox")):
        try:
            jar = extract_cookies_from_browser(name)
        except Exception as e:
            print(f"[提示] 浏览器 {name} 读取失败：{e}")
            continue
        s = requests.Session()
        s.headers.update(_HEADERS)
        for c in jar:
            s.cookies.set(c.name, c.value, domain=c.domain, path=c.path)
        if validate_cookie(s):
            return s
        print(f"[提示] 浏览器 {name} 未登录 B 站")
    raise RuntimeError("未能从浏览器读取有效的 B 站登录态")


def login_web():
    """打开系统浏览器登录页（最后回退方式）。"""
    print("正在打开浏览器…")
    webbrowser.open(LOGIN_PAGE_URL)
    print(f"请在浏览器中登录 B 站，然后重新运行 bilidown --login（cookie 将保存到 {COOKIE_FILE}）")


def login(mode=None):
    """执行登录流程，返回 cookie 文件路径。

    mode: None=自动按序（file→browser→scan→web）；也可指定 file/browser/scan/web。
    """
    steps = {
        None: ["file", "browser", "scan", "web"],
        "file": ["file"],
        "browser": ["browser"],
        "scan": ["scan"],
        "web": ["web"],
    }.get(mode)
    if steps is None:
        raise ValueError(f"未知登录方式：{mode!r}（可选 file/browser/scan/web）")
    for step in steps:
        try:
            if step == "file":
                if load_cookie_file():
                    print("已有有效 cookie，无需重新登录")
                    return COOKIE_FILE
                print("未找到有效的已保存 cookie")
            elif step == "browser":
                s = login_browser()
                print(f"已从浏览器获取 B 站登录态，cookie 保存到 {COOKIE_FILE}")
                return save_cookie_file(s)
            elif step == "scan":
                s = login_scan()
                print(f"扫码登录成功，cookie 保存到 {COOKIE_FILE}")
                return save_cookie_file(s)
            elif step == "web":
                if input("扫码不可用，是否打开浏览器登录 B 站？(y/N) ").strip().lower() == "y":
                    login_web()
                return None
        except Exception as e:
            print(f"[提示] {e}")
    raise RuntimeError("所有可用方式均已尝试")


if __name__ == "__main__":
    login()
