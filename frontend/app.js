/**
 * TwinCare AI — Web Client Application Logic (SPA router, auth, upload polling, and copilot)
 */

const API_BASE = "/api/v1";
let token = localStorage.getItem("token") || "";
let currentUser = null;
let currentPrediction = null;

// DOM Elements
const views = {
    landing: document.getElementById("landing-view"),
    auth: document.getElementById("auth-view"),
    intake: document.getElementById("intake-view"),
    dashboard: document.getElementById("dashboard-view")
};

// Global Helpers — belt-and-suspenders: set both class AND inline style
function showView(viewName) {
    Object.keys(views).forEach(name => {
        if (views[name]) {
            views[name].classList.remove("active");
            views[name].style.display = "none";
        }
    });
    if (views[viewName]) {
        views[viewName].classList.add("active");
        views[viewName].style.display = "flex";
    }
}

/**
 * Parse a FastAPI error response into a human-readable string.
 * FastAPI can return detail as:
 *   - a plain string: "Invalid credentials"
 *   - a list of validation errors: [{loc:[...], msg:"...", type:"..."}]
 */
function parseApiError(data) {
    if (!data || !data.detail) return "An unknown error occurred.";
    if (typeof data.detail === "string") return data.detail;
    if (Array.isArray(data.detail)) {
        return data.detail
            .map(e => {
                const field = e.loc ? e.loc.slice(1).join(" → ") : "";
                return field ? `${field}: ${e.msg}` : e.msg;
            })
            .join("\n");
    }
    return JSON.stringify(data.detail);
}

function getHeaders() {
    return {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
    };
}

// 1. INITIALIZATION & ROUTING STATE
async function initApp() {
    if (token) {
        try {
            // Validate token & fetch user
            const userRes = await fetch(`${API_BASE}/auth/me`, {
                headers: { "Authorization": `Bearer ${token}` }
            });
            if (!userRes.ok) throw new Error("Invalid session");
            currentUser = await userRes.json();

            // Check intake status
            const intakeRes = await fetch(`${API_BASE}/patient-intake`, { headers: getHeaders() });
            if (intakeRes.status === 404) {
                showView("intake");
            } else if (intakeRes.ok) {
                showView("dashboard");
                loadDashboardData();
            } else {
                showView("landing");
            }
        } catch (err) {
            console.error("Auto-login failed:", err);
            logout();
        }
    } else {
        showView("landing");
    }
}

// 2. LANDING NAVIGATION
document.getElementById("get-started-btn").addEventListener("click", () => {
    showView("auth");
});

// ── COPILOT PANEL TOGGLE ──
function openCopilot() {
    const panel = document.getElementById("copilot-panel");
    if (panel) panel.classList.add("open");
}
function closeCopilot() {
    const panel = document.getElementById("copilot-panel");
    if (panel) panel.classList.remove("open");
}

document.getElementById("copilot-toggle-btn")?.addEventListener("click", openCopilot);
document.getElementById("close-copilot-btn")?.addEventListener("click", closeCopilot);
document.getElementById("copilot-shortcut-card")?.addEventListener("click", () => {
    openCopilot();
    document.getElementById("chat-input")?.focus();
});

// 3. AUTH VIEW (LOGIN / REGISTER TABBING)
const tabLoginBtn = document.getElementById("tab-login-btn");
const tabRegisterBtn = document.getElementById("tab-register-btn");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const authAlert = document.getElementById("auth-alert");

function showAuthAlert(msg, type = "danger") {
    authAlert.textContent = msg;
    authAlert.className = `alert alert-${type}`;
    authAlert.classList.remove("hidden");
}

function hideAuthAlert() {
    authAlert.classList.add("hidden");
}

tabLoginBtn.addEventListener("click", () => {
    tabLoginBtn.classList.add("active");
    tabRegisterBtn.classList.remove("active");
    loginForm.classList.add("active");
    registerForm.classList.remove("active");
    hideAuthAlert();
});

tabRegisterBtn.addEventListener("click", () => {
    tabRegisterBtn.classList.add("active");
    tabLoginBtn.classList.remove("active");
    registerForm.classList.add("active");
    loginForm.classList.remove("active");
    hideAuthAlert();
});

