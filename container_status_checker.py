#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import warnings
import logging
import sys
import json
import pandas as pd
from tabulate import tabulate
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementNotInteractableException
from selenium.webdriver.common.action_chains import ActionChains
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import argparse
from urllib.parse import urlencode
from selenium.webdriver.support.select import Select
from selenium.webdriver.chrome.options import Options
import os
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Suppress selenium and urllib3 logging
selenium_logger = logging.getLogger('selenium')
selenium_logger.setLevel(logging.ERROR)
urllib3_logger = logging.getLogger('urllib3')
urllib3_logger.setLevel(logging.ERROR)

# Suppress all urllib3 warnings
with warnings.catch_warnings():
    warnings.simplefilter('ignore')
    warnings.filterwarnings('ignore', category=Warning)

@dataclass
class ContainerStatus:
    container_number: str
    terminal: Optional[str] = None
    available: Optional[str] = None
    line_operator: Optional[str] = None
    dimensions: Optional[str] = None
    customs_hold: Optional[str] = None
    line_hold: Optional[str] = None
    cbpa_hold: Optional[str] = None
    terminal_hold: Optional[str] = None
    location: Optional[str] = None

class TerminalChecker:
    def __init__(self, username: str = None, password: str = None, headless: bool = True):
        self.username = username
        self.password = password
        self.driver = None
        self.setup_driver(headless=headless)
        
    def setup_driver(self, headless=True):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
            # Performance optimizations for headless mode
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.page_load_strategy = 'eager'  # Don't wait for all resources to load
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.set_page_load_timeout(30)  # Set page load timeout
        self.driver.implicitly_wait(5)  # Reduce implicit wait time
        
    def close(self):
        """Close the WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing WebDriver: {str(e)}")
                
    def __del__(self):
        if self.driver:
            self.driver.quit()
        
    def check_containers(self, container_numbers: List[str]) -> Dict[str, ContainerStatus]:
        """Check container status. To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement check_containers()")

