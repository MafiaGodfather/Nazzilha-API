from fastapi import FastAPI, Query
import yt_dlp
import requests

app = FastAPI()

# إعدادات yt-dlp
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'impersonate': 'chrome',
    'skip_download': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    },
    # إعدادات خاصة بـ TikTok لتجاوز الحظر
    'extractor_args': {
        'tiktok': {
            'api_hostname': ['api22-normal-c-useast2a.tiktokv.com'],
            'app_name': ['trill'],
            'app_version': ['34.1.2'],
        }
    }
}

@app.get("/")
def read_root():
    return {"status": "Server is awake and ready!"}

@app.get("/extract")
def extract_url(url: str = Query(...)):
    # ═══════════════════════════════════════════════════════
    # المحاولة 1: استخدام yt-dlp
    # ═══════════════════════════════════════════════════════
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
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
        # إذا فشل yt-dlp، نطبع الخطأ في السجلات وننتقل للمحاولة 2
        print(f"yt-dlp failed: {repr(e)}")

    # ═══════════════════════════════════════════════════════
    # المحاولة 2: استخدام API خارجي (TikWM) كخطة بديلة
    # ═══════════════════════════════════════════════════════
    try:
        tikwm_url = f"https://www.tikwm.com/api/?url={url}"
        response = requests.get(tikwm_url, timeout=15)
        data = response.json()

        if data.get("code") == 0:
            v_data = data["data"]
            
            # هل هو منشور صور؟
            if "images" in v_data and v_data["images"]:
                return {
                    "status": "success",
                    "type": "images",
                    "title": v_data.get("title", "منشور صور"),
                    "count": len(v_data["images"]),
                    "urls": v_data["images"]
                }
            
            # فيديو عادي
            else:
                play_url = v_data.get("hdplay") or v_data.get("play")
                return {
                    "status": "success",
                    "type": "video",
                    "title": v_data.get("title", "فيديو"),
                    "uploader": v_data.get("author", {}).get("unique_id", ""),
                    "duration": v_data.get("duration", 0),
                    # TikWM يعطي أعلى جودة فقط، فنعرضها كـ 1080p
                    "formats": [{"height": 1080, "url": play_url, "ext": "mp4", "filesize": 0}]
                }
    except Exception as e:
        print(f"TikWM failed: {repr(e)}")

    # إذا فشلت كل المحاولات
    return {"status": "error", "message": "All extraction methods failed. Please check the URL."}