// Form Submission: Login
loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAuthAlert();

    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();
        if (!res.ok) {
            throw new Error(parseApiError(data));
        }

        // Backend returns { token, user } per AuthResponse schema
        token = data.token;
        localStorage.setItem("token", token);
        currentUser = data.user;

        // Check patient intake questionnaire status
        const intakeRes = await fetch(`${API_BASE}/patient-intake`, { headers: getHeaders() });
        if (intakeRes.status === 404) {
            showView("intake");
        } else {
            showView("dashboard");
            loadDashboardData();
        }
    } catch (err) {
        showAuthAlert(err.message);
    }
});

// Form Submission: Register
registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    hideAuthAlert();

    const name = document.getElementById("reg-name").value;
    const email = document.getElementById("reg-email").value;
    const dob = document.getElementById("reg-dob").value;
    const gender = document.getElementById("reg-gender").value;
    const password = document.getElementById("reg-password").value;

    try {
        const regRes = await fetch(`${API_BASE}/auth/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password, full_name: name, date_of_birth: dob, gender })
        });

        const regData = await regRes.json();
        if (!regRes.ok) {
            throw new Error(parseApiError(regData));
        }

        // Auto-login after registration (backend returns token+user on register too)
        token = regData.token;
        localStorage.setItem("token", token);
        currentUser = regData.user;

        // Route to questionnaire
        showView("intake");
    } catch (err) {
        showAuthAlert(err.message);
    }
});

// 4. PATIENT CLINICAL HISTORY INTAKE
const intakeForm = document.getElementById("intake-form");
const intakeAlert = document.getElementById("intake-alert");
const intakeSmoker = document.getElementById("intake-smoker");
const cigsGroup = document.getElementById("cigs-per-day-group");
const intakeCigsInput = document.getElementById("intake-cigs");

// Toggle cigs group visibility based on smoking status
intakeSmoker.addEventListener("change", () => {
    if (intakeSmoker.value === "true") {
        cigsGroup.classList.remove("hidden");
        intakeCigsInput.required = true;
    } else {
        cigsGroup.classList.add("hidden");
        intakeCigsInput.required = false;
        intakeCigsInput.value = "0";
    }
});

intakeForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    intakeAlert.classList.add("hidden");

    const payload = {
        education: parseInt(document.getElementById("intake-education").value),
        current_smoker: document.getElementById("intake-smoker").value === "true",
        cigs_per_day: parseInt(intakeCigsInput.value || 0),
        bp_meds: document.getElementById("intake-bpmeds").value === "true",
        prevalent_stroke: document.getElementById("intake-stroke").value === "true",
        prevalent_hyp: document.getElementById("intake-hyp").value === "true",
        diabetes: document.getElementById("intake-diabetes").value === "true",
        doctors_prescription: document.getElementById("intake-prescription").value
    };

    try {
        const res = await fetch(`${API_BASE}/patient-intake`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || "Intake submission failed");
        }

        // Launch Dashboard
        showView("dashboard");
        loadDashboardData();
    } catch (err) {
        intakeAlert.textContent = err.message;
        intakeAlert.className = "alert alert-danger";
        intakeAlert.classList.remove("hidden");
    }
});

// Load patient questionnaire details when editing
document.getElementById("edit-intake-btn").addEventListener("click", async () => {
    try {
        const res = await fetch(`${API_BASE}/patient-intake`, { headers: getHeaders() });
        if (!res.ok) throw new Error();
        const data = await res.json();

        // Populate fields
        document.getElementById("intake-education").value = data.education || "";
        document.getElementById("intake-smoker").value = data.current_smoker ? "true" : "false";
        intakeCigsInput.value = data.cigs_per_day || 0;
        document.getElementById("intake-bpmeds").value = data.bp_meds ? "true" : "false";
        document.getElementById("intake-stroke").value = data.prevalent_stroke ? "true" : "false";
        document.getElementById("intake-hyp").value = data.prevalent_hyp ? "true" : "false";
        document.getElementById("intake-diabetes").value = data.diabetes ? "true" : "false";
        document.getElementById("intake-prescription").value = data.doctors_prescription || "";

        // Trigger toggles
        if (data.current_smoker) {
            cigsGroup.classList.remove("hidden");
        } else {
            cigsGroup.classList.add("hidden");
        }

        showView("intake");
    } catch (err) {
        console.error("Failed to load intake history for editing.");
    }
});

// 5. DASHBOARD POPULATION & COMPUTATION
async function loadDashboardData() {
    if (!currentUser) return;

    // Time-aware greeting
    const hour = new Date().getHours();
    const greeting = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
    const firstName = currentUser.full_name ? currentUser.full_name.split(" ")[0] : "there";
    document.getElementById("user-greeting").textContent = `${greeting}, ${firstName}`;

    // Build weekly strip
    buildWeekStrip();

    // Load clinical profile (intake features)
    loadClinicalProfile();

    try {
        const t0 = performance.now();

        // A. Load digital twin (organ scores, health score, current biomarkers)
        const twinRes = await fetch(`${API_BASE}/digital-twin`, { headers: getHeaders() });
        if (twinRes.ok) {
            const twin = await twinRes.json();
            updateDigitalTwinTiles(twin);
        }

        // B. Load CVD Predictions list
        const predRes = await fetch(`${API_BASE}/risk-predictions`, { headers: getHeaders() });
        if (predRes.ok) {
            const predData = await predRes.json();
            if (predData.predictions && predData.predictions.length > 0) {
                currentPrediction = predData.predictions[0];
                updatePredictionTile(currentPrediction);
            } else {
                resetPredictionTile();
            }
        }

        // C. Dashboard AI insight
        const dashRes = await fetch(`${API_BASE}/dashboard`, { headers: getHeaders() });
        if (dashRes.ok) {
            const dash = await dashRes.json();
            // Update insight text in copilot chat history
            appendAIInsight(dash.ai_insight);
        }

        const elapsed = Math.round(performance.now() - t0);
        const latEl = document.getElementById("amd-latency");
        if (latEl) latEl.textContent = elapsed;

    } catch (err) {
        console.error("Error loading dashboard data:", err);
    }
}

// Build the weekly S M T W T F S strip with today highlighted
function buildWeekStrip() {
    const strip = document.getElementById("week-strip");
    if (!strip) return;
    const days = ["S", "M", "T", "W", "T", "F", "S"];
    const today = new Date().getDay(); // 0=Sun
    strip.innerHTML = days.map((d, i) => `
        <div class="week-day ${i === today ? 'active-day' : ''}">
            <span>${d}</span>
            <div class="day-dot"></div>
        </div>
    `).join("");
}

// Update twin score and organ system bars
function updateDigitalTwinTiles(twin) {
    const score = twin.health_score ? Math.round(twin.health_score) : 0;

    // Health score text
    const scoreEl = document.getElementById("health-score-val");
    if (scoreEl) scoreEl.textContent = score;

    // Organ systems status bars
    const organs = twin.organ_scores || {};
    const heartScore = organs.heart ? Math.round(organs.heart * 100) : 0;
    const metabolicScore = organs.metabolic ? Math.round(organs.metabolic * 100) : 0;
    const liverScore = organs.liver ? Math.round(organs.liver * 100) : 0;
    const kidneyScore = organs.kidney ? Math.round(organs.kidney * 100) : 0;

    document.getElementById("organ-heart-bar").style.width = `${heartScore}%`;
    document.getElementById("organ-heart-val").textContent = `${heartScore}%`;
    document.getElementById("organ-metabolic-bar").style.width = `${metabolicScore}%`;
    document.getElementById("organ-metabolic-val").textContent = `${metabolicScore}%`;
    document.getElementById("organ-liver-bar").style.width = `${liverScore}%`;
    document.getElementById("organ-liver-val").textContent = `${liverScore}%`;
    document.getElementById("organ-kidney-bar").style.width = `${kidneyScore}%`;
    document.getElementById("organ-kidney-val").textContent = `${kidneyScore}%`;

    // Biomarkers
    const bios = twin.current_biomarkers || {};
    const getVal = (name) => bios[name] ? parseFloat(bios[name].value) : null;
    const getStatus = (name) => bios[name] ? bios[name].status : "";

    // 1. Blood Pressure
    const sys = getVal("systolic_bp");
    const dia = getVal("diastolic_bp");
    if (sys && dia) {
        const bpStr = `${Math.round(sys)}/${Math.round(dia)}`;
        document.getElementById("bp-val").textContent = bpStr;
        document.getElementById("bio-bp").innerHTML = `${bpStr} <span class="bio-leg-unit">mmHg</span>`;

        // Animate inner teal ring: scale 0-180/120 → 0-100%
        const bpPct = Math.min((sys / 180), 1);
        animateRing("ring-bp", 213.63, bpPct);

        // BP status markers
        ["bp-marker-normal", "bp-marker-warn", "bp-marker-danger"].forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.classList.remove("active", "normal", "warning", "danger"); }
        });
        if (sys >= 140 || dia >= 90) {
            const el = document.getElementById("bp-marker-danger");
            if (el) el.classList.add("active", "danger");
        } else if (sys >= 120 || dia >= 80) {
            const el = document.getElementById("bp-marker-warn");
            if (el) el.classList.add("active", "warning");
        } else {
            const el = document.getElementById("bp-marker-normal");
            if (el) el.classList.add("active", "normal");
        }
        const pp = sys - dia;
        const map = dia + (sys - dia) / 3;
        document.getElementById("bp-pp").textContent = `${Math.round(pp)} mmHg`;
        document.getElementById("bp-map").textContent = `${Math.round(map)} mmHg`;
    } else {
        document.getElementById("bp-val").textContent = "--";
    }

    // 2. Cholesterol — middle purple ring
    const chol = getVal("total_cholesterol");
    const cholStatus = getStatus("total_cholesterol");
    if (chol) {
        const cholRounded = Math.round(chol);
        document.getElementById("chol-val").textContent = cholRounded;
        document.getElementById("bio-cholesterol").innerHTML = `${cholRounded} <span class="bio-leg-unit">mg/dL</span>`;
        document.getElementById("chol-status-text").textContent = cholStatus === "high" ? "High Level" : "Healthy Range";
        // Purple middle ring: 0-300 mg/dL → 0-100%
        animateRing("ring-cholesterol", 314.16, Math.min(chol / 300, 1));
    } else {
        document.getElementById("chol-val").textContent = "--";
        document.getElementById("chol-status-text").textContent = "No data";
    }

    const glucose = getVal("fasting_glucose");
    const hba1c = getVal("hba1c");
    const glucoseStatus = getStatus("fasting_glucose");
    const hba1cStatus = getStatus("hba1c");
    if (glucose) {
        document.getElementById("bio-glucose").innerHTML = `${Math.round(glucose)} <span class="bio-leg-unit">mg/dL</span>`;
        // Orange outer ring: fasting glucose 0-250 mg/dL → 0-100%
        animateRing("ring-glucose", 414.69, Math.min(glucose / 250, 1));
    }
    document.getElementById("sugar-glucose-val").textContent = glucose ? Math.round(glucose) : "--";
    document.getElementById("sugar-glucose-status").textContent = glucoseStatus ? glucoseStatus.toUpperCase() : "--";
    document.getElementById("sugar-hba1c-val").textContent = hba1c ? hba1c.toFixed(1) : "--";
    document.getElementById("sugar-hba1c-status").textContent = hba1cStatus ? hba1cStatus.toUpperCase() : "--";

    // 4. BMI
    const bmi = getVal("bmi");
    const bmiStatus = getStatus("bmi");
    if (bmi) {
        document.getElementById("bmi-val").textContent = bmi.toFixed(1);
        const dot = document.getElementById("bmi-status-dot");
        let label = "Normal";
        let colorClass = "normal";
        if (bmi >= 30) {
            label = "Obese";
            colorClass = "danger";
        } else if (bmi >= 25) {
            label = "Overweight";
            colorClass = "warning";
        } else if (bmi < 18.5) {
            label = "Underweight";
            colorClass = "warning";
        }
        dot.className = `status-indicator ${colorClass}`;
        document.getElementById("bmi-status-text").textContent = label;
    } else {
        document.getElementById("bmi-val").textContent = "--";
        document.getElementById("bmi-status-text").textContent = "No data";
    }

    // 5. Heart Rate
    const pulse = getVal("heart_rate");
    if (pulse) {
        document.getElementById("pulse-val").textContent = Math.round(pulse);
        const isHealthy = (pulse >= 60 && pulse <= 100);
        document.getElementById("pulse-status-text").textContent = isHealthy ? "Healthy" : "Elevated";
        document.getElementById("pulse-status-text").className = isHealthy ? "text-emerald" : "text-gold";
    } else {
        document.getElementById("pulse-val").textContent = "--";
        document.getElementById("pulse-status-text").textContent = "--";
    }
}

// Update Purple CVD risk metrics card
function updatePredictionTile(pred) {
    const probPercent = (pred.risk_probability * 100).toFixed(1);
    const band = pred.risk_band || "low";

    document.getElementById("risk-prob-val").textContent = `${probPercent}%`;

    const badge = document.getElementById("risk-band-badge");
    badge.textContent = `${band} risk band`;
    badge.className = `badge badge-${band}`;

    const desc = document.getElementById("risk-flagged-desc");
    if (pred.flagged) {
        desc.textContent = "⚠️ Elevated 10-year risk flagged.";
        desc.className = "risk-chip danger";
    } else {
        desc.textContent = "✅ Within healthy baseline constraints.";
        desc.className = "risk-chip success";
    }

    document.getElementById("risk-threshold-val").textContent = pred.threshold_used || "0.15";
}

function resetPredictionTile() {
    document.getElementById("risk-prob-val").textContent = "--%";
    const badge = document.getElementById("risk-band-badge");
    badge.textContent = "--";
    badge.className = "badge";
    const desc = document.getElementById("risk-flagged-desc");
    desc.textContent = "Upload a blood report to calculate risk.";
    desc.className = "risk-chip";
    document.getElementById("risk-threshold-val").textContent = "--";
}

// 6. SHAP WATERFALL INTERACTIVE MODAL
const shapModal = document.getElementById("shap-modal");
const viewShapBtn = document.getElementById("view-shap-btn");
const closeModalBtn = document.getElementById("close-modal-btn");
const closeModalFooterBtn = document.getElementById("close-modal-footer-btn");
const shapContainer = document.getElementById("shap-chart-container");

viewShapBtn.addEventListener("click", () => {
    if (!currentPrediction || !currentPrediction.shap_explanation) {
        alert("No SHAP explainability model cached for this profile. Please generate a prediction first.");
        return;
    }
    renderShapWaterfall(currentPrediction.shap_explanation);
    shapModal.classList.remove("hidden");
});

function hideModal() {
    shapModal.classList.add("hidden");
}
closeModalBtn.addEventListener("click", hideModal);
closeModalFooterBtn.addEventListener("click", hideModal);

// Render horizontal bar graphs for SHAP values
function renderShapWaterfall(shapData) {
    const baseValue = shapData.shap_values.base_value || 0;
    document.getElementById("shap-base-val").textContent = (baseValue * 100).toFixed(1) + "%";

    shapContainer.innerHTML = "";

    const items = shapData.feature_importance || [];
    if (items.length === 0) {
        shapContainer.innerHTML = "<p class='text-center text-xs text-muted py-4'>No significant feature attributions.</p>";
        return;
    }

    // Find max importance to scale the bar graphs
    const maxImportance = Math.max(...items.map(item => item.importance), 0.001);

    items.forEach(item => {
        const sign = item.direction === "increases_risk" ? "+" : "-";
        const impactVal = (item.importance * 100).toFixed(2);
        const percentWidth = Math.min((item.importance / maxImportance) * 100, 100);
        const classDir = item.direction === "increases_risk" ? "positive" : "negative";

        const row = document.createElement("div");
        row.className = "shap-row";
        row.innerHTML = `
            <span class="shap-feature-name" title="${item.feature}">${item.feature}</span>
            <div class="shap-bar-bg">
                <div class="shap-bar ${classDir}" style="width: ${percentWidth}%; ${item.direction === 'increases_risk' ? 'left: 0' : 'right: 0'}"></div>
            </div>
            <span class="shap-val ${item.direction === 'increases_risk' ? 'text-coral' : 'text-emerald'}">
                ${sign}${impactVal}%
            </span>
        `;
        shapContainer.appendChild(row);
    });
}

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const uploadIconBox = document.getElementById("upload-icon-box");
const uploadLoading = document.getElementById("upload-loading");
const uploadStatusText = document.getElementById("upload-status-text");
const uploadReportInfo = document.getElementById("uploaded-report-info");

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
    dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropZone.classList.remove("dragover");
    if (e.dataTransfer.files.length > 0) {
        handleFileUpload(e.dataTransfer.files[0]);
    }
});

fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
        handleFileUpload(fileInput.files[0]);
    }
});

async function handleFileUpload(file) {
    if (file.type !== "application/pdf") {
        alert("Only PDF blood report documents are supported!");
        return;
    }

    // Toggle loading UI
    uploadIconBox.classList.add("hidden");
    uploadLoading.classList.remove("hidden");
    uploadStatusText.textContent = "Uploading PDF document...";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const res = await fetch(`${API_BASE}/reports/upload`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${token}` }, // No content-type header for boundary
            body: formData
        });

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || "Upload failed");
        }

        // Start polling report extraction status
        pollReportStatus(data.report_id, file.name);
    } catch (err) {
        alert(err.message);
        resetUploadUI();
    }
}