class TrapacChecker(TerminalChecker):
    def __init__(self):
        self.username = None
        self.password = None
        self.driver = None
        self.setup_driver(headless=False)  # Use non-headless browser for Trapac
        self.base_url = "https://oakland.trapac.com/quick-check/?terminal=OAK&transaction=availability"
        self.terminal_name = "Trapac"
        
    def check_containers(self, container_numbers):
        results = []
        try:
            # Navigate directly to the quick check page with parameters
            self.driver.get(self.base_url)
            time.sleep(2)  # Increased initial wait time
            
            # Try to close the privacy policy modal if it appears
            try:
                # Try multiple selectors for the close button
                close_button = None
                selectors = [
                    "button.close",
                    "//button[contains(text(), 'Close')]",
                    "//button[@class='close']",
                    "//button[@aria-label='Close']"
                ]
                
                for selector in selectors:
                    try:
                        if selector.startswith("//"):
                            close_button = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                        else:
                            close_button = WebDriverWait(self.driver, 2).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        if close_button:
                            close_button.click()
                            time.sleep(1)  # Wait for modal to close
                            logger.info(f"Privacy policy modal closed using selector: {selector}")
                            break
                    except Exception:
                        continue
                        
            except Exception:
                logger.info("No privacy policy modal found or already closed")

            # Enter container numbers in the containers textarea
            try:
                container_input = WebDriverWait(self.driver, 2).until(  
                    EC.presence_of_element_located((By.NAME, "containers"))
                )
                container_input.clear()
                container_input.send_keys(",".join(container_numbers))
                logger.info(f"Entered container numbers: {container_numbers}")
                
            except Exception as e:
                logger.error(f"Error entering container numbers: {str(e)}")
                raise

            # Check if reCAPTCHA is present and handle it
            try:
                recaptcha_present = False
                recaptcha_selectors = [
                    "//iframe[contains(@src, 'recaptcha')]",
                    "//div[@class='g-recaptcha']",
                    "//div[contains(@class, 'recaptcha')]",
                    "//div[@id='recaptcha-backup']"
                ]
                
                # Log the current state before checking
                logger.info("Starting reCAPTCHA detection...")
                
                for selector in recaptcha_selectors:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    if elements:
                        # Check if the elements are actually visible
                        for element in elements:
                            try:
                                if element.is_displayed():
                                    recaptcha_present = True
                                    logger.info(f"Found visible reCAPTCHA element using selector: {selector}")
                                    break
                                else:
                                    logger.debug(f"Found reCAPTCHA element but it's not visible: {selector}")
                            except:
                                logger.debug(f"Error checking visibility for element with selector: {selector}")
                                continue
                    
                    if recaptcha_present:
                        break
                
                logger.info(f"reCAPTCHA detection result: {'Present' if recaptcha_present else 'Not Present'}")
                
                if recaptcha_present:
                    logger.warning("reCAPTCHA verification required. Please complete the verification manually.")
                    print("\nreCAPTCHA verification required for Trapac. Please complete the verification manually in the browser window.")
                    print("After completing the verification, the script will automatically continue.")
                    print("You have 5 minutes to complete the verification.")
                    
                    # Wait for recaptcha to be solved (max 5 minutes)
                    max_wait = 300  # 5 minutes
                    start_time = time.time()
                    
                    while time.time() - start_time < max_wait:
                        recaptcha_still_present = False
                        for selector in recaptcha_selectors:
                            elements = self.driver.find_elements(By.XPATH, selector)
                            if elements:
                                for element in elements:
                                    try:
                                        if element.is_displayed():
                                            recaptcha_still_present = True
                                            break
                                    except:
                                        continue
                            
                            if recaptcha_still_present:
                                break
                        
                        if not recaptcha_still_present:
                            logger.info("reCAPTCHA verification completed.")
                            time.sleep(2)  # Wait for page to update after verification
                            break
                            
                        time.sleep(1)  # Check every second
                        
                        # Log progress every 30 seconds
                        elapsed = time.time() - start_time
                        if elapsed % 30 < 1:
                            logger.info(f"Still waiting for reCAPTCHA verification... ({int(max_wait - elapsed)} seconds remaining)")
                    
                    if time.time() - start_time >= max_wait:
                        logger.error("reCAPTCHA verification timeout")
                        raise TimeoutException("reCAPTCHA verification timeout")
                else:
                    logger.info("No reCAPTCHA detected, proceeding with container check.")
                
            except Exception as e:
                logger.error(f"Error handling reCAPTCHA: {str(e)}")
                raise
                
            # Click the Check button
            try:
                submit_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@class='submit']/button"))
                )
                submit_button.click()
                logger.info("Clicked submit button")
                
            except Exception as e:
                logger.error(f"Error clicking submit button: {str(e)}")
                raise

            # Wait for results to load and add explicit wait for table
            time.sleep(5)  # Increase wait time slightly
            
            # Select the results table using the specified selector
            try:
                # Wait for table to be present
                table = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@class='table-scroll']//table"))
                )
                logger.info("Found results table with XPath: //div[@class='table-scroll']//table")
            except Exception as e:
                logger.error(f"Could not find the results table: {str(e)}")
                # Check if there's a "no results" message
                no_results_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'No result found')]")
                if no_results_elements:
                    logger.info("No results found message displayed")
                    # Add all containers as NOT FOUND
                    for container in container_numbers:
                        results.append(ContainerStatus(container, terminal="NOT FOUND"))
                    return results
                raise  # Re-raise the exception if no "no results" message found
                
            # Get all rows
            rows = table.find_elements(By.TAG_NAME, "tr")
            
            # Log the number of rows found
            logger.info(f"Found {len(rows)} rows in the results table")
            
            # Skip header row if there are more than 1 rows
            if len(rows) > 1:
                rows = rows[1:]
                logger.info(f"Processing {len(rows)} data rows after skipping header")
            
            # Process each row
            for row_index, row in enumerate(rows):
                try:
                    # Get all columns in the row
                    cols = row.find_elements(By.TAG_NAME, "td")
                    
                    # Skip rows with class 'th-second', 'row-final', or 'row-payment'
                    row_class = row.get_attribute('class')
                    if row_class in ['th-second', 'row-final', 'row-payment']:
                        logger.info(f"Skipping UI row with class: {row_class}")
                        continue
                    
                    # If only one column, check if it's a "not found" message
                    if len(cols) == 1:
                        message_text = cols[0].text.strip()
                        
                        # Only process if it's a "No result found" message
                        if "No result found for the reference number:" in message_text:
                            # Extract container number from the message
                            container = message_text.split(":")[1].strip()
                            results.append(ContainerStatus(
                                container,
                                terminal="NOT FOUND"
                            ))
                            logger.info(f"Added container {container} as NOT FOUND from row {row_index + 1}")
                        continue
                    
                    # For normal data rows, verify we have enough columns and it's a container row
                    if len(cols) >= 9 and cols[0].text.strip() == "Container":
                        try:
                            # Log each column's content before processing
                            column_contents = [col.text.strip() for col in cols]
                            
                            container = cols[1].text.strip()
                            # Remove the <strong> tags if present
                            container = container.replace('<strong>', '').replace('</strong>', '')
                            
                            line_op = cols[2].text.strip()
                            line_hold = cols[3].text.strip()
                            customs_hold = cols[4].text.strip()
                            cbpa_hold = cols[5].text.strip()
                            terminal_hold = cols[6].text.strip()
                            location = cols[7].text.strip()
                            dimensions = cols[8].text.strip()

                            # Create a ContainerStatus object and add it to the results
                            results.append(ContainerStatus(
                                container,
                                terminal=self.terminal_name,
                                line_operator=line_op,
                                dimensions=dimensions,
                                customs_hold=customs_hold,
                                line_hold=line_hold,
                                cbpa_hold=cbpa_hold,
                                terminal_hold=terminal_hold,
                                location=location
                            ))
                            logger.info(f"Successfully processed container {container} from row {row_index + 1}")
                        except IndexError as e:
                            logger.error(f"Error accessing column data in row {row_index + 1}: {str(e)}")
                            logger.error(f"Available columns: {[col.text.strip() for col in cols]}")
                            continue
                except Exception as e:
                    logger.error(f"Error processing row {row_index + 1}: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Error checking containers at Trapac: {str(e)}")

        # Add any containers that weren't found in the results
        found_containers = {r.container_number for r in results}
        for container in container_numbers:
            if container not in found_containers:
                results.append(ContainerStatus(container, terminal="NOT FOUND"))
                logger.info(f"Container {container} not found, adding as NOT FOUND")

        return results

