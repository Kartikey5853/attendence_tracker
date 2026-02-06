from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from typing import List, Dict, Optional
import os
import threading
from queue import Queue, Empty

LOGIN_URL = "https://103.171.190.44/TKRCET/index.php"

# Default seed if none provided
DEFAULT_STUDENTS: List[Dict] = [
    {"roll_number": "24K91A6790", "name": "Kartikey"},
    {"roll_number": "24K91A6781", "name": "Hansika"},
    {"roll_number": "24K91A6768", "name": "Hanisha"},
    {"roll_number": "24K91A05B7", "name": "Srikanth"},
    {"roll_number": "24K91A0576", "name": "Dheeraj"},
    {"roll_number": "24K91A05C2", "name": "Mahathi"},
    {"roll_number": "24K91A05W8", "name": "Praneeth"},
]


def create_driver() -> webdriver.Chrome:
    options = webdriver.ChromeOptions()
    # Headless and container-friendly flags
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--window-size=1366,768")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--remote-debugging-port=9222")

    # Speed: disable images/fonts
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2,
    }
    options.add_experimental_option("prefs", prefs)

    # Optional binary location (for containers)
    chrome_bin = os.environ.get("CHROME_BIN")
    if chrome_bin:
        options.binary_location = chrome_bin

    options.page_load_strategy = "eager"

    # Use Selenium 4 manager or provided CHROMEDRIVER
    driver_path = os.environ.get("CHROMEDRIVER")
    service = ChromeService(executable_path=driver_path) if driver_path else ChromeService()
    # Verbose logs to help diagnose
    service.log_output = True

    try:
        return webdriver.Chrome(service=service, options=options)
    except Exception:
        # Retry once after short delay
        try:
            import time
            time.sleep(1)
            return webdriver.Chrome(service=service, options=options)
        except Exception as e:
            raise e


def fetch_with_driver(driver: webdriver.Chrome, roll: str) -> Dict:
    try:
        # Reset session between accounts
        driver.delete_all_cookies()
        driver.get(LOGIN_URL)

        # Login
        driver.find_element(By.ID, "username").send_keys(roll)
        driver.find_element(By.ID, "password").send_keys(roll)
        driver.find_element(By.XPATH, '//*[@id="loginForm"]/div/div[3]/div/div[2]/button').click()

        # Wait for frames
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "frame")))

        # Menu frame
        driver.switch_to.frame(0)
        WebDriverWait(driver, 8).until(lambda d: d.execute_script("return typeof index === 'function'"))
        driver.execute_script("index('a:b+0','b')")
        driver.execute_script("index('a:b:bd+3', 'bd')")
        driver.find_element(By.XPATH, "/html/body/table[6]/tbody/tr/td[4]/table/tbody/tr/td/nobr/font/a").click()

        # Main frame
        driver.switch_to.default_content()
        driver.switch_to.frame("main")

        WebDriverWait(driver, 8).until(EC.presence_of_element_located((By.XPATH, "//h5[contains(text(),'Student Attendance Report')]")))
        percentage_cell = driver.find_element(By.XPATH, "//h5[contains(text(),'Student Attendance Report')]/following::table[1]//tbody/tr/td[last()]//strong")
        attendance = percentage_cell.text.strip()
        return {"roll_number": roll, "attendance_percent": attendance, "error": None}
    except Exception as e:
        return {"roll_number": roll, "attendance_percent": "ERROR", "error": str(e)}
    finally:
        try:
            driver.switch_to.default_content()
        except Exception:
            pass


def fetch_attendance_for_roll(roll: str) -> Dict:
    # Backward-compatible single-use driver fetch
    driver = None
    try:
        driver = create_driver()
        return fetch_with_driver(driver, roll)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


def fetch_all_attendance(max_workers: int = 6, students: Optional[List[Dict]] = None) -> List[Dict]:
    students = students or DEFAULT_STUDENTS

    # Use a small pool of persistent drivers to avoid Chrome startup cost
    task_q: Queue = Queue()
    for s in students:
        task_q.put(s)

    results: List[Dict] = []
    results_lock = threading.Lock()

    def worker_thread():
        driver = create_driver()
        try:
            while True:
                try:
                    s = task_q.get_nowait()
                except Empty:
                    break
                res = fetch_with_driver(driver, s["roll_number"]) if driver else {"roll_number": s["roll_number"], "attendance_percent": "ERROR", "error": "no driver"}
                # Attach name and collect
                res_named = {"roll_number": res["roll_number"], "name": s["name"], "attendance_percent": res.get("attendance_percent"), "error": res.get("error")}
                with results_lock:
                    results.append(res_named)
                task_q.task_done()
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    threads: List[threading.Thread] = []
    for _ in range(max(1, max_workers)):
        t = threading.Thread(target=worker_thread, daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return results
