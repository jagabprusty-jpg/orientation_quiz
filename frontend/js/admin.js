/**
 * Admin Control Panel Controller
 */

import { adminApi } from "./admin-api.js";

// Application State
const adminState = {
  activeRound: null,
  activeQuestion: null,
  questions: [],
  rounds: [],
  students: [],
  isSubmitting: false,
};

// DOM References
const dom = {
  // Screens
  loginModal: document.getElementById("modal-admin-login"),
  adminApp: document.getElementById("admin-app"),
  toastContainer: document.getElementById("admin-toast-container"),

  // Login Form
  formLogin: document.getElementById("form-admin-login"),
  inputUsername: document.getElementById("admin-username"),
  inputPassword: document.getElementById("admin-password"),
  btnLogin: document.getElementById("btn-admin-login"),
  btnLogout: document.getElementById("btn-admin-logout"),

  // Quiz Hero Control Card
  statusBadge: document.getElementById("hero-status-badge"),
  statusText: document.getElementById("hero-status-text"),
  selectQuestion: document.getElementById("select-active-question"),
  btnStartQuestion: document.getElementById("btn-start-question"),
  btnEndQuestion: document.getElementById("btn-end-question"),
  liveQuestionDisplay: document.getElementById("live-question-display"),
  liveQuestionText: document.getElementById("live-question-text"),
  optionsPreviewGrid: document.getElementById("options-preview-grid"),

  // Question Management
  btnOpenCreateQuestion: document.getElementById("btn-open-create-question"),
  modalQuestion: document.getElementById("modal-question-editor"),
  formQuestion: document.getElementById("form-question-editor"),
  modalQuestionTitle: document.getElementById("modal-question-title"),
  inputQId: document.getElementById("q-edit-id"),
  inputQText: document.getElementById("q-text"),
  inputQOptA: document.getElementById("q-opt-a"),
  inputQOptB: document.getElementById("q-opt-b"),
  inputQOptC: document.getElementById("q-opt-c"),
  inputQOptD: document.getElementById("q-opt-d"),
  inputQCorrect: document.getElementById("q-correct-opt"),
  btnCancelQuestion: document.getElementById("btn-cancel-question"),
  tableQuestionsBody: document.getElementById("table-questions-body"),

  // Leaderboard Modal
  modalLeaderboard: document.getElementById("modal-leaderboard"),
  btnCloseLeaderboard: document.getElementById("btn-close-leaderboard"),
  lbModalTitle: document.getElementById("lb-modal-title"),
  lbMetricSubmissions: document.getElementById("lb-metric-submissions"),
  lbMetricCorrect: document.getElementById("lb-metric-correct"),
  lbMetricIncorrect: document.getElementById("lb-metric-incorrect"),
  lbModalTop5List: document.getElementById("lb-modal-top5-list"),
  lbModalAllList: document.getElementById("lb-modal-all-list"),

  // Previous Rounds & Students
  tableRoundsBody: document.getElementById("table-rounds-body"),
  tableStudentsBody: document.getElementById("table-students-body"),
  studentCountBadge: document.getElementById("student-count-badge"),
};

// UI Helper: Toast Notifications
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;

  dom.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// Escape HTML for safety
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Authentication Check
async function checkAuth() {
  const token = adminApi.getToken();
  if (!token) {
    showLoginModal();
    return false;
  }

  try {
    await adminApi.getMe();
    dom.loginModal.classList.remove("active");
    dom.adminApp.style.display = "block";
    await refreshDashboard();
    return true;
  } catch {
    showLoginModal();
    return false;
  }
}

function showLoginModal() {
  dom.loginModal.classList.add("active");
  dom.adminApp.style.display = "none";
}

// Refresh entire dashboard
async function refreshDashboard() {
  try {
    await Promise.all([
      loadQuestions(),
      loadRounds(),
      loadStudents(),
    ]);
  } catch (err) {
    console.error("Dashboard refresh error:", err);
  }
}