class TideworksChecker(TerminalChecker):
    def __init__(self, username, password, terminal_name, base_url, headless=True):
        self.username = username
        self.password = password
        self.driver = None
        self.setup_driver(headless)
        self.base_url = base_url
        self.terminal_name = terminal_name
        
    def login(self):
        """Login to Tideworks terminal website"""
        try:
            self.driver.get(self.base_url)
            
            # Try to close any privacy policy or popup with multiple selectors
            try:
                selectors = [
                    "//button[contains(text(), 'Close')]",
                    "//button[@class='close']",
                    "//button[@aria-label='Close']",
                    "//button[contains(@class, 'close')]",
                    "//div[contains(@class, 'modal')]//button[contains(text(), 'Close')]",
                    "//div[contains(@class, 'modal')]//button[@class='close']",
                    "//div[contains(@class, 'popup')]//button[contains(text(), 'Close')]",
                    "//div[contains(@class, 'dialog')]//button[contains(text(), 'Close')]"
                ]
                
                for selector in selectors:
                    try:
                        close_buttons = WebDriverWait(self.driver, 2).until(
                            EC.presence_of_all_elements_located((By.XPATH, selector))
                        )
                        for button in close_buttons:
                            try:
                                if button.is_displayed() and button.is_enabled():
                                    # Try to click using JavaScript if regular click fails
                                    try:
                                        button.click()
                                    except:
                                        self.driver.execute_script("arguments[0].click();", button)
                                    time.sleep(1)  # Wait for modal to close
                                    logger.info(f"Privacy/popup closed using selector: {selector}")
                            except:
                                continue
                    except:
                        continue
                
            except Exception as e:
                logger.info(f"No privacy policy or popup found or already closed: {str(e)}")
            
            # Check if we need to log in with a shorter timeout
            try:
                login_elements = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, "j_username"))
                )
                
                # Enter username and password
                username_field = self.driver.find_element(By.ID, "j_username")
                password_field = self.driver.find_element(By.ID, "j_password")
                
                username_field.send_keys(self.username)
                password_field.send_keys(self.password)
                
                # Click login button
                login_button = self.driver.find_element(By.ID, "signIn")
                login_button.click()
                
                # Check if login was successful with a short timeout
                error_elements = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//*[contains(text(), 'Invalid username or password')]"))
                )
                if error_elements:
                    logger.error("Login failed: Invalid username or password")
                    return False
                
                logger.info("Login successful")
            except TimeoutException:
                logger.info("Already logged in or no login required")
            
            return True
        
        except Exception as e:
            logger.error(f"Error during login: {str(e)}")
            return False
    
    def check_containers(self, container_numbers):
        results = []
        
        try:
            # Login first
            if not self.login():
                logger.error(f"Failed to login to {self.terminal_name} terminal")
                return [ContainerStatus(container, terminal="LOGIN FAILED") for container in container_numbers]
            
            # Try to close any pop up menu with a short timeout
            try:
                close_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Close')]"))
                )
                close_button.click()
            except TimeoutException:
                pass  # No popup found, continue

            try:
                # Wait for the page to load completely
                time.sleep(5)
                
                # Click the Import button in the menu
                menu_button = WebDriverWait(self.driver, 3).until(
                    EC.element_to_be_clickable((By.ID, "menu-import"))
                )
                menu_button.click()
                logger.info("Clicked menu button")
                
                # Clear the container input field and enter the container numbers
                container_input = WebDriverWait(self.driver, 3).until(
                    EC.presence_of_element_located((By.ID, "numbers"))
                )   
                container_input.clear()
                container_input.send_keys("\n".join(container_numbers))
                logger.info(f"Entered container numbers: {container_numbers}")
                
                # Click search button and wait for results
                search_button = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.ID, "search"))
                )
                search_button.click()
                logger.info("Clicked search button")
                
                # Wait for the result div to be present
                result_div = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.ID, "result"))
                )
                
                # Find the table inside the result div
                table = WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.XPATH, "//div[@id='result']//table"))
                )
                logger.info("Found results table with XPath")
                
                # Get table headers for debugging
                headers = table.find_elements(By.TAG_NAME, "th")
                header_texts = [h.text.strip() for h in headers]
                logger.info(f"Table headers: {header_texts}")
                
                # Get all rows
                rows = table.find_elements(By.TAG_NAME, "tr")[1:]  # Skip header row
                logger.info(f"Found {len(rows)} rows in results table")
                # Process each row
                for row in rows:
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        
                        # Check if this is a "not found" row
                        if len(cols) == 1 and "could not be found" in cols[0].text:
                            container_text = cols[0].text
                            # Extract container number from the text
                            container = container_text.split()[0].strip()
                            results.append(ContainerStatus(
                                container,
                                terminal="NOT FOUND"
                            ))
                            logger.info(f"Container {container} not found")
                            continue
                            
                        # Process normal row with container information
                        if len(cols) >= 4:
                            container = cols[0].text.strip()
                            available = cols[1].text.strip()
                            dimensions = cols[2].text.strip()
                            holds_text = cols[3].text.strip()
                            
                            # Initialize hold statuses as empty strings to capture exact values
                            customs_hold = ""
                            line_hold = ""
                            cbpa_hold = ""
                            terminal_hold = ""
                            
                            # Get the raw HTML to check for strong tags and exact values
                            holds_html = cols[3].get_attribute('innerHTML')
                            
                            # Split holds text by newlines or semicolons to separate different hold types
                            hold_parts = [p.strip() for p in holds_text.replace('\n', ';').split(';') if p.strip()]
                            
                            # Process each hold part
                            for part in hold_parts:
                                if "Cust" in part:  # Customs hold
                                    customs_hold = part.split(':')[-1].strip() if ':' in part else part
                                elif "Line" in part:  # Line hold
                                    line_hold = part.split(':')[-1].strip() if ':' in part else part
                                elif "Add" in part:  # CBPA hold
                                    cbpa_hold = part.split(':')[-1].strip() if ':' in part else part
                                elif "Holds" in part:  # Terminal hold
                                    terminal_hold = part.split(':')[-1].strip() if ':' in part else part
                            
                            # Get additional information if available
                            additional_info = cols[4].text.strip() if len(cols) > 4 else ""
                            
                            # Extract fees and satisfaction date if present
                            fees_text = ""
                            satisfaction_date = ""
                            for part in hold_parts:
                                if "Total Fees:" in part:
                                    fees_text = part.strip()
                                elif "Satisfied Thru:" in part:
                                    satisfaction_date = part.strip()
                            
                            # Combine terminal hold with fees and satisfaction date if present
                            if fees_text or satisfaction_date:
                                terminal_parts = []
                                if terminal_hold:
                                    terminal_parts.append(terminal_hold)
                                if fees_text:
                                    terminal_parts.append(fees_text)
                                if satisfaction_date:
                                    terminal_parts.append(satisfaction_date)
                                terminal_hold = " | ".join(terminal_parts)
                            
                            location = additional_info.split("|")[0].strip() if "|" in additional_info else additional_info
                            line_operator = additional_info.split("|")[1].strip() if "|" in additional_info else ""
                            
                            results.append(ContainerStatus(
                                container,
                                terminal=self.terminal_name,
                                available=available,
                                line_operator=line_operator,
                                dimensions=dimensions,
                                customs_hold=customs_hold,
                                line_hold=line_hold,
                                cbpa_hold=cbpa_hold,
                                terminal_hold=terminal_hold,
                                location=location
                            ))
                    except Exception as e:
                        logger.error(f"Error processing row: {str(e)}")
                        continue

            except Exception as e:
                logger.error(f"Error searching containers: {str(e)}")
                raise
            
        except Exception as e:
            logger.error(f"Error checking containers at {self.terminal_name}: {str(e)}")
        
        # Add any containers that weren't found in the results
        found_containers = {r.container_number for r in results}
        for container in container_numbers:
            if container not in found_containers:
                results.append(ContainerStatus(container, terminal="NOT FOUND"))
        
        return results

