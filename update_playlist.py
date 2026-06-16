import requests
import re
import os
from datetime import datetime

# Hedef kanal ID=91
URL = "https://daddylive.li/embed/embed.php?id=91&player=1"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Referer": "https://daddylive.li/",
    "Accept": "*/*",
}

def get_stream():
    session = requests.Session()
    try:
        response = session.get(URL, headers=HEADERS, timeout=20)
        source_code = response.text

        # 1. Yöntem: Direkt m3u8 linkini ara (MD5'li yapı)
        direct_match = re.search(r'["\'](https?://.*?\.m3u8\?md5v1=[^"\']+)["\']', source_code)
        if direct_match:
            return direct_match.group(1).replace("\\", "")

        # 2. Yöntem: JavaScript değişkenlerinden linki inşa et
        # DaddyLive genellikle 'source', 'src' veya 'stream_url' değişkenleri kullanır
        server = re.search(r"var\s+server\s*=\s*['\"]([^'\"]+)['\"]", source_code)
        m3u8_file = re.search(r"var\s+source\s*=\s*['\"]([^'\"]+)['\"]", source_code)
        
        if server and m3u8_file:
            final_url = f"https://{server.group(1)}/premium91/{m3u8_file.group(1)}"
            # Eğer token değişkenleri varsa onları da eklemeye çalış
            return final_url

        # 3. Yöntem: Sayfa içindeki tüm m3u8 uzantılarını tara
        all_links = re.findall(r'https?://[^\s\'"<>]+?\.m3u8[^\s\'"<>]*', source_code)
        for link in all_links:
            if "md5" in link or "premium" in link:
                return link.replace("\\", "")

        return None

    except Exception as e:
        print(f"Hata: {e}")
        return None

def main():
    link = get_stream()
    
    with open("daddylive.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        if link:
            f.write(f"# Generated at: {datetime.now()}\n")
            f.write("#EXTINF:-1, beIN Sports 1 Arabic (ID 91)\n")
            f.write(f"{link}\n")
            print(f"✅ Link bulundu ve yazıldı: {link}")
        else:
            f.write("# Link yakalanamadi. Sayfa yapisi değişmiş veya bot korumasi var.\n")
            print("❌ Link bulunamadı.")

if __name__ == "__main__":
    main()
