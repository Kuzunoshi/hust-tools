# 创建时间：2026-08-11（精确到秒的执行时时间）
"""B 站登录模块单元测试：mock requests 验证 cookie 检查/保存/扫码流程。"""
import os
import tempfile
import unittest
from unittest import mock

import bilibili_login


def make_session_cookie(name="SESSDATA", value="abc"):
    """构造带单个 cookie 的 mock session。"""
    s = mock.Mock()
    c = mock.Mock()
    c.name, c.value, c.domain, c.path, c.secure, c.expires = \
        name, value, ".bilibili.com", "/", False, 1750000000
    s.cookies = [c]
    return s


class TestValidate(unittest.TestCase):
    def test_已登录返回True(self):
        with mock.patch("bilibili_login.requests.Session") as S:
            S.return_value.get.return_value.json.return_value = {"code": 0, "data": {"isLogin": True}}
            self.assertTrue(bilibili_login.validate_cookie(S.return_value))

    def test_未登录返回False(self):
        with mock.patch("bilibili_login.requests.Session") as S:
            S.return_value.get.return_value.json.return_value = {"code": -101, "data": {"isLogin": False}}
            self.assertFalse(bilibili_login.validate_cookie(S.return_value))


class TestCookieFile(unittest.TestCase):
    def test_保存Netscape格式(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cookies.txt")
            bilibili_login.save_cookie_file(make_session_cookie(), path)
            with open(path, encoding="utf-8") as f:
                content = f.read()
            self.assertIn(".bilibili.com", content)
            self.assertIn("SESSDATA\tabc", content)
            self.assertTrue(content.startswith("# Netscape"))

    def test_加载有效cookie文件(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cookies.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write("# Netscape HTTP Cookie File\n"
                        ".bilibili.com\tTRUE\t/\tFALSE\t1750000000\tSESSDATA\tabc\n")
            with mock.patch("bilibili_login.validate_cookie", return_value=True):
                s = bilibili_login.load_cookie_file(path)
            self.assertIsNotNone(s)
            self.assertEqual(s.cookies.get("SESSDATA"), "abc")

    def test_无效cookie文件返回None(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "cookies.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(".bilibili.com\tTRUE\t/\tFALSE\t1750000000\tSESSDATA\tabc\n")
            with mock.patch("bilibili_login.validate_cookie", return_value=False):
                self.assertIsNone(bilibili_login.load_cookie_file(path))

    def test_文件不存在返回None(self):
        self.assertIsNone(bilibili_login.load_cookie_file("/nonexistent/c.txt"))


class TestScan(unittest.TestCase):
    def test_扫码轮询成功(self):
        with mock.patch("bilibili_login.requests.Session") as S, \
             mock.patch("bilibili_login.qrcode.QRCode") as QR, \
             mock.patch("bilibili_login.time.sleep") as sleep, \
             mock.patch("bilibili_login.validate_cookie", return_value=True):
            session = S.return_value
            # generate 返回 qrcode_key
            session.get.return_value.json.side_effect = [
                {"code": 0, "data": {"url": "https://passport.bilibili.com/x/passport-login/web/login?code=1",
                                     "qrcode_key": "K1"}},
                # 第一次轮询：未扫码
                {"code": 0, "data": {"code": 86101}},
                # 第二次轮询：已扫码未确认
                {"code": 0, "data": {"code": 86090}},
                # 第三次轮询：成功
                {"code": 0, "data": {"code": 0}},
            ]
            result = bilibili_login.login_scan()
            self.assertIs(result, session)
            QR.return_value.get_matrix.return_value = [[True, True], [False, False]]
            self.assertEqual(bilibili_login._render_qr(QR.return_value), "##\n  ")

    def test_二维码失效抛错(self):
        with mock.patch("bilibili_login.requests.Session") as S, \
             mock.patch("bilibili_login.qrcode.QRCode"), \
             mock.patch("bilibili_login.time.sleep"):
            S.return_value.get.return_value.json.side_effect = [
                {"code": 0, "data": {"url": "u", "qrcode_key": "K1"}},
                {"code": 0, "data": {"code": 86038}},
            ]
            with self.assertRaises(RuntimeError):
                bilibili_login.login_scan()

    def test_轮询超时抛错(self):
        times = iter(range(200, 400, 2))  # 每次轮询递增 2 秒，至 380 退出

        def _json():
            yield {"code": 0, "data": {"url": "u", "qrcode_key": "K1"}}
            while True:
                yield {"code": 0, "data": {"code": 86101}}
        gen = _json()
        with mock.patch("bilibili_login.requests.Session") as S, \
             mock.patch("bilibili_login.qrcode.QRCode"), \
             mock.patch("bilibili_login.time.sleep"), \
             mock.patch("bilibili_login.time.time", side_effect=lambda: next(times)):
            S.return_value.get.return_value.json.side_effect = lambda: next(gen)
            with self.assertRaises(RuntimeError):
                bilibili_login.login_scan()
class TestLoginFlow(unittest.TestCase):
    def test_已有cookie优先(self):
        with mock.patch("bilibili_login.load_cookie_file", return_value=object()), \
             mock.patch("bilibili_login.login_browser") as lb, \
             mock.patch("bilibili_login.login_scan") as ls:
            result = bilibili_login.login(None)
            self.assertEqual(result, bilibili_login.COOKIE_FILE)
            lb.assert_not_called()
            ls.assert_not_called()

    def test_无cookie时尝试浏览器与扫码(self):
        with mock.patch("bilibili_login.load_cookie_file", return_value=None), \
             mock.patch("bilibili_login.login_browser", return_value=object()) as lb:
            with mock.patch("bilibili_login.save_cookie_file", return_value=bilibili_login.COOKIE_FILE):
                result = bilibili_login.login(None)
            self.assertEqual(result, bilibili_login.COOKIE_FILE)
            lb.assert_called_once()

    def test_指定scan只扫码(self):
        with mock.patch("bilibili_login.load_cookie_file") as lf, \
             mock.patch("bilibili_login.login_browser") as lb, \
             mock.patch("bilibili_login.login_scan", return_value=object()) as ls:
            with mock.patch("bilibili_login.save_cookie_file", return_value=bilibili_login.COOKIE_FILE):
                result = bilibili_login.login("scan")
            self.assertEqual(result, bilibili_login.COOKIE_FILE)
            lf.assert_not_called()
            lb.assert_not_called()
            ls.assert_called_once()


if __name__ == "__main__":
    unittest.main()