def output_csv(container_results, output_file=None):
    """Output results in CSV format"""
    # Prepare data for CSV
    csv_data = []
    headers = ["Container Number", "Terminal", "Available", "Line Operator", 
               "Dimensions", "Location", "Customs Hold", "Line Hold", "CBPA Hold", "Terminal Hold"]
    
    for container, results in container_results.items():
        for result in results:
            row = {
                "Container Number": result.container_number,
                "Terminal": result.terminal,
                "Available": result.available or "",
                "Line Operator": result.line_operator or "",
                "Dimensions": result.dimensions or "",
                "Location": result.location or "",
                "Customs Hold": result.customs_hold or "",
                "Line Hold": result.line_hold or "",
                "CBPA Hold": result.cbpa_hold or "",
                "Terminal Hold": result.terminal_hold or ""
            }
            csv_data.append(row)

    
    # Write to file or stdout
    if output_file:
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(csv_data)
        logger.info(f"Results exported to {output_file}")
        print(f"\nResults exported to {output_file}")
    else:
        writer = csv.DictWriter(sys.stdout, fieldnames=headers)
        writer.writeheader()
        writer.writerows(csv_data)

def output_json(container_results, output_file=None):
    """Output results in JSON format"""
    # Prepare data for JSON
    json_data = {}
    
    for container, results in container_results.items():
        json_data[container] = []
        for result in results:
            json_data[container].append({
                "terminal": result.terminal,
                "available": result.available,
                "line_operator": result.line_operator,
                "dimensions": result.dimensions,
                "location": result.location,
                "customs_hold": result.customs_hold,
                "line_hold": result.line_hold,
                "cbpa_hold": result.cbpa_hold,
                "terminal_hold": result.terminal_hold
            })
    
    # Write to file or stdout
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(json_data, f, indent=2)
        logger.info(f"Results exported to {output_file}")
        print(f"\nResults exported to {output_file}")
    else:
        print(json.dumps(json_data, indent=2))

