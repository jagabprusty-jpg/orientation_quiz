/**
 * Live Janmashtami Quiz Frontend Controller
 */

import { state } from "./state.js";
import { api } from "./api.js";
import { wsClient } from "./websocket.js";

// DOM Elements
const elements = {
  connectionBadge: document.getElementById("connection-badge"),
  connectionText: document.getElementById("connection-text"),
  toastContainer: document.getElementById("toast-container"),

  // Screens
  screens: {
    registration: document.getElementById("screen-registration"),
    waiting: document.getElementById("screen-waiting"),
    question: document.getElementById("screen-question"),
    leaderboard: document.getElementById("screen-leaderboard"),
  },

  // Registration Form
  form: document.getElementById("registration-form"),
  btnRegister: document.getElementById("btn-register"),
  inputName: document.getElementById("input-name"),
  inputRegNo: document.getElementById("input-regno"),
  inputBranch: document.getElementById("input-branch"),
  inputPhone: document.getElementById("input-phone"),
  inputEmail: document.getElementById("input-email"),

  // Waiting View
  waitingName: document.getElementById("waiting-student-name"),
  waitingMeta: document.getElementById("waiting-student-meta"),

  // Question View
  questionRoundTitle: document.getElementById("question-round-title"),
  questionText: document.getElementById("question-text"),
  optionsGrid: document.getElementById("options-grid"),
  submissionStatus: document.getElementById("submission-status"),

  // Leaderboard View
  lbRoundTitle: document.getElementById("lb-round-title"),
  lbPersonalBanner: document.getElementById("lb-personal-banner"),
  lbPersonalText: document.getElementById("lb-personal-text"),
  lbTop5List: document.getElementById("lb-top5-list"),
  lbAllList: document.getElementById("lb-all-list"),
  lbWaitingNext: document.getElementById("lb-waiting-next"),
};

// UI Helper: Toast Notifications
function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;

  elements.toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transition = "opacity 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// UI Helper: Screen Switcher
function showScreen(screenName) {
  Object.keys(elements.screens).forEach((name) => {
    const el = elements.screens[name];
    if (el) {
      if (name === screenName) {
        el.classList.add("active");
      } else {
        el.classList.remove("active");
      }
    }
  });
  state.set("currentScreen", screenName);
}

// UI Helper: Connection Status
function updateConnectionUI(status) {
  const badge = elements.connectionBadge;
  const text = elements.connectionText;
  if (!badge || !text) return;

  badge.className = `connection-badge ${status}`;

  if (status === "connected") {
    text.textContent = "Live";
  } else if (status === "reconnecting") {
    text.textContent = "Reconnecting...";
  } else {
    text.textContent = "Offline";
  }
}

// Render Question Screen
function renderQuestion(roundId, question, hasAnswered = false, selectedOption = null) {
  elements.questionRoundTitle.textContent = `Question #${roundId}`;
  elements.questionText.textContent = question.question_text;
  elements.optionsGrid.innerHTML = "";

  const options = [
    { key: "A", text: question.option_a },
    { key: "B", text: question.option_b },
    { key: "C", text: question.option_c },
    { key: "D", text: question.option_d },
  ];

  options.forEach((opt) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "option-btn";
    btn.dataset.option = opt.key;

    if (hasAnswered) {
      btn.disabled = true;
      if (selectedOption === opt.key) {
        btn.classList.add("selected");
      }
    }

    btn.innerHTML = `
      <span class="option-letter">${opt.key}</span>
      <span class="option-text">${escapeHtml(opt.text)}</span>
    `;

    btn.addEventListener("click", () => handleAnswerSubmit(roundId, opt.key));
    elements.optionsGrid.appendChild(btn);
  });

  if (hasAnswered) {
    elements.submissionStatus.classList.add("active");
  } else {
    elements.submissionStatus.classList.remove("active");
  }

  showScreen("question");
}