// Load Questions
async function loadQuestions() {
  try {
    const questions = await adminApi.getQuestions();
    adminState.questions = questions;
    renderQuestionsTable(questions);
    renderQuestionDropdown(questions);
  } catch (err) {
    console.error("Failed to load questions:", err);
    showToast("Failed to load questions list", "error");
  }
}

function renderQuestionDropdown(questions) {
  const select = dom.selectQuestion;
  select.innerHTML = '<option value="" disabled selected>-- Choose a question to start --</option>';

  const activeQuestions = questions.filter((q) => q.is_active);
  activeQuestions.forEach((q) => {
    const opt = document.createElement("option");
    opt.value = q.id;
    opt.textContent = `[#${q.id}] ${q.question_text} (Correct: ${q.correct_option})`;
    select.appendChild(opt);
  });
}

function renderQuestionsTable(questions) {
  const tbody = dom.tableQuestionsBody;
  tbody.innerHTML = "";

  if (questions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--text-dim);">No questions created yet.</td></tr>';
    return;
  }

  questions.forEach((q) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td><strong>#${q.id}</strong></td>
      <td>${escapeHtml(q.question_text)}</td>
      <td><span class="badge-correct-opt">Option ${q.correct_option}</span></td>
      <td>${q.is_active ? '<span class="badge-active">Active</span>' : '<span class="badge-inactive">Inactive</span>'}</td>
      <td>
        <div style="display:flex; gap: 0.5rem;">
          <button class="btn btn-edit-q" data-id="${q.id}" style="padding: 0.3rem 0.6rem; font-size: 0.8rem; background: rgba(0, 180, 216, 0.2); color: var(--peacock-teal); border: 1px solid rgba(0, 180, 216, 0.4); border-radius: var(--radius-sm); cursor: pointer;">Edit</button>
          ${q.is_active ? `<button class="btn btn-deact-q" data-id="${q.id}" style="padding: 0.3rem 0.6rem; font-size: 0.8rem; background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); border-radius: var(--radius-sm); cursor: pointer;">Deactivate</button>` : ''}
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });

  // Attach button listeners
  tbody.querySelectorAll(".btn-edit-q").forEach((btn) => {
    btn.addEventListener("click", () => openEditQuestionModal(parseInt(btn.dataset.id)));
  });

  tbody.querySelectorAll(".btn-deact-q").forEach((btn) => {
    btn.addEventListener("click", () => handleDeactivateQuestion(parseInt(btn.dataset.id)));
  });
}

// Load Rounds & Active State
async function loadRounds() {
  try {
    const rounds = await adminApi.getRounds();
    adminState.rounds = rounds;

    // Check for active round
    const active = rounds.find((r) => r.status === "active");
    adminState.activeRound = active || null;

    if (active) {
      // Find question details
      const q = adminState.questions.find((x) => x.id === active.question_id);
      adminState.activeQuestion = q || null;
      renderLiveState(active, q);
    } else {
      adminState.activeQuestion = null;
      renderWaitingState();
    }

    renderRoundsTable(rounds);
  } catch (err) {
    console.error("Failed to load rounds:", err);
  }
}

function renderLiveState(round, question) {
  dom.statusBadge.className = "status-badge live";
  dom.statusText.textContent = `🔴 Live Round #${round.id}`;

  dom.selectQuestion.style.display = "none";
  dom.btnStartQuestion.style.display = "none";
  dom.btnEndQuestion.style.display = "inline-flex";
  dom.btnEndQuestion.disabled = false;

  dom.liveQuestionDisplay.style.display = "block";
  if (question) {
    dom.liveQuestionText.textContent = `[#${question.id}] ${question.question_text}`;

    const options = [
      { key: "A", text: question.option_a },
      { key: "B", text: question.option_b },
      { key: "C", text: question.option_c },
      { key: "D", text: question.option_d },
    ];

    dom.optionsPreviewGrid.innerHTML = "";
    options.forEach((opt) => {
      const isCorrect = question.correct_option === opt.key;
      const card = document.createElement("div");
      card.className = `option-preview-item ${isCorrect ? "correct" : ""}`;
      card.innerHTML = `
        <strong>${opt.key}.</strong>
        <span>${escapeHtml(opt.text)}</span>
        ${isCorrect ? '<span class="option-badge-correct">✓ CORRECT</span>' : ''}
      `;
      dom.optionsPreviewGrid.appendChild(card);
    });
  }
}

