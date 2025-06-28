from ..common_utils import setup_chrome_driver, random_delay
from selenium.webdriver.common.by import By

def scrape_manheim(make):
    driver = setup_chrome_driver()
    listings = []
    try:
        url = f"https://manheim.com.au/damaged-vehicles/search?refineName=ManufacturerCode&ManufacturerCode={make.upper()}"
        driver.get(url)
        random_delay()

        vehicle_cards = driver.find_elements(By.CLASS_NAME, "vehicle-card")
        for card in vehicle_cards:
            try:
                title = card.find_element(By.XPATH, ".//a/h2").text
                link = card.find_element(By.XPATH, ".//a").get_attribute("href")
                img = card.find_element(By.XPATH, "./div/div/div/div/div/div/img").get_attribute("src")
                listings.append({"title": title, "link": link, "img": img, "vendor": "Manheim"})
            except:
                continue
    finally:
        driver.quit()
    return listings