// Handle Answer Selection
async function handleAnswerSubmit(roundId, optionKey) {
  const token = state.get("token");
  if (!token) {
    showToast("Session expired. Please register again.", "error");
    showScreen("registration");
    return;
  }

  // Prevent double click: immediately disable all buttons
  const buttons = elements.optionsGrid.querySelectorAll(".option-btn");
  buttons.forEach((btn) => {
    btn.disabled = true;
    if (btn.dataset.option === optionKey) {
      btn.classList.add("selected");
    }
  });

  elements.submissionStatus.classList.add("active");
  elements.submissionStatus.textContent = "Submitting answer to server...";

  try {
    const response = await api.submitAnswer(token, optionKey);
    state.set("hasAnsweredCurrentRound", true);
    state.set("selectedOption", optionKey);

    elements.submissionStatus.textContent = `✓ Answer recorded (${response.response_time_ms} ms). Waiting for round to end...`;
    showToast("Answer recorded!", "success");
  } catch (error) {
    console.error("Answer submission error:", error);
    elements.submissionStatus.textContent = `✓ ${error.message}`;

    if (error.status === 409) {
      // Duplicate answer
      state.set("hasAnsweredCurrentRound", true);
    } else if (error.status === 401) {
      state.clearSession();
      wsClient.disconnect();
      showScreen("registration");
      showToast(error.message, "error");
    } else {
      showToast(error.message, "error");
    }
  }
}

// Render Leaderboard
function renderLeaderboard(roundId, data) {
  elements.lbRoundTitle.textContent = `🏆 Question #${roundId} Results`;
  const currentStudent = state.get("student");
  const myStudentId = currentStudent ? currentStudent.id : null;

  // Personal placement banner
  let myEntry = null;
  if (myStudentId && data.all_entries) {
    myEntry = data.all_entries.find((e) => e.student_id === myStudentId);
  }

  if (myEntry) {
    elements.lbPersonalBanner.style.display = "block";
    if (myEntry.is_correct) {
      elements.lbPersonalText.textContent = `🎉 Rank #${myEntry.rank} • ${myEntry.response_time_ms} ms ${myEntry.is_top_5 ? "• TOP 5 WINNER! 🏅" : ""}`;
    } else {
      elements.lbPersonalText.textContent = `Your Answer: Incorrect (${myEntry.response_time_ms} ms)`;
    }
  } else {
    elements.lbPersonalBanner.style.display = "none";
  }

  // Top 5 Highlight List
  elements.lbTop5List.innerHTML = "";
  if (data.top_5_winners && data.top_5_winners.length > 0) {
    data.top_5_winners.forEach((entry) => {
      elements.lbTop5List.appendChild(createLeaderboardRow(entry, myStudentId));
    });
  } else {
    elements.lbTop5List.innerHTML = `<div style="text-align: center; color: var(--text-dim); padding: 1rem;">No correct answers submitted in this round.</div>`;
  }

  // Remaining participants
  elements.lbAllList.innerHTML = "";
  const remainingEntries = (data.all_entries || []).filter(
    (e) => !e.is_top_5
  );

  if (remainingEntries.length > 0) {
    remainingEntries.forEach((entry) => {
      elements.lbAllList.appendChild(createLeaderboardRow(entry, myStudentId));
    });
  }

  showScreen("leaderboard");
}

function createLeaderboardRow(entry, myStudentId) {
  const row = document.createElement("div");
  const isMe = entry.student_id === myStudentId;
  row.className = `lb-item ${entry.is_top_5 ? "top-5" : ""} ${isMe ? "is-me" : ""}`;

  let rankBadge = `<span class="lb-rank">${entry.rank || "-"}</span>`;
  if (entry.rank === 1) rankBadge = `<span class="lb-rank gold">🥇</span>`;
  else if (entry.rank === 2) rankBadge = `<span class="lb-rank silver">🥈</span>`;
  else if (entry.rank === 3) rankBadge = `<span class="lb-rank bronze">🥉</span>`;

  let resultTag = `<span class="lb-time">${entry.response_time_ms} ms</span>`;
  if (!entry.is_correct) {
    resultTag = `<span class="lb-incorrect-badge">Incorrect</span>`;
  }

  row.innerHTML = `
    <div class="lb-item-left">
      ${rankBadge}
      <div class="lb-student-info">
        <div class="lb-student-name">${escapeHtml(entry.student_name)} ${isMe ? "(You)" : ""}</div>
        <div class="lb-student-meta">${escapeHtml(entry.branch)} • ${escapeHtml(entry.registration_number)}</div>
      </div>
    </div>
    ${resultTag}
  `;
  return row;
}

