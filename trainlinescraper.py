import datetime
import time
import os
from types import SimpleNamespace
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def select_origin_and_destination(driver, origin, destination):
    wait = WebDriverWait(driver, 20)

    # ----- ORIGIN -----
    origin_trigger = wait.until(EC.element_to_be_clickable((By.ID, "jsf-origin-input")))
    origin_trigger.click()
    print(" Clicked origin input")

    origin_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[data-testid='jsf-origin']")))
    origin_input.clear()
    origin_input.send_keys(origin)
    print(f" Typed origin: {origin}")
    time.sleep(1.5)
    origin_input.send_keys(Keys.RETURN)
    time.sleep(1)

    selected_origin = driver.find_element(By.ID, "jsf-origin-input").get_attribute("value")
    if origin.lower() in selected_origin.lower():
        print(f" Origin confirmed: {selected_origin}")
    else:
        print(f" Origin mismatch: Got '{selected_origin}', expected '{origin}'")

    # ----- DESTINATION -----
    dest_trigger = wait.until(EC.element_to_be_clickable((By.ID, "jsf-destination-input")))
    dest_trigger.click()
    print(" Clicked destination input")

    dest_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[data-testid='jsf-destination']")))
    dest_input.clear()
    dest_input.send_keys(destination)
    print(f" Typed destination: {destination}")
    time.sleep(1.5)
    dest_input.send_keys(Keys.RETURN)
    time.sleep(1)

    selected_dest = driver.find_element(By.ID, "jsf-destination-input").get_attribute("value")
    if destination.lower() in selected_dest.lower():
        print(f" Destination confirmed: {selected_dest}")
    else:
        print(f" Destination mismatch: Got '{selected_dest}', expected '{destination}'")


