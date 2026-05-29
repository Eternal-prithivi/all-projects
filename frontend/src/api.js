// =============================================================================
// MODULE: api.js  (400 lines)
// PURPOSE: Central Axios client + all named API function exports used across the frontend
//   - apiClient: Axios instance with base URL + Authorization interceptor (auto-attaches token)
//   - Named exports for every API call: listFiles, getDownloadUrl, deleteFile, uploadFile,
//     syncAwsBucket, getCurrentUser, status2FA, enable2FA, finalize2FA, verify2FA, disable2FA,
//     listSecureFiles, deleteSecureFile, uploadSecureFile, syncAwsSecureBucket,
//     chooseEncryption, decryptAndDownload, etc.
// BASE URL: http://localhost:8000 (dev) | https://zenith-backend-707i.onrender.com (prod)
// USED BY: Every page component — import { functionName } from '../api'
// EXCEPTIONS:
//   - VMClusterPage.jsx uses raw fetch() directly — intentional, does NOT use this file's apiClient
//   - SecurityPage.jsx imports named functions from here (NOT apiClient directly)
// DO NOT:
//   - Add a second Axios instance — one apiClient is the standard
//   - Hardcode the base URL inside individual functions — use the top-level constant
//   - Import apiClient in VMClusterPage — it uses its own fetch() pattern
// =============================================================================
import axios from "axios";

// Determine API base URL based on environment
// Use local backend for development
const API_BASE_URL = import.meta.env.MODE === 'production' 
  ? 'https://zenith-backend-707i.onrender.com/api'
  : 'http://localhost:8000/api';

console.log('🚀 API Base URL:', API_BASE_URL);
console.log('🚀 Environment:', import.meta.env.MODE);

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

export const requestPasswordReset = async (identifier, method = "email") => {
  try {
    const response = await apiClient.post("/auth/forgot-password", {
      identifier,
      method,
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const resetPasswordWithToken = async ({ newPassword, method, token, otp, identifier }) => {
  try {
    const response = await apiClient.post("/auth/reset-password", {
      new_password: newPassword,
      method,
      token: token || null,
      otp: otp || null,
      identifier: identifier || null,
    });
    return response.data;
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

export const uploadFile = async (file, csp, storageClass, token) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("csp", csp);
  formData.append("storage_class", storageClass);

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
    const response = await apiClient.get(`/storage/download/${encodeURIComponent(filename)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const deleteFile = async (filename, token) => {
  try {
    await apiClient.delete(`/storage/delete/${encodeURIComponent(filename)}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const syncAwsBucket = async (token) => {
  try {
    const response = await apiClient.post(
      "/storage/sync/aws",
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.data;
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

export const syncAwsSecureBucket = async (token) => {
  try {
    const response = await apiClient.post(
      "/security/sync/aws",
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const uploadClientEncrypted = async (
  encryptedBlob,
  originalFilename,
  isSensitive,
  token
) => {
  const formData = new FormData();
  formData.append("file", encryptedBlob, `${originalFilename}.enc`);
  formData.append("original_filename", originalFilename);
  formData.append("is_sensitive", isSensitive ? "true" : "false");

  try {
    const response = await apiClient.post("/security/upload-client-encrypted", formData, {
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

export const downloadClientCiphertext = async (filename, token) => {
  try {
    const response = await apiClient.get(
      `/security/download-ciphertext/${encodeURIComponent(filename)}`,
      {
        headers: { Authorization: `Bearer ${token}` },
        responseType: "blob",
      }
    );
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const chooseEncryption = async (filename, encryptionMethod, password, token) => {
  try {
    const response = await apiClient.post(
      "/security/choose-encryption",
      {
        filename,
        encryption_method: encryptionMethod,
        password: null,
      },
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

export const decryptAndDownload = async (filename, password, token) => {
  try {
    console.log('Making decrypt request for:', filename);
    const response = await apiClient.post(
      "/security/decrypt-download",
      {
        filename,
        password,
      },
      {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        responseType: 'blob', // Important: handle binary file data
      }
    );
    
    console.log('Full response:', response);
    console.log('Response data:', response.data);
    console.log('Response data type:', typeof response.data);
    console.log('Is Blob?:', response.data instanceof Blob);
    
    if (response.data instanceof Blob) {
      console.log('Response received, blob size:', response.data.size, 'type:', response.data.type);
    }
    
    // Check if response is actually an error (blob might be JSON error)
    if (response.data.type === 'application/json') {
      const text = await response.data.text();
      const error = JSON.parse(text);
      throw error;
    }
    
    // Create a download link and trigger download
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename; // Use download property instead of setAttribute
    link.style.display = 'none';
    
    // Add to DOM, click, then remove
    document.body.appendChild(link);
    console.log('Triggering download for:', filename);
    link.click();
    
    // Cleanup after a short delay
    setTimeout(() => {
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      console.log('Download cleanup complete');
    }, 100);
    
    return { success: true, message: "File downloaded successfully" };
  } catch (error) {
    console.error('Decrypt API error:', error);
    // If error.response exists and is a blob, parse it
    if (error.response?.data instanceof Blob) {
      try {
        const text = await error.response.data.text();
        const errorData = JSON.parse(text);
        throw errorData;
      } catch {
        throw { detail: "Decryption failed" };
      }
    }
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

// Export apiClient as default for convenience
export default apiClient;
