from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from .base import TerminalChecker
from .logging_utils import logger
from .models import ContainerStatus


class TideworksChecker(TerminalChecker):
    def __init__(self, username, password, terminal_name, base_url, headless=True):
        self.username = username
        self.password = password
        self.driver = None
        self.setup_driver(headless)
        self.base_url = base_url
        self.terminal_name = terminal_name

    def login(self):
        try:
            self.driver.get(self.base_url)
            try:
                WebDriverWait(self.driver, 1).until(EC.presence_of_element_located((By.ID, "j_username")))
                self.driver.find_element(By.ID, "j_username").send_keys(self.username)
                self.driver.find_element(By.ID, "j_password").send_keys(self.password)
                self.driver.find_element(By.ID, "signIn").click()

                error_elements = WebDriverWait(self.driver, 1).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//*[contains(text(), 'Invalid username or password')]"))
                )
                if error_elements:
                    logger.error("Login failed: Invalid username or password")
                    return False
            except TimeoutException:
                pass  # already logged in or no login form

            return True
        except Exception as exc:
            logger.error(f"Error during login: {exc}")
            return False

    def check_containers(self, container_numbers):
        results = []
        try:
            if not self.login():
                logger.error(f"Failed to login to {self.terminal_name}")
                return [ContainerStatus(c, terminal="LOGIN FAILED") for c in container_numbers]

            try:
                WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Close')]"))
                ).click()
            except TimeoutException:
                pass

            menu_button = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.ID, "menu-import")))
            menu_button.click()

            container_input = WebDriverWait(self.driver, 3).until(EC.presence_of_element_located((By.ID, "numbers")))
            container_input.clear()
            container_input.send_keys("\n".join(container_numbers))

            WebDriverWait(self.driver, 2).until(EC.element_to_be_clickable((By.ID, "search"))).click()

            WebDriverWait(self.driver, 2).until(EC.presence_of_element_located((By.ID, "result")))
            table = WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//div[@id='result']//table"))
            )

            rows = table.find_elements(By.TAG_NAME, "tr")[1:]
            for row in rows:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) == 1 and "could not be found" in cols[0].text:
                        container = cols[0].text.split()[0].strip()
                        results.append(ContainerStatus(container, terminal="NOT FOUND"))
                        continue

                    if len(cols) >= 4:
                        container = cols[0].text.strip()
                        available = cols[1].text.strip()
                        dimensions = cols[2].text.strip()
                        holds_text = cols[3].text.strip()

                        customs_hold = line_hold = cbpa_hold = terminal_hold = ""
                        hold_parts = [p.strip() for p in holds_text.replace("\n", ";").split(";") if p.strip()]
                        for part in hold_parts:
                            value = part.split(":")[-1].strip() if ":" in part else part
                            if "Cust" in part:
                                customs_hold = value
                            elif "Line" in part:
                                line_hold = value
                            elif "Add" in part:
                                cbpa_hold = value
                            elif "Holds" in part:
                                terminal_hold = value

                        fees_parts = []
                        if terminal_hold:
                            fees_parts.append(terminal_hold)
                        for part in hold_parts:
                            if "Total Fees:" in part:
                                fees_parts.append(part.strip())
                            elif "Satisfied Thru:" in part:
                                fees_parts.append(part.strip())
                        if len(fees_parts) > 1:
                            terminal_hold = " | ".join(fees_parts)

                        additional_info = cols[4].text.strip() if len(cols) > 4 else ""
                        location = additional_info.split("|")[0].strip() if "|" in additional_info else additional_info
                        line_operator = additional_info.split("|")[1].strip() if "|" in additional_info else ""

                        results.append(
                            ContainerStatus(
                                container,
                                terminal=self.terminal_name,
                                available=available,
                                line_operator=line_operator,
                                dimensions=dimensions,
                                customs_hold=customs_hold,
                                line_hold=line_hold,
                                cbpa_hold=cbpa_hold,
                                terminal_hold=terminal_hold,
                                location=location,
                            )
                        )
                except Exception as exc:
                    logger.error(f"Error processing row: {exc}")
        except Exception as exc:
            logger.error(f"Error checking containers at {self.terminal_name}: {exc}")

        found_containers = {r.container_number for r in results}
        for container in container_numbers:
            if container not in found_containers:
                results.append(ContainerStatus(container, terminal="NOT FOUND"))

        return results
