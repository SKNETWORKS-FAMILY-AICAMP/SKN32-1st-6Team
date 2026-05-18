import time
import re

from selenium import webdriver as wd
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

from webdriver_manager.chrome import ChromeDriverManager

from crawlers.kia_faq_crawler import crawl_kia_faq
from crawlers.hyundai_faq_crawler import run

def crawl_generic_faq(
    url=None,
    company_code=None,
    company_name=None,
    progress_callback=None
):

    return crawl_kia_faq(
        progress_callback=progress_callback
    )