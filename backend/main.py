from fastapi import FastAPI, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from scraper import fetch_all_attendance
from database import init_db, get_students as db_get_students, insert_attendance_batch, get_latest_attendance_for_all, get_history_for_roll
from datetime import datetime
from typing import List, Dict

app = FastAPI(title="Attendance Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scraping_status = {"is_running": False, "last_run": None, "message": ""}


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/students")
def get_students():
    return {"students": get_latest_attendance_for_all(), "status": scraping_status}


@app.get("/api/history/{roll_number}")
def history(roll_number: str):
    return {"history": get_history_for_roll(roll_number)}


@app.post("/api/refresh")
def refresh(background_tasks: BackgroundTasks, workers: int = Query(6, ge=1, le=8)):
    if scraping_status["is_running"]:
        return {"message": "Scraping is already in progress. Please wait."}
    background_tasks.add_task(_run_scraper, workers)
    return {"message": f"Attendance refresh started with {workers} workers..."}


def _run_scraper(workers: int):
    global scraping_status
    scraping_status["is_running"] = True
    scraping_status["message"] = f"Fetching attendance from college portal (x{workers})..."
    try:
        students = db_get_students()
        scraped = fetch_all_attendance(max_workers=workers, students=students)
        # Persist last results in memory history
        rows = [{"roll_number": r["roll_number"], "attendance_percent": r["attendance_percent"]} for r in scraped]
        insert_attendance_batch(rows)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        scraping_status["message"] = "Attendance updated successfully!"
        scraping_status["last_run"] = now
    except Exception as e:
        scraping_status["message"] = f"Error: {str(e)}"
    finally:
        scraping_status["is_running"] = False


@app.get("/api/status")
def status():
    return scraping_status


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