function resetUploadUI() {
    uploadIconBox.classList.remove("hidden");
    uploadLoading.classList.add("hidden");
}

// Poll status of OCR extraction
async function pollReportStatus(reportId, filename) {
    uploadStatusText.textContent = "Analyzing biomarkers (OCR)...";

    const interval = setInterval(async () => {
        try {
            const res = await fetch(`${API_BASE}/reports/${reportId}/status`, { headers: getHeaders() });
            if (!res.ok) return;
            const data = await res.json();

            if (data.status === "extracted") {
                clearInterval(interval);
                uploadStatusText.textContent = "Assessing health risks...";

                // Refresh dashboard to display newly extracted data
                await loadDashboardData();

                resetUploadUI();
                uploadReportInfo.innerHTML = `
                    <i class="fa-solid fa-circle-check text-emerald"></i> 
                    Latest: <b>${filename}</b> (Extracted successfully)
                `;
            } else if (data.status === "failed") {
                clearInterval(interval);
                alert("Biomarker extraction failed. Please ensure the PDF is a readable blood panel.");
                resetUploadUI();
            }
        } catch (err) {
            console.error("Polling error:", err);
            clearInterval(interval);
            resetUploadUI();
        }
    }, 2000);
}

// 4. HEADER ACTIONS
document.getElementById("download-pdf-btn").addEventListener("click", () => {
    window.print();
});

