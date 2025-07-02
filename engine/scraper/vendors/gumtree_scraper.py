from ..common_utils import random_delay
import time
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_gumtree(max_pages=5):
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = uc.Chrome(options=options)
    listings = []

    try:
        for page in range(1, max_pages + 1):
            url = f"https://www.gumtree.com.au/s-cars-vans-utes/page-{page}/c18320r500"
            print(f"\nLoading page {page}: {url}")
            driver.get(url)
            random_delay()

            # Give time for listings to load
            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "user-ad-row-new-design"))
                )
            except:
                print("⚠️ Listings not found or page blocked. Exiting.")
                break

            ad_elements = driver.find_elements(By.CLASS_NAME, "user-ad-row-new-design")

            if not ad_elements:
                print("⚠️ No listings found. Likely last page or blocked.")
                break

            for ad in ad_elements:
                try:
                    link = ad.get_attribute("href")
                    title = ad.find_element(By.CLASS_NAME, "user-ad-row-new-design__title-span").text
                    price_elem = ad.find_elements(By.CLASS_NAME, "user-ad-price-new-design__price")
                    price = price_elem[0].text if price_elem else "N/A"
                    img_elem = ad.find_elements(By.TAG_NAME, "img")
                    img = img_elem[0].get_attribute("src") if img_elem else ""
                    listings.append({
                        "title": title,
                        "price": price,
                        "link": link,
                        "img": img,
                        "vendor": "Gumtree"
                    })
                except:
                    continue

            print(f"Collected {len(ad_elements)} listings on page {page}.")
            random_delay()

    finally:
        driver.quit()

    return listings