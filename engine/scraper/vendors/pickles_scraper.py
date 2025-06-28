from ..common_utils import setup_chrome_driver, random_delay
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time

def scrape_pickles(make=None):
    driver = setup_chrome_driver(headless=True)
    listings = []
    try:
        if make:
            url = f"https://www.pickles.com.au/used/search/lob/salvage/items/{make}?page=1&limit=120"
        else:
            url = "https://www.pickles.com.au/used/search/lob/salvage/cars?page=1&limit=120"

        driver.get(url)
        random_delay()

        page = 1

        while True:

            vehicle_cards = driver.find_elements(By.XPATH, '//*[@id="product-search-id"]/div/div')
            for card in vehicle_cards:
                try:
                    title = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ct-title-wrapper-")]/header/h2[1]/span').text
                    link = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ccg-product-card-link-")]').get_attribute("href")
                    img = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ci-img-wrapper-")]/div/div[1]/div/div[1]/img').get_attribute("src")
                    listings.append({"title": title, "link": link, "img": img, "vendor": "Pickles"})
                except:
                    continue

            try:
                next_button = driver.find_element(By.XPATH, '//*[@id="ps-ch-right-btn"]')

                if "disabled" in next_button.get_attribute("class").lower():
                    break

                print("Clicking next page button...")
                driver.execute_script("arguments[0].click();", next_button)
                random_delay()
                page += 1

            except (NoSuchElementException, IndexError):
                break

    finally:
        driver.quit()
    return listings