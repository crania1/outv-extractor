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


@app.get("/")
def home():
    return {"status": "souTV Extractor is running successfully!"}


@app.get("/version")
def extract_with_ytdlp(url: str):
    opts = {
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
        "format": "best",  # استخدام أفضل صيغة متاحة تلقائياً بدون تقييد بـ mp4
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        stream_url = info.get("url")
        
        # إذا لم يكن الرابط مباشراً في المستوى الأول، ابحث عنه في الـ formats المتاحة
        if not stream_url and "formats" in info:
            for f in info["formats"]:
                if f.get("url"):
                    stream_url = f.get("url")
                    break

        if not stream_url:
            return None
            
        return {
            "stream_url": stream_url,
            "headers": info.get("http_headers", {})
        }


def extract_with_scraping(url: str):
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    text, referer = r.text, url

    iframe = BeautifulSoup(text, "html.parser").find("iframe", src=True)
    if iframe:
        player_url = urljoin(url, iframe["src"])
        pr = requests.get(player_url, headers={**HEADERS, "Referer": url}, timeout=15)
        text, referer = pr.text, player_url

    links = VIDEO_RE.findall(text.replace("\\/", "/"))
    if not links:
        return None
    return {"stream_url": links[0],
            "headers": {"User-Agent": UA, "Referer": referer}}


@app.get("/extract")
def extract_video(url: str):
    ytdlp_error = None

    try:
        result = extract_with_ytdlp(url)
        if result:
            return {"success": True, **result}
    except Exception as e:
        ytdlp_error = str(e)[:600]

    try:
        result = extract_with_scraping(url)
    except requests.RequestException as e:
        raise HTTPException(
            status_code=502,
            detail=f"Fetch failed: {e} | yt-dlp: {ytdlp_error}",
        )

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Direct stream link not found | yt-dlp: {ytdlp_error}",
        )
    return {"success": True, **result}
