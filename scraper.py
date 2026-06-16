import re
import time
import json
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Ayarlar
# ─────────────────────────────────────────────
BASE_URL = "https://daddylive.li/embed/embed.php?id={channel_id}&player={player_id}&source=tv.json"
CHANNEL_IDS = [63]           # İstediğin kanal ID'lerini ekle
PLAYER_RANGE = range(1)  # player=1 ... player=10
OUTPUT_FILE = "daddylive.m3u"
TIMEOUT = 30


def create_driver():
    """Headless Chrome tarayıcı oluştur."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    # Otomasyon algılamayı devre dışı bırak
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    # navigator.webdriver flag'ini gizle
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"},
    )
    return driver


def extract_m3u8_from_page(driver, url):
    """
    Sayfayı aç, ağ isteklerini ve sayfa kaynağını tarayarak
    m3u8 linklerini bul.
    """
    m3u8_links = set()

    try:
        # Performance log'u etkinleştir (ağ isteklerini yakalamak için)
        driver.execute_cdp_cmd("Network.enable", {})

        logger.info(f"Sayfa açılıyor: {url}")
        driver.get(url)
        time.sleep(5)  # Sayfanın yüklenmesini bekle

        # ── Yöntem 1: Sayfa kaynağından m3u8 linklerini regex ile bul ──
        page_source = driver.page_source
        pattern = r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)'
        found = re.findall(pattern, page_source)
        for link in found:
            clean = link.rstrip("\\").rstrip("/")
            m3u8_links.add(clean)
            logger.info(f"  [Kaynak] Bulundu: {clean}")

        # ── Yöntem 2: iframe içine gir, orada da ara ──
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for idx, iframe in enumerate(iframes):
            try:
                iframe_src = iframe.get_attribute("src")
                logger.info(f"  iframe[{idx}] src: {iframe_src}")

                # iframe src'sinde m3u8 var mı?
                if iframe_src and ".m3u8" in iframe_src:
                    m3u8_links.add(iframe_src)

                driver.switch_to.frame(iframe)
                time.sleep(3)

                inner_source = driver.page_source
                found_inner = re.findall(pattern, inner_source)
                for link in found_inner:
                    clean = link.rstrip("\\").rstrip("/")
                    m3u8_links.add(clean)
                    logger.info(f"  [iframe] Bulundu: {clean}")

                # İç iframe'leri de kontrol et
                inner_iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iidx, inner_iframe in enumerate(inner_iframes):
                    try:
                        inner_src = inner_iframe.get_attribute("src")
                        if inner_src and ".m3u8" in inner_src:
                            m3u8_links.add(inner_src)

                        driver.switch_to.frame(inner_iframe)
                        time.sleep(2)
                        deep_source = driver.page_source
                        found_deep = re.findall(pattern, deep_source)
                        for link in found_deep:
                            clean = link.rstrip("\\").rstrip("/")
                            m3u8_links.add(clean)
                            logger.info(f"  [deep-iframe] Bulundu: {clean}")
                        driver.switch_to.parent_frame()
                    except Exception:
                        driver.switch_to.parent_frame()

                driver.switch_to.default_content()
            except Exception as e:
                logger.warning(f"  iframe[{idx}] hata: {e}")
                driver.switch_to.default_content()

        # ── Yöntem 3: JavaScript ile video elementlerini kontrol et ──
        try:
            video_srcs = driver.execute_script("""
                var results = [];
                var videos = document.querySelectorAll('video, video source');
                videos.forEach(function(v) {
                    if (v.src) results.push(v.src);
                    if (v.currentSrc) results.push(v.currentSrc);
                });
                return results;
            """)
            for src in (video_srcs or []):
                if ".m3u8" in src:
                    m3u8_links.add(src)
                    logger.info(f"  [video-element] Bulundu: {src}")
        except Exception:
            pass

        # ── Yöntem 4: JavaScript değişkenlerinden m3u8 bul ──
        try:
            js_vars = driver.execute_script("""
                var results = [];
                for (var key in window) {
                    try {
                        var val = window[key];
                        if (typeof val === 'string' && val.includes('.m3u8')) {
                            results.push(val);
                        }
                    } catch(e) {}
                }
                return results;
            """)
            for val in (js_vars or []):
                found_js = re.findall(pattern, val)
                for link in found_js:
                    m3u8_links.add(link)
                    logger.info(f"  [js-var] Bulundu: {link}")
        except Exception:
            pass

        # ── Yöntem 5: Performance log'larından ağ isteklerini tara ──
        try:
            logs = driver.execute_script("""
                var entries = performance.getEntriesByType('resource');
                return entries.map(function(e) { return e.name; });
            """)
            for entry in (logs or []):
                if ".m3u8" in entry:
                    m3u8_links.add(entry)
                    logger.info(f"  [perf-log] Bulundu: {entry}")
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Sayfa işlenirken hata: {e}")

    return m3u8_links


def try_direct_request(url):
    """Selenium olmadan doğrudan HTTP isteği ile m3u8 ara."""
    m3u8_links = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://daddylive.li/",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        if resp.status_code == 200:
            pattern = r'(https?://[^\s"\'<>]+\.m3u8[^\s"\'<>]*)'
            found = re.findall(pattern, resp.text)
            for link in found:
                clean = link.rstrip("\\").rstrip("/")
                m3u8_links.add(clean)
                logger.info(f"  [HTTP] Bulundu: {clean}")
    except Exception as e:
        logger.warning(f"HTTP istek hatası: {e}")
    return m3u8_links


def write_m3u(all_links, output_file):
    """Bulunan linkleri M3U dosyasına yaz."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# DaddyLive M3U8 Linkleri\n")
        f.write(f"# Son güncelleme: {now}\n")
        f.write(f"# Toplam link sayısı: {len(all_links)}\n\n")

        for idx, (info, link) in enumerate(all_links, 1):
            channel_id = info.get("channel_id", "?")
            player_id = info.get("player_id", "?")
            f.write(f'#EXTINF:-1 tvg-id="ch{channel_id}_p{player_id}" '
                    f'group-title="DaddyLive",'
                    f'Kanal {channel_id} - Player {player_id} - Stream {idx}\n')
            f.write(f"{link}\n")

    logger.info(f"✅ {len(all_links)} link '{output_file}' dosyasına yazıldı.")


