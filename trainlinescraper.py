# trainlinescraper.py


import datetime
import time
from types import SimpleNamespace
from urllib.parse import urlencode

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def select_origin_and_destination(driver, origin, destination):
    wait = WebDriverWait(driver, 20)

    # ----- ORIGIN -----
    origin_trigger = wait.until(EC.element_to_be_clickable((By.ID, "jsf-origin-input")))
    origin_trigger.click()
    print("✅ Clicked origin input")

    origin_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[data-testid='jsf-origin']")))
    origin_input.clear()
    origin_input.send_keys(origin)
    print(f"⌨️ Typed origin: {origin}")
    time.sleep(1.5)
    origin_input.send_keys(Keys.RETURN)
    time.sleep(1)

    selected_origin = driver.find_element(By.ID, "jsf-origin-input").get_attribute("value")
    if origin.lower() in selected_origin.lower():
        print(f"✅ Origin confirmed: {selected_origin}")
    else:
        print(f"❌ Origin mismatch: Got '{selected_origin}', expected '{origin}'")

    # ----- DESTINATION -----
    dest_trigger = wait.until(EC.element_to_be_clickable((By.ID, "jsf-destination-input")))
    dest_trigger.click()
    print("✅ Clicked destination input")

    dest_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[data-testid='jsf-destination']")))
    dest_input.clear()
    dest_input.send_keys(destination)
    print(f"⌨️ Typed destination: {destination}")
    time.sleep(1.5)
    dest_input.send_keys(Keys.RETURN)
    time.sleep(1)

    selected_dest = driver.find_element(By.ID, "jsf-destination-input").get_attribute("value")
    if destination.lower() in selected_dest.lower():
        print(f"✅ Destination confirmed: {selected_dest}")
    else:
        print(f"❌ Destination mismatch: Got '{selected_dest}', expected '{destination}'")


def select_date_and_time(driver, field_id, target_month, target_day, hour_val, minute_val):
    wait = WebDriverWait(driver, 15)
    print(f"🔍 Looking for: {target_month} {target_day}")

    # Open calendar
    field = wait.until(EC.element_to_be_clickable((By.ID, field_id)))
    driver.execute_script("arguments[0].click();", field)
    print("📅 Calendar field clicked")

    # Navigate calendar
    for _ in range(12):
        month_label = driver.find_element(By.ID, "datetime-picker-label").text.strip()
        print(f"📆 Current calendar: {month_label}")

        if month_label == target_month:
            print("✅ Month found")
            try:
                day_button = driver.find_element(
                    By.CSS_SELECTOR,
                    f'button[data-testid="jsf-calendar-date-button-{target_day}"]'
                )
                driver.execute_script("arguments[0].scrollIntoView(true);", day_button)
                day_button.click()
                print(f"✅ Selected: {target_month} {target_day}")

                time.sleep(1)

                # Select hour and minute
                Select(driver.find_element(By.ID, "jsf-outbound-time-time-picker-hour")).select_by_value(hour_val)
                Select(driver.find_element(By.ID, "jsf-outbound-time-time-picker")).select_by_value(minute_val)
                print(f"⏰ Time set to {hour_val}:{minute_val}")

                return {"status": f"Selected {target_month} {target_day} {hour_val}:{minute_val}"}
            except Exception as e:
                print(f"❌ Could not click day {target_day} or select time:", e)
                return {"error": f"Could not complete selection for {target_day}"}
        else:
            driver.find_element(By.CSS_SELECTOR, 'button[data-testid="calendar-navigate-to-next-month"]').click()
            print("⏩ Clicked next month")
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
    wait = WebDriverWait(driver, 20)

    try:
        driver.get("https://www.thetrainline.com")
        # accept cookies/remove overlays
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
        except:
            pass
        driver.execute_script("document.querySelector('.onetrust-pc-dark-filter')?.remove();")

        # fill in form
        select_origin_and_destination(driver, departure, destination)
        select_date_and_time(
            driver,
            field_id="jsf-outbound-time-input-toggle",
            target_month=date.strftime("%B %Y"),
            target_day=str(date.day),
            hour_val=hr,
            minute_val=mn
        )

        # submit
        driver.execute_script("document.querySelector('.onetrust-pc-dark-filter')?.remove();")
        wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button[data-testid='jsf-submit']")
        )).click()

        # wait & grab URL
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='outbound-journey']")))
            results_url = driver.execute_script("return window.location.href;")
        except TimeoutException:
            results_url = None

    finally:
        driver.quit()

    # fallback if needed
    if not results_url:
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