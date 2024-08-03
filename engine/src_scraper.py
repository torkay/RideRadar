from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from utils import *
import asyncio
import logging
import platform
import re
import math
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from time import sleep

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
            self.chrome_options.add_argument("--headless")
            self.chrome_options.add_argument("--window-size=1920,1080")
            self.chrome_options.add_argument("--disable-gpu")
            self.chrome_options.add_argument("--no-sandbox")
            self.chrome_options.add_argument("--disable-dev-shm-usage")
            self.chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            self.chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
       
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
                    
                write.console("green", "\nProcessing manheim data...")
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

            driver.get(f"https://www.pickles.com.au/used/search/lob/salvage/items/{vehicle_make}?page=1")
            returned_vehicle_list = []

            try:
                WebDriverWait(driver,5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="product-search-id"]/div/div[1]'))
                )

                # Find all vehicle cards
                vehicle_cards = driver.find_elements(By.XPATH, '//*[@id="product-search-id"]/div/div')

                # Iterate over each card
                for card in vehicle_cards:
                    # Find the first direct child <a> tag within the card
                    vehicle_link = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ccg-product-card-link-")]').get_attribute("href")
                    # Find the title text within the div with class "title pb-0 text-truncate-2l"
                    vehicle_name = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ct-title-wrapper-")]/header/h2[1]/span').text
                    # Find the image URL from the "lazy-load-bg"
                    image_url = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ci-img-wrapper-")]/div/div[1]/div/div[1]/img').get_attribute("src")
                    # Append the data to the list if the link is not already present
                    returned_vehicle_list.append({"title": vehicle_name, "link": vehicle_link, "img": image_url, "vendor": "Pickles"})

                # Print a message indicating data processing
                write.console("green", "\nProcessing pickles data...")

            except Exception as e:
                write.console("red", f"\nNo results for {vehicle_make.capitalize()} on pickles...")

            driver.quit()
            return returned_vehicle_list
        

        async def search_gumtree(self):
            vehicle_make = self.vehicle_make
            write.console("cyan", f"\nSearching gumtree for {vehicle_make}...")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            url = f"https://www.gumtree.com.au/s-cars-vans-utes/{vehicle_make}/k0c18320r10?forsaleby=ownr&view=gallery"

            driver.get(url)
            returned_vehicle_list = []

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            try:
                # Check if the URL has changed, indicating no results
                if driver.current_url != url:
                    write.console("red", f"\nNo results for {vehicle_make.capitalize()} on gumtree...")
                    # print("Did not pass url test")
                    driver.quit()
                    return []
                else:
                    # print("Passed url test")
                    pass

                # sleep(15)

                # Wait until the parent element is present
                parent_element = WebDriverWait(driver, 5).until(
                    # //*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div
                    # //*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div
                    # //*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div
                    # //*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div
                    EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div[1]/div'))
                )
                print("Passed initial check")
                
                # Find all 'a' elements that are children of the parent element
                child_elements = parent_element.find_elements(By.TAG_NAME, 'a')
                
                # Iterate over each child element
                for child in child_elements:
                    try:
                        # Extract necessary information from each child element
                        vehicle_link = child.get_attribute('href')
                        aria_label = child.get_attribute('aria-label')
                        image_url = child.find_element(By.XPATH, './/img').get_attribute('src')
                        
                        # Split the aria-label to extract individual pieces of information
                        parts = aria_label.split(".")
                        vehicle_name = parts[0].strip()
                        vehicle_price = parts[1].strip().replace("Price: ", "")
                        vehicle_location = parts[2].strip().replace("Location: ", "")
                        time_listed = parts[3].strip().replace("Ad listed ", "")
                        
                        returned_vehicle_list.append({
                            "title": vehicle_name,
                            "price": vehicle_price,
                            "link": vehicle_link,
                            "img": image_url,
                            "location": vehicle_location,
                            "date": time_listed,
                            "vendor": "Gumtree"
                        })
                    except NoSuchElementException as e:
                        pass

                write.console("green", "\nProcessing gumtree data...")

            except TimeoutException as e:
                write.console("red", f"\nError 1. No results for {vehicle_make.capitalize()} on gumtree...")

            except NoSuchElementException as e:
                write.console("red", f"\nError 2. No results for {vehicle_make.capitalize()} on gumtree...")

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
                    
                write.console("green", "\nProcessing manheim data...")
            except Exception:
                write.console("red", f"\nNo results for {specific_search_clean.capitalize()} on manheim...")
                pass

            driver.quit()
    
            return returned_vehicle_list
        
        async def search_pickles(self):

            specific_search_clean = self.specific_search.upper()
            specific_search = self.specific_search.split()
            first_word = specific_search[0]
            second_word = specific_search[1] if len(specific_search) > 1 else ""
            write.console("cyan", f"\nSearching pickles for {specific_search_clean.capitalize()}...")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            driver.get(f"https://www.pickles.com.au/used/search/lob/salvage/items/{first_word}?page=1&search={second_word}")

            returned_vehicle_list = []

            try:
                WebDriverWait(driver,5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="product-search-id"]/div/div[1]'))
                )

                # Find all vehicle cards
                vehicle_cards = driver.find_elements(By.XPATH, '//*[@id="product-search-id"]/div/div')

                # Iterate over each card
                for card in vehicle_cards:
                    # Find the first direct child <a> tag within the card
                    vehicle_link = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ccg-product-card-link-")]').get_attribute("href")
                    # Find the title text within the div with class "title pb-0 text-truncate-2l"
                    vehicle_name = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ct-title-wrapper-")]/header/h2[1]/span').text
                    # Find vehicle subheading / subtitle
                    vehicle_subheading = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ct-title-wrapper-")]/header/h2[2]/span').text
                    # Find the image URL from the "lazy-load-bg"
                    image_url = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-ci-img-wrapper-")]/div/div[1]/div/div[1]/img').get_attribute("src")
                    # Find location of vehicle //*[@id="ps-cu-location-wrapper-61628702"]/p
                    vehicle_location = card.find_element(By.XPATH, './/*[starts-with(@id, "ps-cu-location-wrapper-")]/p').text
                    # Find the WOVR status
                    wovr_status = card.find_element(By.XPATH, '//*[starts-with(@id, "ps-ckf-key-features-4to6")]/div[3]/span[2]/p').text
                    # Find cylinder count //*[@id="ps-ckf-key-features-4to6-61628702"]/div[1]/span[2]/p
                    vehicle_cylinder = card.find_element(By.XPATH, '//*[starts-with(@id, "ps-ckf-key-features-4to6")]/div[1]/span[2]/p').text
                    # Find gearbox detail //*[@id="ps-ckf-key-features-4to6-61628702"]/div[2]/span[2]/p
                    vehicle_gearbox = card.find_element(By.XPATH, '//*[starts-with(@id, "ps-ckf-key-features-4to6")]/div[2]/span[2]/p').text
                    # Find vehicle kilometers (Not always valid) //*[@id="ps-ckf-key-features-1to3-61621077"]/div[1]/span[2]/p
                    try:
                        vehicle_odometer = card.find_element(By.XPATH, '//*[starts-with(@id, "ps-ckf-key-features-1to3")]/div[1]/span[2]/p').text
                    except:
                        vehicle_odometer = "N/A odometer"
                    # Find the auction date //*[@id="details-timezone-dropdown-61628702"]/div/time
                    auction_date = card.find_element(By.XPATH, '//*[starts-with(@id, "details-timezone-dropdown-")]/div/time').text
                    # Find other information (Date/KM's) //*[@id="ps-ckf-key-features-1to3-"]/div/span[2]/p
                    wovr_status = card.find_element(By.XPATH, '//*[starts-with(@id, "ps-ckf-key-features-4to6")]/div[3]/span[2]/p').text
                    # Append the data to the list if the link is not already present
                    returned_vehicle_list.append({"title": vehicle_name, "subtitle": vehicle_subheading, "link": vehicle_link, "img": image_url, "location": vehicle_location, "cylinder": vehicle_cylinder, "gearbox": vehicle_gearbox, "wovr": wovr_status, "odometer": vehicle_odometer, "date": auction_date, "vendor": "Pickles"})


                # Print a message indicating data processing
                write.console("green", "\nProcessing pickles data...")

            except Exception as e:
                write.console("red", f"\nNo results for {specific_search_clean.capitalize()} on pickles...")
                # print(e)

            driver.quit()
            return returned_vehicle_list
        
        async def search_gumtree(self):
            
            specific_search_clean = self.specific_search.lower()
            specific_search_split = specific_search_clean.split()

            write.console("cyan", f"\nSearching gumtree for {specific_search_clean.capitalize()}...")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            # Construct the URL
            if specific_search_clean[0] == 'bmw':
                carmake = f"carmake-{specific_search_split[0]}"
                carmodel = f"carmodel-{specific_search_split[0]}_{specific_search_split[1][0]}/variant-{specific_search_split[1][1:]}"
                url = f"https://www.gumtree.com.au/s-cars-vans-utes/brisbane/{carmake}/{carmodel}/c18320l3005721?forsaleby=ownr&view=gallery"
            else:
                carmake = f"carmake-{specific_search_split[0]}"
                carmodel = f"carmodel-{specific_search_split[0]}_{specific_search_split[1]}"
                url = f"https://www.gumtree.com.au/s-cars-vans-utes/brisbane/{carmake}/{carmodel}/c18320l3005721?forsaleby=ownr&view=gallery"
            
            # Fetch the page
            driver.get(url)
            
            returned_vehicle_list = []

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            # Check if the URL has changed, indicating no results
            if driver.current_url != url:
                write.console("red", f"\nNo results for {specific_search_clean.capitalize()} on gumtree...")
                # print("Did not pass url test")
                driver.quit()
                return []
            else:
                # print("Passed url test")
                pass

            print(url)

            try:
                # Wait until the parent element is present
                WebDriverWait(driver, 5).until(
                    # //*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div
                    # //*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div
                    # //*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div
                    # //*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div
                    # //*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div[1]/div
                    EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div'))
                )

                parent_element = driver.find_element(By.XPATH, '//*[@id="react-root"]/div/div[4]/div/div[2]/main/section/div/div')

                WebDriverWait(driver,5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="product-search-id"]/div/div[1]'))
                )

                # Find all 'a' elements that are children of the parent element
                child_elements = parent_element.find_elements(By.TAG_NAME, 'a')
                
                # Iterate over each child element
                for child in child_elements:
                    # Extract necessary information from each child element
                    vehicle_link = child.get_attribute('href')
                    aria_label = child.get_attribute('aria-label')
                    image_url = child.find_element(By.XPATH, './/img').get_attribute('src')
                    
                    # Split the aria-label to extract individual pieces of information
                    parts = aria_label.split(".")
                    vehicle_name = parts[0].strip()
                    vehicle_price = parts[1].strip().replace("Price: ", "")
                    vehicle_location = parts[2].strip().replace("Location: ", "")
                    time_listed = parts[3].strip().replace("Ad listed ", "")
                    
                    returned_vehicle_list.append({
                        "title": vehicle_name,
                        "price": vehicle_price,
                        "link": vehicle_link,
                        "img": image_url,
                        "location": vehicle_location,
                        "date": time_listed,
                        "vendor": "Gumtree"
                    })


                write.console("green", "\nProcessing gumtree data...")

            except TimeoutException as e:
                write.console("red", f"\nError 1. No results for {specific_search_clean.capitalize()} on gumtree...")

            except NoSuchElementException as e:
                write.console("red", f"\nError 2. No results for {specific_search_clean.capitalize()} on gumtree...")

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
            write.console("cyan", f"\nSearching gumtree for {specific_search_clean.capitalize()}...")

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)

            driver.get(f"https://www.gumtree.com.au/s-cars-vans-utes/{self.specific_search}/k0c18320r10?view=gallery")

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            # Wait for contents
            WebDriverWait(driver,5).until(
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

class mass:
    class scrape:
        ''' Asynchronous web worker initialization
        Worker -> (manheim, pickles, gumtree)
        '''

        def __init__(self, specific_search=None):
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

            # Setup ChromeDriver
            self.service = Service(ChromeDriverManager().install())

        class manheim:
            def __init__(self, parent):
                self.parent = parent

            async def assign(self):
                self.driver = webdriver.Chrome(service=self.parent.service, options=self.parent.chrome_options)

                '''
                    Discover page iterable
                '''
                try:
                    self.driver.get('https://manheim.com.au/damaged-vehicles/search?CategoryCodeDescription=Cars%20%26%20Light%20Commercial&CategoryCode=13&PageNumber=1&RecordsPerPage=120&searchType=Z&page=1')
                    # Find total listing amount element
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="result-Container"]/nav[1]/div/div[1]/span/span[2]'))
                    )
                    _yield = self.driver.find_element(By.XPATH, '//*[@id="result-Container"]/nav[1]/div/div[1]/span/span[2]').text
                    self.net_vehicles = _yield
                    _yield = int(_yield)/120
                    # Find page round count
                    self.pages = math.ceil(_yield)
                
                finally:
                    write.console("green", f"Manheim begining work on {self.pages} pages and {self.net_vehicles} vehicles.")

                '''
                    Iterate worker through listings
                '''
                try:
                    # Iterate over pages and navigate to each URL
                    for i in range(self.pages):
                        # Await first listing to load
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="result-Container"]/section/ul/li[1]'))
                        )

                        # Find all listings on the current page
                        listings = self.driver.find_elements(By.XPATH, '//*[@id="result-Container"]/section/ul/li')

                        # Use relative XPath to find the title within the current listing element
                        for index, listing in enumerate(listings):
                            try:
                                title = listing.find_element(By.XPATH, './/div[2]/div[2]/div[1]/div[1]/a/h2').text
                            except NoSuchElementException:
                                title = None

                            try:
                                location = listing.find_element(By.XPATH, f'//*[@id="result-Container"]/section/ul/li[{index + 1}]/div[2]/div[2]/div[1]/div[1]/div/span/span[3]').text
                            except NoSuchElementException:
                                location = None

                            try:
                                odometer = listing.find_element(By.XPATH, f'//*[@id="result-Container"]/section/ul/li[{index + 1}]/div[2]/div[2]/div[3]/div/div[1]/div[2]').text
                            except NoSuchElementException:
                                odometer = None

                            try:
                                transmission = listing.find_element(By.XPATH, f'//*[@id="result-Container"]/section/ul/li[{index + 1}]/div[2]/div[2]/div[3]/div/div[3]/div[2]').text
                            except NoSuchElementException:
                                transmission = None

                            try:
                                body = listing.find_element(By.XPATH, f'//*[@id="result-Container"]/section/ul/li[{index + 1}]/div[2]/div[2]/div[3]/div/div[5]/div[2]').text
                            except NoSuchElementException:
                                body = None

                            try:
                                wovr = listing.find_element(By.XPATH, f'//*[@id="result-Container"]/section/ul/li[{index + 1}]/div[2]/div[2]/div[3]/div/div[7]/div[2]').text
                            except NoSuchElementException:
                                wovr = None

                            try:
                                colour = listing.find_element(By.XPATH, f'//*[@id="result-Container"]/section/ul/li[{index + 1}]/div[2]/div[2]/div[3]/div/div[2]/div[2]').text
                            except NoSuchElementException:
                                colour = None

                            try:
                                engine = listing.find_element(By.XPATH, f'//*[@id="result-Container"]/section/ul/li[{index + 1}]/div[2]/div[2]/div[3]/div/div[4]/div[2]').text
                            except NoSuchElementException:
                                engine = None

                            try:
                                fuel = listing.find_element(By.XPATH, f'//*[@id="result-Container"]/section/ul/li[{index + 1}]/div[2]/div[2]/div[3]/div/div[6]/div[2]').text
                            except NoSuchElementException:
                                fuel = None

                            try:
                                start = listing.find_element(By.XPATH, f'//*[@id="result-Container"]/section/ul/li[{index + 1}]/div[1]/div[1]/div/p').text
                            except NoSuchElementException:
                                start = None
                                
                            # Process the gathered information
                            print(f"Title: {title}")
                            print(f"Location: {location}")
                            print(f"Odometer: {odometer}")
                            print(f"Transmission: {transmission}")
                            print(f"Body: {body}")
                            print(f"WOVR: {wovr}")
                            print(f"Colour: {colour}")
                            print(f"Engine: {engine}")
                            print(f"Fuel: {fuel}")
                            print(f"Start: {start}")
                            print("------------")

                        # Load next page
                        write.console("yellow", "Loading next page.")
                        self.driver.get(f'https://manheim.com.au/damaged-vehicles/search?CategoryCodeDescription=Cars%20%26%20Light%20Commercial&CategoryCode=13&PageNumber={i+1}&RecordsPerPage=120&searchType=P&')
                        
                except Exception as e:
                    # Print exception details if something goes wrong
                    write.console("red", f"Something went wrong: {e}")

                finally:
                    if self.driver:
                        self.driver.quit()

        class pickles:
            def __init__(self, parent):
                self.parent = parent

            async def assign(self):
                self.driver = webdriver.Chrome(service=self.parent.service, options=self.parent.chrome_options)

                '''
                    Discover page iterable
                '''
                try:
                    self.driver.get('https://www.pickles.com.au/used/search/lob/salvage/cars?page=1&limit=120&sort=titleSort+asc%2C+year+desc')
                    # Find total listing amount element
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, '//*[@id="ps-ht-search-header-container"]/header/h1'))
                    )
                    _yield = self.driver.find_element(By.XPATH, '//*[@id="ps-ht-search-header-container"]/header/h1').text
                    _yield = _yield.split()
                    self.net_vehicles = int(_yield[0].replace(',', ''))  # Ensure this is an integer
                    _yield = int(self.net_vehicles)/120
                    print(_yield, type(_yield))
                    # Find page round count
                    self.pages = math.ceil(_yield)
                    print(self.pages, self.net_vehicles)
                
                finally:
                    write.console("green", f"Pickles begining work on {self.pages} pages and {self.net_vehicles} vehicles.")
                
                '''
                    Iterate worker through listings
                '''
                try:
                    # Iterate over pages and navigate to each URL
                    for i in range(self.pages):
                        # Await first listing to load
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, '//*[@id="product-search-id"]/div/div[1]'))
                        )

                        # Find all listings on the current page
                        listings = self.driver.find_elements(By.XPATH, '//*[@id="product-search-id"]/div/div')

                        # Use relative XPath to find the title within the current listing element
                        for index, listing in enumerate(listings):
                            try:
                                title = listing.find_element(By.XPATH, './/*[starts-with(@id, "ps-ct-title-wrapper-")]/header/h2[1]/span').text
                            except NoSuchElementException:
                                title = None

                            try:
                                subtitle = listing.find_element(By.XPATH, './/*[starts-with(@id, "ps-ct-title-wrapper-")]/header/h2[2]/span').text
                            except NoSuchElementException:
                                subtitle = None

                            try:
                                odometer = listing.find_element(By.XPATH, './/*[starts-with(@id, "ps-ckf-key-features-1to3")]/div[1]/span[2]/p').text
                            except NoSuchElementException:
                                odometer = None
                            
                            try:
                                engine = listing.find_element(By.XPATH, './/*[starts-with(@id, "ps-ckf-key-features-4to6")]/div[1]/span[2]/p').text
                            except NoSuchElementException:
                                engine = None

                            try:
                                transmission = listing.find_element(By.XPATH, '//*[starts-with(@id, "ps-ckf-key-features-4to6")]/div[2]/span[2]/p').text
                            except NoSuchElementException:
                                transmission = None

                            try:
                                wovr = listing.find_element(By.XPATH, './/*[starts-with(@id, "ps-ckf-key-features-4to6")]/div[3]/span[2]/p').text
                            except NoSuchElementException:
                                wovr = None

                            try:
                                location = listing.find_element(By.XPATH, './/*[starts-with(@id, "ps-cu-location-wrapper-")]/p').text
                            except NoSuchElementException:
                                location = None

                            try:
                                time = listing.find_element(By.XPATH, './/*[starts-with(@id, "details-timezone-dropdown-")]/div/time').text
                            except NoSuchElementException:
                                time = None

                            # Process the gathered information
                            print(f"Title: {title}")
                            print(f"Subtitle: {subtitle}")
                            print(f"Odometer: {odometer}")
                            print(f"Engine: {engine}")
                            print(f"Transmission: {transmission}")
                            print(f"WOVR: {wovr}")
                            print(f"Location: {location}")
                            print(f"Time: {time}")
                            print("------------")

                            
                            # Load next page
                        write.console("yellow", "Loading next page.")
                        self.driver.get(f'https://www.pickles.com.au/used/search/lob/salvage/cars?page={i+1}&limit=120&sort=titleSort+asc%2C+year+desc')
                            
                except:
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
    write.console("red", "Unable to run src_scraper from source")
    pass