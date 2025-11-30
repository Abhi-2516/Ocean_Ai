#!/usr/bin/env python3
# Generated Selenium test script (run inside your venv).
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys

def run_test():
    # Use Service with ChromeDriverManager for robust driver handling
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    # optional: run headless by uncommenting the next two lines
    # options.add_argument('--headless=new')
    # options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 10)
    driver.get(r'file:///D:/a last chancce/Ocean.AI/assets/checkout.html')  # update this path to the local file or server URL of checkout.html

    # --- Fill checkout form fields (update selectors if needed) ---
    try:
        # optional example field fill (if present)
        if driver.find_elements(By.ID, 'name'):
            driver.find_element(By.ID, 'name').send_keys('Test User')
    except Exception:
        pass

    # Coupon input detected by id='coupon_input'
    wait.until(EC.presence_of_element_located((By.ID, 'coupon_input')))
    driver.find_element(By.ID, 'coupon_input').clear()
    driver.find_element(By.ID, 'coupon_input').send_keys('SAVE15')
    try:
        btn = driver.find_element(By.XPATH, "//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply')]")
        btn.click()
    except Exception:
        # fallback: try button with id 'apply_coupon' or name 'apply'
        try:
            driver.find_element(By.ID, 'apply_coupon').click()
        except Exception:
            pass

    # --- Assertions ---
    # Update the assertion below to match the expected result, for example checking the total price or success message.
    time.sleep(0.5)
    page_text = driver.page_source.lower()
    if 'discount applied' in page_text or 'discount' in page_text:
        print('TEST PASSED: Discount message found on page.')
        result = 0
    else:
        print('TEST FAILED: Discount message NOT found.')
        print(page_text[:800])
        result = 2
    driver.quit()
    sys.exit(result)

if __name__ == '__main__':
    run_test()