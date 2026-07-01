import axios from "axios";
import Cookies from "js-cookie";

const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    if (error.response?.status === 401) {
      const refresh = Cookies.get("refresh_token");
      if (refresh) {
        try {
          const { data } = await axios.post("/api/v1/auth/refresh", null, {
            params: { refresh_token: refresh },
          });
          Cookies.set("access_token", data.access_token);
          Cookies.set("refresh_token", data.refresh_token);
          error.config.headers.Authorization = `Bearer ${data.access_token}`;
          return api.request(error.config);
        } catch {
          Cookies.remove("access_token");
          Cookies.remove("refresh_token");
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: {
    email: string;
    full_name: string;
    password: string;
    organization_name?: string;
  }) => api.post("/auth/register", data),

  login: (data: { email: string; password: string }) =>
    api.post("/auth/login", data),

  me: () => api.get("/auth/me"),
};

// ─── Documents ───────────────────────────────────────────────────────────────
export const docsApi = {
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/documents/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  list: () => api.get("/documents"),
  delete: (id: number) => api.delete(`/documents/${id}`),
};

// ─── Chat ─────────────────────────────────────────────────────────────────────
export const chatApi = {
  send: (message: string, conversationId?: number) =>
    api.post("/chat", { message, conversation_id: conversationId }),

  listConversations: () => api.get("/chat/conversations"),

  getConversation: (id: number) => api.get(`/chat/conversations/${id}`),

  deleteConversation: (id: number) =>
    api.delete(`/chat/conversations/${id}`),
};

// ─── Dashboard ───────────────────────────────────────────────────────────────
export const dashboardApi = {
  getStats: () => api.get("/dashboard/stats"),
};

export default api;
