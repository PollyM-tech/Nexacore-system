import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  withCredentials: true,
  xsrfCookieName: "csrftoken",
  xsrfHeaderName: "X-CSRFToken",
  headers: { "Content-Type": "application/json" },
});


let csrfRequest: Promise<unknown> | undefined;
api.interceptors.request.use(async config => {
  if (!["get", "head", "options"].includes(config.method?.toLowerCase() || "get") &&
      typeof document !== "undefined" && !document.cookie.split(";").some(c => c.trim().startsWith("csrftoken="))) {
    csrfRequest ??= api.get("/auth/csrf/").finally(() => { csrfRequest = undefined; });
    await csrfRequest;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const path = window.location.pathname;
    if (err.response?.status === 401 && path.startsWith("/admin") && path !== "/admin/login") {
      window.location.assign("/admin/login");
    }
    return Promise.reject(err);
  },
);
