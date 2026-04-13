import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from .base import TerminalChecker
from .logging_utils import logger
from .models import ContainerStatus


class TrapacChecker(TerminalChecker):
    def __init__(self):
        self.username = None
        self.password = None
        self.driver = None
        self.setup_driver(headless=False)
        self.base_url = "https://oakland.trapac.com/quick-check/?terminal=OAK&transaction=availability"
        self.terminal_name = "Trapac"

    def _dismiss_modal(self):
        selectors = [
            ("css", "button.close"),
            ("xpath", "//button[contains(text(), 'Close')]"),
            ("xpath", "//button[@class='close']"),
            ("xpath", "//button[@aria-label='Close']"),
        ]
        for kind, selector in selectors:
            by = By.CSS_SELECTOR if kind == "css" else By.XPATH
            btn = self.wait_for_element(by, selector, timeout=1, condition=EC.element_to_be_clickable)
            if btn:
                btn.click()
                return

    def _wait_for_captcha_results(self):
        logger.warning("reCAPTCHA required. Complete verification in the browser window, then click Check.")
        print("\nreCAPTCHA verification required for Trapac.")
        print("Complete the verification in the browser, then click the Check button.")
        print("The script will continue automatically once results appear (5 min timeout).")

        deadline = time.time() + 300
        while time.time() < deadline:
            table = self.wait_for_element(
                By.XPATH, "//div[@class='transaction-result availability']//table", timeout=1
            )
            if table:
                return
            remaining = int(deadline - time.time())
            if remaining % 30 == 0:
                logger.info(f"Still waiting for reCAPTCHA results... ({remaining}s remaining)")
            time.sleep(1)

        raise TimeoutException("Timeout waiting for results after reCAPTCHA verification")

    def _check_recaptcha(self):
        recaptcha_selectors = [
            "//iframe[contains(@src, 'recaptcha')]",
            "//div[@class='g-recaptcha']",
            "//div[contains(@class, 'recaptcha')]",
            "//div[@id='recaptcha-backup']",
        ]
        for selector in recaptcha_selectors:
            for element in self.driver.find_elements(By.XPATH, selector):
                try:
                    if element.is_displayed():
                        return True
                except Exception:
                    continue
        return False

    def _parse_batch(self, batch):
        results = []

        self.driver.get(self.base_url)
        time.sleep(2)
        self._dismiss_modal()

        container_input = self.wait_for_element(By.NAME, "containers", timeout=1)
        if not container_input:
            raise RuntimeError("Container input field not found")
        container_input.clear()
        container_input.send_keys("\n".join(batch))
        time.sleep(5)

        submit_button = self.wait_for_element(
            By.XPATH, "//div[@class='submit']/button", timeout=1, condition=EC.element_to_be_clickable
        )
        if not submit_button:
            raise RuntimeError("Submit button not found")
        submit_button.click()
        time.sleep(5)

        if self._check_recaptcha():
            self._wait_for_captcha_results()

        table = self.wait_for_element(By.XPATH, "//div[@class='table-scroll']//table", timeout=2)
        if not table:
            no_results = self.wait_for_elements(By.XPATH, "//*[contains(text(), 'No result found')]", timeout=1)
            if no_results:
                return [ContainerStatus(c, terminal="NOT FOUND") for c in batch]
            raise RuntimeError("Results table not found")

        tbody = table.find_element(By.TAG_NAME, "tbody")
        for row in tbody.find_elements(By.TAG_NAME, "tr"):
            try:
                row_class = row.get_attribute("class")
                cols = row.find_elements(By.TAG_NAME, "td")

                if row_class == "error-row":
                    if cols:
                        message_text = cols[0].text.strip()
                        if "No result found for the reference number:" in message_text or "is not an Inbound Container" in message_text:
                            try:
                                container = message_text.split(":")[1].strip()
                            except IndexError:
                                container = message_text.split()[0].strip()
                            results.append(ContainerStatus(container, terminal="NOT FOUND"))
                    continue

                if row_class == "row-odd" and len(cols) >= 9:
                    container = cols[1].text.strip()
                    location = cols[7].text.strip()
                    customs_hold = cols[4].text.strip()
                    line_hold = cols[3].text.strip()
                    cbpa_hold = cols[5].text.strip()
                    terminal_hold = cols[6].text.strip()

                    if "Delivered" in location:
                        available = "Delivered"
                    elif (
                        (not customs_hold or customs_hold.lower() == "released")
                        and (not line_hold or line_hold.lower() == "released")
                        and (not cbpa_hold or cbpa_hold.lower() == "released")
                        and (not terminal_hold or terminal_hold.lower() == "none")
                    ):
                        available = "Available"
                    else:
                        available = ""

                    results.append(
                        ContainerStatus(
                            container,
                            terminal=self.terminal_name,
                            available=available,
                            line_operator=cols[2].text.strip(),
                            dimensions=cols[8].text.strip(),
                            customs_hold=customs_hold,
                            line_hold=line_hold,
                            cbpa_hold=cbpa_hold,
                            terminal_hold=terminal_hold,
                            location=location,
                        )
                    )
            except Exception as exc:
                logger.error(f"Error processing row: {exc}")

        return results

    def check_containers(self, container_numbers):
        results = []
        batch_size = 10
        try:
            for i in range(0, len(container_numbers), batch_size):
                batch = container_numbers[i: i + batch_size]
                results.extend(self._parse_batch(batch))
        except Exception as exc:
            logger.error(f"Error checking containers at Trapac: {exc}")

        found_containers = {r.container_number for r in results}
        for container in container_numbers:
            if container not in found_containers:
                results.append(ContainerStatus(container, terminal="NOT FOUND"))

        return results
