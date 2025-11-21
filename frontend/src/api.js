import axios from "axios";

// Determine API base URL based on environment
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.PROD 
    ? 'https://zenith-backend-707i.onrender.com/api'  // Production backend
    : 'http://localhost:8000/api'        // Development
  );

// Create a reusable axios client
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

// Add request interceptor to automatically attach token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken'); // Changed from 'token' to 'authToken'
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// ---------------- AUTH ----------------

// Register
export const registerUser = async (userData) => {
  try {
    const response = await apiClient.post("/auth/register", userData);
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// Login
export const loginUser = async (credentials) => {
  const formData = new URLSearchParams();
  formData.append("username", credentials.username);
  formData.append("password", credentials.password);

  try {
    const response = await apiClient.post("/auth/token", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
    return response.data; // { access_token, token_type }
  } catch (error) {
    throw error.response?.data || error;
  }
};

// Current user
export const getCurrentUser = async (token) => {
  try {
    const response = await apiClient.get("/users/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// ---------------- STORAGE ----------------

export const uploadFile = async (file, token) => {
  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await apiClient.post("/storage/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const listFiles = async (token) => {
  try {
    const response = await apiClient.get("/storage/files", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const getDownloadUrl = async (filename, token) => {
  try {
    const response = await apiClient.get(`/storage/download/${filename}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const deleteFile = async (filename, token) => {
  try {
    await apiClient.delete(`/storage/delete/${filename}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (error) {
    throw error.response?.data || error;
  }
};

// ---------------- DASHBOARD ----------------

export const getDashboardStats = async (token) => {
  try {
    const response = await apiClient.get("/dashboard/stats", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// ---------------- SECURE STORAGE ----------------

export const uploadSecureFile = async (file, encrypt, token) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("encrypt_manual", encrypt);

  try {
    const response = await apiClient.post("/security/upload-secure", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const listSecureFiles = async (token) => {
  try {
    const response = await apiClient.get("/security/list-secure", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const getSecureDownloadUrl = async (filename, token) => {
  try {
    const response = await apiClient.get(`/security/download/${filename}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const deleteSecureFile = async (filename, token) => {
  try {
    await apiClient.delete(`/security/delete/${filename}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (error) {
    throw error.response?.data || error;
  }
};

// ---------------- 2FA ----------------

export const status2FA = async (token) => {
  try {
    const response = await apiClient.get("/2fa/status-2fa", {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data; // { enabled: true/false }
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const enable2FA = async (token) => {
  try {
    const response = await apiClient.post(
      "/2fa/enable-2fa",
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.data; // { qr_code: "...base64..." }
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const verify2FA = async (token, code) => {
  try {
    const response = await apiClient.post(
      "/2fa/verify-2fa",
      { code }, // JSON body
      {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data; // { verified: true/false }
  } catch (error) {
    throw error.response?.data || error;
  }
};

// Finalize 2FA
export const finalize2FA = async (token, code) => {
  try {
    const response = await apiClient.post(
      "/2fa/finalize-2fa",
      { code },
      {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

// Disable 2FA
export const disable2FA = async (token) => {
  try {
    const response = await apiClient.post(
      "/2fa/disable-2fa",
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};