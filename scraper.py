import re
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ayarlar
BASE_URL = "https://daddylive.li/embed/embed.php?id={channel_id}&player={player_id}&source=tv.json"
CHANNEL_IDS = [63, 64, 65] # Buraya istediğin ID'leri ekle
PLAYER_RANGE = range(1, 11)
OUTPUT_FILE = "daddylive.m3u"

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

def get_channel_name(driver, channel_id):
    """Sayfadan kanal ismini çekmeye çalışır."""
    try:
        # 1. Yöntem: Sayfa başlığını kontrol et (Genelde 'Kanal Adı - DaddyLive' şeklindedir)
        title = driver.title
        if title and "DaddyLive" in title:
            # "Kanal Ismi - DaddyLive" formatını temizle
            name = title.split('-')[0].strip()
            if name and name.lower() != "daddylive":
                return name
        
        # 2. Yöntem: Sayfa içindeki h3 veya h4 başlıklarını kontrol et
        elements = driver.find_elements(By.TAG_NAME, "h3")
        for el in elements:
            if el.text: return el.text.strip()
            
    except:
        pass
    return f"Kanal {channel_id}"

def extract_m3u8(driver, url):
    """M3U8 linklerini bulur."""
    m3u8_links = set()
    try:
        driver.get(url)
        time.sleep(4) # Yüklenmesi için bekle
        
        # Regex ile kaynak kodda m3u8 ara
        pattern = r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)'
        found = re.findall(pattern, driver.page_source)
        for link in found:
            m3u8_links.add(link.replace('\\', ''))
            
        # iframe taraması
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            src = iframe.get_attribute("src")
            if src and ".m3u8" in src:
                m3u8_links.add(src)
    except Exception as e:
        logger.error(f"Hata oluştu: {e}")
    return m3u8_links

def main():
    driver = create_driver()
    results = [] # (name, m3u8_url, channel_id, player_id)
    
    for c_id in CHANNEL_IDS:
        channel_name = None
        for p_id in PLAYER_RANGE:
            url = BASE_URL.format(channel_id=c_id, player_id=p_id)
            logger.info(f"Taranıyor: Kanal {c_id} - Player {p_id}")
            
            links = extract_m3u8(driver, url)
            
            # Kanal ismini sadece ilk başarılı player'da bir kez alalım
            if links and not channel_name:
                channel_name = get_channel_name(driver, c_id)
            
            for link in links:
                results.append({
                    "name": channel_name or f"Kanal {c_id}",
                    "url": link,
                    "p_id": p_id
                })
            
            time.sleep(1)

    driver.quit()

    # M3U Dosyasına Yaz
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for item in results:
            f.write(f'#EXTINF:-1 tvg-name="{item["name"]}" group-title="DaddyLive",{item["name"]} (P{item["p_id"]})\n')
            f.write(f'{item["url"]}\n')
    
    logger.info("Bitti! m3u dosyası güncellendi.")

if __name__ == "__main__":
    main()