function renderWaitingState() {
  dom.statusBadge.className = "status-badge waiting";
  dom.statusText.textContent = "⏸️ Waiting / Ready";

  dom.selectQuestion.style.display = "block";
  dom.btnStartQuestion.style.display = "inline-flex";
  dom.btnStartQuestion.disabled = false;
  dom.btnEndQuestion.style.display = "none";

  dom.liveQuestionDisplay.style.display = "none";
}

function renderRoundsTable(rounds) {
  const tbody = dom.tableRoundsBody;
  tbody.innerHTML = "";

  if (rounds.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--text-dim);">No rounds conducted yet.</td></tr>';
    return;
  }

  // Sort latest first
  const sorted = [...rounds].sort((a, b) => b.id - a.id);

  sorted.forEach((r) => {
    const tr = document.createElement("tr");
    const started = r.started_at ? new Date(r.started_at).toLocaleTimeString() : "-";
    const statusBadge = r.status === "active" 
      ? '<span class="badge-active" style="background: rgba(239,68,68,0.2); color:#f87171;">LIVE</span>'
      : '<span class="badge-active">Ended</span>';

    tr.innerHTML = `
      <td><strong>Round #${r.id}</strong></td>
      <td>Question #${r.question_id}</td>
      <td>${statusBadge}</td>
      <td>${started}</td>
      <td>
        <button class="btn btn-view-lb" data-id="${r.id}" style="padding: 0.3rem 0.6rem; font-size: 0.8rem; background: rgba(255, 183, 3, 0.15); color: var(--primary-gold); border: 1px solid rgba(255, 183, 3, 0.4); border-radius: var(--radius-sm); cursor: pointer;">
          🏆 View Results
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });

  tbody.querySelectorAll(".btn-view-lb").forEach((btn) => {
    btn.addEventListener("click", () => openLeaderboardModal(parseInt(btn.dataset.id)));
  });
}

// Load Students
async function loadStudents() {
  try {
    const students = await adminApi.getStudents();
    adminState.students = students;
    dom.studentCountBadge.textContent = `${students.length} Registered`;

    const tbody = dom.tableStudentsBody;
    tbody.innerHTML = "";

    if (students.length === 0) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color: var(--text-dim);">No students registered yet.</td></tr>';
      return;
    }

    students.forEach((s) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>#${s.id}</strong></td>
        <td>${escapeHtml(s.name)}</td>
        <td>${escapeHtml(s.registration_number)}</td>
        <td>${escapeHtml(s.branch)}</td>
        <td>${escapeHtml(s.phone)} • ${escapeHtml(s.email)}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to load students:", err);
  }
}

// Leaderboard Modal
async function openLeaderboardModal(roundId) {
  dom.lbModalTitle.textContent = `🏆 Round #${roundId} Leaderboard`;
  dom.modalLeaderboard.classList.add("active");

  dom.lbMetricSubmissions.textContent = "...";
  dom.lbMetricCorrect.textContent = "...";
  dom.lbMetricIncorrect.textContent = "...";
  dom.lbModalTop5List.innerHTML = '<div style="text-align:center; color:var(--text-dim); padding:1rem;">Loading results...</div>';
  dom.lbModalAllList.innerHTML = "";

  try {
    const lb = await adminApi.getRoundLeaderboard(roundId);

    dom.lbMetricSubmissions.textContent = lb.total_submissions;
    dom.lbMetricCorrect.textContent = lb.total_correct;
    dom.lbMetricIncorrect.textContent = lb.total_incorrect;

    // Render Top 5 Winners
    dom.lbModalTop5List.innerHTML = "";
    if (lb.top_5_winners && lb.top_5_winners.length > 0) {
      lb.top_5_winners.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "lb-item top-5";

        let rankBadge = `<span class="lb-rank">${entry.rank}</span>`;
        if (entry.rank === 1) rankBadge = `<span class="lb-rank gold">🥇</span>`;
        else if (entry.rank === 2) rankBadge = `<span class="lb-rank silver">🥈</span>`;
        else if (entry.rank === 3) rankBadge = `<span class="lb-rank bronze">🥉</span>`;
        else rankBadge = `<span class="lb-rank">⭐ ${entry.rank}</span>`;

        row.innerHTML = `
          <div class="lb-item-left">
            ${rankBadge}
            <div class="lb-student-info">
              <div class="lb-student-name">${escapeHtml(entry.student_name)}</div>
              <div class="lb-student-meta">${escapeHtml(entry.branch)} • ${escapeHtml(entry.registration_number)}</div>
            </div>
          </div>
          <span class="lb-time">${entry.response_time_ms} ms</span>
        `;
        dom.lbModalTop5List.appendChild(row);
      });
    } else {
      dom.lbModalTop5List.innerHTML = '<div style="text-align:center; color:var(--text-dim); padding:1rem;">No correct answers submitted.</div>';
    }

    // Render remaining submissions
    dom.lbModalAllList.innerHTML = "";
    const remaining = (lb.all_entries || []).filter((e) => !e.is_top_5);
    if (remaining.length > 0) {
      remaining.forEach((entry) => {
        const row = document.createElement("div");
        row.className = "lb-item";

        const resultTag = entry.is_correct
          ? `<span class="lb-time">${entry.response_time_ms} ms</span>`
          : `<span class="lb-incorrect-badge">Incorrect</span>`;

        row.innerHTML = `
          <div class="lb-item-left">
            <span class="lb-rank">${entry.rank || "-"}</span>
            <div class="lb-student-info">
              <div class="lb-student-name">${escapeHtml(entry.student_name)}</div>
              <div class="lb-student-meta">${escapeHtml(entry.branch)} • ${escapeHtml(entry.registration_number)}</div>
            </div>
          </div>
          ${resultTag}
        `;
        dom.lbModalAllList.appendChild(row);
      });
    }
  } catch (err) {
    console.error("Failed to load leaderboard:", err);
    showToast("Failed to load round leaderboard", "error");
  }
}