// Update Waiting View Details
function updateWaitingView() {
  const student = state.get("student");
  if (student) {
    elements.waitingName.textContent = `Welcome, ${student.name}!`;
    elements.waitingMeta.textContent = `${student.registration_number} • ${student.branch}`;
  }
}

// Helper: Escape HTML
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// ==========================================
// App Initialization & Event Listeners
// ==========================================

export async function initApp() {
  // 1. Monitor Connection State
  state.on("change:connectionState", ({ value }) => {
    updateConnectionUI(value);
  });

  // 2. WebSocket Events
  state.on("ws:quiz_state", (data) => {
    if (data.status === "active" && data.question) {
      // Check if we already answered this round
      const currentRoundId = state.get("currentRoundId");
      const isNewRound = currentRoundId !== data.round_id;

      if (isNewRound) {
        state.set("currentRoundId", data.round_id);
        state.set("currentQuestion", data.question);
        state.set("hasAnsweredCurrentRound", false);
        state.set("selectedOption", null);
      }

      renderQuestion(
        data.round_id,
        data.question,
        state.get("hasAnsweredCurrentRound"),
        state.get("selectedOption")
      );
    } else {
      updateWaitingView();
      showScreen("waiting");
    }
  });

  state.on("ws:question_started", (data) => {
    state.set("currentRoundId", data.round_id);
    state.set("currentQuestion", data.question);
    state.set("hasAnsweredCurrentRound", false);
    state.set("selectedOption", null);

    renderQuestion(data.round_id, data.question, false, null);
    showToast(`Question #${data.round_id} has started!`, "info");
  });

  state.on("ws:round_ended", async (data) => {
    showToast("Round ended! Fetching leaderboard...", "info");
    try {
      const lbData = await api.getRoundLeaderboard(data.round_id);
      renderLeaderboard(data.round_id, lbData);
    } catch (err) {
      console.error("Failed to load leaderboard:", err);
      showToast("Unable to load round leaderboard.", "error");
    }
  });

  state.on("ws:auth_failed", () => {
    state.clearSession();
    showToast("Authentication failed. Please re-register.", "error");
    showScreen("registration");
  });

  // 3. Form Submit Listener
  elements.form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = elements.inputName.value.trim();
    const regNo = elements.inputRegNo.value.trim();
    const branch = elements.inputBranch.value.trim();
    const phone = elements.inputPhone.value.trim();
    const email = elements.inputEmail.value.trim();

    if (!name || !regNo || !branch || !phone || !email) {
      showToast("Please fill in all registration fields.", "error");
      return;
    }

    elements.btnRegister.disabled = true;
    elements.btnRegister.textContent = "Entering live quiz...";

    try {
      const authRes = await api.register({
        name,
        registration_number: regNo,
        branch,
        phone,
        email,
      });

      state.setSession(authRes.student, authRes.access_token);
      updateWaitingView();
      showScreen("waiting");
      showToast("Registration successful! Connecting to live quiz...", "success");

      // Connect live WebSocket
      wsClient.connect();
    } catch (err) {
      console.error("Registration error:", err);
      showToast(err.message, "error");
    } finally {
      elements.btnRegister.disabled = false;
      elements.btnRegister.textContent = "Enter Live Quiz";
    }
  });

  // 4. Session Restoration on Refresh / Load
  if (state.hasSession()) {
    const token = state.get("token");
    try {
      const student = await api.getMe(token);
      state.setSession(student, token);
      updateWaitingView();
      showScreen("waiting");

      // Connect WebSocket to retrieve active state
      wsClient.connect();
    } catch (err) {
      console.warn("Stored session invalid or expired:", err);
      state.clearSession();
      showScreen("registration");
    }
  } else {
    showScreen("registration");
  }
}

// Start app once DOM is ready
document.addEventListener("DOMContentLoaded", initApp);
