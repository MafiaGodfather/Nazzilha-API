from fastapi import FastAPI, Query
import yt_dlp
import os

app = FastAPI()

# إعدادات هامة جداً لتجاوز حماية TikTok
YDL_OPTS = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,          # جلب التفاصيل الكاملة
    'impersonate': 'chrome',        # انتحال شخصية متصفح Chrome (باستخدام curl_cffi)
    'skip_download': True,
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
}

@app.get("/")
def read_root():
    return {"status": "Server is awake and ready!"}

@app.get("/extract")
def extract_url(url: str = Query(...)):
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # 1. التحقق: هل هو منشور صور (Carousel)؟
            if 'entries' in info:
                urls = [entry['url'] for entry in info['entries'] if entry and entry.get('url')]
                return {
                    "status": "success",
                    "type": "images",
                    "title": info.get('title', 'منشور صور'),
                    "count": len(urls),
                    "urls": urls
                }
            
            # 2. إذا كان فيديو عادي
            else:
                formats = []
                seen_heights = set()
                
                # استخراج الجودات الفريدة (بدون تكرار)
                for fmt in info.get('formats', []):
                    height = fmt.get('height')
                    if height and height not in seen_heights:
                        seen_heights.add(height)
                        formats.append({
                            "height": height,
                            "url": fmt.get('url'),
                            "ext": fmt.get('ext', 'mp4'),
                            "filesize": fmt.get('filesize') or fmt.get('filesize_approx') or 0
                        })
                
                # ترتيب الجودات من الأعلى للأقل
                formats.sort(key=lambda x: x['height'], reverse=True)
                
                return {
                    "status": "success",
                    "type": "video",
                    "title": info.get('title', 'فيديو'),
                    "uploader": info.get('uploader', ''),
                    "duration": info.get('duration', 0),
                    "formats": formats
                }
                
    except Exception as e:
        return {"status": "error", "message": str(e)}
