from ..common_utils import random_delay, setup_chrome_driver
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape_ebay():
    driver = setup_chrome_driver(headless=True)
    listings = []

    try:
        base_url = (
            "https://www.ebay.com.au/b/Cars/29690/bn_1843284"
            "?Manufacturer=Volvo%7CAlfa%2520Romeo%7CAudi%7CBentley%7CBMW%7CBuick%7CChevrolet%7CCadillac%7CChrysler%7CCitro%25C3%25ABn%7CCorvette%7CDaihatsu%7CDatsun%7CDodge%7CFerrari%7CFiat%7CFord%7CGMC%7CGreat%2520Wall%2520Motors%7CHonda%7CHolden%7CHSV%7CHyundai%7CInfiniti%7CIsuzu%7CJaguar%7CJeep%7CKia%7CLamborghini%7CLand%2520Rover%7CLexus%7CLincoln%7CMaserati%7CMazda%7CMercedes%252DBenz%7CMG%7CMini%7CMitsubishi%7CNissan%7CPeugeot%7CPlymouth%7CPontiac%7CPorsche%7CReliant%7CRenault%7CRover%7CSaab%7C%25C5%25A0koda%7CSubaru%7CSuzuki%7CToyota%7CVolkswagen&mag=1"
        )

        page = 1
        while True:
            url = f"{base_url}&_pgn={page}"
            print(f"Scraping page {page}")
            driver.get(url)
            random_delay()

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located(
                        (By.XPATH, '//*[starts-with(@class, "brwrvr__item-card brwrvr__item-card--")]')
                    )
                )
                ad_elements = driver.find_elements(By.XPATH, '//*[starts-with(@class, "brwrvr__item-card brwrvr__item-card--")]')

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

                        if not link or "ebay.com.au" not in link:
                            continue

                        listings.append({
                            "title": title,
                            "link": link,
                            "img": img,
                            "vendor": "eBay"
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