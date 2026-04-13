from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .logging_utils import logger


class TerminalChecker:
    def __init__(self, username: str = None, password: str = None, headless: bool = True):
        self.username = username
        self.password = password
        self.driver = None
        self.setup_driver(headless=headless)

    def setup_driver(self, headless: bool = True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-popup-blocking")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--log-level=3")
            chrome_options.add_argument("--disable-images")
            chrome_options.add_argument("--blink-settings=imagesEnabled=false")
            chrome_options.add_argument("--disable-javascript")
            chrome_options.add_argument("--disable-css-animations")
            chrome_options.add_argument("--disable-web-security")
            chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
            chrome_options.page_load_strategy = "eager"

        self.driver = webdriver.Chrome(options=chrome_options)

    def wait_for_element(self, by, value, timeout=2, condition=EC.presence_of_element_located):
        try:
            return WebDriverWait(self.driver, timeout).until(condition((by, value)))
        except TimeoutException:
            return None

    def wait_for_elements(self, by, value, timeout=2, condition=EC.presence_of_all_elements_located):
        try:
            return WebDriverWait(self.driver, timeout).until(condition((by, value)))
        except TimeoutException:
            return []

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception as exc:
                logger.error(f"Error closing WebDriver: {exc}")
            finally:
                self.driver = None

    def check_containers(self, container_numbers: list[str]):
        raise NotImplementedError("Subclasses must implement check_containers()")
