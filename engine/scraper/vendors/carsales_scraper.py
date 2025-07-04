from ..common_utils import random_delay, setup_chrome_driver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_carsales():
    driver = setup_chrome_driver(headless=False)
    listings = []

    try:
        url = "https://www.carsales.com.au/cars/"
        driver.get(url)
        random_delay()

        page = 1
        while True:
            print(f"Scraping page {page}...")

            try:
                # Locate listings container
                container = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//*[@id="__next"]/div/div[3]/div[2]/div/div/div[2]/main/div[1]/div[1]/div[2]/div/div/div')
                    )
                )
                ad_elements = container.find_elements(By.TAG_NAME, "a")

            except:
                print("⚠️ Listings container or ads not found. Ending scrape.")
                break

            for ad in ad_elements:
                try:
                    link = ad.get_attribute("href")
                    if not link or "carsales.com.au/cars" not in link:
                        continue  # Filter only relevant ads

                    title = ad.text.strip()
                    img = ad.find_element(By.TAG_NAME, "img").get_attribute("src") if ad.find_elements(By.TAG_NAME, "img") else None

                    listings.append({
                        "title": title,
                        "link": link,
                        "img": img,
                        "vendor": "Carsales"
                    })

                except:
                    continue

            # Paginate
            try:
                next_button = driver.find_element(By.XPATH, '//*[@id="pagination-form"]/nav/button[2]')
                if not next_button.is_enabled():
                    print("Reached last page.")
                    break
                driver.execute_script("arguments[0].click();", next_button)
                random_delay()
                page += 1

            except:
                print("No next button found or pagination ended.")
                break

    finally:
        driver.quit()

    return listings