def output_table(container_results, output_file=None):
    """Output results in table format"""
    # Prepare data for table
    table_data = []
    headers = ["Container", "Terminal", "Available", "Line Operator", 
               "Dimensions", "Location", "Customs", "Line", "CBPA", "Terminal"]
    
    for container, results in sorted(container_results.items()):
        for result in results:
            row = [
                result.container_number,
                result.terminal,
                result.available or "",
                result.line_operator or "",
                result.dimensions or "",
                result.location or "",
                result.customs_hold or "",
                result.line_hold or "",
                result.cbpa_hold or "",
                result.terminal_hold or ""
            ]
            table_data.append(row)
    
    # Generate table
    table = tabulate(table_data, headers=headers, tablefmt="grid")
    
    # Write to file or stdout
    if output_file:
        with open(output_file, 'w') as f:
            f.write(table)
        logger.info(f"Results exported to {output_file}")
        print(f"\nResults exported to {output_file}")
    else:
        print("\n" + table)

def check_terminal(checker, container_numbers):
    """Helper function for parallel processing"""
    try:
        logger.info(f"Checking containers at {checker.terminal_name}")
        results = checker.check_containers(container_numbers)
        logger.info(f"Completed checking at {checker.terminal_name}")
        return results
    except Exception as e:
        logger.error(f"Error checking containers at {checker.terminal_name}: {str(e)}")
        return []
    finally:
        if hasattr(checker, 'driver') and checker.driver:
            checker.driver.quit()

