#!/usr/bin/env python3
# tests/generated_test.py
# Selenium test that opens the checkout.html, enters coupon SAVE15 and clicks Apply.
from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sys
def run_test():
    # use Service with ChromeDriverManager
    service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=service, options=options)
    wait = WebDriverWait(driver, 10)
    # update this path if needed
    url = r'file:///D:/a last chancce/Ocean.AI/assets/checkout.html'
    try:
        driver.get(url)
        # wait for coupon input to be present
        wait.until(EC.presence_of_element_located((By.ID, "coupon_input")))
        # fill coupon
        coupon = driver.find_element(By.ID, "coupon_input")
        coupon.clear()
        coupon.send_keys("SAVE15")
        # click apply
        apply_btn = driver.find_element(By.ID, "apply_coupon")
        apply_btn.click()
        # wait briefly for message to update
        time.sleep(0.5)
        # assert message shown contains 'Discount applied' or 'discount'
        page_text = driver.page_source.lower()
        if "discount applied" in page_text or "discount" in page_text:
            print("TEST PASSED: Discount message found on page.")
            result = 0
        else:
            print("TEST FAILED: Discount message NOT found.")
            print("Page excerpt:")
            print(page_text[:400])
            result = 2
    except Exception as e:
        print("ERROR during test run:", repr(e))
        result = 3
    finally:
        driver.quit()
        sys.exit(result)
if __name__ == '__main__':
    run_test()
