from ..common_utils import random_delay, setup_chrome_driver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_bikesales():
    driver = setup_chrome_driver(headless=True, stealth=True)  # Assuming your setup_chrome_driver supports stealth arg
    listings = []

    try:
        base_url = "https://www.bikesales.com.au/bikes/?q=Service.bikesales."

        page = 1
        while True:
            url = f"{base_url}&_pgn={page}"
            print(f"Scraping page {page}")
            driver.get(url)
            random_delay()

            try:
                # Check for captcha page (very basic detection, can be improved)
                if "captcha" in driver.page_source.lower():
                    print("⚠️ CAPTCHA detected. Exiting scrape.")
                    break

                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, "//*[contains(@class, 'listing-card_listing-card')]")
                    )
                )
                ad_elements = driver.find_elements(By.XPATH, "//*[contains(@class, 'listing-card_listing-card')]")

                print(f"{len(ad_elements)} listings found, Success")

                if not ad_elements:
                    print("⚠️ No listings found. Likely last page.")
                    break

                for ad in ad_elements:
                    try:
                        link_elem = ad.find_element(By.TAG_NAME, "a")
                        link = link_elem.get_attribute("href")
                        title = ad.text.strip()
                        img_elem = ad.find_elements(By.TAG_NAME, "img")
                        img = img_elem[0].get_attribute("src") if img_elem else None

                        if not link or "bikesales.com.au" not in link:
                            continue

                        listings.append({
                            "title": title,
                            "link": link,
                            "img": img,
                            "vendor": "Bikesales"
                        })

                    except:
                        continue

                if len(ad_elements) < 60:
                    print("Likely last page due to fewer listings.")
                    break

                page += 1
                random_delay()

            except:
                print("⚠️ Listings not loaded. Ending scrape.")
                break

    finally:
        driver.quit()

    return listings