def select_date_and_time(driver, field_id, target_month, target_day, hour_val, minute_val):
    wait = WebDriverWait(driver, 15)
    print(f" Looking for: {target_month} {target_day}")

    # Open calendar
    field = wait.until(EC.element_to_be_clickable((By.ID, field_id)))
    driver.execute_script("arguments[0].click();", field)
    print(" Calendar field clicked")

    # Navigate calendar
    for _ in range(12):
        month_label = driver.find_element(By.ID, "datetime-picker-label").text.strip()
        print(f" Current calendar: {month_label}")

        if month_label == target_month:
            print(" Month found")
            try:
                day_button = driver.find_element(
                    By.CSS_SELECTOR,
                    f'button[data-testid="jsf-calendar-date-button-{target_day}"]'
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", day_button)
                day_button.click()
                print(f" Selected: {target_month} {target_day}")

                time.sleep(1)

                # Select hour and minute
                Select(driver.find_element(By.ID, "jsf-outbound-time-time-picker-hour")).select_by_value(hour_val)
                Select(driver.find_element(By.ID, "jsf-outbound-time-time-picker")).select_by_value(minute_val)
                print(f" Time set to {hour_val}:{minute_val}")

                return {"status": f"Selected {target_month} {target_day} {hour_val}:{minute_val}"}
            except Exception as e:
                print(f" Could not click day {target_day} or select time:", e)
                return {"error": f"Could not complete selection for {target_day}"}
        else:
            driver.find_element(By.CSS_SELECTOR, 'button[data-testid="calendar-navigate-to-next-month"]').click()
            print(" Clicked next month")
            time.sleep(0.8)

    return {"error": f"Could not reach {target_month}"}


def build_trainline_link(departure_code, destination_code, date, time_of_day):
    params = {
        "originStation":      departure_code,
        "destinationStation": destination_code,
        "outwardDate":        date.isoformat(),
        "outwardTime":        time_of_day,
        "journeyType":        "single"
    }
    return "https://www.thetrainline.com/search?" + urlencode(params)

def save_screenshot(driver, prefix="screenshot"):
    """Save a screenshot with timestamp """
    try:
        os.makedirs("screenshots", exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"screenshots/{prefix}_{timestamp}.png"
        driver.save_screenshot(filename)
        print(f" Saved screenshot to {filename}")
        return filename
    except Exception as e:
        print(f" Failed to save screenshot: {e}")
        return None

def find_cheapest_ticket(departure, destination,
                         date, time_of_day=None,
                         trip_type="single", return_date=None, return_time=None):
    """
    Fill the Trainline form via Selenium, then return the results-page URL.
    Falls back to build_trainline_link(...) on any timeout or JS failure.
    """
    # 1) Normalize time_of_day
    if time_of_day is None:
        hr, mn = "00", "00"
        time_of_day = "00:00"
    elif isinstance(time_of_day, str):
        hr, mn = time_of_day.split(":")
    else:
        hr, mn = time_of_day.strftime("%H"), time_of_day.strftime("%M")
        time_of_day = f"{hr}:{mn}"

    # 2) Stealthy ChromeOptions
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless") 
    opts.add_argument("--window-size=1920,1080")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts
    )
    # hide webdriver flag
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator, 'webdriver', {get:()=>undefined});"}
    )
    
    # Increased timeout for slow connections
    wait = WebDriverWait(driver, 30)  # Increased from 20 to 30 seconds

    results_url = None
    
    try:
        driver.get("https://www.thetrainline.com")
        print(" Loaded Trainline homepage")
        save_screenshot(driver, "homepage")
        
        # accept cookies/remove overlays
        try:
            cookie_button = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
            cookie_button.click()
            print(" Accepted cookies")
        except Exception as e:
            print(f" Cookie banner handling: {e}")
            
        try:
            driver.execute_script("document.querySelector('.onetrust-pc-dark-filter')?.remove();")
        except:
            pass
            
        # fill in form
        select_origin_and_destination(driver, departure, destination)
        save_screenshot(driver, "after_stations")
        
        select_date_and_time(
            driver,
            field_id="jsf-outbound-time-input-toggle",
            target_month=date.strftime("%B %Y"),
            target_day=str(date.day),
            hour_val=hr,
            minute_val=mn
        )
        save_screenshot(driver, "after_date_time")

        # remove any remaining overlays
        try:
            driver.execute_script("document.querySelector('.onetrust-pc-dark-filter')?.remove();")
        except:
            pass
            
        # Find and click submit
        try:
            print(" Looking for submit button")
            submit_button = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "button[data-testid='jsf-submit']")
            ))
            print(" Found submit button")
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_button)
            time.sleep(0.5)
            submit_button.click()
            print(" Clicked submit button")
        except Exception as e:
            print(f" Submit button error: {e}")
            save_screenshot(driver, "submit_error")
            
            # Try alternative method
            try:
                buttons = driver.find_elements(By.TAG_NAME, "button")
                for button in buttons:
                    if "search" in button.text.lower():
                        print(f" Found alternative submit button with text: {button.text}")
                        button.click()
                        print(" Clicked alternative submit button")
                        break
            except Exception as e2:
                print(f" Alternative submit failed: {e2}")

        # Wait for the page to load with various checks
        # Increased timeout for this critical step
        longer_wait = WebDriverWait(driver, 45)
        
        print(" Waiting for results page to load...")
        save_screenshot(driver, "after_submit")
        
        # Try multiple possible indicators that the page has loaded
        possible_result_indicators = [
            (By.CSS_SELECTOR, "[data-testid='outbound-journey']"),
            (By.CSS_SELECTOR, ".journey-option"),
            (By.CSS_SELECTOR, ".results-list"),
            (By.CSS_SELECTOR, "[id*='journey']"),
            (By.CSS_SELECTOR, "[class*='result']"),
            (By.CSS_SELECTOR, "h1"),  # Even just finding any H1 is a sign the page loaded
        ]
        
        found_results = False
        for selector_type, selector_value in possible_result_indicators:
            try:
                longer_wait.until(EC.presence_of_element_located((selector_type, selector_value)))
                print(f" Results page loaded - found element: {selector_type}='{selector_value}'")
                found_results = True
                break
            except:
                pass
                
        if not found_results:
            print(" Could not definitively confirm results page loaded")
        
        # Wait a bit to ensure page fully stabilizes
        time.sleep(5)
        
        # Get URL even if we couldn't find result elements
        # Multiple methods to get the URL
        url_methods = [
            lambda: driver.current_url,
            lambda: driver.execute_script("return window.location.href;"),
            lambda: driver.execute_script("return document.URL;")
        ]
        
        for i, url_method in enumerate(url_methods, 1):
            try:
                results_url = url_method()
                if results_url and results_url != "https://www.thetrainline.com/":
                    print(f" Got URL method {i}: {results_url}")
                    break
                else:
                    print(f"️ URL method {i} returned invalid URL: {results_url}")
            except Exception as e:
                print(f" URL method {i} failed: {e}")
        
        # Take a final screenshot of where we ended up
        save_screenshot(driver, "final_page")
            
    except Exception as e:
        print(f" General error: {e}")
    finally:
        # Take a screenshot before quitting if there was an error
        if not results_url or "thetrainline.com" not in results_url:
            save_screenshot(driver, "error_final")
        
        print(" Quitting WebDriver")
        driver.quit()

    # fallback if needed
    if not results_url or "thetrainline.com" not in results_url:
        print(" Using fallback URL generation")
        results_url = build_trainline_link(departure, destination, date, time_of_day)

    return SimpleNamespace(price=None, url=results_url)


if __name__ == "__main__":
    # Quick test harness
    departure = "Norwich"
    destination = "Ipswich"
    travel_date = datetime.date(2025, 7, 15)
    travel_time = "20:00"

    ticket = find_cheapest_ticket(
        departure=departure,
        destination=destination,
        date=travel_date,
        time_of_day=travel_time,
        trip_type="single"
    )
    print("Booking URL:", ticket.url)