// 8. INTERACTIVE AI COPILOT CHAT PANEL
const copilotForm = document.getElementById("copilot-form");
const chatInput = document.getElementById("chat-input");
const chatMessages = document.getElementById("chat-messages");

copilotForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    // Append user message
    appendChatMessage(query, "user");
    chatInput.value = "";

    // Show typing visualizer
    const typingBubble = document.createElement("div");
    typingBubble.className = "chat-msg assistant typing";
    typingBubble.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Copilot is thinking...`;
    chatMessages.appendChild(typingBubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const t0 = performance.now();
        const res = await fetch(`${API_BASE}/copilot/chat`, {
            method: "POST",
            headers: getHeaders(),
            body: JSON.stringify({ message: query })
        });

        const data = await res.json();
        chatMessages.removeChild(typingBubble);

        if (res.ok) {
            const elapsed = Math.round(performance.now() - t0);
            const latEl = document.getElementById("amd-latency");
            if (latEl) latEl.textContent = elapsed;

            appendChatMessage(data.response, "assistant");
        } else {
            appendChatMessage("Sorry, I encountered an error communicating with Kimi. Please try again.", "assistant");
        }
    } catch (err) {
        chatMessages.removeChild(typingBubble);
        appendChatMessage("Network error. Unable to contact Kimi Health Copilot.", "assistant");
    }
});

function appendChatMessage(text, role) {
    const bubble = document.createElement("div");
    const isAi = (role === "assistant" || role === "ai");
    bubble.className = `dc-msg ${isAi ? 'dc-msg--ai' : 'dc-msg--user'}`;

    // Convert newlines to breaks
    bubble.innerHTML = text.replace(/\n/g, "<br>");

    chatMessages.appendChild(bubble);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Injects the LLM health insight dynamically in the Copilot window
function appendAIInsight(insight) {
    let card = document.getElementById("copilot-insight-card");
    if (!card) {
        card = document.createElement("div");
        card.id = "copilot-insight-card";
        card.className = "dc-msg dc-msg--ai";
        card.style.border = "1px solid rgba(124, 113, 217, 0.25)";
        card.style.background = "rgba(124, 113, 217, 0.05)";
        card.style.fontWeight = "600";
        // Prepend it so it is at the very top of history
        chatMessages.insertBefore(card, chatMessages.firstChild);
    }
    card.innerHTML = `<i class="fa-solid fa-circle-info" style="color:var(--ring-purple);"></i> Twin Insight:<br>${insight.replace(/\n/g, "<br>")}`;
}

// ── CLINICAL PROFILE CARD ──────────────────────────────────────────
async function loadClinicalProfile() {
    try {
        const [intakeRes, userRes] = await Promise.all([
            fetch(`${API_BASE}/patient-intake`, { headers: getHeaders() }),
            fetch(`${API_BASE}/auth/me`, { headers: getHeaders() })
        ]);

        if (!intakeRes.ok || !userRes.ok) return;
        const intake = await intakeRes.json();
        const user = await userRes.json();

        // Remove skeleton class from all chips
        document.querySelectorAll('.profile-chip.skeleton')
            .forEach(c => c.classList.remove('skeleton'));

        // ─ Age (from date_of_birth) ─
        const ageEl = document.getElementById('pc-age');
        if (ageEl && user.date_of_birth) {
            const dob = new Date(user.date_of_birth);
            const age = Math.floor((Date.now() - dob) / (365.25 * 24 * 3600 * 1000));
            ageEl.textContent = `${age} yrs`;
            ageEl.className = 'pc-val pc-neutral';
        }

        // ─ Sex ─
        const sexEl = document.getElementById('pc-sex');
        if (sexEl && user.gender) {
            sexEl.textContent = user.gender.charAt(0).toUpperCase() + user.gender.slice(1);
            sexEl.className = 'pc-val pc-neutral';
        }

        // ─ Education ─
        const eduMap = { 1: 'Some HS', 2: 'HS / GED', 3: 'Some College', 4: 'College+' };
        const eduEl = document.getElementById('pc-education');
        if (eduEl && intake.education) {
            eduEl.textContent = eduMap[intake.education] ?? `Level ${intake.education}`;
            eduEl.className = 'pc-val pc-neutral';
        }

        // ─ Smoking ─
        const smokerEl = document.getElementById('pc-smoker');
        if (smokerEl) {
            const smokes = intake.current_smoker;
            smokerEl.textContent = smokes ? 'Active Smoker' : 'Non-Smoker';
            smokerEl.className = `pc-val ${smokes ? 'pc-yes' : 'pc-no'}`;
        }

        // ─ Cigs/Day ─
        const cigsEl = document.getElementById('pc-cigs');
        if (cigsEl) {
            const n = intake.cigs_per_day ?? 0;
            cigsEl.textContent = n > 0 ? `${n} / day` : '0 (none)';
            cigsEl.className = `pc-val ${n > 0 ? 'pc-yes' : 'pc-no'}`;
        }

        // ─ Boolean risk flags ─
        const flags = [
            { id: 'pc-bpmeds', key: 'bp_meds', yes: 'On Meds', no: 'Not on Meds' },
            { id: 'pc-hyp', key: 'prevalent_hyp', yes: 'Diagnosed', no: 'None' },
            { id: 'pc-stroke', key: 'prevalent_stroke', yes: 'Hx Stroke', no: 'None' },
            { id: 'pc-diabetes', key: 'diabetes', yes: 'Diabetic', no: 'No Diabetes' },
        ];
        flags.forEach(({ id, key, yes, no }) => {
            const el = document.getElementById(id);
            if (!el) return;
            const val = intake[key];
            el.textContent = val ? yes : no;
            el.className = `pc-val ${val ? 'pc-yes' : 'pc-no'}`;
        });

        // ─ Doctors Prescription ─
        const rxEl = document.getElementById('pc-prescription');
        if (rxEl) {
            rxEl.textContent = intake.doctors_prescription || 'None';
            rxEl.className = `pc-val ${intake.doctors_prescription ? 'pc-neutral' : 'pc-no'}`;
        }

    } catch (err) {
        console.warn('Clinical profile load failed:', err);
    }
}

// Wire the Edit button to open the intake view
document.getElementById('edit-profile-btn')?.addEventListener('click', async () => {
    // Pre-populate the intake form first
    document.getElementById('edit-intake-btn')?.click();
});

// Animate SVG ring: circumference-based stroke-dashoffset fill
function animateRing(id, circumference, pct) {
    const el = document.getElementById(id);
    if (!el) return;
    const offset = circumference - pct * circumference;
    // Small delay so CSS transition fires after paint
    requestAnimationFrame(() => { el.style.strokeDashoffset = offset; });
}

// 8. LOGOUT
function logout() {
    token = "";
    localStorage.removeItem("token");
    currentUser = null;
    currentPrediction = null;
    showView("landing");
}
document.getElementById("logout-btn").addEventListener("click", logout);

// Initialize App on load
window.addEventListener("DOMContentLoaded", initApp);
