import os
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select

# gdrive
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload

class WMS:
    def __init__(self) -> None:
        # WMS credentials and URLs
        self.username = 'example@domain.com'  # Example username
        self.password = 'example_password'      # Example password
        self.login_url = 'http://www.example.com/login'  # Example login URL
        self.inbound_url = 'http://www.example.com/inbound'  # Example inbound URL
        self.outbound_url = 'http://www.example.com/outbound'  # Example outbound URL
        self.download_dir = "/path/to/download/directory"  # Example download directory
        self.driver = None
        self.setup_driver()
        
        # Field names and selectors for inbound receipt
        self._new_receipt_btn_name = "ctl07$SearchResultsDataGridController$btnNewButtonSearchControl"
        self._warehouse_select_name = 'WarehouseDropDown'
        self._receive_ref_name = 'ReceiveRef'
        self._booking_date_name = 'BookingDate$ctl00$TextBox'
        self._today = datetime.today().strftime("%d-%b-%y")
        self._total_units_name = 'TotalUnits'
        self._total_pallets_name = 'TotalPallets'
        self._save_name = 'SaveReceive'
        self._add_line_btn_template_id = 'WhsReceiveInventoryGrid_ctl{:02d}_ga'  # Template for add line button using zero-padding
        self._line_product_template_name = 'WhsReceiveInventoryGrid$ctl{:02d}$ctl00$TextBox'  # Template for product field
        self._line_packs_template_name = 'WhsReceiveInventoryGrid$ctl{:02d}$ctl02'  # Template for packs field
        self._packs_unit_template_name = 'WhsReceiveInventoryGrid$ctl02$ctl03'  # Template for packs unit field
        self._line_expected_quantity_name = 'WhsReceiveInventoryGrid$ctl02$ctl04'  # Template for expected quantity field

        # outbound field names
        self._new_order_name = "WhsReceiveInventoryGrid$ctl02$ctl07"
        self._order_number_name = "OrderNumber"
        self._required_date = "RequiredByDate$ctl00$TextBox"
        self._total_units_name = "TotalUnits"
        self._order_update = "SaveOrder"

        # gdrive credentials
        self.scopes = ['https://www.googleapis.com/auth/drive']
        self.service_account_file = '/path/to/service_account.json'  # Example service account file path

        # gdrive file ID
        self.file_id = 'example_file_id'  # Example file ID
        self.file_path = '/path/to/file/inbound.xls'  # Example file path
        self.mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

        # In __init__, add these new field names:
        self._new_order_btn_name = "ctl07$SearchResultsDataGridController$btnNewButtonSearchControl"
        self._order_warehouse_select_name = 'WarehouseDropDown'
        self._required_date_name = "RequiredByDate$ctl00$TextBox"
        self._order_total_units_name = "TotalUnits"
        self._order_save_name = "SaveOrder"

    def setup_driver(self):
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        chrome_options = Options()
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": self.download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True
        })
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

    def close_driver(self):
        self.driver.quit()

    def login(self):
        try:
            self.driver.get(self.login_url)
            username_input = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.NAME, 'LoginNameTextBox')))
            password_input = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.NAME, 'PasswordTextBox')))
            login_button = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.NAME, 'SigninBtn')))

            username_input.send_keys(self.username)
            password_input.send_keys(self.password)
            login_button.click()

            WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.ID, 'LoginStatusString')))
            print("Login successful.")
            return True
        
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False

    def navigate_to_receipt(self):
        try:
            warehouse_menu = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//a[text()='Warehouse']")))
            receipts_link = WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located((By.XPATH, "//a[text()='Receipts']")))

            receipts_link.click()
        except Exception as e:
            print(f"Navigation failed: {str(e)}")

    def query_inventory(self):
        try:
            self.driver.get(self.inbound_url)
            find_btn = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.NAME, 'ctl07$ctl01$FooterRow_FindButton')))
            find_btn.click()

            WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.ID, 'ctl07_SearchResultsDataGridController_SearchResultsDataGrid')))

            export_btn = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.NAME, 'ctl07$SearchResultsDataGridController$SearchResultsDataGrid_ExcelButton')))
            export_btn.click()

            time.sleep(10)

            # TODO: search for latest download instead of 'SearchResults.xls'
            new_filename = 'inbound.xls'
            os.rename(os.path.join(self.download_dir, 'SearchResults.xls'), os.path.join(self.download_dir, new_filename))
            return True

        except Exception as e:
            return False

    def create_inbound(self, container='', product='', num_pallets=22):
        """
        Create a new inbound receipt with specified container number and number of pallets.
        
        Args:
            container (str): Container reference number
            num_pallets (int): Number of pallets to create (default: 22)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Navigate to inbound page
            self.driver.get(self.inbound_url)
            
            # Click New Receipt button
            new_receipt = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.NAME, self._new_receipt_btn_name)))
            new_receipt.click()
            
            # Select HAYMAN WAREHOUSE
            warehouse_select = Select(WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.NAME, self._warehouse_select_name))))
            warehouse_select.select_by_visible_text('HAYMAN WAREHOUSE')
            
            # Set Receive Ref #
            receive_ref = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.NAME, self._receive_ref_name)))
            receive_ref.clear()
            receive_ref.send_keys(container)
            
            # Set Booking Date 
            date_input = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.NAME, self._booking_date_name)))
            date_input.clear()
            date_input.send_keys(self._today)

            # Set Total Units
            total_units = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.NAME, self._total_units_name)))
            total_units.clear()
            total_units.send_keys(str(num_pallets * 60))  # Assuming each pallet has 60 units
            
            # Set Total Pallets
            total_pallets = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.NAME, self._total_pallets_name)))
            total_pallets.clear()
            total_pallets.send_keys(str(num_pallets))

            # Add specified number of pallet lines
            for i in range(2, num_pallets + 2):  # Starting from 2 as per the field naming convention
                # Click add line button (note: ID changes with each new line)
                # The {:02d} format will automatically handle both single and double digits:
                # i=2  -> "02"
                # i=10 -> "10"
                add_line_btn_id = self._add_line_btn_template_id.format(i)
                add_line = WebDriverWait(self.driver, 2).until(
                    EC.element_to_be_clickable((By.ID, add_line_btn_id)))
                add_line.click()
                print(f"Adding line {i}, button ID: {add_line_btn_id}")  # Debug print
                
                # Fill in Product
                product_field = WebDriverWait(self.driver, 2).until(
                    EC.visibility_of_element_located((By.NAME, self._line_product_template_name.format(i))))
                product_field.clear()
                product_field.send_keys(product)  # You might want to make this configurable
                
                # Fill in Packs 
                packs_field = WebDriverWait(self.driver, 2).until(
                    EC.visibility_of_element_located((By.NAME, self._line_packs_template_name.format(i))))
                packs_field.clear()
                packs_field.send_keys(str(60))

                # Fill in Packs Unit
                packs_unit_field = Select(WebDriverWait(self.driver, 2).until(
                    EC.visibility_of_element_located((By.NAME, self._packs_unit_template_name))))
                packs_unit_field.select_by_visible_text('Unit')

                # Fill in Expected Quantity
                expected_quantity_field = WebDriverWait(self.driver, 2).until(
                    EC.visibility_of_element_located((By.NAME, self._line_expected_quantity_name.format(i))))
                expected_quantity_field.clear()
                expected_quantity_field.send_keys(str(60))
                time.sleep(1)


            # Save the receipt
            save = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.NAME, self._save_name)))
            save.click()
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"Error creating inbound receipt: {str(e)}")
            return False

    
    def create_outbound(self, container='', date='', num_pallets=22):
        """
        Create a new outbound order.
        
        Args:
            container (str): Container/order reference number
            date (str): Required delivery date
            num_pallets (int): Number of pallets (default: 22)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Navigate to outbound page
            self.driver.get(self.outbound_url)
            
            # Click Place New Order button
            new_order = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.NAME, self._new_order_btn_name)))
            new_order.click()
            
            # Select HAYMAN WAREHOUSE
            warehouse_select = Select(WebDriverWait(self.driver, 2).until(
                EC.presence_of_element_located((By.NAME, self._order_warehouse_select_name))))
            warehouse_select.select_by_visible_text('HAYMAN WAREHOUSE')
            
            # Set Order Number (container number)
            order_number = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.NAME, self._order_number_name)))
            order_number.clear()
            order_number.send_keys(container)
            
            # Set Required Date
            required_date = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.NAME, self._required_date_name)))
            required_date.clear()
            required_date.send_keys(date)
            time.sleep(2)
            
            # Set Total Units (pallets * 60)
            total_units = WebDriverWait(self.driver, 2).until(
                EC.visibility_of_element_located((By.NAME, self._order_total_units_name)))
            total_units.clear()
            total_units.send_keys(int(num_pallets) * 60)
            time.sleep(2)
            
            # Save the order
            save = WebDriverWait(self.driver, 2).until(
                EC.element_to_be_clickable((By.NAME, self._order_save_name)))
            save.click()
            time.sleep(3)
            return True
            
        except Exception as e:
            print(f"Error creating outbound order: {str(e)}")
            return False

    def upload_to_gdrive(self):
        # Authenticate and create the service
        credentials = service_account.Credentials.from_service_account_file(self.service_account_file, scopes=self.scopes)
        # print(credentials)
        service = build('drive', 'v3', credentials=credentials)

        # Upload the file
        try:
            media = MediaFileUpload(self.file_path, mimetype=self.mime_type) 
            file = service.files().update(fileId=self.file_id, media_body=media).execute()
            # print('Updated File ID: %s' % file.get('id'))
            return True
        except:
            return False
