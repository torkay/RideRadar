from ..common_utils import setup_chrome_driver, random_delay
from selenium.webdriver.common.by import By

def scrape_pickles(make):
    driver = setup_chrome_driver()
    listings = []
    try:
        url = f"https://www.pickles.com.au/used/search/lob/salvage/items/{make}?page=1"
        driver.get(url)
        random_delay()

        vehicle_cards = driver.find_elements(By.XPATH, '//*[@id="product-search-id"]/div/div')
        for card in vehicle_cards:
            try:
                title = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ct-title-wrapper-")]/header/h2[1]/span').text
                link = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ccg-product-card-link-")]').get_attribute("href")
                img = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ci-img-wrapper-")]/div/div[1]/div/div[1]/img').get_attribute("src")
                listings.append({"title": title, "link": link, "img": img, "vendor": "Pickles"})
            except:
                continue
    finally:
        driver.quit()
    return listings