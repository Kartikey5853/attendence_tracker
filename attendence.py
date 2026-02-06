import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
import time

LOGIN_URL = "https://103.171.190.44/TKRCET/index.php"
FILE_PATH = r"Departments/CSE-B.xlsx"
OUTPUT_PATH = r"Attendence/CSE-B-attendance-6-2-26.xlsx"

df = pd.read_excel(FILE_PATH)

# assuming roll numbers are in 2nd column (change if needed)
roll_numbers = df.iloc[:, 1].astype(str).tolist()

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")  
options.add_argument("--ignore-certificate-errors")
options.add_argument("--ignore-ssl-errors")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")
options.add_argument("--disable-extensions")
options.add_argument("--disable-infobars")
driver = webdriver.Chrome(options=options)

results = []

for roll in roll_numbers:

    if roll.lower() == "nan":
        continue

    userid = password = roll

    try:
        driver.get(LOGIN_URL)

        # login
        driver.find_element(By.ID, "username").send_keys(userid)
        driver.find_element(By.ID, "password").send_keys(password)
        driver.find_element(By.XPATH, '//*[@id="loginForm"]/div/div[3]/div/div[2]/button').click()

        # wait for frames
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "frame"))
        )

        # menu frame
        driver.switch_to.frame(0)

        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return typeof index === 'function'")
        )

        driver.execute_script("index('a:b+0','b')")
        driver.execute_script("index('a:b:bd+3', 'bd')")

        driver.find_element(
            By.XPATH,
            "/html/body/table[6]/tbody/tr/td[4]/table/tbody/tr/td/nobr/font/a"
        ).click()

        # main frame
        driver.switch_to.default_content()
        driver.switch_to.frame("main")

        # wait attendance section
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//h5[contains(text(),'Student Attendance Report')]"
            ))
        )

        # extract percentage
        percentage_cell = driver.find_element(
            By.XPATH,
            "//h5[contains(text(),'Student Attendance Report')]/following::table[1]//tbody/tr/td[last()]//strong"
        )

        attendance = percentage_cell.text.strip()

        print(f"{roll}  ->  {attendance}")

        results.append({
            "Roll Number": roll,
            "Attendance %": attendance
        })

        time.sleep(1)  # small delay (safer for server)

    except Exception as e:
        print(f"ERROR for {roll}:", e)

        results.append({
            "Roll Number": roll,
            "Attendance %": "ERROR"
        })

# close browser
driver.quit()

# save to excel
output_df = pd.DataFrame(results)
output_df.to_excel(OUTPUT_PATH, index=False)

print("\nSaved to:", OUTPUT_PATH)
