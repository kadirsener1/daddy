import requests
import re
import json
from datetime import datetime

# Hedef embed linkin
TARGET_URL = "https://daddylive.li/embed/embed.php?id=63&player=1&source=tv.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Referer": "https://daddylive.li/",
    "Accept": "*/*"
}

def get_final_m3u8():
    session = requests.Session()
    session.headers.update(HEADERS)

    try:
        # 1. Aşama: Embed sayfasını çek ve tv.json veya kaynak verisini bul
        response = session.get(TARGET_URL, timeout=15)
        response.raise_for_status()
        
        # Regex ile .m3u8 uzantılı, içinde md5v1 veya benzeri token olan linkleri ara
        # Senin verdiğin formata uygun regex:
        pattern = r'(https?://[^\s\'"]+?\.m3u8\?md5v1=[^\s\'"&]+&md5v2=[^\s\'"&]+&expires=\d+)'
        
        links = re.findall(pattern, response.text)
        
        if not links:
            # Eğer sayfada direkt yoksa, muhtemelen JS içinde dinamik oluşturuluyordur.
            # Alternatif regex: Tüm m3u8'leri bul
            all_m3u8 = re.findall(r'(https?://[^\s\'"]+?\.m3u8[^\s\'"]*)', response.text)
            links = [l for l in all_m3u8 if "md5" in l.lower()]

        if links:
            final_link = links[0].replace('\\', '') # Kaçış karakterlerini temizle
            print(f"✅ Link Bulundu: {final_link}")
            return final_link
        else:
            print("❌ Link bulunamadı. Site yapısı değişmiş olabilir.")
            return None

    except Exception as e:
        print(f"⚠️ Hata oluştu: {e}")
        return None

def save_to_m3u(stream_url):
    with open("daddylive.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        if stream_url:
            f.write("#EXTINF:-1, DaddyLive ID-63\n")
            f.write(f"{stream_url}\n")
        else:
            f.write("# Link yakalanamadı.\n")

if __name__ == "__main__":
    url = get_final_m3u8()
    save_to_m3u(url)
