from ..common_utils import setup_chrome_driver, random_delay
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time

def scrape_manheim(make=None):
    driver = setup_chrome_driver(headless=False)  # Disable headless for debugging
    listings = []
    try:
        if make:
            url = f"https://manheim.com.au/damaged-vehicles/search?refineName=ManufacturerCode&ManufacturerCode={make.upper()}&RecordsPerPage=120"
        else:
            url = "https://manheim.com.au/damaged-vehicles/search?CategoryCodeDescription=Cars%20%26%20Light%20Commercial&RecordsPerPage=120"

        driver.get(url)
        random_delay()

        while True:

            vehicle_cards = driver.find_elements(By.CLASS_NAME, "vehicle-card")
            for card in vehicle_cards:
                try:
                    title = card.find_element(By.XPATH, ".//a/h2").text
                    link = card.find_element(By.XPATH, ".//a").get_attribute("href")
                    img = card.find_element(By.XPATH, "./div/div/div/div/div/div/img").get_attribute("src")
                    listings.append({"title": title, "link": link, "img": img, "vendor": "Manheim"})
                except:
                    continue

            # Extract visible count and total count
            try:
                count_text = driver.find_element(By.XPATH, '//*[@id="result-Container"]/nav[1]/div/div[1]/span/span[1]').text
                total_text = driver.find_element(By.XPATH, '//*[@id="result-Container"]/nav[1]/div/div[1]/span/span[2]').text

                visible_end = int(count_text.split("-")[1])
                total = int(total_text)

                if visible_end >= total:
                    break
            except Exception as e:
                print(f"Error extracting page count info: {e}")
                break

            try:
                pagination = driver.find_elements(By.XPATH, '//*[@id="result-Container"]/nav[1]/div/div[2]/div[2]/ul/li')
                next_button = pagination[-1].find_element(By.TAG_NAME, "a")
                driver.execute_script("arguments[0].click();", next_button)
                random_delay()
            except NoSuchElementException:
                break

    finally:
        driver.quit()

    return listings