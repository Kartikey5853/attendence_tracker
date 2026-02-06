from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import List, Dict, Optional
import os

LOGIN_URL = "https://103.171.190.44/TKRCET/index.php"

# Default seed if none provided
DEFAULT_STUDENTS: List[Dict] = [
    {"roll_number": "24K91A6790", "name": "Kartikey"},
    {"roll_number": "24K91A6781", "name": "Hansika"},
    {"roll_number": "24K91A6768", "name": "Hanisha"},
    {"roll_number": "24K91A05B7", "name": "Srikanth"},
    {"roll_number": "24K91A0576", "name": "Dheeraj"},
    {"roll_number": "24K91A05C2", "name": "Mahathi"},
]


def create_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    # Headless and container-friendly flags
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")

    # Disable images and fonts to speed up
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2,
    }
    options.add_experimental_option("prefs", prefs)

    # Optional binary location (for containers)
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin

    # Faster page load strategy (Selenium 4 way)
    options.page_load_strategy = "eager"

    return webdriver.Chrome(options=options)


def fetch_attendance_for_roll(roll: str) -> Dict:
    driver = None
    try:
        driver = create_driver()
        userid = password = roll

        driver.get(LOGIN_URL)

        # Login
        driver.find_element(By.ID, "username").send_keys(userid)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.XPATH, '//*[@id="loginForm"]/div/div[3]/div/div[2]/button').click()

        # Wait for frames
        WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "frame")))

        # Menu frame
        driver.switch_to.frame(0)
        WebDriverWait(driver, 10).until(lambda d: d.execute_script("return typeof index === 'function'"))
        driver.execute_script("index('a:b+0','b')")
        driver.execute_script("index('a:b:bd+3', 'bd')")
        driver.find_element(By.XPATH, "/html/body/table[6]/tbody/tr/td[4]/table/tbody/tr/td/nobr/font/a").click()

        # Main frame
        driver.switch_to.default_content()
        driver.switch_to.frame("main")

        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//h5[contains(text(),'Student Attendance Report')]")))

        percentage_cell = driver.find_element(By.XPATH, "//h5[contains(text(),'Student Attendance Report')]/following::table[1]//tbody/tr/td[last()]//strong")
        attendance = percentage_cell.text.strip()
        return {"roll_number": roll, "attendance_percent": attendance, "error": None}
    except Exception as e:
        return {"roll_number": roll, "attendance_percent": "ERROR", "error": str(e)}
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def fetch_all_attendance(max_workers: int = 6, students: Optional[List[Dict]] = None) -> List[Dict]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    students = students or DEFAULT_STUDENTS
    results: List[Dict] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_attendance_for_roll, s["roll_number"]): s for s in students}
        for fut in as_completed(futures):
            s = futures[fut]
            try:
                res = fut.result(timeout=120)
            except Exception as e:
                res = {"roll_number": s["roll_number"], "attendance_percent": "ERROR", "error": str(e)}
            results.append({"roll_number": res["roll_number"], "name": s["name"], "attendance_percent": res["attendance_percent"], "error": res.get("error")})

    return results
