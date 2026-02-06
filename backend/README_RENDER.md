# Deploy FastAPI backend to Render

1. Push your repo to GitHub.
2. In Render, create a new Web Service from this repo.
3. Environment: Docker
4. Root directory: `backend/` (Render will detect the Dockerfile inside backend)
5. Region: Any
6. Health check path: `/api/status`
7. After deploy finishes, copy the Render URL, e.g. `https://tkrcet-attendance-backend.onrender.com`.
8. Edit `frontend/config.js` to set:
   ```js
   window.API_BASE = "https://tkrcet-attendance-backend.onrender.com";
   ```
9. Commit & push; GitHub Pages workflow will publish frontend.
