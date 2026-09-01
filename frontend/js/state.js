/**
 * Application State & SessionStorage Management
 */

class AppState {
  constructor() {
    this.listeners = {};
    this.state = {
      token: sessionStorage.getItem("student_token") || null,
      student: this._getStoredStudent(),
      connectionState: "disconnected", // 'connected' | 'reconnecting' | 'disconnected'
      currentScreen: "registration",
      currentRoundId: null,
      currentQuestion: null,
      hasAnsweredCurrentRound: false,
      selectedOption: null,
      activeLeaderboard: null,
    };
  }

  _getStoredStudent() {
    try {
      const data = sessionStorage.getItem("student_profile");
      return data ? JSON.parse(data) : null;
    } catch {
      return null;
    }
  }

  get(key) {
    return this.state[key];
  }

  set(key, value) {
    const oldValue = this.state[key];
    this.state[key] = value;
    this.emit(`change:${key}`, { value, oldValue });
    this.emit("change", { key, value, oldValue });
  }

  setSession(student, token) {
    sessionStorage.setItem("student_token", token);
    sessionStorage.setItem("student_profile", JSON.stringify(student));
    this.state.token = token;
    this.state.student = student;
    this.emit("session:saved", { student, token });
  }

  clearSession() {
    sessionStorage.removeItem("student_token");
    sessionStorage.removeItem("student_profile");
    this.state.token = null;
    this.state.student = null;
    this.state.hasAnsweredCurrentRound = false;
    this.state.selectedOption = null;
    this.emit("session:cleared");
  }

  hasSession() {
    return Boolean(this.state.token && this.state.student);
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach((cb) => {
        try {
          cb(data);
        } catch (err) {
          console.error(`Error in listener for ${event}:`, err);
        }
      });
    }
  }
}

export const state = new AppState();
