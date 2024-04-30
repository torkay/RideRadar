from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import *
import asyncio
import logging
import platform
import re

#init()

class NoSearchResultsException(Exception):
    pass

class search_by:
    class vehicle_brand:
        def __init__(self, vehicle_make):
            # Set the vehicle make
            self.vehicle_make = vehicle_make
            print(vehicle_make)
            
            # Set Chrome options for headless mode and suppress logging
            self.chrome_options = Options()
            self.chrome_options.add_argument("--headless")  # Enable headless mode
            self.chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration (needed for headless mode)
            self.chrome_options.add_argument("--log-level=3")  # Suppress logging

            os = platform.system()
            # Set the chromedriver_path based on the operating system
            if os == "Windows":
                self.chromedriver_path = "chromedriver.exe"
                write.console("green", "Windows platform detected")
            elif os == "Darwin":  # "Darwin" is the platform name for macOS
                write.console("green", "Darwin platform detected")
                self.chromedriver_path = "/Users/torrinkay/Documents/RideRadar/chromedriver-arm64.app"
            else:
                logging.error("OS not identified: Check src_scraper chromedriver_path declaration")

        async def search_manheim(self):
            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)

            driver.get("https://manheim.com.au/damaged-vehicles/search?")

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            # Wait for content (Net car auctions)
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "js-searchTitleHeading"))
            )

            # Print net car auctions
            net_result = driver.find_element(By.ID, "js-searchTitleHeading").text

            # Open vehicle menu
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.ID, "ManufacturerCode"))
            )
            self.vehicle_make = driver.find_element(By.ID, "ManufacturerCode")
            self.vehicle_make.click()
            # Wait for contents
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.TAG_NAME, "label"))
            )

            # Select desired vehicle(s)
            desired_make = driver.find_elements(By.TAG_NAME, "label")
            for items in desired_make:
                label = WebDriverWait(driver, 4).until(
                    EC.presence_of_element_located((By.XPATH, f"//label[text()='{self.vehicle_make}']"))
                )
                label.click()

            returned_vehicle_list = []

            # Save title of each vehicle
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "vehicle-card"))
            )
            vehicle_cards = driver.find_elements(By.CLASS_NAME, "vehicle-card")
            for card in vehicle_cards:
                # Main details
                vehicle_name = card.find_element(By.XPATH, ".//a/h2").text
                print(vehicle_name)
                vehicle_link = card.find_element(By.XPATH, ".//a").get_attribute("href")
                print(vehicle_link)
                vehicle_img = card.find_element(By.XPATH, "./div/div/div/div/div/div/img").get_attribute("src")
                print(vehicle_img)

                returned_vehicle_list.append({"title": vehicle_name, "link": vehicle_link, "img": vehicle_img, "vendor": "Manheim"})

            driver.quit()
            write.console("yellow", "Processing manheim data...")
            return returned_vehicle_list



        async def search_pickles(self):
            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)

            driver.get(f"https://www.pickles.com.au/damaged-salvage/item/search#!/search-result?q=(And.ProductType.Vehicles._.Make.{self.vehicle_make}.)")

            WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@ng-repeat='resultItem in searchResults']//a"))
                )

            # Find all cards
            vehicle_cards = driver.find_elements(By.XPATH, "//div[@ng-repeat='resultItem in searchResults']")

            returned_vehicle_list = []

            # Iterate over each card
            for card in vehicle_cards:
                # Find the first direct child <a> tag within the card
                vehicle_link = card.find_element(By.XPATH, ".//a[not(ancestor::a)]").get_attribute("href")
                # Find the title text within the div with class "title pb-0 text-truncate-2l"
                vehicle_name = card.find_element(By.XPATH, ".//div[@class='title pb-0 text-truncate-2l']//a").text
                # Find the image URL from the "lazy-load-bg" attribute
                style_attribute = card.find_element(By.XPATH, ".//div[@ng-repeat='imageName in resultItem.Thumbnails track by $index']").get_attribute("style")
                img_extraction_sequence = r'background-image:\s*url\("([^"]+)"\)' # Define the regex pattern to match the background image URL
                img_content = re.findall(img_extraction_sequence, style_attribute)
                image_url = img_content[0]
                # Append the data to the list if the link is not already present
                returned_vehicle_list.append({"title": vehicle_name, "link": vehicle_link, "img": image_url, "vendor": "Pickles"})

            # print(f"Processing data...{Style.RESET_ALL}")
            return returned_vehicle_list

        async def search_by_brand(self):
            try:
                manheim_task = asyncio.create_task(self.search_manheim())
                pickles_task = asyncio.create_task(self.search_pickles())

                manheim_result = await manheim_task
                pickles_result = await pickles_task

                return manheim_result + pickles_result
            except NoSearchResultsException:
                write.console("red", f"No search results on Manheim for {self.vehicle_make}")
                return await self.search_pickles()


    async def vehicle_model(brand, model):
        await vehicle_brand(brand, True)
        pass

async def request(function_name, *args, **kwargs):
    search_result = await search_by.search_by_brand(*args)  # Store the result in a separate variable

    # Check chromedriver
    # update = update_chromedriver()
    # update.check()

    if hasattr(request, function_name):
        function_to_call = getattr(request, function_name)
        return await function_to_call(*args, **kwargs)  # Call the function asynchronously
    else:
        raise AttributeError(f"Function {function_name} does not exist.")

if __name__ == "__main__":
    write.console("red", "Unable to run src_scraper from raw")
    pass