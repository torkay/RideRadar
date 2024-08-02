from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
from utils import *
from bs4 import BeautifulSoup
import asyncio
import logging
import platform
import re
import tracemalloc

class bot:
    """ Velocicast is the online auction service used by pickles to host their bidding sessions """
# https://www.pickles.com.au/trucks/pickles-live/registration?p_p_id=PicklesLiveRegistrationPortlet_WAR_PWRWeb&p_p_lifecycle=1&p_p_state=normal&saleId=7011