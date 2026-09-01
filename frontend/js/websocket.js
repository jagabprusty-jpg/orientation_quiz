/**
 * WebSocket Real-Time Client with Auto-Reconnection & Exponential Backoff
 */

import { state } from "./state.js";

class QuizWebSocket {
  constructor() {
    this.socket = null;
    this.reconnectTimer = null;
    this.pingTimer = null;
    this.attempts = 0;
    this.maxAttempts = 20;
    this.baseDelayMs = 1000;
    this.maxDelayMs = 10000;
    this.isExplicitlyClosed = false;
  }

  connect() {
    const token = state.get("token");
    if (!token) {
      console.warn("Cannot connect WebSocket: No student token found.");
      return;
    }

    this.isExplicitlyClosed = false;
    this._clearTimers();

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/ws/quiz?token=${encodeURIComponent(token)}`;

    state.set("connectionState", this.attempts > 0 ? "reconnecting" : "reconnecting");

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        this.attempts = 0;
        state.set("connectionState", "connected");
        this._startKeepAlive();
      };

      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          this._handleMessage(message);
        } catch (err) {
          console.error("Failed to parse WebSocket message:", err);
        }
      };

      this.socket.onclose = (event) => {
        this._stopKeepAlive();

        if (this.isExplicitlyClosed) {
          state.set("connectionState", "disconnected");
          return;
        }

        // Code 1008: Policy Violation (Invalid / Expired student token)
        if (event.code === 1008) {
          console.warn("WebSocket closed due to auth failure (1008).");
          state.set("connectionState", "disconnected");
          state.emit("ws:auth_failed");
          return;
        }

        state.set("connectionState", "reconnecting");
        this._scheduleReconnect();
      };

      this.socket.onerror = (error) => {
        console.warn("WebSocket encountered an error:", error);
      };
    } catch (err) {
      console.error("Error creating WebSocket:", err);
      this._scheduleReconnect();
    }
  }

  _handleMessage(message) {
    const { type, data } = message;

    switch (type) {
      case "quiz_state":
        state.emit("ws:quiz_state", data);
        break;
      case "question_started":
        state.emit("ws:question_started", data);
        break;
      case "round_ended":
        state.emit("ws:round_ended", data);
        break;
      case "pong":
        // Keepalive response
        break;
      default:
        console.debug("Received unknown WebSocket message:", message);
    }
  }

  _scheduleReconnect() {
    if (this.isExplicitlyClosed) return;

    this.attempts += 1;
    const delay = Math.min(
      this.baseDelayMs * Math.pow(1.8, this.attempts - 1),
      this.maxDelayMs
    );

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, delay);
  }

  _startKeepAlive() {
    this._stopKeepAlive();
    // Send ping every 25 seconds
    this.pingTimer = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send("ping");
      }
    }, 25000);
  }

  _stopKeepAlive() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  _clearTimers() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this._stopKeepAlive();
  }

  disconnect() {
    this.isExplicitlyClosed = true;
    this._clearTimers();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    state.set("connectionState", "disconnected");
  }
}

export const wsClient = new QuizWebSocket();
