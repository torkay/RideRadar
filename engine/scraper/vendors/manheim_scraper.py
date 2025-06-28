from ..common_utils import setup_chrome_driver, random_delay
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time

def scrape_manheim(make=None):
    driver = setup_chrome_driver(headless=True)
    listings = []
    try:
        if make:
            url = f"https://manheim.com.au/damaged-vehicles/search?refineName=ManufacturerCode&ManufacturerCode={make.upper()}&RecordsPerPage=120"
        else:
            url = "https://manheim.com.au/damaged-vehicles/search?CategoryCodeDescription=Cars%20%26%20Light%20Commercial&RecordsPerPage=120"

        driver.get(url)
        random_delay()

        total_text = driver.find_element(By.XPATH, '//*[@id="result-Container"]/nav[1]/div/div[1]/span/span[2]').text
        total_listings = int(total_text.replace(",", ""))
        
        page = 1

        while True:
            print(f"Scraping page {page}...")

            vehicle_cards = driver.find_elements(By.XPATH, '//*[@id="result-Container"]/section/ul/li')

            for i, card in enumerate(vehicle_cards):
                try:
                    title = card.find_element(By.XPATH, './/a/h2').text
                    link = card.find_element(By.XPATH, './/a').get_attribute("href")
                    img = card.find_element(By.XPATH, './/img').get_attribute("src")

                    # Dynamically build XPath based on position
                    base_xpath = f'//*[@id="result-Container"]/section/ul/li[{i+1}]/div[2]/div[2]/div[3]/div'

                    try:
                        odometer = driver.find_element(By.XPATH, base_xpath + '/div[1]/div[2]').text
                    except:
                        odometer = None

                    try:
                        colour = driver.find_element(By.XPATH, base_xpath + '/div[2]/div[2]').text
                    except:
                        colour = None

                    try:
                        transmission = driver.find_element(By.XPATH, base_xpath + '/div[3]/div[2]').text
                    except:
                        transmission = None

                    try:
                        engine = driver.find_element(By.XPATH, base_xpath + '/div[4]/div[2]').text
                    except:
                        engine = None

                    try:
                        body = driver.find_element(By.XPATH, base_xpath + '/div[5]/div[2]').text
                    except:
                        body = None

                    try:
                        fuel = driver.find_element(By.XPATH, base_xpath + '/div[6]/div[2]').text
                    except:
                        fuel = None

                    try:
                        wovr = driver.find_element(By.XPATH, base_xpath + '/div[7]/div[2]').text
                    except:
                        wovr = None

                    try:
                        seller_type = driver.find_element(By.XPATH, base_xpath + '/div[9]/div[2]').text
                    except:
                        seller_type = None

                    listings.append({
                        "title": title,
                        "link": link,
                        "img": img,
                        "vendor": "Manheim",
                        "odometer": odometer,
                        "colour": colour,
                        "transmission": transmission,
                        "engine": engine,
                        "body": body,
                        "fuel": fuel,
                        "wovr": wovr,
                        "seller_type": seller_type
                    })

                except:
                    continue

            # Pagination check
            count_text = driver.find_element(By.XPATH, '//*[@id="result-Container"]/nav[1]/div/div[1]/span/span[1]').text
            current_total = int(count_text.split("-")[1].replace(",", ""))

            if current_total >= total_listings:
                print("Reached last page. Ending scrape.")
                break

            try:
                next_button = driver.find_element(By.XPATH, '//*[@id="result-Container"]/nav[1]/div/div[2]/div[2]/ul/li[last()]/a')
                driver.execute_script("arguments[0].click();", next_button)
                random_delay()
                page += 1
            except NoSuchElementException:
                print("No next page button found. Ending scrape.")
                break

    finally:
        driver.quit()
    return listings