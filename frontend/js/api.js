/**
 * REST API Client for Student Quiz
 */

const API_BASE = "/api";

class ApiError extends Error {
  constructor(message, status, errorCode, raw) {
    super(message);
    this.status = status;
    this.errorCode = errorCode;
    this.raw = raw;
  }
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };

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
      let message = "A server error occurred. Please try again.";
      let errorCode = "UNKNOWN_ERROR";

      if (data && typeof data === "object") {
        if (data.detail) {
          message = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
        }
        if (data.error_code) {
          errorCode = data.error_code;
        }
      }

      // Friendly translations for common errors
      if (response.status === 401) {
        message = "Your quiz session has expired. Please sign in again.";
      } else if (response.status === 409 || errorCode === "DUPLICATE_ANSWER") {
        message = "You have already submitted an answer for this question.";
      } else if (response.status === 400 && errorCode === "ROUND_NOT_ACTIVE") {
        message = "This question is no longer accepting answers.";
      }

      throw new ApiError(message, response.status, errorCode, data);
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network failure / offline
    throw new ApiError(
      "Unable to connect to quiz server. Please check your connection.",
      0,
      "NETWORK_ERROR",
      error
    );
  }
}

export const api = {
  /**
   * Register or restore a student profile and obtain access token
   */
  async register(studentData) {
    return request("/students/register", {
      method: "POST",
      body: JSON.stringify(studentData),
    });
  },

  /**
   * Validate existing student session token
   */
  async getMe(token) {
    return request("/students/me", {
      method: "GET",
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
  },

  /**
   * Fetch current active question
   */
  async getActiveQuiz() {
    return request("/quiz/active", {
      method: "GET",
    });
  },

  /**
   * Submit student answer for the active round
   */
  async submitAnswer(token, selectedOption) {
    return request("/quiz/answers", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        selected_option: selectedOption,
      }),
    });
  },

  /**
   * Fetch independent leaderboard for a specific round
   */
  async getRoundLeaderboard(roundId) {
    return request(`/quiz/rounds/${roundId}/leaderboard`, {
      method: "GET",
    });
  },
};
