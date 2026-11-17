import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI, HTTPException
from yt_dlp import YoutubeDL

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


def extract_with_ytdlp(url: str):
    opts = {
        "quiet": True,
        "noplaylist": True,
        "skip_download": True,
        # صيغة واحدة فيها صوت وصورة معاً ليشغّلها video_player مباشرة
        "format": "best[ext=mp4]/best",
    }
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    stream = info.get("url")
    if not stream:
        return None
    return {"stream_url": stream, "headers": info.get("http_headers", {})}


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
    # 1) yt-dlp يدعم يوتيوب وعشرات المواقع الأخرى
    try:
        result = extract_with_ytdlp(url)
        if result:
            return {"success": True, **result}
    except Exception:
        pass  # ننتقل إلى الطريقة الاحتياطية

    # 2) الاستخراج اليدوي من الصفحة
    try:
        result = extract_with_scraping(url)
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Fetch failed: {e}")

    if not result:
        raise HTTPException(status_code=404, detail="Direct stream link not found")
    return {"success": True, **result}