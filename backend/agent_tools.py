# backend/agent_tools.py
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

# -----------------------------
# Extraction helpers (unchanged)
# -----------------------------
def extract_discount_info_from_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    code_re = re.compile(r'(?:code|coupon|promo)\s*(?:[:\-]?\s*)?([A-Z0-9]{3,20})', re.I)
    percent_re = re.compile(r'(\d{1,2})\s*%\s*(?:off|discount)?', re.I)
    min_order_re = re.compile(r'(?:orders?)\s*(?:above|over|>=)\s*\$?(\d+)', re.I)
    for c in chunks:
        text = (c.get("document") or "")
        source = c.get("metadata", {}).get("source", "unknown")
        codes = code_re.findall(text)
        percents = percent_re.findall(text)
        mins = min_order_re.findall(text)
        for code in codes:
            percent = int(percents[0]) if percents else None
            min_order = int(mins[0]) if mins else None
            findings.append({"code": code.strip(), "percent": percent, "min_order": min_order, "source": source})
    return findings

def extract_shipping_info_from_chunks(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    findings = []
    free_ship_re = re.compile(r'free\s+for\s+orders\s+(?:over|above|>=)\s*\$?(\d+)', re.I)
    for c in chunks:
        text = (c.get("document") or "")
        source = c.get("metadata", {}).get("source", "unknown")
        m = free_ship_re.search(text)
        if m:
            findings.append({"free_over": int(m.group(1)), "source": source})
    return findings

# -----------------------------
# Testcase generation
# -----------------------------
def generate_test_cases_from_context(query: str, retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    testcases = []
    discount_facts = extract_discount_info_from_chunks(retrieved_chunks)
    shipping_facts = extract_shipping_info_from_chunks(retrieved_chunks)
    for i, fact in enumerate(discount_facts, 1):
        if not fact.get("code"):
            continue
        code = fact["code"]
        pct = fact.get("percent")
        min_order = fact.get("min_order")
        src = fact["source"]
        tid = f"TC-DISCOUNT-{i:03d}"
        steps = [
            "Open the checkout page.",
            f"Add items totaling ${min_order if min_order else 60} to the cart.",
            f"Enter discount code '{code}' in the coupon field.",
            "Apply the coupon.",
        ]
        expected = f"Order total is reduced by {pct}%." if pct else "Order total is reduced accordingly."
        pre = f"Cart subtotal >= ${min_order}" if min_order else "Cart subtotal meets the promotion requirement."
        testcases.append({
            "Test_ID": tid,
            "Feature": "Discount Code",
            "Test_Scenario": f"Valid discount code {code} applies correct discount",
            "Test_Steps": steps,
            "Preconditions": pre,
            "Expected_Result": expected,
            "Type": "Positive",
            "Grounded_In": [src]
        })
        tid2 = f"TC-DISCOUNT-{i:03d}-NEG"
        steps2 = [
            "Open the checkout page.",
            "Add items totaling $60 to the cart.",
            "Enter discount code 'INVALIDCODE' in the coupon field.",
            "Apply the coupon"
        ]
        testcases.append({
            "Test_ID": tid2,
            "Feature": "Discount Code",
            "Test_Scenario": "Invalid discount code is rejected",
            "Test_Steps": steps2,
            "Preconditions": "Cart subtotal valid",
            "Expected_Result": "An error message is shown and no discount is applied.",
            "Type": "Negative",
            "Grounded_In": [src]
        })
    for j, sf in enumerate(shipping_facts, 1):
        free_over = sf["free_over"]
        src = sf["source"]
        tid = f"TC-SHIP-{j:03d}"
        steps = [
            "Open the checkout page.",
            f"Add items totaling ${free_over + 10} to the cart.",
            "Proceed to shipping step."
        ]
        testcases.append({
            "Test_ID": tid,
            "Feature": "Shipping",
            "Test_Scenario": f"Free shipping for orders over ${free_over}",
            "Test_Steps": steps,
            "Preconditions": "Cart subtotal meets threshold",
            "Expected_Result": "Shipping cost is $0 (free).",
            "Type": "Positive",
            "Grounded_In": [src]
        })
        tid2 = f"TC-SHIP-{j:03d}-NEG"
        steps2 = [
            "Open the checkout page.",
            f"Add items totaling ${free_over - 10} to the cart.",
            "Proceed to shipping step"
        ]
        testcases.append({
            "Test_ID": tid2,
            "Feature": "Shipping",
            "Test_Scenario": f"No free shipping for orders under ${free_over}",
            "Test_Steps": steps2,
            "Preconditions": "Cart subtotal below threshold",
            "Expected_Result": "Shipping cost is greater than $0.",
            "Type": "Negative",
            "Grounded_In": [src]
        })
    return testcases

# -----------------------------
# HTML parsing helpers
# -----------------------------
def find_coupon_input_in_html(html: str) -> Optional[Dict[str, str]]:
    """
    Returns a dict describing how to locate the coupon input, e.g.
      {"by": "id", "selector": "coupon_input"}
      {"by": "name", "selector": "coupon"}
      {"by": "css", "selector": "input[placeholder=\"Enter coupon\"]"}
    or None if not found.
    """
    soup = BeautifulSoup(html, "html.parser")
    keywords = ['coupon', 'discount', 'promo', 'code', 'voucher']
    # search inputs
    inputs = soup.find_all('input')
    for inp in inputs:
        for attr in ('id', 'name', 'placeholder', 'class'):
            val = inp.get(attr)
            if val:
                val_low = val.lower()
                if any(k in val_low for k in keywords):
                    if attr == 'id':
                        return {"by": "id", "selector": val}
                    elif attr == 'name':
                        return {"by": "name", "selector": val}
                    else:
                        # placeholder or class -> return a css selector
                        if attr == 'placeholder':
                            # escape double quotes inside placeholder if any
                            placeholder = val.replace('"', '\\"')
                            return {"by": "css", "selector": f'input[placeholder=\"{placeholder}\"]'}
                        else:
                            # class or other attribute
                            return {"by": "css", "selector": f'input[{attr}=\"{val}\"]'}
    # fallback: find a button that looks like "apply" and try to find a nearby input
    buttons = soup.find_all(['button', 'a'])
    for b in buttons:
        text = b.get_text(" ", strip=True).lower()
        if any(k in text for k in ['apply coupon', 'apply code', 'apply promo', 'apply']):
            parent = b.find_parent()
            if parent:
                inp = parent.find('input')
                if inp:
                    if inp.get('id'):
                        return {"by": "id", "selector": inp.get('id')}
                    if inp.get('name'):
                        return {"by": "name", "selector": inp.get('name')}
    return None

def extract_coupon_code_from_testcase(test_case: Dict[str, Any]) -> Optional[str]:
    """
    Try to find a coupon code string in Test_Steps or Test_Scenario.
    Looks for an uppercase alphanumeric token like SAVE15.
    """
    text_candidates = []
    if isinstance(test_case.get("Test_Steps"), list):
        text_candidates.extend(test_case["Test_Steps"])
    if test_case.get("Test_Scenario"):
        text_candidates.append(test_case["Test_Scenario"])
    joined = " ".join(text_candidates)
    # look for token inside single or double quotes first
    m = re.search(r"['\"]([A-Z0-9]{3,20})['\"]", joined)
    if m:
        return m.group(1)
    # fallback: any uppercase token
    m2 = re.search(r"\b([A-Z0-9]{3,20})\b", joined)
    if m2:
        return m2.group(1)
    return None

# -----------------------------
# Selenium script generator
# -----------------------------
def generate_selenium_script_html(test_case: Dict[str, Any], checkout_html: str, html_path: str) -> str:
    """
    Generates a Python Selenium script (string) given a test_case dict and the checkout HTML (string).
    The returned value is a string containing the full Python script.
    """
    coupon_sel = find_coupon_input_in_html(checkout_html)
    coupon_code = extract_coupon_code_from_testcase(test_case) or "SAVE15"

    script_lines: List[str] = []
    script_lines.append("#!/usr/bin/env python3")
    script_lines.append("# Generated Selenium test script (run inside your venv).")
    script_lines.append("from selenium import webdriver")
    script_lines.append("from webdriver_manager.chrome import ChromeDriverManager")
    script_lines.append("from selenium.webdriver.chrome.service import Service")
    script_lines.append("from selenium.webdriver.common.by import By")
    script_lines.append("from selenium.webdriver.support.ui import WebDriverWait")
    script_lines.append("from selenium.webdriver.support import expected_conditions as EC")
    script_lines.append("import time")
    script_lines.append("import sys")
    script_lines.append("")
    script_lines.append("def run_test():")
    script_lines.append("    # Use Service with ChromeDriverManager for robust driver handling")
    script_lines.append("    service = Service(ChromeDriverManager().install())")
    script_lines.append("    options = webdriver.ChromeOptions()")
    script_lines.append("    # optional: run headless by uncommenting the next two lines")
    script_lines.append("    # options.add_argument('--headless=new')")
    script_lines.append("    # options.add_argument('--disable-gpu')")
    script_lines.append("    driver = webdriver.Chrome(service=service, options=options)")
    script_lines.append("    wait = WebDriverWait(driver, 10)")
    script_lines.append(f"    driver.get(r'{html_path}')  # update this path to the local file or server URL of checkout.html")
    script_lines.append("")
    script_lines.append("    # --- Fill checkout form fields (update selectors if needed) ---")
    script_lines.append("    try:")
    script_lines.append("        # optional example field fill (if present)")
    script_lines.append("        if driver.find_elements(By.ID, 'name'):")
    script_lines.append("            driver.find_element(By.ID, 'name').send_keys('Test User')")
    script_lines.append("    except Exception:")
    script_lines.append("        pass")
    script_lines.append("")

    if coupon_sel:
        by = coupon_sel['by']
        sel = coupon_sel['selector']
        # ensure quotes inside selectors are escaped
        sel_escaped = sel.replace("'", "\\'")
        if by == "id":
            script_lines.append(f"    # Coupon input detected by id='{sel_escaped}'")
            script_lines.append(f"    wait.until(EC.presence_of_element_located((By.ID, '{sel_escaped}')))")
            script_lines.append(f"    driver.find_element(By.ID, '{sel_escaped}').clear()")
            script_lines.append(f"    driver.find_element(By.ID, '{sel_escaped}').send_keys('{coupon_code}')")
            script_lines.append("    try:")
            script_lines.append("        btn = driver.find_element(By.XPATH, \"//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply')]\")")
            script_lines.append("        btn.click()")
            script_lines.append("    except Exception:")
            script_lines.append("        # fallback: try button with id 'apply_coupon' or name 'apply'")
            script_lines.append("        try:")
            script_lines.append("            driver.find_element(By.ID, 'apply_coupon').click()")
            script_lines.append("        except Exception:")
            script_lines.append("            pass")
        elif by == "name":
            script_lines.append(f"    # Coupon input detected by name='{sel_escaped}'")
            script_lines.append(f"    wait.until(EC.presence_of_element_located((By.NAME, '{sel_escaped}')))")
            script_lines.append(f"    driver.find_element(By.NAME, '{sel_escaped}').clear()")
            script_lines.append(f"    driver.find_element(By.NAME, '{sel_escaped}').send_keys('{coupon_code}')")
            script_lines.append("    try:")
            script_lines.append("        btn = driver.find_element(By.XPATH, \"//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply')]\")")
            script_lines.append("        btn.click()")
            script_lines.append("    except Exception:")
            script_lines.append("        pass")
        else:
            # CSS selector
            sel_css = sel.replace('"', '\\"')
            script_lines.append(f"    # Coupon input detected by CSS selector: {sel_css}")
            script_lines.append(f"    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, \"{sel_css}\")))")
            script_lines.append(f"    driver.find_element(By.CSS_SELECTOR, \"{sel_css}\").clear()")
            script_lines.append(f"    driver.find_element(By.CSS_SELECTOR, \"{sel_css}\").send_keys('{coupon_code}')")
            script_lines.append("    # click apply button (best-effort)")
            script_lines.append("    try:")
            script_lines.append("        btn = driver.find_element(By.XPATH, \"//button[contains(translate(text(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'apply')]\")")
            script_lines.append("        btn.click()")
            script_lines.append("    except Exception:")
            script_lines.append("        pass")
    else:
        script_lines.append("    # No coupon input could be reliably detected in the provided checkout.html.")
        script_lines.append("    # Please open the page and inspect the coupon input's id or name and replace the selector below:")
        script_lines.append("    # driver.find_element(By.ID, 'coupon_input_id').send_keys('SAVE15')")
        script_lines.append("    pass")

    script_lines.append("")
    script_lines.append("    # --- Assertions ---")
    script_lines.append("    # Update the assertion below to match the expected result, for example checking the total price or success message.")
    script_lines.append("    time.sleep(0.5)")
    script_lines.append("    page_text = driver.page_source.lower()")
    script_lines.append("    if 'discount applied' in page_text or 'discount' in page_text:")
    script_lines.append("        print('TEST PASSED: Discount message found on page.')")
    script_lines.append("        result = 0")
    script_lines.append("    else:")
    script_lines.append("        print('TEST FAILED: Discount message NOT found.')")
    script_lines.append("        print(page_text[:800])")
    script_lines.append("        result = 2")
    script_lines.append("    driver.quit()")
    script_lines.append("    sys.exit(result)")
    script_lines.append("")
    script_lines.append("if __name__ == '__main__':")
    script_lines.append("    run_test()")

    # *** CRITICAL: return the generated script as a single string ***
    return "\n".join(script_lines)
