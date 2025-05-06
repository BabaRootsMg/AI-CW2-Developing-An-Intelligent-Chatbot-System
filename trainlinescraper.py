from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def select_stations_with_check(origin, destination):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    driver = webdriver.Chrome(options=chrome_options)

    try:
        driver.get("https://www.thetrainline.com")
        wait = WebDriverWait(driver, 20)
        time.sleep(2)

        # Accept cookie banner
        try:
            wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler"))).click()
            print("✅ Cookie banner closed")
            time.sleep(1)
        except:
            print("⚠️ No cookie banner")

        # ----- ORIGIN -----
        origin_trigger = wait.until(EC.element_to_be_clickable((By.ID, "jsf-origin-input")))
        origin_trigger.click()
        print("✅ Clicked origin input")

        origin_input = wait.until(EC.element_to_be_clickable((By.ID, "jsf-origin")))
        origin_input.clear()
        origin_input.send_keys(origin)
        print(f"⌨️ Typed origin: {origin}")
        time.sleep(1.5)
        origin_input.send_keys(Keys.RETURN)
        time.sleep(1)

        selected_origin = driver.find_element(By.ID, "jsf-origin-input").get_attribute("value")
        if origin.lower() not in selected_origin.lower():
            print(f"❌ Origin mismatch: Got '{selected_origin}', expected '{origin}'")
            return {"error": f"Origin mismatch: got '{selected_origin}'"}
        print(f"✅ Origin confirmed: {selected_origin}")

        # ----- DESTINATION -----
        dest_trigger = wait.until(EC.element_to_be_clickable((By.ID, "jsf-destination-input")))
        dest_trigger.click()
        print("✅ Clicked destination input")

        dest_input = wait.until(EC.element_to_be_clickable((By.ID, "jsf-destination")))
        dest_input.clear()
        dest_input.send_keys(destination)
        print(f"⌨️ Typed destination: {destination}")
        time.sleep(1.5)
        dest_input.send_keys(Keys.RETURN)
        time.sleep(1)

        selected_dest = driver.find_element(By.ID, "jsf-destination-input").get_attribute("value")
        if destination.lower() not in selected_dest.lower():
            print(f"❌ Destination mismatch: Got '{selected_dest}', expected '{destination}'")
            return {"error": f"Destination mismatch: got '{selected_dest}'"}
        print(f"✅ Destination confirmed: {selected_dest}")

        return {"status": f"From {selected_origin} to {selected_dest}"}

    except Exception as e:
        print("❌ Error:", e)
        return {"error": str(e)}
    finally:
        driver.quit()


if __name__ == "__main__":
    test_cases = [
        ("Norwich", "London Liverpool Street"),
        ("Cambridge", "Ipswich"),
        ("Egham", "Clapham Junction"),
        ("losesdf123", "Paddington"),  # Invalid origin
        ("Norwich", "garbageasdf123"),     # Invalid destination
    ]

    for origin, destination in test_cases:
        print(f"\n🔍 Testing journey: {origin} → {destination}")
        result = select_stations_with_check(origin, destination)
        print("🎯 Final Result:", result)

