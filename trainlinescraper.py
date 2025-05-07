from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time
from types import SimpleNamespace


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
    print(f"📅 Calendar field clicked")

    # Navigate calendar
    for _ in range(12):
        month_label = driver.find_element(By.ID, "datetime-picker-label").text.strip()
        print(f"📆 Current calendar: {month_label}")

        if month_label == target_month:
            print("✅ Month found")
            try:
                day_button = driver.find_element(By.CSS_SELECTOR,
                    f'button[data-testid="jsf-calendar-date-button-{target_day}"]')
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


def find_cheapest_ticket(departure, destination, date, time_of_day=None, trip_type="single"):
    """
    Wraps your Selenium helper functions into a single call.
    Returns SimpleNamespace(price: float, url: str).
    """
    # ────────────────────────────────────────────────────────────
    # HANDLE MISSING TIME
    if time_of_day is None:
        hr, mn = "00", "00"
    elif isinstance(time_of_day, str):
        hr, mn = time_of_day.split(":")
    else:
        hr, mn = time_of_day.strftime("%H"), time_of_day.strftime("%M")
    # ────────────────────────────────────────────────────────────

    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless")
    opts.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=opts)
    wait   = WebDriverWait(driver, 20)

    try:
        driver.get("https://www.thetrainline.com")

        # Accept cookies if needed
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
        except Exception:
            pass

        # ──────────────────────────────────────────────────────
        # MAKE SURE DARK COOKIE OVERLAY IS GONE
        try:
            wait.until(EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, ".onetrust-pc-dark-filter")
            ))
        except Exception:
            driver.execute_script("""
                const o = document.querySelector('.onetrust-pc-dark-filter');
                if (o) o.remove();
            """)
        # ──────────────────────────────────────────────────────

        # Step 1: select origin & destination
        select_origin_and_destination(driver, departure, destination)

        # Step 2: select date & time
        select_date_and_time(
            driver,
            field_id="jsf-outbound-time-input-toggle",
            target_month=date.strftime("%B %Y"),
            target_day=str(date.day),
            hour_val=hr,
            minute_val=mn
        )

        # Step 3: remove any lingering overlay before submit
        driver.execute_script("""
            const o = document.querySelector('.onetrust-pc-dark-filter');
            if (o) o.remove();
        """)

        # Step 4: Submit search
        btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button[data-testid='jsf-submit']")
        ))
        btn.click()

        # Step 5: Wait for results
        wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "[data-testid='outbound-journey']")
        ))

        # Step 6: Scrape cheapest price & link
        price_txt = driver.find_element(
            By.CSS_SELECTOR,
            ".outbound-journey .ticket-info .price .amount"
        ).text.replace("£", "")
        price = float(price_txt)
        url = driver.find_element(
            By.CSS_SELECTOR,
            ".outbound-journey .cta a"
        ).get_attribute("href")

        return SimpleNamespace(price=price, url=url)

    finally:
        driver.quit()


# ---------- Run Script ----------
if __name__ == "__main__":
    options = webdriver.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get("https://www.thetrainline.com")
        print("🌍 Opened Trainline")
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Accept cookies
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))
            ).click()
            print("✅ Cookie banner closed")
        except:
            print("⚠️ No cookie banner")

        # Step 1: Select stations
        select_origin_and_destination(driver, "Norwich", "London Liverpool Street")

        # Step 2: Select date and time
        result = select_date_and_time(
            driver,
            field_id="jsf-outbound-time-input-toggle",
            target_month="August 2025",
            target_day="20",
            hour_val="18",
            minute_val="15"
        )

        # Step 3: Dismiss calendar
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            body.click()
            time.sleep(1)
            print("🧹 Dismissed calendar/modal")
        except Exception as e:
            print("⚠️ Could not dismiss calendar:", e)

        # Step 4: Click 'Get cheapest tickets'
        search_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[data-testid="jsf-submit"]'))
        )
        search_button.click()
        print("🔎 Clicked 'Get cheapest tickets'")

        # Step 5: Wait for results
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='outbound-journey']"))
        )
        print("✅ Results page loaded")

        print("🎯 Final result:", result)

        input("⏸ Press Enter to close browser...")

    finally:
        driver.quit()