// Question Editor Modal
function openCreateQuestionModal() {
  dom.modalQuestionTitle.textContent = "Create New Question";
  dom.inputQId.value = "";
  dom.inputQText.value = "";
  dom.inputQOptA.value = "";
  dom.inputQOptB.value = "";
  dom.inputQOptC.value = "";
  dom.inputQOptD.value = "";
  dom.inputQCorrect.value = "A";
  dom.modalQuestion.classList.add("active");
}

function openEditQuestionModal(questionId) {
  const q = adminState.questions.find((x) => x.id === questionId);
  if (!q) return;

  dom.modalQuestionTitle.textContent = `Edit Question #${q.id}`;
  dom.inputQId.value = q.id;
  dom.inputQText.value = q.question_text;
  dom.inputQOptA.value = q.option_a;
  dom.inputQOptB.value = q.option_b;
  dom.inputQOptC.value = q.option_c;
  dom.inputQOptD.value = q.option_d;
  dom.inputQCorrect.value = q.correct_option;
  dom.modalQuestion.classList.add("active");
}

async function handleSaveQuestion(e) {
  e.preventDefault();
  const id = dom.inputQId.value ? parseInt(dom.inputQId.value) : null;
  const payload = {
    question_text: dom.inputQText.value.trim(),
    option_a: dom.inputQOptA.value.trim(),
    option_b: dom.inputQOptB.value.trim(),
    option_c: dom.inputQOptC.value.trim(),
    option_d: dom.inputQOptD.value.trim(),
    correct_option: dom.inputQCorrect.value,
  };

  try {
    if (id) {
      await adminApi.updateQuestion(id, payload);
      showToast(`Question #${id} updated successfully!`, "success");
    } else {
      payload.is_active = true;
      const created = await adminApi.createQuestion(payload);
      showToast(`Question #${created.id} created successfully!`, "success");
    }
    dom.modalQuestion.classList.remove("active");
    await loadQuestions();
  } catch (err) {
    showToast(err.message, "error");
  }
}

