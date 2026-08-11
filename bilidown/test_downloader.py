# 创建时间：2026-08-11 09:38:48
"""download 引擎单元测试：mock yt-dlp 验证选项构建与调用。"""
import unittest
from unittest import mock

import downloader


class TestBuildOpts(unittest.TestCase):
    def test_默认视频选项_含清晰度与输出模板(self):
        opts = downloader.build_opts(out_dir="dl", quality=720)
        self.assertIn("bestvideo[height<=720]+bestaudio", opts["format"])
        self.assertIn("dl", opts["outtmpl"])
        self.assertFalse(opts["noplaylist"])

    def test_音频m4a_取原生格式(self):
        opts = downloader.build_opts(audio_codec="m4a")
        self.assertIn("bestaudio[ext=m4a]", opts["format"])
        self.assertNotIn("postprocessors", opts)

    def test_音频mp3_走FFmpeg转码(self):
        opts = downloader.build_opts(audio_codec="mp3")
        self.assertEqual(opts["postprocessors"][0]["preferredcodec"], "mp3")

    def test_多P_输出模板带P编号(self):
        opts = downloader.build_opts(multi=True)
        self.assertIn("_P%(playlist_index)02d", opts["outtmpl"])
        self.assertFalse(opts["noplaylist"])

    def test_单视频_输出模板无P编号(self):
        opts = downloader.build_opts(multi=False)
        self.assertNotIn("_P", opts["outtmpl"])

    def test_cookies与format透传(self):
        opts = downloader.build_opts(cookies="c.txt", format_expr="best")
        self.assertEqual(opts["cookiefile"], "c.txt")
        self.assertEqual(opts["format"], "best")


class TestExtractAndDownload(unittest.TestCase):
    def test_extract_info_调用ytdlp且不下载(self):
        with mock.patch("downloader.YoutubeDL") as Ydl:
            Ydl.return_value.__enter__.return_value.extract_info.return_value = {"id": "x"}
            info = downloader.extract_info("https://bilibili.com/video/BV1xx", {"quiet": True})
            self.assertEqual(info["id"], "x")
            Ydl.return_value.__enter__.return_value.extract_info.assert_called_once()
            # download=False 参数必须在调用中
            call_kwargs = Ydl.return_value.__enter__.return_value.extract_info.call_args
            self.assertTrue(call_kwargs.kwargs["download"] is False)

    def test_download_成功返回True(self):
        with mock.patch("downloader.YoutubeDL") as Ydl:
            ok = downloader.download("https://x", {})
            self.assertTrue(ok)
            Ydl.return_value.__enter__.return_value.download.assert_called_once_with(["https://x"])

    def test_prepare_paths_按outtmpl计算(self):
        info = {"title": "t", "id": "BV1", "ext": "mp4"}
        with mock.patch("downloader.YoutubeDL") as Ydl:
            Ydl.return_value.__enter__.return_value.prepare_filename.return_value = "dl/t [BV1].mp4"
            paths = downloader.prepare_paths(info, {"outtmpl": "dl/%(title)s [%(id)s].%(ext)s"})
            self.assertEqual(paths, ["dl/t [BV1].mp4"])


if __name__ == "__main__":
    unittest.main()
