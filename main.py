import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from yt_dlp import YoutubeDL
from yt_dlp.version import __version__ as YTDLP_VERSION

app = FastAPI()

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
HEADERS = {"User-Agent": UA}
VIDEO_RE = re.compile(
    r'https?://[^\s"\'<>\\]+?\.(?:m3u8|mp4)(?:\?[^\s"\'<>\\]*)?'
)

YDL_BASE = {
    "quiet": True,
    "skip_download": True,
    "noplaylist": True,
    "ignore_no_formats_error": True,
    "js_runtimes": {"node": {}},
    "remote_components": ["ejs:github"],
}


@app.get("/")
def home():
    return {"status": "souTV Extractor is running successfully!"}


@app.get("/version")
def version():
    return {"yt_dlp": YTDLP_VERSION}


@app.get("/formats")
def formats(url: str):
    try:
        with YoutubeDL(YDL_BASE) as ydl:
            info = ydl.extract_info(url, download=False)
        return [
            {"id": f.get("format_id"), "ext": f.get("ext"),
             "res": f.get("resolution"), "v": f.get("vcodec"),
             "a": f.get("acodec"), "proto": f.get("protocol")}
            for f in info.get("formats", [])
        ]
    except Exception as e:
        return {"error": str(e)[:600]}


def extract_with_ytdlp(url: str):
    with YoutubeDL(YDL_BASE) as ydl:
        info = ydl.extract_info(url, download=False)

    # صيغ فيها صورة وصوت معاً وبرابط مباشر
    candidates = [
        f for f in info.get("formats", [])
        if f.get("url")
        and f.get("vcodec") not in (None, "none")
        and f.get("acodec") not in (None, "none")
    ]
    if candidates:
        best = candidates[-1]  # yt-dlp يرتّبها من الأسوأ إلى الأفضل
        return {
            "stream_url": best["url"],
            "headers": best.get("http_headers") or info.get("http_headers", {}),
        }

    if info.get("url"):
        return {"stream_url": info["url"],
                "headers": info.get("http_headers", {})}
    return None


def extract_with_scraping(url: str):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    text, referer = r.text, url

    iframe = BeautifulSoup(text, "html.parser").find("iframe", src=True)
    if iframe:
        player_url =