def main():
    logger.info("=" * 60)
    logger.info("DaddyLive M3U8 Scraper başlatılıyor...")
    logger.info("=" * 60)

    all_links = []  # [(info_dict, m3u8_url), ...]
    driver = None

    try:
        driver = create_driver()

        for channel_id in CHANNEL_IDS:
            for player_id in PLAYER_RANGE:
                url = BASE_URL.format(channel_id=channel_id, player_id=player_id)
                info = {"channel_id": channel_id, "player_id": player_id}

                logger.info(f"\n{'─'*40}")
                logger.info(f"Kanal: {channel_id} | Player: {player_id}")
                logger.info(f"URL: {url}")

                # Önce HTTP ile dene
                m3u8_set = try_direct_request(url)

                # Sonra Selenium ile dene
                selenium_links = extract_m3u8_from_page(driver, url)
                m3u8_set.update(selenium_links)

                if m3u8_set:
                    for link in m3u8_set:
                        all_links.append((info, link))
                    logger.info(f"  ✅ {len(m3u8_set)} link bulundu")
                else:
                    logger.warning(f"  ❌ Link bulunamadı")

                # Rate limiting - siteye nazik olalım
                time.sleep(3)

    except Exception as e:
        logger.error(f"Genel hata: {e}")
    finally:
        if driver:
            driver.quit()

    # Sonuçları yaz
    if all_links:
        write_m3u(all_links, OUTPUT_FILE)
    else:
        # Boş dosya oluştur (GitHub Actions'da commit yapılabilsin)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            f.write(f"# DaddyLive M3U8 Linkleri\n")
            f.write(f"# Son güncelleme: {now}\n")
            f.write(f"# Hiç link bulunamadı.\n")
        logger.warning("⚠️ Hiç m3u8 linki bulunamadı!")

    logger.info("Scraper tamamlandı.")


if __name__ == "__main__":
    main()
