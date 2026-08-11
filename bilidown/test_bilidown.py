# 创建时间：2026-08-11 09:38:48
"""CLI 入口单元测试：mock 下载引擎与增强模块验证流程。"""
import unittest
from unittest import mock

import bilidown


class TestPageSpec(unittest.TestCase):
    def test_空串返回None(self):
        self.assertIsNone(bilidown.parse_page_spec("", 10))

    def test_单页与范围(self):
        self.assertEqual(bilidown.parse_page_spec("3", 10), "3")
        self.assertEqual(bilidown.parse_page_spec("1-3", 10), "1,2,3")

    def test_乱序去重(self):
        self.assertEqual(bilidown.parse_page_spec("5,1-2,5", 10), "1,2,5")

    def test_非法字符报错(self):
        with self.assertRaises(ValueError):
            bilidown.parse_page_spec("1;2", 10)

    def test_超范围报错(self):
        with self.assertRaises(ValueError):
            bilidown.parse_page_spec("11", 10)


class TestSelectedIndexes(unittest.TestCase):
    def test_全部(self):
        self.assertEqual(bilidown.selected_indexes(None, 3), {0, 1, 2})

    def test_子集转0基(self):
        self.assertEqual(bilidown.selected_indexes("1-3,5", 6), {0, 1, 2, 4})


class TestMain(unittest.TestCase):
    def test_下载流程_单视频无附件(self):
        with mock.patch("bilidown.extract_info", return_value={"id": "BV1", "title": "t"}), \
             mock.patch("bilidown.download", return_value=True) as dl, \
             mock.patch("bilidown.fetch_extras") as fe:
            code = bilidown.main(["https://www.bilibili.com/video/BV1xx"])
            self.assertEqual(code, 0)
            dl.assert_called_once()
            fe.assert_not_called()

    def test_下载流程_多P指定范围(self):
        info = {"id": "BV1", "title": "t", "entries": [
            {"id": "BV1", "title": "p1", "cid": 1},
            {"id": "BV1", "title": "p2", "cid": 2},
            {"id": "BV1", "title": "p3", "cid": 3},
        ]}
        with mock.patch("bilidown.extract_info", return_value=info), \
             mock.patch("bilidown.download", return_value=True) as dl, \
             mock.patch("bilidown.fetch_extras") as fe, \
             mock.patch("bilidown.choose_pages", return_value="1-2"):
            code = bilidown.main(["https://www.bilibili.com/video/BV1xx", "--danmaku"])
            self.assertEqual(code, 0)
            # playlist_items 透传给下载
            opts = dl.call_args.args[1]
            self.assertEqual(opts["playlist_items"], "1,2")
            fe.assert_called_once()

    def test_下载失败返回非零(self):
        with mock.patch("bilidown.extract_info", return_value={"id": "BV1"}), \
             mock.patch("bilidown.download", return_value=False):
            code = bilidown.main(["https://www.bilibili.com/video/BV1xx"])
            self.assertEqual(code, 1)

    def test_交互选择_多P未指定p时调用choose_pages(self):
        info = {"id": "BV1", "title": "t", "entries": [{"id": "BV1"}, {"id": "BV1"}]}
        with mock.patch("bilidown.extract_info", return_value=info), \
             mock.patch("bilidown.download", return_value=True), \
             mock.patch("bilidown.choose_pages", return_value="2") as cp:
            bilidown.main(["https://www.bilibili.com/video/BV1xx"])
            cp.assert_called_once()


class TestFetchExtras(unittest.TestCase):
    def test_封面与弹幕命名(self):
        info = {"id": "BV1", "title": "t", "ext": "mp4",
                "thumbnail": "https://i0.hdslb.com/c.jpg", "cid": 99}
        opts = {"outtmpl": "dl/%(title)s [%(id)s].%(ext)s"}
        with mock.patch("bilidown.prepare_paths", return_value=["dl/t [BV1].mp4"]), \
             mock.patch("bilidown.fetch_cover") as fc, \
             mock.patch("bilidown.fetch_danmaku") as fd, \
             mock.patch("bilidown.fetch_cid") as fcid:
            n = bilidown.fetch_extras(info, opts, None, True, True, True,
                                      "https://www.bilibili.com/video/BV1xx")
            self.assertEqual(n, 2)
            fc.assert_called_once_with("https://i0.hdslb.com/c.jpg", "dl/t [BV1].cover.jpg")
            fd.assert_called_once_with(99, "dl/t [BV1].danmaku.xml")
            fcid.assert_not_called()

    def test_无cid时回退viewAPI(self):
        info = {"id": "BV1xx411c7mD", "title": "t", "ext": "mp4",
                "thumbnail": "https://i0.hdslb.com/c.jpg"}
        opts = {"outtmpl": "dl/%(title)s [%(id)s].%(ext)s"}
        with mock.patch("bilidown.prepare_paths", return_value=["dl/t [BV1xx411c7mD].mp4"]), \
             mock.patch("bilidown.fetch_cover"), \
             mock.patch("bilidown.fetch_danmaku") as fd, \
             mock.patch("bilidown.fetch_cid", return_value=62131) as fcid:
            n = bilidown.fetch_extras(info, opts, None, True, True, True,
                                      "https://www.bilibili.com/video/BV1xx411c7mD")
            self.assertEqual(n, 2)
            fcid.assert_called_once_with("BV1xx411c7mD", 0)
            fd.assert_called_once_with(62131, "dl/t [BV1xx411c7mD].danmaku.xml")

    def test_非b站跳过弹幕(self):
        info = {"id": "x", "title": "t", "ext": "mp4",
                "thumbnail": "https://x/c.jpg"}
        opts = {"outtmpl": "dl/%(title)s.%(ext)s"}
        with mock.patch("bilidown.prepare_paths", return_value=["dl/t.mp4"]), \
             mock.patch("bilidown.fetch_cover") as fc, \
             mock.patch("bilidown.fetch_danmaku") as fd:
            n = bilidown.fetch_extras(info, opts, None, True, True, False,
                                      "https://www.youtube.com/watch?v=x")
            self.assertEqual(n, 1)
            fc.assert_called_once()
            fd.assert_not_called()


if __name__ == "__main__":
    unittest.main()
