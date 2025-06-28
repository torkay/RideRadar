from ..common_utils import setup_chrome_driver, random_delay
from selenium.webdriver.common.by import By

def scrape_gumtree(make):
    driver = setup_chrome_driver()
    listings = []
    try:
        url = f"https://www.gumtree.com.au/s-cars-vans-utes/{make}/k0c18320r10?forsaleby=ownr&view=gallery"
        driver.get(url)
        random_delay()

        parent_element = driver.find_element(By.XPATH, '//*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div[1]/div')
        child_elements = parent_element.find_elements(By.TAG_NAME, 'a')

        for child in child_elements:
            try:
                vehicle_link = child.get_attribute('href')
                aria_label = child.get_attribute('aria-label')
                image_url = child.find_element(By.XPATH, './/img').get_attribute('src')

                parts = aria_label.split(".")
                vehicle_name = parts[0].strip()
                vehicle_price = parts[1].strip().replace("Price: ", "")
                vehicle_location = parts[2].strip().replace("Location: ", "")
                time_listed = parts[3].strip().replace("Ad listed ", "")

                listings.append({
                    "title": vehicle_name,
                    "price": vehicle_price,
                    "link": vehicle_link,
                    "img": image_url,
                    "location": vehicle_location,
                    "date": time_listed,
                    "vendor": "Gumtree"
                })
            except:
                continue
    finally:
        driver.quit()
    return listings