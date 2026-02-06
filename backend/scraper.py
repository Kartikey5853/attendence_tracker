import os
from typing import List, Dict, Optional
import time
import re

import requests
from bs4 import BeautifulSoup

LOGIN_URL = "https://103.171.190.44/TKRCET/index.php"
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
    "Referer": LOGIN_URL,
}


def login_and_get_session(roll: str) -> Optional[requests.Session]:
    s = requests.Session()
    s.headers.update(COMMON_HEADERS)

    try:
        # Initial GET
        resp = s.get(LOGIN_URL, timeout=15, verify=False)
        resp.raise_for_status()

        # Parse CSRF if present
        soup = BeautifulSoup(resp.text, "html.parser")
        csrf_token = None
        token_el = soup.find("input", {"name": "csrf_token"})
        if token_el and token_el.get("value"):
            csrf_token = token_el["value"]

        payload = {
            "username": roll,
            "password": roll,
        }
        if csrf_token:
            payload["csrf_token"] = csrf_token

        post_resp = s.post(LOGIN_URL, data=payload, timeout=20, verify=False)
        post_resp.raise_for_status()

        # If post redirects to index or contains frames, consider login success
        if "frame" not in post_resp.text.lower():
            # Some portals redirect; follow landing page
            landing = s.get("https://103.171.190.44/TKRCET/index.php", timeout=15, verify=False)
            if landing.status_code != 200:
                return None
            if "frame" not in landing.text.lower():
                # Still might be a dashboard; proceed anyway
                pass

        return s
    except Exception:
        return None


def discover_attendance_url(session: requests.Session) -> Optional[str]:
    """After login, load the main menu frame and find the attendance link href."""
    try:
        # Load the frameset or dashboard
        resp = session.get("https://103.171.190.44/TKRCET/index.php", timeout=15, verify=False)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find frame src for menu (first frame usually)
        menu_frame = soup.find("frame")
        menu_src = menu_frame.get("src") if menu_frame else None
        if not menu_src:
            # Try frameset tag
            frames = soup.find_all("frame")
            if frames:
                menu_src = frames[0].get("src")
        if not menu_src:
            return None

        # Fetch the menu frame content
        menu_resp = session.get(requests.compat.urljoin(LOGIN_URL, menu_src), timeout=15, verify=False)
        menu_resp.raise_for_status()
        menu_soup = BeautifulSoup(menu_resp.text, "html.parser")

        # Find link with text containing 'Attendance' or exact anchor structure used earlier
        link = None
        # Try by text
        for a in menu_soup.find_all("a"):
            txt = a.get_text(strip=True).lower()
            if "attendance" in txt:
                link = a
                break
        if not link:
            # Try precise xpath-original path fallback by navigating tables
            link = menu_soup.find("a", string=lambda t: t and "attendance" in t.lower())
        if not link:
            return None

        href = link.get("href")
        if not href:
            return None

        return requests.compat.urljoin(LOGIN_URL, href)
    except Exception:
        return None


def parse_attendance_percentage(html: str) -> Optional[str]:
    soup = BeautifulSoup(html, "html.parser")
    percentage_text = None

    # Look near heading
    heading = soup.find(lambda tag: tag.name in ["h5", "h4", "h3"] and "Student Attendance Report" in tag.get_text(strip=True))
    if heading:
        table = heading.find_next("table")
        if table:
            strongs = table.select("tbody tr td strong")
            for st in reversed(strongs):
                txt = st.get_text(strip=True)
                if re.search(r"\d+\.\d+%|\d+%", txt):
                    percentage_text = txt
                    break
    if not percentage_text:
        # Generic search
        m = re.search(r"(\d{1,3}\.\d{1,2}%|\d{1,3}%)", soup.get_text(" ", strip=True))
        if m:
            percentage_text = m.group(1)

    return percentage_text


def fetch_attendance_for_roll_http(session: requests.Session, roll: str) -> Dict:
    try:
        att_url = discover_attendance_url(session)
        if not att_url:
            return {"roll_number": roll, "attendance_percent": "ERROR", "error": "attendance url not found"}

        # Load attendance page
        att_resp = session.get(att_url, timeout=20, verify=False)
        att_resp.raise_for_status()

        percentage_text = parse_attendance_percentage(att_resp.text)
        attendance = percentage_text or "ERROR"
        return {"roll_number": roll, "attendance_percent": attendance, "error": None if percentage_text else "not found"}
    except Exception as e:
        return {"roll_number": roll, "attendance_percent": "ERROR", "error": str(e)}


def fetch_all_attendance(max_workers: int = 6, students: Optional[List[Dict]] = None) -> List[Dict]:
    students = students or DEFAULT_STUDENTS
    results: List[Dict] = []

    for s in students:
        roll = s["roll_number"]
        sess = login_and_get_session(roll)
        if not sess:
            results.append({"roll_number": roll, "name": s["name"], "attendance_percent": "ERROR", "error": "login failed"})
            continue
        res = fetch_attendance_for_roll_http(sess, roll)
        results.append({"roll_number": res["roll_number"], "name": s["name"], "attendance_percent": res["attendance_percent"], "error": res.get("error")})
        time.sleep(0.3)

    return results

# Debug helper: fetch raw HTML for a given roll (not exposed via API directly)
def debug_fetch_raw_html(roll: str) -> Dict:
    sess = login_and_get_session(roll)
    if not sess:
        return {"ok": False, "error": "login failed"}
    url = discover_attendance_url(sess)
    if not url:
        return {"ok": False, "error": "attendance url not found"}
    r = sess.get(url, timeout=20, verify=False)
    return {"ok": True, "url": url, "html": r.text[:4000]}
