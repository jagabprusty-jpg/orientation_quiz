/**
 * Admin API Client for Quiz Control Panel
 */

const API_BASE = "/api";

class AdminApiError extends Error {
  constructor(message, status, errorCode, raw) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
    this.raw = raw;
  }
}

function getAdminToken() {
  return sessionStorage.getItem("admin_token");
}

function setAdminToken(token) {
  if (token) {
    sessionStorage.setItem("admin_token", token);
  } else {
    sessionStorage.removeItem("admin_token");
  }
}

async function adminRequest(endpoint, options = {}) {
  const token = getAdminToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = `${API_BASE}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    let data = null;
    const contentType = response.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    if (!response.ok) {
      let message = "An error occurred.";
      let errorCode = "UNKNOWN_ERROR";

      if (data && typeof data === "object") {
        if (data.detail) {
          message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
        }
        if (data.error_code) {
          errorCode = data.error_code;
        }
      }

      if (response.status === 401) {
        setAdminToken(null);
      }

      throw new AdminApiError(message, response.status, errorCode, data);
    }

    return data;
  } catch (error) {
    if (error instanceof AdminApiError) {
      throw error;
    }
    throw new AdminApiError(
      "Network connection failure. Unable to reach server.",
      0,
      "NETWORK_ERROR",
      error
    );
  }
}

export const adminApi = {
  getToken: getAdminToken,
  setToken: setAdminToken,

  async login(username, password) {
    const data = await adminRequest("/admin/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    if (data && data.access_token) {
      setAdminToken(data.access_token);
    }
    return data;
  },

  async getMe() {
    return adminRequest("/admin/auth/me", { method: "GET" });
  },

  async getQuestions() {
    return adminRequest("/admin/questions", { method: "GET" });
  },

  async createQuestion(questionData) {
    return adminRequest("/admin/questions", {
      method: "POST",
      body: JSON.stringify(questionData),
    });
  },

  async updateQuestion(questionId, updateData) {
    return adminRequest(`/admin/questions/${questionId}`, {
      method: "PUT",
      body: JSON.stringify(updateData),
    });
  },

  async deactivateQuestion(questionId) {
    return adminRequest(`/admin/questions/${questionId}`, {
      method: "DELETE",
    });
  },

  async startRound(questionId) {
    return adminRequest("/admin/rounds/start", {
      method: "POST",
      body: JSON.stringify({ question_id: questionId }),
    });
  },

  async endRound(roundId) {
    return adminRequest(`/admin/rounds/${roundId}/end`, {
      method: "POST",
    });
  },

  async getRounds() {
    return adminRequest("/admin/rounds", { method: "GET" });
  },

  async getRound(roundId) {
    return adminRequest(`/admin/rounds/${roundId}`, { method: "GET" });
  },

  async getRoundLeaderboard(roundId) {
    return adminRequest(`/admin/rounds/${roundId}/leaderboard`, {
      method: "GET",
    });
  },

  async getStudents() {
    return adminRequest("/students", { method: "GET" });
  },
};
