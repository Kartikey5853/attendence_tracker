import os
from typing import List, Dict, Optional
import time
import re

import requests
from bs4 import BeautifulSoup

LOGIN_URL = "https://103.171.190.44/TKRCET/index.php"
# After inspecting the app, the attendance report is linked from the menu and loads inside the main frame.
# On the HTTP layer, it resolves to a PHP endpoint. Adjust path if your deployment differs.
ATTENDANCE_ENDPOINT = "https://103.171.190.44/TKRCET/student_attendance_report.php"

DEFAULT_STUDENTS: List[Dict] = [
    {"roll_number": "24K91A6790", "name": "Kartikey"},
    {"roll_number": "24K91A6781", "name": "Hansika"},
    {"roll_number": "24K91A6768", "name": "Hanisha"},
    {"roll_number": "24K91A05B7", "name": "Srikanth"},
    {"roll_number": "24K91A0576", "name": "Dheeraj"},
    {"roll_number": "24K91A05C2", "name": "Mahathi"},
    {"roll_number": "24K91A05W8", "name": "Praneeth"},
]

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def login_and_get_session(roll: str) -> Optional[requests.Session]:
    """Perform login with requests and return an authenticated session.
    Assumes form fields 'username' and 'password' as in Selenium version.
    """
    s = requests.Session()
    s.headers.update(COMMON_HEADERS)

    try:
        # 1) GET login page to obtain cookies (and any CSRF tokens, if present)
        resp = s.get(LOGIN_URL, timeout=15, verify=False)
        resp.raise_for_status()

        # Optionally parse CSRF tokens if the form uses them (not observed in Selenium flow)
        csrf_token = None
        soup = BeautifulSoup(resp.text, "html.parser")
        token_el = soup.find("input", {"name": "csrf_token"})
        if token_el and token_el.get("value"):
            csrf_token = token_el["value"]

        # 2) POST credentials
        payload = {
            "username": roll,
            "password": roll,
        }
        if csrf_token:
            payload["csrf_token"] = csrf_token

        post_resp = s.post(LOGIN_URL, data=payload, timeout=20, verify=False)
        post_resp.raise_for_status()

        # Check login success by looking for a known element or redirect pattern
        if "Invalid" in post_resp.text or "login" in post_resp.url.lower():
            # Some portals redirect back to login on failure
            return None

        return s
    except Exception:
        return None


def fetch_attendance_for_roll_http(session: requests.Session, roll: str) -> Dict:
    """Use an authenticated session to fetch attendance percentage for a single roll.
    Navigates directly to the attendance endpoint and parses the summary table.
    """
    try:
        # Some systems require a menu click before the report; often a GET to a menu endpoint.
        # If your portal needs an intermediate request, add it here.
        # Example placeholder (commented):
        # session.get("https://103.171.190.44/TKRCET/menu.php?open=attendance", timeout=10, verify=False)

        # Fetch the attendance report page
        resp = session.get(ATTENDANCE_ENDPOINT, timeout=20, verify=False)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Strategy 1: Find the table near the heading "Student Attendance Report" and read last <td><strong>
        heading = soup.find(lambda tag: tag.name in ["h5", "h4", "h3"] and "Student Attendance Report" in tag.get_text(strip=True))
        percentage_text = None

        if heading:
            # find the first table after the heading
            table = heading.find_next("table")
            if table:
                # look for last cell with strong
                strongs = table.select("tbody tr td strong")
                for st in reversed(strongs):
                    txt = st.get_text(strip=True)
                    if re.search(r"\d+\.\d+%|\d+%", txt):
                        percentage_text = txt
                        break

        # Strategy 2: Fallback - search any text matching percentage pattern
        if not percentage_text:
            m = re.search(r"(\d{1,3}\.\d{1,2}%|\d{1,3}%)", soup.get_text(" ", strip=True))
            if m:
                percentage_text = m.group(1)

        attendance = percentage_text or "ERROR"
        return {"roll_number": roll, "attendance_percent": attendance, "error": None if percentage_text else "not found"}
    except Exception as e:
        return {"roll_number": roll, "attendance_percent": "ERROR", "error": str(e)}


def fetch_all_attendance(max_workers: int = 6, students: Optional[List[Dict]] = None) -> List[Dict]:
    """HTTP-based parallel scraping using sessions per student.
    Render free tier friendly (no browser).
    """
    students = students or DEFAULT_STUDENTS

    results: List[Dict] = []

    # Simple sequential loop is usually fast enough without browser startup; still can parallelize if needed
    # but many hosts limit concurrent network calls. We'll keep it simple and reliable.
    for s in students:
        roll = s["roll_number"]
        sess = login_and_get_session(roll)
        if not sess:
            results.append({"roll_number": roll, "name": s["name"], "attendance_percent": "ERROR", "error": "login failed"})
            continue
        res = fetch_attendance_for_roll_http(sess, roll)
        results.append({"roll_number": res["roll_number"], "name": s["name"], "attendance_percent": res["attendance_percent"], "error": res.get("error")})
        time.sleep(0.3)  # small delay to be gentle

    return results
