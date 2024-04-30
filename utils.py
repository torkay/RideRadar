from colorama import init, Fore, Style
import logging
import os
import shutil
import requests
import zipfile
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.common.exceptions import SessionNotCreatedException

class write:
    def console(color, text: str):
        colors = {
            'black': '\033[30m',
            'red': '\033[31m',
            'green': '\033[32m',
            'yellow': '\033[33m',
            'blue': '\033[34m',
            'magenta': '\033[35m',
            'cyan': '\033[36m',
            'white': '\033[37m',
            'reset': '\033[0m'
        }
        
        if color.lower() in colors:
            color_code = colors[color.lower()]
            reset_code = colors['reset']
            print(color_code + text + reset_code)
        else:
            logging.error("Error occured during coloring console: Invalid Color")

class create:
    @staticmethod
    def create_webdriver(service, chrome_options):
        while True:
            try:
                driver = webdriver.Chrome(service=service, options=chrome_options)
                return driver
            except SessionNotCreatedException as e:
                write.console("yellow", f"Chromedriver is outdated. Initiating update...")
                update = update_chromedriver("https://googlechromelabs.github.io/chrome-for-testing/#stable")
                update.find_installation()
                # After attempting to update, retry creating the WebDriver

class update_chromedriver:

    def __init__(self, url):
        self.url = url
    
    def find_installation(self):
        # Send HTTP request to the URL
        response = requests.get(self.url)
        if response.status_code != 200:
            logging("Failed to retrieve the webpage.")
            return
        
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find all <tbody> elements
        tbody_elements = soup.find_all('tbody')
        
        # Flag to control loop
        update_completed = False
        
        # Iterate over <tbody> elements
        for tbody in tbody_elements:
            # Find all <tr> elements with class "status-ok"
            tr_elements = tbody.find_all('tr', class_='status-ok')
            
            # Iterate over <tr> elements
            for tr in tr_elements:
                # Find all <th> elements
                th_elements = tr.find_all('th')

                # Check if the second <th> element contains a <code> element with text "win64"
                if len(th_elements) >= 2 and th_elements[1].find('code') and th_elements[1].find('code').text.strip() == "win64" and th_elements[0].find('code').text.strip() == "chromedriver":
                    #write.console("red", f"code yielded: {th_elements[1].find('code').text.strip()}")
                    
                    # Find the common ancestor of the <th> and <td> elements
                    common_ancestor = th_elements[1].find_parent('tr')

                    # Find the <td> element containing the download link within the common ancestor
                    td_download_link = common_ancestor.find('td')
                    if td_download_link:
                        # Check if the <td> element contains a <code> element
                        code_element = td_download_link.find('code')
                        if code_element:
                            download_link = code_element.text.strip()
                            
                            # Download the file
                            write.console("yellow", f"Installing latest version of chromedriver...")
                            self.download_update(download_link)
                            
                            # Update completed
                            update_completed = True
                            break  # Exit the loop if download successful

            if update_completed:
                break
                        
    def download_update(self, url):
        # Define the directory to store the downloaded file
        directory = os.path.dirname(os.path.realpath(__file__))
        
        # Define the filename (extracted from the URL)
        filename = url.split('/')[-1]
        
        # Define the filepath
        filepath = os.path.join(directory, filename)
        
        # Download the file
        with requests.get(url, stream=True) as r:
            with open(filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        
        write.console("yellow", f"Chromedriver update downloaded successfully: '{filename}'")
        
        # Unzip the file
        with zipfile.ZipFile(filepath, 'r') as zip_ref:
            # Extract all contents to the same directory
            zip_ref.extractall(directory)
        
        # Delete the zip file after extraction
        os.remove(filepath)
        
        # Rename the extracted file to 'chromedriver.exe'
        extracted_filepath = os.path.join(directory, filename.replace('.zip', ''))
        renamed_filepath = os.path.join(directory, 'chromedriver.exe')
        
        write.console("green", "Chromedriver update installed successfully.")

        # If there's an existing chromedriver.exe, remove it before replacing
        existing_chromedriver = os.path.join(directory, 'chromedriver.exe')
        if os.path.exists(existing_chromedriver):
            os.remove(existing_chromedriver)
            write.console("green", "Existing chromedriver removed.")

        os.rename(extracted_filepath, renamed_filepath)

        write.console("green", "Updated chromedriver installed.")



# Example usage:
#print_colored_text('red', 'This text is red.')
#print_colored_text('blue', 'This text is blue.') 
