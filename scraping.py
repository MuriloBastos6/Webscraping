from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import csv
import os
import re


def scrape_google_maps(search_query, location):
    # Initialize the webdriver (Chrome) using webdriver-manager for convenience
    chrome_options = Options()
    chrome_options.add_argument('--start-maximized')
    # optional: run headless by uncommenting next line (useful for servers)
    # chrome_options.add_argument('--headless=new')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Navigate to Google Maps
        driver.get("https://www.google.com/maps")
        time.sleep(2)

        # Find search box and enter query
        search_box = driver.find_element(By.ID, "searchboxinput")
        search_box.send_keys(f"{search_query} in {location}")
        search_box.send_keys(Keys.ENTER)
        time.sleep(3)

        # Wait for results to load
        wait = WebDriverWait(driver, 10)
        try:
            results = wait.until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "Nv2PK")))
        except TimeoutException:
            # fallback: proceed even if explicit class not found
            results = []

        stores_info = []

        # Scroll through results to load more (try multiple possible containers)
        try:
            scrollable_div = driver.find_element(
                By.CSS_SELECTOR, 'div[aria-label="Results for"]')
        except NoSuchElementException:
            try:
                scrollable_div = driver.find_element(
                    By.CSS_SELECTOR, 'div[role="region"]')
            except NoSuchElementException:
                scrollable_div = None

        if scrollable_div:
            for _ in range(4):  # Scroll 4 times to load more results
                driver.execute_script(
                    'arguments[0].scrollTop = arguments[0].scrollHeight', scrollable_div)
                time.sleep(2)

        # Get all store listings
        stores = driver.find_elements(By.CLASS_NAME, "Nv2PK")

        for store in stores:
            try:
                # Click on each store to get details
                driver.execute_script(
                    "arguments[0].scrollIntoView(true);", store)
                time.sleep(0.5)
                store.click()
                time.sleep(2)

                # Helper to try multiple selectors
                def try_get_text(by, selector):
                    try:
                        el = driver.find_element(by, selector)
                        return el.text.strip()
                    except Exception:
                        return None

                # Get store name (common selector)
                name = None
                possible_name_selectors = [
                    (By.CLASS_NAME, "DUwDvf"),
                    (By.CSS_SELECTOR, 'h1'),
                    (By.CSS_SELECTOR, 'h1 span[jsaction]')
                ]
                for by, sel in possible_name_selectors:
                    name = try_get_text(by, sel)
                    if name:
                        break

                # Address
                address = None
                possible_address_selectors = [
                    (By.CSS_SELECTOR, 'button[data-item-id="address"]'),
                    (By.CSS_SELECTOR, 'button[aria-label*="Endereço"]'),
                    (By.CSS_SELECTOR,
                     '[data-item-id="address"] .section-info-text')
                ]
                for by, sel in possible_address_selectors:
                    addr_text = try_get_text(by, sel)
                    if addr_text:
                        address = addr_text
                        break

                # Phone
                phone = None
                possible_phone_selectors = [
                    (By.CSS_SELECTOR, 'button[data-item-id="phone"]'),
                    (By.CSS_SELECTOR, 'button[aria-label*="Telefone"]'),
                    (By.CSS_SELECTOR, 'a[href^="tel:"]')
                ]
                for by, sel in possible_phone_selectors:
                    ph = try_get_text(by, sel)
                    if ph:
                        phone = ph
                        break

                # Site/Website
                site = None
                possible_site_selectors = [
                    (By.CSS_SELECTOR, 'a[data-item-id="authority"]'),
                    (By.CSS_SELECTOR, 'a[data-item-id="website"]'),
                    (By.CSS_SELECTOR, 'a[aria-label^="Site"]'),
                    (By.CSS_SELECTOR, 'a[href^="http"]')
                ]
                for by, sel in possible_site_selectors:
                    s = None
                    try:
                        el = driver.find_element(by, sel)
                        s = el.get_attribute('href') or el.text
                    except Exception:
                        s = None
                    if s:
                        site = s.strip()
                        break

                # Description / category (e.g., "Loja de produtos naturais")
                description = None
                possible_desc_selectors = [
                    (By.CSS_SELECTOR, '.qW6peb'),
                    (By.CSS_SELECTOR, '.HlvSq'),
                    (By.CSS_SELECTOR, '[data-tooltip*="categoria"]'),
                ]
                for by, sel in possible_desc_selectors:
                    d = try_get_text(by, sel)
                    if d:
                        description = d
                        break

                # Fallbacks: sometimes phone/address are inside spans with icons
                if not phone:
                    try:
                        phone = try_get_text(
                            By.XPATH, "//button[contains(@aria-label,'Telefone') or contains(@data-item-id,'phone')]//div/span")
                    except Exception:
                        phone = None

                if not address:
                    try:
                        address = try_get_text(
                            By.XPATH, "//button[contains(@aria-label,'Endereço') or contains(@data-item-id,'address')]//div/span")
                    except Exception:
                        address = None

                stores_info.append({
                    "name": name or "Not available",
                    "address": address or "Not available",
                    "phone": phone or "Not available",
                    "site": site or "Not available",
                    "description": description or "Not available"
                })

            except Exception as e:
                print(f"Error processing store: {e}")
                continue

        return stores_info

    finally:
        driver.quit()


# Example usage
if __name__ == "__main__":
    search_query = "Casa do norte"  # Change this to your search term
    location = "São Paulo"  # Change this to your desired location

    results = scrape_google_maps(search_query, location)

    print(f"Total stores found: {len(results)}")

    # Save to CSV
    out_path = os.path.join(os.path.dirname(__file__), 'results.csv')
    fieldnames = ['name', 'address', 'phone', 'site', 'description']
    try:
        # clean function: remove newlines, control characters, collapse spaces
        # remove control chars and private-use area symbols (like icon glyphs)
        CONTROL_RE = re.compile(r'[\x00-\x1f\x7f\ue000-\uf8ff]')

        def clean_cell(v):
            if v is None:
                return ''
            s = str(v)
            s = s.replace('\r', ' ').replace('\n', ' ')
            s = CONTROL_RE.sub('', s)
            s = ' '.join(s.split())
            return s.strip()

        # write with semicolon delimiter and BOM for Excel compatibility
        with open(out_path, 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';', quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            for store in results:
                # ensure keys exist and clean values
                row = {k: clean_cell(store.get(k, '')) for k in fieldnames}
                writer.writerow(row)
        print(f"Wrote {len(results)} rows to {out_path} (delimiter=';')")
    except Exception as e:
        print(f"Error writing CSV: {e}")

    # Also print the first few results for quick inspection
    for store in results[:5]:
        print(f"Name: {store.get('name')}")
        print(f"Address: {store.get('address')}")
        print(f"Phone: {store.get('phone')}")
        print(f"Site: {store.get('site')}")
        print(f"Description: {store.get('description')}")
        print("-" * 50)