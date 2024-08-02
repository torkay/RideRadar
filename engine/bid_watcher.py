from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils import *
import asyncio

class watch:
    class bid:
        def __init__(self, vehicle, headless=None):
            # Set the vehicle make
            self.vehicle = vehicle

            # Set Chrome options for headless mode and suppress logging
            self.chrome_options = Options()
            if headless:
                self.chrome_options.add_argument("--headless")  # Enable headless mode
                self.chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration (needed for headless mode)
                self.chrome_options.add_argument("--log-level=3")  # Suppress logging

            self.chromedriver_path = None # Pass as None-Type, arg will be determined via utils, no longer here

            # Here, await the execution of the async method
            return await self.stalk_address()

        async def add_bot():
            test = watch.bid("https://manheim.com.au/damaged-vehicles/6916204/2017-bmw-m4-f82-coupe-coup%C3%A9?referringPage=SearchResults")
            print(test)

        async def stalk_address(self):

            # Initialize Chrome WebDriver with the configured options
            service = Service(executable_path=self.chromedriver_path)
            write.console("cyan", f"\nPinging the bot watching the auction...")

            write.line()
            driver = create.create_webdriver(service=service, chrome_options=self.chrome_options)
            write.line(1)
            
            # Vendor and validity fundamentals
            if "manheim" in self.vehicle:
                self.vendor = "manheim"
            elif "pickles" in self.vehicle:
                self.vendor = "pickles"
            else:
                return

            driver.get(self.vehicle) # Follow address

            if self.vendor == "manheim":
                WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "bidnow-content-section"))
                    )
                auction_content = driver.find_element(By.CLASS_NAME, "bidnow-content-section")
                
                def vehicle_name():
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    vehicle_heading_element = soup.select_one('.vdp-heading.vehicle')
                    if vehicle_heading_element:
                        return(vehicle_heading_element.text.strip())
                    else:
                        return("Vehicle heading element not found")
                    
                def vehicle_image():
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "bidnow-content-section"))
                    )
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    img_element = soup.select_one('img.owl-lazy')
                    if img_element:
                        image_src = img_element.get('data-src')
                        return(image_src)
                    else:
                        return("Image element not found")

                def time_left():
                    # Time left on auction
                    WebDriverWait(driver, 10).until(
                        EC.visibility_of_element_located((By.XPATH, './/div/p[2]'))
                    )
                    time_element = auction_content.find_element(By.XPATH, './/div/p[2]')
                    auction_end_date = time_element.get_attribute("data-countdown")
                    auction_end_date = datetime.strptime(auction_end_date, "%Y-%m-%d %H:%M:%S")

                    current_time = datetime.now()
                    remaining_auction_time = auction_end_date - current_time
                    days = remaining_auction_time.days
                    hours, remainder = divmod(remaining_auction_time.seconds, 3600)
                    minutes, seconds = divmod(remainder, 60)
                
                    time_remaining = "" # Construct a coherent string representing the time remaining
                    if days > 0:
                        time_remaining += f"{days}d "
                    if hours > 0:
                        time_remaining += f"{hours}h "
                    if minutes > 0:
                        time_remaining += f"{minutes}m "
                    if seconds > 0:
                        time_remaining += f"{seconds}s "

                    return(f"Time remaining: {time_remaining}")

                def bid_increment():
                    WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "bidnow-content-section"))
                    )
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    increment_element = soup.select_one('.bidnow-content-section div:nth-of-type(2) p:nth-of-type(2)')
                    if increment_element:
                        return(increment_element.text.strip())
                    else:
                        return("Increment element not found")
                
                def bid_history():
                    return None #TODO: this is broken and needs to have a signed in client
                    # WebDriverWait(driver, 10).until(
                    #     EC.presence_of_element_located((By.XPATH, ".//div[3]/a"))
                    # )
                    # history_element = auction_content.find_element(By.XPATH, './/div[3]/a').text
                    # return history_element

                def current_bid():
                    WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "bidnow-content-section"))
                    )
                    page_source = driver.page_source
                    soup = BeautifulSoup(page_source, 'html.parser')
                    current_bid_element = soup.select_one('.bidnow-content-section div:nth-of-type(3) div:nth-of-type(2) div p:nth-of-type(2)')
                    if current_bid_element:
                        return(current_bid_element.text.strip())
                    else:
                        return("Current bid element not found")

                return vehicle_name, vehicle_image, time_left, bid_increment, bid_history, current_bid
            
            if self.vendor == "pickle":
                pass

asyncio.run(watch.bid.add_bot())
