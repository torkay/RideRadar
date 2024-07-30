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

            driver.get(f"https://www.gumtree.com.au/s-cars-vans-utes/{vehicle_make}/k0c18320r10?forsaleby=ownr&view=gallery")
            returned_vehicle_list = []

            # Suppress logging
            logging.getLogger('selenium').setLevel(logging.WARNING)

            try:
                # Wait until the parent element is present
                parent_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div[3]/div/div[2]/main/section/div[2]/div'))
                )
                
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
                        

                        returned_vehicle_list.append({"title": vehicle_name, "price": vehicle_price, "link": vehicle_link, "img": image_url, "location": vehicle_location, "date": time_listed, "vendor": "Gumtree"})
                    
                    except:
                        pass

                write.console("green", "\nProcessing gumtree data...")

            except:
                write.console("red", f"\nNo results for {vehicle_make.capitalize()} on gumtree...")
                        
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

            try:
                # Check if the URL has changed, indicating no results
                if driver.current_url != url:
                    write.console("red", f"\nNo results for {specific_search_clean.capitalize()} on gumtree...")
                    driver.quit()
                    return []
                print("Passed url test")

                # Wait until the parent element is present
                parent_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="react-root"]/div/div[2]/div/div[2]/main/section/div[1]/div'))
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
                write.console("red", f"\n1 No results for {specific_search_clean.capitalize()} on gumtree...")

            except NoSuchElementException as e:
                write.console("red", f"\n2 No results for {specific_search_clean.capitalize()} on gumtree...")

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