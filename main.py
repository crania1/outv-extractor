from fastapi import FastAPI, HTTPException
import requests
from bs4 import BeautifulSoup
import re

app = FastAPI()

@app.get("/")
def home():
    return {"status": "souTV Extractor is running successfully!"}

@app.get("/extract")
def extract_video(url: str):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch the target URL")
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن إطار المشغل أو روابط الفيديو المباشرة داخل الصفحة
        iframe = soup.find('iframe', {'class': 'player_iframe'}) or soup.find('iframe')
        target_page_text = response.text
        
        if iframe and iframe.get('src'):
            player_url = iframe.get('src')
            if not player_url.startswith('http'):
                player_url = "https:" + player_url if player_url.startswith("//") else "https://www.fasel-hd.co" + player_url
            
            player_res = requests.get(player_url, headers=headers)
            target_page_text = player_res.text

        # البحث عن روابط .m3u8 أو .mp4
        video_links = re.findall(r'(https?://[^\s"\'<>]+?\.(?:m3u8|mp4)(?:\?[^\s"\'<>]*)?)', target_page_text)
        
        if video_links:
            return {"success": True, "stream_url": video_links[0]}
        else:
            raise HTTPException(status_code=404, detail="Direct stream link not found")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))