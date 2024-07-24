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
            
            # Set Chrome options for headless mode and suppress logging
            self.chrome_options = Options()
            self.chrome_options.add_argument("--headless")  # Enable headless mode
            self.chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration (needed for headless mode)
            self.chrome_options.add_argument("--log-level=3")  # Suppress logging

       
            self.chromedriver_path = None # Pass as None-Type, arg will be determined via utils, no longer here


        async def search_manheim(self):

            vehicle_make = self.vehicle_make
            
            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)
            write.console("cyan", f"\nSearching manheim for {vehicle_make}...")

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            driver.get(f"https://manheim.com.au/damaged-vehicles/search?refineName=ManufacturerCode&ManufacturerCode={vehicle_make.upper()}&ManufacturerCodeDescription={vehicle_make.capitalize()}")

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            # Wait for contents
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.TAG_NAME, "label"))
            )

            returned_vehicle_list = []

            # Save title of each vehicle
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "vehicle-card"))
                )
                vehicle_cards = driver.find_elements(By.CLASS_NAME, "vehicle-card")
                for card in vehicle_cards:
                    # Main details
                    vehicle_name = card.find_element(By.XPATH, ".//a/h2").text
                    # print(vehicle_name)
                    vehicle_link = card.find_element(By.XPATH, ".//a").get_attribute("href")
                    # print(vehicle_link)
                    vehicle_img = card.find_element(By.XPATH, "./div/div/div/div/div/div/img").get_attribute("src")
                    # print(vehicle_img)

                    returned_vehicle_list.append({"title": vehicle_name, "link": vehicle_link, "img": vehicle_img, "vendor": "Manheim"})
                    
                write.console("yellow", "\nProcessing manheim data...")
            except Exception:
                write.console("red", f"\nNo results for {vehicle_make} on manheim...")
                pass

            driver.quit()
    
            return returned_vehicle_list



        async def search_pickles(self):

            vehicle_make = self.vehicle_make
            write.console("cyan", f"\nSearching pickles for {vehicle_make}")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            driver.get(f"https://www.pickles.com.au/damaged-salvage/item/search#!/search-result?q=(And.ProductType.Vehicles._.Make.{vehicle_make}.)")

            returned_vehicle_list = []

            try:
                WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@ng-repeat='resultItem in searchResults']//a"))
                    )
                
                # Find all cards
                vehicle_cards = driver.find_elements(By.XPATH, "//div[@ng-repeat='resultItem in searchResults']")

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
                write.console("yellow", "\nProcessing pickles data...")

            except Exception:
                write.console("red", f"\nNo results for {vehicle_make} on pickles...")
                pass

            driver.quit()
            return returned_vehicle_list
        
        async def search_gumtree(self):
            vehicle_make = self.vehicle_make
            write.console("cyan", f"\nSearching gumtree for {vehicle_make}")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            driver.get(f"https://www.gumtree.com.au/s-cars-vans-utes/{specific_search}/k0c18320r10?view=gallery")

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            # Wait for contents
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div[3]/div/div[2]/main/section/div[1]/div'))
            )

            vehicle_cards = driver.find_elements(By.XPATH, '//*[@id="react-root"]/div/div[3]/div/div[2]/main/section/div[1]/div/a')
            vehicle_names = []
            returned_vehicle_list = []
    
            for vehicle in vehicle_cards:
                try:
                    vehicle_text = vehicle.get_attribute('aria-label')

                    # Information extrapolation
                    lines = vehicle_text.strip().split('\n')
                    vehicle_name = lines[0].strip()
                    vehicle_price = lines[1].strip().split(': ')[1].replace(' .', '')
                    vehicle_location = lines[2].strip().split(': ')[1].replace('. Ad listed Yesterday.', '')
                    vehicle_list_date = lines[2].strip().split('. Ad listed ')[1].replace('.', '')
                    vehicle_link = vehicle.get_attribute("href")
                    image_url = vehicle.find_element((By.XPATH, '//*[@id="user-ad-1326229396"]/div[1]/div/div/div[1]/div/div[1]/img')).get_attribute("src")

                    returned_vehicle_list.append({"title": vehicle_name, "link": vehicle_link, "price": vehicle_price, "img": image_url, "location": vehicle_location, "listed": vehicle_list_date, "vendor": "Gumtree"})
                    

                except Exception as e:
                    print(f"Error extracting aria-label: {e}")
                    vehicle_names.append('Error extracting aria-label')

            driver.quit()

            return returned_vehicle_list
        
        async def search_by_brand(self):
            vehicle_make = self.vehicle_make

            try:
                manheim_task = asyncio.create_task(self.search_manheim())
            except NoSearchResultsException:
                write.console("red", f"No search results on Manheim for {vehicle_make}")
                return await self.search_pickles()
            
            try:
                pickles_task = asyncio.create_task(self.search_pickles())
            except NoSearchResultsException:
                write.console("red", f"No search results on Pickles for {vehicle_make}")
                pass

            # try:
            #     gumtree_task = asyncio.create_task(self.search_gumtree())
            # except NoSearchResultsException:
            #     write.console("red", f"No search results on Gumtree for {vehicle_make}")
            #     pass

            manheim_result = await manheim_task
            pickles_result = await pickles_task
            # gumtree_results = await gumtree_task

            return manheim_result + pickles_result
        
    class specific:
        def __init__(self, specific_search):
            # Set the vehicle make
            self.specific_search = specific_search
            
            # Set Chrome options for headless mode and suppress logging
            self.chrome_options = Options()
            self.chrome_options.add_argument("--headless")
            self.chrome_options.add_argument("--window-size=1920,1080")
            self.chrome_options.add_argument("--disable-gpu")
            self.chrome_options.add_argument("--no-sandbox")
            self.chrome_options.add_argument("--disable-dev-shm-usage")
            self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            self.chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

            self.chromedriver_path = None # Pass as None-Type, arg will be determined via utils, no longer here


        async def search_manheim(self):
            specific_search_clean = self.specific_search.upper()
            specific_search = self.specific_search.replace(" ", "+")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)
            write.console("cyan", f"\nSearching manheim for {specific_search_clean.capitalize()}...")

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            driver.get(f"https://manheim.com.au/damaged-vehicles/search?ManufacturerDescription=&FamilyCodeDescription=&CategoryCodeDescription=&StateDescription=&State=&ItemLocationDescription=&Keywords={specific_search}&CategoryCode=")

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            # Wait for contents
            WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.TAG_NAME, "label"))
            )

            returned_vehicle_list = []

            # Save title of each vehicle
            try:
                WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "vehicle-card"))
                )
                vehicle_cards = driver.find_elements(By.CLASS_NAME, "vehicle-card")
                for card in vehicle_cards:
                    # Main details
                    vehicle_name = card.find_element(By.XPATH, ".//a/h2").text
                    # print(vehicle_name)
                    vehicle_link = card.find_element(By.XPATH, ".//a").get_attribute("href")
                    # print(vehicle_link)
                    vehicle_img = card.find_element(By.XPATH, "./div/div/div/div/div/div/img").get_attribute("src")
                    # print(vehicle_img)

                    returned_vehicle_list.append({"title": vehicle_name, "link": vehicle_link, "img": vehicle_img, "vendor": "Manheim"})
                    
                write.console("yellow", "\nProcessing manheim data...")
            except Exception:
                write.console("red", f"\nNo results for {specific_search_clean.capitalize()} on manheim...")
                pass

            driver.quit()
    
            return returned_vehicle_list
        
        async def search_pickles(self):

            specific_search_clean = self.specific_search.upper()
            specific_search = self.specific_search.replace(" ", "%20")
            write.console("cyan", f"\nSearching pickles for {specific_search_clean.capitalize()}")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            driver.get(f"https://www.pickles.com.au/damaged-salvage/item/search#!/search-result?q=(And.ProductType.Vehicles._.All.keyword({specific_search}).)")

            returned_vehicle_list = []

            try:
                WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH, "//div[@ng-repeat='resultItem in searchResults']//a"))
                    )
                
                # Find all cards
                vehicle_cards = driver.find_elements(By.XPATH, "//div[@ng-repeat='resultItem in searchResults']")

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
                write.console("yellow", "\nProcessing pickles data...")

            except Exception:
                write.console("red", f"\nNo results for {specific_search_clean.capitalize()} on pickles...")
                pass

            driver.quit()
            return returned_vehicle_list
        
        async def search_gumtree(self):
            specific_search_clean = self.specific_search.lower()
            specific_search = self.specific_search.replace(" ", "+")
            write.console("cyan", f"\nSearching gumtree for {specific_search_clean.capitalize()}")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            driver.get(f"https://www.gumtree.com.au/s-cars-vans-utes/{specific_search}/k0c18320r10?view=gallery")

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            # Wait for contents
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div[3]/div/div[2]/main/section/div[1]/div'))
            )

            vehicle_cards = driver.find_elements(By.XPATH, '//*[@id="react-root"]/div/div[3]/div/div[2]/main/section/div[1]/div/a')
            vehicle_names = []
            returned_vehicle_list = []
    
            for vehicle in vehicle_cards:
                try:
                    vehicle_text = vehicle.get_attribute('aria-label')

                    # Information extrapolation
                    lines = vehicle_text.strip().split('\n')
                    vehicle_name = lines[0].strip()
                    vehicle_price = lines[1].strip().split(': ')[1].replace(' .', '')
                    vehicle_location = lines[2].strip().split(': ')[1].replace('. Ad listed Yesterday.', '')
                    vehicle_list_date = lines[2].strip().split('. Ad listed ')[1].replace('.', '')
                    vehicle_link = vehicle.get_attribute("href")
                    image_url = vehicle.find_element((By.XPATH, '//*[@id="user-ad-1326229396"]/div[1]/div/div/div[1]/div/div[1]/img')).get_attribute("src")

                    returned_vehicle_list.append({"title": vehicle_name, "link": vehicle_link, "price": vehicle_price, "img": image_url, "location": vehicle_location, "listed": vehicle_list_date, "vendor": "Gumtree"})
                    

                except Exception as e:
                    print(f"Error extracting aria-label: {e}")
                    vehicle_names.append('Error extracting aria-label')

            driver.quit()

            return returned_vehicle_list

        async def search_autotrader(self):
            specific_search_clean = self.specific_search.lower()
            try:
                if " " not in self.specific_search:
                    # TODO: raise exceptions (no multi-layerd title requests)
                    return None
                else:
                    raise Exception
            except Exception as e:
                pass
            write.console("cyan", f"\nSearching gumtree for {specific_search_clean.capitalize()}")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            driver.get(f"https://www.gumtree.com.au/s-cars-vans-utes/{self.specific_search}/k0c18320r10?view=gallery")

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            # Wait for contents
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div[3]/div/div[2]/main/section/div[1]/div'))
            )

            vehicle_cards = driver.find_elements(By.XPATH, '//*[@id="react-root"]/div/div[3]/div/div[2]/main/section/div[1]/div/a')
            vehicle_names = []
            returned_vehicle_list = []
    
            for vehicle in vehicle_cards:
                try:
                    vehicle_text = vehicle.get_attribute('aria-label')

                    # Information extrapolation
                    lines = vehicle_text.strip().split('\n')
                    vehicle_name = lines[0].strip()
                    vehicle_price = lines[1].strip().split(': ')[1].replace(' .', '')
                    vehicle_location = lines[2].strip().split(': ')[1].replace('. Ad listed Yesterday.', '')
                    vehicle_list_date = lines[2].strip().split('. Ad listed ')[1].replace('.', '')
                    vehicle_link = vehicle.get_attribute("href")
                    image_url = vehicle.find_element((By.XPATH, '//*[@id="user-ad-1326229396"]/div[1]/div/div/div[1]/div/div[1]/img')).get_attribute("src")

                    returned_vehicle_list.append({"title": vehicle_name, "link": vehicle_link, "price": vehicle_price, "img": image_url, "location": vehicle_location, "listed": vehicle_list_date, "vendor": "Gumtree"})
                    

                except Exception as e:
                    # print(f"Error extracting aria-label: {e}")
                    # vehicle_names.append('Error extracting aria-label')
                    pass

            driver.quit()

            return returned_vehicle_list

        async def search_by_specific(self):
            specific_search = self.specific_search

            try:
                manheim_task = asyncio.create_task(self.search_manheim())
            except NoSearchResultsException:
                write.console("red", f"No search results on Manheim for {specific_search}")
                return await self.search_pickles()
            
            try:
                pickles_task = asyncio.create_task(self.search_pickles())
            except NoSearchResultsException:
                write.console("red", f"No search results on Pickles for {specific_search}")
                pass
            
            try:
                gumtree_task = asyncio.create_task(self.search_gumtree())
            except NoSearchResultsException:
                write.console("red", f"No search results on Gumtree for {specific_search}")
                pass

            manheim_result = await manheim_task
            pickles_result = await pickles_task
            gumtree_result = await gumtree_task

            return manheim_result + pickles_result + gumtree_result
                
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