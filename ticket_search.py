from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def build_calendar_xpath(day: int, month: int, year: int):
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_str = month_names[month - 1]
    formatted_date = f"{month_str} {day:02d} {year}"
    return f"//a[@data-date='{day}' and contains(@aria-label, '{formatted_date}')]"

def search_cheapest_ticket(departure, destination, depart_date_str, return_date_str=None):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        print("Loading site...")
        driver.get("https://www.greateranglia.co.uk/tickets")
        print("Page loaded:", driver.current_url)

        wait = WebDriverWait(driver, 20)

        print("No iframe needed — skipping iframe step")

        # Cookie banner
        try:
            cookie_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept')]"))
            )
            cookie_btn.click()
            print("✅ Cookie accepted")
        except:
            print("No cookie banner")

        # Departure input
        print("Waiting for departure input...")
        from_input = wait.until(EC.presence_of_element_located((By.ID, "from-buy-header")))
        from_input.clear()
        from_input.send_keys(departure)
        from_input.send_keys(Keys.RETURN)
        print("✅ Departure entered")

        # Destination input
        print("Waiting for destination input...")
        to_input = wait.until(EC.presence_of_element_located((By.ID, "to-header")))
        to_input.clear()
        to_input.send_keys(destination)
        to_input.send_keys(Keys.RETURN)
        print("✅ Destination entered")

        # Outbound date
        print("Selecting outbound date...")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'Outbound')]"))).click()
        d_day, d_month, d_year = map(int, depart_date_str.split("-")[::-1])
        wait.until(EC.element_to_be_clickable((By.XPATH, build_calendar_xpath(d_day, d_month, d_year)))).click()
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Set')]"))).click()
        print("✅ Outbound date selected")

        # Return date
        if return_date_str:
            print("Selecting return date...")
            wait.until(EC.element_to_be_clickable((By.XPATH, "//label[contains(text(), 'Return')]"))).click()
            r_day, r_month, r_year = map(int, return_date_str.split("-")[::-1])
            wait.until(EC.element_to_be_clickable((By.XPATH, build_calendar_xpath(r_day, r_month, r_year)))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Set')]"))).click()
            print("✅ Return date selected")

        # Search button
        print("Clicking search button...")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Search')]"))).click()

        # Extract price
        print("Waiting for ticket price...")
        price_element = wait.until(
            EC.presence_of_element_located((By.XPATH, "//span[@data-test='standard-ticket-price']"))
        )
        price = price_element.text.strip()
        print("✅ Price found:", price)

        return {
            "departure": departure,
            "destination": destination,
            "depart_date": depart_date_str,
            "return_date": return_date_str,
            "price": price,
            "link": driver.current_url,
            "ticket_type": "Return" if return_date_str else "Single"
        }

    except Exception as e:
        print("❌ Scraper error:", e)
        return {"error": str(e)}
    finally:
        driver.quit()

if __name__ == "__main__":
    result = search_cheapest_ticket(
        "Norwich", "London Liverpool Street", "2025-05-06", "2025-05-16"
    )
    print("🎯 Final Result:", result)
