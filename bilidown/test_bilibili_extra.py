# 创建时间：2026-08-11 09:38:48
"""B 站增强模块单元测试：mock requests 验证弹幕/封面下载。"""
import os
import tempfile
import unittest
from unittest import mock

import bilibili_extra


class TestLinkDetection(unittest.TestCase):
    def test_b站链接识别(self):
        for url in ("https://www.bilibili.com/video/BV1xx411c7mD",
                    "https://b23.tv/abc123"):
            self.assertTrue(bilibili_extra.is_bilibili_url(url), url)

    def test_非b站链接不识别(self):
        self.assertFalse(bilibili_extra.is_bilibili_url("https://www.youtube.com/watch?v=x"))

    def test_提取BV号(self):
        self.assertEqual(bilibili_extra.extract_bvid("https://www.bilibili.com/video/BV1xx411c7mD"),
                         "BV1xx411c7mD")

    def test_提取av号(self):
        self.assertEqual(bilibili_extra.extract_bvid("https://www.bilibili.com/video/av170001"), "av170001")

    def test_无视频号返回None(self):
        self.assertIsNone(bilibili_extra.extract_bvid("https://www.bilibili.com/"))


class TestFetch(unittest.TestCase):
    def test_弹幕下载(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "d.xml")
            with mock.patch("bilibili_extra.requests.get") as get:
                get.return_value.raise_for_status.return_value = None
                get.return_value.content = b"<i>xml</i>"
                result = bilibili_extra.fetch_danmaku(12345, out)
            self.assertEqual(result, out)
            get.assert_called_once()
            self.assertIn("comment.bilibili.com/12345.xml", get.call_args.args[0])
            self.assertIn("User-Agent", get.call_args.kwargs["headers"])
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"<i>xml</i>")

    def test_封面下载(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = os.path.join(tmp, "c.jpg")
            with mock.patch("bilibili_extra.requests.get") as get:
                get.return_value.raise_for_status.return_value = None
                get.return_value.content = b"\xff\xd8jpg"
                result = bilibili_extra.fetch_cover("https://i0.hdslb.com/cover.jpg", out)
            self.assertEqual(result, out)
            with open(out, "rb") as f:
                self.assertEqual(f.read(), b"\xff\xd8jpg")

    def test_获取cid(self):
        with mock.patch("bilibili_extra.requests.get") as get:
            get.return_value.raise_for_status.return_value = None
            get.return_value.json.return_value = {"code": 0, "data": {"pages": [
                {"cid": 111}, {"cid": 222},
            ]}}
            self.assertEqual(bilibili_extra.fetch_cid("BV1xx411c7mD"), 111)
            self.assertEqual(bilibili_extra.fetch_cid("BV1xx411c7mD", 1), 222)
            self.assertIn("bvid=BV1xx411c7mD", get.call_args.args[0])

    def test_获取cid_支持av号(self):
        with mock.patch("bilibili_extra.requests.get") as get:
            get.return_value.raise_for_status.return_value = None
            get.return_value.json.return_value = {"code": 0, "data": {"pages": [{"cid": 7}]}}
            self.assertEqual(bilibili_extra.fetch_cid("av170001"), 7)
            self.assertIn("aid=170001", get.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