async function handleDeactivateQuestion(questionId) {
  if (!confirm(`Are you sure you want to deactivate Question #${questionId}?`)) return;

  try {
    await adminApi.deactivateQuestion(questionId);
    showToast(`Question #${questionId} deactivated.`, "info");
    await loadQuestions();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Start Round
async function handleStartRound() {
  const selectedQId = dom.selectQuestion.value;
  if (!selectedQId) {
    showToast("Please select an active question first.", "error");
    return;
  }

  dom.btnStartQuestion.disabled = true;
  dom.btnStartQuestion.textContent = "Starting...";

  try {
    const round = await adminApi.startRound(parseInt(selectedQId));
    showToast(`Round #${round.id} is now LIVE! Broadcast sent to students.`, "success");
    await refreshDashboard();
  } catch (err) {
    showToast(err.message, "error");
    dom.btnStartQuestion.disabled = false;
    dom.btnStartQuestion.textContent = "⚡ START QUESTION";
  }
}

// End Round
async function handleEndRound() {
  if (!adminState.activeRound) return;

  const roundId = adminState.activeRound.id;
  if (!confirm(`End Round #${roundId}? Students will no longer be able to submit answers.`)) {
    return;
  }

  dom.btnEndQuestion.disabled = true;
  dom.btnEndQuestion.textContent = "Ending...";

  try {
    await adminApi.endRound(roundId);
    showToast(`Round #${roundId} ended! Opening leaderboard...`, "success");
    await refreshDashboard();
    // Open leaderboard immediately
    await openLeaderboardModal(roundId);
  } catch (err) {
    showToast(err.message, "error");
    dom.btnEndQuestion.disabled = false;
    dom.btnEndQuestion.textContent = "🛑 END QUESTION";
  }
}

// Event Listeners Setup
export function initAdmin() {
  // Login Form
  dom.formLogin.addEventListener("submit", async (e) => {
    e.preventDefault();
    const username = dom.inputUsername.value.trim();
    const password = dom.inputPassword.value.trim();

    dom.btnLogin.disabled = true;
    dom.btnLogin.textContent = "Authenticating...";

    try {
      await adminApi.login(username, password);
      showToast("Welcome, Admin! Login successful.", "success");
      dom.loginModal.classList.remove("active");
      dom.adminApp.style.display = "block";
      await refreshDashboard();
    } catch (err) {
      showToast(err.message, "error");
    } finally {
      dom.btnLogin.disabled = false;
      dom.btnLogin.textContent = "Sign In to Admin Panel";
    }
  });

  // Logout
  dom.btnLogout.addEventListener("click", () => {
    adminApi.setToken(null);
    showToast("Logged out.", "info");
    showLoginModal();
  });

  // Quiz Controls
  dom.btnStartQuestion.addEventListener("click", handleStartRound);
  dom.btnEndQuestion.addEventListener("click", handleEndRound);

  // Question Management
  dom.btnOpenCreateQuestion.addEventListener("click", openCreateQuestionModal);
  dom.formQuestion.addEventListener("submit", handleSaveQuestion);
  dom.btnCancelQuestion.addEventListener("click", () => dom.modalQuestion.classList.remove("active"));

  // Leaderboard Modal
  dom.btnCloseLeaderboard.addEventListener("click", () => dom.modalLeaderboard.classList.remove("active"));

  // Check existing session
  checkAuth();
}

document.addEventListener("DOMContentLoaded", initAdmin);
