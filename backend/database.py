# No-DB stub for compatibility
# Keeps minimal in-memory structures to avoid crashes if imported
import os
from typing import List, Dict
from datetime import datetime

# Seed list (same as backend)
_STUDENTS: List[Dict] = [
    {"roll_number": "24K91A6790", "name": "Kartikey"},
    {"roll_number": "24K91A6781", "name": "Hansika"},
    {"roll_number": "24K91A6768", "name": "Hanisha"},
    {"roll_number": "24K91A05B7", "name": "Srikanth"},
    {"roll_number": "24K91A0576", "name": "Dheeraj"},
    {"roll_number": "24K91A05C2", "name": "Mahathi"},
    {"roll_number": "24K91A05W8", "name": "Praneeth"},
]

# In-memory history per roll (non-persistent)
_HISTORY: Dict[str, List[Dict]] = {s["roll_number"]: [] for s in _STUDENTS}


def init_db():
    # No-op
    return None


def get_students() -> List[Dict]:
    return _STUDENTS.copy()


def insert_attendance_batch(rows: List[Dict]):
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    for r in rows:
        roll = r.get("roll_number")
        if not roll:
            continue
        _HISTORY.setdefault(roll, []).insert(0, {
            "attendance_percent": r.get("attendance_percent"),
            "fetched_at": now,
        })


def get_latest_attendance_for_all() -> List[Dict]:
    out: List[Dict] = []
    for s in _STUDENTS:
        h = _HISTORY.get(s["roll_number"], [])
        rec = h[0] if h else None
        out.append({
            "roll_number": s["roll_number"],
            "name": s["name"],
            "attendance_percent": rec.get("attendance_percent") if rec else None,
            "last_updated": rec.get("fetched_at") if rec else None,
        })
    return out


def get_history_for_roll(roll_number: str, limit: int = 20) -> List[Dict]:
    return (_HISTORY.get(roll_number, []) or [])[:limit]