def main():
    parser = argparse.ArgumentParser(description='Check container status across multiple terminals')
    parser.add_argument('container_numbers', nargs='+', help='Container numbers to check')
    parser.add_argument('--headless', action='store_true', help='Run in headless mode')
    parser.add_argument('--output', choices=['csv', 'json', 'table'], default='table', help='Output format')
    parser.add_argument('--output-file', help='Output file path')
    args = parser.parse_args()
    
    # Normalize container numbers (strip whitespace and convert to uppercase)
    container_numbers = [c.strip().upper() for c in args.container_numbers]
    logger.info(f"Checking status for containers: {container_numbers}")
    
    # Get credentials from environment variables
    sto_username = os.environ.get("STO_USERNAME", "yifei@hnlens.com")
    sto_password = os.environ.get("STO_PASSWORD", "ERvhiktGCW7Hj97")
    oict_username = os.environ.get("OICT_USERNAME", "yifei@hnlens.com")
    oict_password = os.environ.get("OICT_PASSWORD", "nan!5YuKqCRF3Fp")
    
    headless = args.headless
    
    # Initialize checkers
    checkers = [
        TrapacChecker(),
        TideworksChecker(sto_username, sto_password, "Shippers Transport", "https://sto.tideworks.com", headless=headless),
        TideworksChecker(oict_username, oict_password, "Oakland International", "https://b58.tideworks.com/", headless=headless)
    ]
    
    # Initialize container results dictionary
    container_results = {}
    remaining_containers = container_numbers.copy()
    
    # Check containers across all terminals sequentially
    for checker in checkers:
        try:
            if not remaining_containers:  # Skip if no containers left to check
                break
                
            logger.info(f"Checking containers at {checker.terminal_name}")
            results = checker.check_containers(remaining_containers)
            
            # Process results and update remaining containers
            new_remaining = remaining_containers.copy()
            for result in results:
                container = result.container_number
                # If container is found (not marked as NOT FOUND), remove it from remaining list
                if result.terminal != "NOT FOUND":
                    if container in new_remaining:
                        new_remaining.remove(container)
                    # Update or add the result to container_results
                    container_results[container] = [result]
                else:
                    # Only add NOT FOUND result if container hasn't been found yet
                    if container not in container_results:
                        container_results[container] = [result]
            
            remaining_containers = new_remaining
            logger.info(f"Completed checking at {checker.terminal_name}")
            logger.info(f"Remaining containers to check: {remaining_containers}")
            
        except Exception as e:
            logger.error(f"Error checking containers at {checker.terminal_name}: {str(e)}")
        finally:
            if checker.driver:
                checker.driver.quit()
    
    # Output results
    if args.output == 'csv':
        output_csv(container_results, args.output_file)
    elif args.output == 'json':
        output_json(container_results, args.output_file)
    else:  # table
        output_table(container_results, args.output_file)

if __name__ == "__main__":
    main() 