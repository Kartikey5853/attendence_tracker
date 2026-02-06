const API_BASE = window.API_BASE || (location.hostname === 'localhost' ? 'http://localhost:8000' : 'https://YOUR-RENDER-BACKEND.onrender.com');

// Color palette for avatars
const AVATAR_COLORS = [
    "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e", "#f97316", "#0ea5e9"
];

// On page load
document.addEventListener("DOMContentLoaded", () => {
    loadStudents();
});

async function loadStudents() {
    try {
        const res = await fetch(`${API_BASE}/api/students`);
        const data = await res.json();

        if (data.students && data.students.length > 0) {
            renderCards(data.students);
            updateStats(data.students);
            updateLastUpdated(data.students, data.status);
        }

        const hasData = data.students.some(s => s.attendance_percent !== null);
        document.getElementById("skeletonGrid").style.display = hasData ? "none" : "grid";
        document.getElementById("cardsGrid").style.display = hasData ? "grid" : "none";

        if (data.status && data.status.is_running) {
            showStatus(data.status.message, true);
            pollStatus(2000);
        }
    } catch (err) {
        console.error("Failed to load students:", err);
        showStatus("Cannot connect to backend. Configure API URL in config.js", false);
        document.getElementById("statusBanner").style.display = "block";
        document.getElementById("statusBanner").style.background = "var(--red-bg)";
        document.getElementById("statusBanner").style.borderColor = "rgba(239,68,68,0.25)";
        document.getElementById("statusMessage").style.color = "var(--red)";
    }
}

function renderCards(students) {
    const grid = document.getElementById("cardsGrid");
    grid.innerHTML = "";

    students.forEach((s, i) => {
        const pct = parsePercent(s.attendance_percent);
        const statusClass = getStatusClass(pct);
        const colorClass = getColorClass(pct);
        const initial = s.name.charAt(0).toUpperCase();
        const avatarColor = AVATAR_COLORS[i % AVATAR_COLORS.length];
        const displayPct = pct !== null ? `${pct}%` : "—";

        const card = document.createElement("div");
        card.className = `student-card status-${statusClass}`;
        card.innerHTML = `
            <div class="card-top">
                <div class="student-info">
                    <div class="avatar" style="background:${avatarColor}">${initial}</div>
                    <div>
                        <div class="student-name">${s.name}</div>
                        <div class="student-roll">${s.roll_number}</div>
                    </div>
                </div>
                <div class="attendance-badge ${colorClass}">${displayPct}</div>
            </div>
            <div class="progress-container">
                <div class="progress-label">
                    <span>Attendance</span>
                    <span>${pct !== null ? (pct >= 75 ? '✓ Safe' : '⚠ Low') : 'No data'}</span>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill ${colorClass}" style="width:${pct !== null ? pct : 0}%"></div>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function updateStats(students) {
    const total = students.length;
    let above = 0, below = 0, sum = 0, count = 0;

    students.forEach(s => {
        const pct = parsePercent(s.attendance_percent);
        if (pct !== null) {
            count++;
            sum += pct;
            if (pct >= 75) above++;
            else below++;
        }
    });

    document.getElementById("totalStudents").textContent = total;
    document.getElementById("aboveThreshold").textContent = count > 0 ? above : "-";
    document.getElementById("belowThreshold").textContent = count > 0 ? below : "-";
    document.getElementById("avgAttendance").textContent = count > 0 ? (sum / count).toFixed(1) + "%" : "-";
}

function updateLastUpdated(students, status) {
    const el = document.getElementById("lastUpdatedText");
    const latestRecord = students
        .filter(s => s.last_updated)
        .sort((a, b) => new Date(b.last_updated) - new Date(a.last_updated))[0];

    if (latestRecord) {
        const d = new Date(latestRecord.last_updated + "Z");
        el.textContent = `Last updated: ${d.toLocaleString()}`;
    } else {
        el.textContent = 'No data yet — click "Refresh Attendance" to fetch';
    }
}

async function refreshAttendance() {
    const btn = document.getElementById("refreshBtn");
    const icon = document.getElementById("refreshIcon");
    const text = document.getElementById("refreshText");

    btn.disabled = true;
    icon.classList.add("spinning");
    text.textContent = "Fetching...";

    try {
        const workers = 6; // adjust here if needed
        const res = await fetch(`${API_BASE}/api/refresh?workers=${workers}`, { method: "POST" });
        const data = await res.json();
        showStatus(data.message, true);
        pollStatus(2000);
    } catch (err) {
        showStatus("Failed to start refresh. Is the backend running?", false);
        btn.disabled = false;
        icon.classList.remove("spinning");
        text.textContent = "Refresh Attendance";
    }
}

function showStatus(message, showSpinner) {
    const banner = document.getElementById("statusBanner");
    const spinner = document.getElementById("statusSpinner");
    const msg = document.getElementById("statusMessage");

    banner.style.display = "block";
    banner.style.background = "var(--blue-bg)";
    banner.style.borderColor = "rgba(59,130,246,0.25)";
    msg.style.color = "var(--blue)";
    spinner.style.display = showSpinner ? "block" : "none";
    msg.textContent = message;
}

function hideStatus() {
    document.getElementById("statusBanner").style.display = "none";
}

async function pollStatus(intervalMs = 3000) {
    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/api/status`);
            const status = await res.json();

            if (status.is_running) {
                showStatus(status.message, true);
            } else {
                clearInterval(interval);

                if (status.message.includes("Error")) {
                    showStatus(status.message, false);
                    document.getElementById("statusBanner").style.background = "var(--red-bg)";
                    document.getElementById("statusMessage").style.color = "var(--red)";
                } else {
                    // Success
                    showStatus("✓ " + status.message, false);
                    document.getElementById("statusBanner").style.background = "var(--green-bg)";
                    document.getElementById("statusBanner").style.borderColor = "rgba(34,197,94,0.25)";
                    document.getElementById("statusMessage").style.color = "var(--green)";
                    setTimeout(hideStatus, 4000);
                }

                // Reload data
                loadStudents();

                // Reset button
                const btn = document.getElementById("refreshBtn");
                const icon = document.getElementById("refreshIcon");
                const text = document.getElementById("refreshText");
                btn.disabled = false;
                icon.classList.remove("spinning");
                text.textContent = "Refresh Attendance";
            }
        } catch (err) {
            clearInterval(interval);
        }
    }, intervalMs);
}

// Helpers
function parsePercent(val) {
    if (!val || val === "ERROR" || val === "null") return null;
    const num = parseFloat(val.replace("%", ""));
    return isNaN(num) ? null : num;
}

function getStatusClass(pct) {
    if (pct === null) return "none";
    if (pct >= 75) return "good";
    if (pct >= 65) return "warning";
    return "danger";
}

function getColorClass(pct) {
    if (pct === null) return "none";
    if (pct >= 75) return "good";
    if (pct >= 65) return "warning";
    return "danger";
}
