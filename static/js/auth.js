(function () {
  var TOKEN_KEY = "ai_tutor_token";
  var SESSION_KEY = "ai_tutor_session";

  window.AITutorAuth = {
    getToken: function () {
      return localStorage.getItem(TOKEN_KEY);
    },
    setToken: function (t) {
      localStorage.setItem(TOKEN_KEY, t);
    },
    clear: function () {
      localStorage.removeItem(TOKEN_KEY);
    },
    sessionId: function () {
      var s = localStorage.getItem(SESSION_KEY);
      if (!s) {
        s = crypto.randomUUID();
        localStorage.setItem(SESSION_KEY, s);
      }
      return s;
    },
    resetSession: function () {
      localStorage.removeItem(SESSION_KEY);
    },
    authHeaders: function () {
      var t = this.getToken();
      return t ? { Authorization: "Bearer " + t } : {};
    },
    requireAuth: function () {
      if (!this.getToken()) {
        window.location.href = "/login";
        return false;
      }
      return true;
    },
    logout: function () {
      this.clear();
      window.location.href = "/";
    },
    /** FastAPI: detail may be a string, or Pydantic 422 array of {loc,msg}, or {msg}. */
    formatApiError: function (data, statusText) {
      if (!data) return statusText || "Request failed";
      if (typeof data.error === "string" && data.error) return data.error;
      var d = data.detail;
      if (d == null || d === "") {
        if (typeof data.message === "string") return data.message;
        return statusText || "Request failed";
      }
      if (typeof d === "string") return d;
      if (Array.isArray(d)) {
        return d
          .map(function (item) {
            if (typeof item === "string") return item;
            if (item && typeof item.msg === "string") {
              var loc = item.loc && item.loc.length > 1 ? item.loc.slice(1).join(".") : "";
              return (loc ? loc + ": " : "") + item.msg;
            }
            try {
              return JSON.stringify(item);
            } catch (y) {
              return String(item);
            }
          })
          .filter(Boolean)
          .join(" ");
      }
      if (typeof d === "object" && typeof d.msg === "string") return d.msg;
      try {
        return JSON.stringify(d);
      } catch (z) {
        return String(d);
      }
    },
  };
})();
