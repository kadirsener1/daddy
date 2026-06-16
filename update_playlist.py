import requests
import re
import urllib.parse
from datetime import datetime

# Hedef linkin (id=91)
URL = "https://daddylive.li/embed/embed.php?id=91&player=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://daddylive.li/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.8,en-US;q=0.5,en;q=0.3",
}

def get_stream_link():
    session = requests.Session()
    try:
        # 1. Sayfayı çek
        response = session.get(URL, headers=HEADERS, timeout=20)
        content = response.text

        # 2. Regex ile m3u8 linkini ara (Özellikle md5 içeren yapıyı hedefle)
        # Bu pattern: http(s) ile başlayan, içinde .m3u8 olan ve md5v1 parametresi içeren linki bulur
        pattern = r'(https?://[^\s\'"<>]+?\.m3u8\?md5v1=[^\s\'"<>]+)'
        matches = re.findall(pattern, content)

        if not matches:
            # Eğer direkt m3u8 yoksa, bazen \ ile kaçırılmış olabilir (JS içinde)
            content_cleaned = content.replace('\\', '')
            matches = re.findall(pattern, content_cleaned)

        if matches:
            # Bulunan ilk linki al ve HTML entitylerini temizle
            final_link = urllib.parse.unquote(matches[0])
            print(f"✅ Başarıyla bulundu: {final_link}")
            return final_link
        else:
            print("❌ m3u8 linki sayfa kaynağında bulunamadı.")
            # Hata ayıklama için sayfa başlığını yazdıralım
            title = re.search(r'<title>(.*?)</title>', content)
            if title: print(f"Sayfa Başlığı: {title.group(1)}")
            return None

    except Exception as e:
        print(f"⚠️ Hata: {e}")
        return None

def save_m3u(link):
    with open("daddylive.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if link:
            f.write("#EXTINF:-1, DaddyLive - ID 91\n")
            f.write(f"{link}\n")
        else:
            f.write("# Link bulunamadı veya sunucu engelledi.\n")

if __name__ == "__main__":
    stream_url = get_stream_link()
    save_m3u(stream_url)
