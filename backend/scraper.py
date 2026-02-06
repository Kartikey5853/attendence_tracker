"""
HTTP-based attendance scraper for TKRCET portal.
Uses requests + BeautifulSoup (no Selenium/Chrome needed).

Flow per student:
  1. GET  index.php              — load login page (get session cookie)
  2. POST index.php              — submit credentials (username=roll, password=roll, login="")
     Server responds with JS redirect: document.location = 'MainFrameset.php'
  3. GET  MainFrameset.php       — follow the JS redirect (validates session)
  4. GET  StudentInformationForStudent.php — the attendance page (loaded in "main" frame)
  5. Parse the last <strong> in the table after "Student Attendance Report" <h5>
"""

import re
import time
import warnings
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from bs4 import BeautifulSoup
from urllib3.exceptions import InsecureRequestWarning

# Suppress SSL warnings (the college portal uses a self-signed cert)
warnings.simplefilter("ignore", InsecureRequestWarning)

BASE_URL = "https://103.171.190.44/TKRCET"
LOGIN_URL = f"{BASE_URL}/index.php"
FRAMESET_URL = f"{BASE_URL}/MainFrameset.php"
ATTENDANCE_URL = f"{BASE_URL}/StudentInformationForStudent.php"

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
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 20


def _fetch_one(roll: str) -> Dict:
    """Scrape attendance percentage for a single roll number."""
    session = requests.Session()
    session.headers.update(COMMON_HEADERS)

    try:
        # Step 1: GET login page (sets PHPSESSID cookie)
        session.get(LOGIN_URL, timeout=TIMEOUT, verify=False)

        # Step 2: POST login
        # The submit button has name="login" — the server requires it
        payload = {"username": roll, "password": roll, "login": ""}
        post_resp = session.post(
            LOGIN_URL, data=payload, timeout=TIMEOUT, verify=False, allow_redirects=True
        )

        # Verify login succeeded: response should start with JS redirect to MainFrameset.php
        if "MainFrameset.php" not in post_resp.text[:200]:
            return {"roll_number": roll, "attendance_percent": None, "error": "login failed"}

        # Step 3: Follow JS redirect — GET the frameset page (validates session)
        session.get(FRAMESET_URL, timeout=TIMEOUT, verify=False)

        # Step 4: GET the attendance page directly
        att_resp = session.get(ATTENDANCE_URL, timeout=TIMEOUT, verify=False)
        att_resp.raise_for_status()

        # Step 5: Parse percentage
        pct = _parse_percentage(att_resp.text)
        if pct:
            return {"roll_number": roll, "attendance_percent": pct, "error": None}
        else:
            return {"roll_number": roll, "attendance_percent": None, "error": "percentage not found in page"}

    except requests.RequestException as e:
        return {"roll_number": roll, "attendance_percent": None, "error": f"request error: {e}"}
    except Exception as e:
        return {"roll_number": roll, "attendance_percent": None, "error": str(e)}


def _parse_percentage(html: str) -> Optional[str]:
    """
    Find the overall attendance percentage in the attendance page HTML.
    Structure: <h5>Student Attendance Report …</h5> followed by a <table>.
    The last <strong> in that table holds the percentage (e.g. "64.00%").
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find the heading
    heading = soup.find(
        lambda tag: tag.name in ("h5", "h4", "h3", "h2")
        and "attendance" in tag.get_text(strip=True).lower()
    )
    if not heading:
        return None

    # The attendance table is the first <table> after the heading
    table = heading.find_next("table")
    if not table:
        return None

    # Walk <strong> tags in reverse — the last one with a percentage pattern is what we want
    for strong in reversed(table.find_all("strong")):
        txt = strong.get_text(strip=True)
        if re.search(r"\d+\.\d+%", txt):
            return txt

    # Fallback: search for any percentage pattern in the table text
    m = re.search(r"(\d{1,3}\.\d{1,2}%)", table.get_text(" ", strip=True))
    if m:
        return m.group(1)

    return None


def fetch_all_attendance(
    max_workers: int = 6,
    students: Optional[List[Dict]] = None,
) -> List[Dict]:
    """Fetch attendance for all students, optionally in parallel."""
    students = students or DEFAULT_STUDENTS
    results: List[Dict] = []

    # Use ThreadPoolExecutor for parallel fetching
    roll_to_name = {s["roll_number"]: s["name"] for s in students}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_fetch_one, s["roll_number"]): s["roll_number"]
            for s in students
        }
        for future in as_completed(futures):
            res = future.result()
            roll = res["roll_number"]
            results.append({
                "roll_number": roll,
                "name": roll_to_name.get(roll, ""),
                "attendance_percent": res["attendance_percent"],
                "error": res.get("error"),
            })

    # Sort by original order
    order = {s["roll_number"]: i for i, s in enumerate(students)}
    results.sort(key=lambda r: order.get(r["roll_number"], 999))
    return results
