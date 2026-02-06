# 📊 Attendance Tracker — TKRCET (No-DB)

- Backend: FastAPI + Selenium (in-memory cache, no database)
- Frontend: Static site (GitHub Pages)
- Deploy backend on Render (Docker), set `frontend/config.js` to your API URL, push to main, Pages workflow publishes.

## 👥 Students Tracked

| Roll Number   | Name      |
|---------------|-----------|
| 24K91A6790    | Kartikey  |
| 24K91A6781    | Hansika   |
| 24K91A6768    | Hanisha   |
| 24K91A05B7   | Srikanth  |
| 24K91A0576   | Dheeraj   |
| 24K91A05C2   | Mahathi   |

## 🚀 Quick Start

```bash
python start.py
```

This starts both the **backend** (port 8000) and **frontend** (port 3000) and opens the browser.

## Manual Start

### Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python main.py
```

### Frontend
```bash
cd frontend
python -m http.server 3000
```

Then open http://localhost:3000

## Deploy
1) Render (backend)
- Connect repo, Web Service (Docker), health check `/api/status`.
- After deploy, note URL, e.g. `https://tkrcet-attendance-backend.onrender.com`.

2) GitHub Pages (frontend)
- Edit `frontend/config.js`:
  ```js
  window.API_BASE = "https://tkrcet-attendance-backend.onrender.com";
  ```
- Commit to `main` or `master`.
- Pages workflow publishes `frontend/`.

## Local Dev
- Backend: `cd backend && pip install -r requirements.txt && uvicorn main:app --reload`
- Frontend: `cd frontend && python -m http.server 3000`

## 📁 Project Structure

```
├── backend/
│   ├── main.py           # FastAPI app (API routes)
│   ├── database.py       # SQLite DB setup & seed data
│   ├── scraper.py        # Selenium scraper (attendance logic)
│   ├── requirements.txt  # Python dependencies
│   └── attendance.db     # SQLite database (auto-created)
├── frontend/
│   ├── index.html        # Main page
│   ├── style.css         # Dark theme styles
│   └── script.js         # Fetch & render logic
├── start.py              # One-click launcher
└── README.md
```

## 🔄 How It Works

1. Open the dashboard at `http://localhost:3000`
2. Click **Refresh Attendance** to scrape from the college portal
3. The backend uses Selenium (headless Chrome) to log into each student's account
4. Attendance percentages are stored in SQLite
5. The frontend polls for updates and displays the results with progress bars & stats
