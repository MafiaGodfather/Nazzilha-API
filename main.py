from fastapi import FastAPI, Query
import yt_dlp
import requests
import re

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "Server is awake and ready!"}

@app.get("/extract")
def extract_url(url: str = Query(...)):
    print(f"--- New Request: {url} ---")

    # ═══════════════════════════════════════════════════════════════════
    # المحرك 1: استخدام واجهة "Douyin WTF" (مفتوحة المصدر ومجانية)
    # ═══════════════════════════════════════════════════════════════════
    try:
        api_url = f"https://api.douyin.wtf/api/hybrid/video_data?url={url}&minimal=true"
        res = requests.get(api_url, timeout=15)
        data = res.json()
        
        if data.get("code") == 200:
            v_data = data.get("data", {})
            # هل هو فيديو؟
            if "video_data" in v_data:
                play_url = v_data["video_data"].get("nwm_video_url_HQ") or v_data["video_data"].get("wm_video_url_HQ")
                if play_url:
                    return {
                        "status": "success",
                        "type": "video",
                        "title": v_data.get("desc", "فيديو"),
                        "uploader": v_data.get("author", {}).get("nickname", ""),
                        "duration": 0,
                        "formats": [{"height": 1080, "url": play_url, "ext": "mp4", "filesize": 0}]
                    }
            # هل هو صور؟
            elif "images" in v_data and v_data["images"]:
                return {
                    "status": "success",
                    "type": "images",
                    "title": v_data.get("desc", "صور"),
                    "count": len(v_data["images"]),
                    "urls": v_data["images"]
                }
    except Exception as e:
        print(f"Engine 1 (Douyin WTF) failed: {repr(e)}")

    # ═══════════════════════════════════════════════════════════════════
    # المحرك 2: استخدام واجهة "TikWM" مع ترويسات كاملة
    # ═══════════════════════════════════════════════════════════════════
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Referer": "https://www.tikwm.com/"
        }
        api_url = f"https://www.tikwm.com/api/?url={url}&hd=1"
        res = requests.get(api_url, headers=headers, timeout=15)
        data = res.json()
        
        if data.get("code") == 0:
            v_data = data["data"]
            if "images" in v_data and v_data["images"]:
                return {"status": "success", "type": "images", "title": v_data.get("title", ""), "count": len(v_data["images"]), "urls": v_data["images"]}
            else:
                play_url = v_data.get("hdplay") or v_data.get("play")
                return {"status": "success", "type": "video", "title": v_data.get("title", ""), "uploader": v_data.get("author", {}).get("unique_id", ""), "duration": v_data.get("duration", 0), "formats": [{"height": 1080, "url": play_url, "ext": "mp4", "filesize": 0}]}
    except Exception as e:
        print(f"Engine 2 (TikWM) failed: {repr(e)}")

    # ═══════════════════════════════════════════════════════════════════
    # المحرك 3: استخدام yt-dlp (المحلي)
    # ═══════════════════════════════════════════════════════════════════
    try:
        ydl_opts = {
            'quiet': True, 'no_warnings': True, 'extract_flat': False, 'impersonate': 'chrome', 'skip_download': True,
            'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                urls = [entry['url'] for entry in info['entries'] if entry and entry.get('url')]
                return {"status": "success", "type": "images", "title": info.get('title', 'منشور'), "count": len(urls), "urls": urls}
            else:
                formats = []
                seen = set()
                for fmt in info.get('formats', []):
                    h = fmt.get('height')
                    if h and h not in seen:
                        seen.add(h)
                        formats.append({"height": h, "url": fmt.get('url'), "ext": fmt.get('ext', 'mp4'), "filesize": fmt.get('filesize') or 0})
                formats.sort(key=lambda x: x['height'], reverse=True)
                return {"status": "success", "type": "video", "title": info.get('title', ''), "uploader": info.get('uploader', ''), "duration": info.get('duration', 0), "formats": formats}
    except Exception as e:
        print(f"Engine 3 (yt-dlp) failed: {repr(e)}")

    # ═══════════════════════════════════════════════════════════════════
    # المحرك 4: استخدام TikMate
    # ═══════════════════════════════════════════════════════════════════
    try:
        res = requests.get(f"https://api.tikmate.app/api/lookup?url={url}", timeout=15)
        data = res.json()
        if data.get("success"):
            video_url = f"https://tikmate.app/download/{data['token']}/{data['id']}.mp4"
            return {"status": "success", "type": "video", "title": "", "formats": [{"height": 1080, "url": video_url, "ext": "mp4", "filesize": 0}]}
    except Exception as e:
        print(f"Engine 4 (TikMate) failed: {repr(e)}")

    # إذا فشلت كل المحركات الأربعة
    return {"status": "error", "message": "All 4 extraction methods failed."}
