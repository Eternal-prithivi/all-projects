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
import { getApiBaseUrl } from "./config/apiBase.js";
import { shouldHandle401, triggerSessionExpired } from "./utils/sessionExpiry.js";

const API_BASE_URL = getApiBaseUrl();

if (import.meta.env.MODE === 'production') {
  console.info('[Zenith] API →', API_BASE_URL);
}

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

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401 && shouldHandle401(error.config)) {
      triggerSessionExpired();
    }
    return Promise.reject(error);
  }
);

// ---------------- AUTH ----------------

/** Parse FastAPI / Zenith error payloads for UI messages */
export const getApiErrorMessage = (error, fallback = "Something went wrong.") => {
  if (!error) return fallback;
  const detail = error.detail ?? error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object") {
    const parts = [];
    if (detail.message) parts.push(detail.message);
    if (Array.isArray(detail.setup_steps) && detail.setup_steps.length) {
      parts.push(...detail.setup_steps);
    }
    if (parts.length) return parts.join(" ");
    if (detail.error) return String(detail.error);
  }
  if (error.message && !error.message.includes("Network Error")) return error.message;
  if (!error.response) {
    return "Cannot reach the server. Start the backend (http://localhost:8000) and try again.";
  }
  return fallback;
};

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
export const loginUser = async (credentials, deviceFingerprint = null) => {
  const formData = new URLSearchParams();
  formData.append("username", String(credentials.username || "").trim());
  formData.append("password", credentials.password);

  const headers = { "Content-Type": "application/x-www-form-urlencoded" };
  if (deviceFingerprint) {
    headers["X-Device-Fingerprint"] = deviceFingerprint;
  }

  try {
    const response = await apiClient.post("/auth/token", formData, { headers });
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
  const response = await apiClient.get("/users/me", {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

// ---------------- STORAGE ----------------

export const uploadFile = async (
  file,
  csp,
  storageClass,
  token,
  { bucket, regionSlug, lifecyclePolicy, userPriority, userIntent, initialPlannedTier } = {}
) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("csp", csp);
  formData.append("storage_class", storageClass);
  if (bucket) formData.append("bucket", bucket);
  if (regionSlug) formData.append("region_slug", regionSlug);
  if (lifecyclePolicy) formData.append("lifecycle_policy", lifecyclePolicy);
  if (userPriority) formData.append("user_priority", userPriority);
  if (userIntent) formData.append("user_intent", userIntent);
  if (initialPlannedTier) formData.append("initial_planned_tier", initialPlannedTier);

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

export const storageLifecycleAction = async (filename, action, { snoozeDays = 30 } = {}) => {
  const response = await apiClient.post("/storage/lifecycle/action", {
    filename,
    action,
    snooze_days: snoozeDays,
  });
  return response.data;
};

export const fetchStorageIntelligenceSummary = async (params = {}) => {
  const response = await apiClient.get("/storage/intelligence/summary", { params });
  return response.data;
};

export const fetchStorageCostPreview = async (payload) => {
  const response = await apiClient.post("/storage/intelligence/cost-preview", payload);
  return response.data;
};

export const fetchSecurityIntelligenceSummary = async (token, params = {}) => {
  const response = await apiClient.get("/security/intelligence/summary", {
    params,
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const fetchSecurityCostPreview = async (token, payload) => {
  const response = await apiClient.post("/security/intelligence/cost-preview", payload, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return response.data;
};

export const securityVaultAction = async (token, filename, action, { snoozeDays = 30 } = {}) => {
  const response = await apiClient.post(
    "/security/vault/action",
    { filename, action, snooze_days: snoozeDays },
    { headers: { Authorization: `Bearer ${token}` } },
  );
  return response.data;
};

export const getAwsBuckets = async (surface = "storage", { region } = {}) => {
  try {
    const params = { surface };
    if (region) params.region = region;
    const response = await apiClient.get("/byoc/aws-buckets", { params });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const refreshAwsBuckets = async (surface = "storage", { region } = {}) => {
  try {
    const params = { surface };
    if (region) params.region = region;
    const response = await apiClient.post("/byoc/aws-buckets/refresh", null, { params });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const getGcpBuckets = async ({ surface = "storage" } = {}) => {
  try {
    const response = await apiClient.get("/byoc/gcp-buckets", { params: { surface } });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const getAzureContainers = async ({ surface = "storage" } = {}) => {
  try {
    const response = await apiClient.get("/byoc/azure-containers", { params: { surface } });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const listFiles = async (token, { bucket, region, platformSlug } = {}) => {
  try {
    const params = {};
    if (platformSlug) params.platform_slug = platformSlug;
    else {
      if (bucket) params.bucket = bucket;
      if (region && region !== "all") params.region = region;
    }
    const response = await apiClient.get("/storage/files", {
      params,
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const getDownloadUrl = async (filename, token, { bucket, region, platformSlug } = {}) => {
  try {
    const params = {};
    if (bucket) params.bucket = bucket;
    if (region) params.region = region;
    if (platformSlug) params.platform_slug = platformSlug;
    const response = await apiClient.get(
      `/storage/download/${encodeURIComponent(filename)}`,
      {
        params,
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const deleteFile = async (filename, token, { bucket, region, platformSlug } = {}) => {
  try {
    const params = {};
    if (bucket) params.bucket = bucket;
    if (region) params.region = region;
    if (platformSlug) params.platform_slug = platformSlug;
    await apiClient.delete(`/storage/delete/${encodeURIComponent(filename)}`, {
      params,
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const syncAwsBucket = async (token, { bucket, region, regionSlug } = {}) => {
  try {
    const params = {};
    if (regionSlug) params.region_slug = regionSlug;
    else {
      if (bucket) params.bucket = bucket;
      if (region && region !== "all") params.region = region;
    }
    const response = await apiClient.post("/storage/sync/aws", {}, {
      params,
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const syncGcpBucket = async (token, { bucket, regionSlug } = {}) => {
  try {
    const params = {};
    if (regionSlug) params.region_slug = regionSlug;
    else if (bucket) params.bucket = bucket;
    const response = await apiClient.post("/storage/sync/gcp", {}, {
      params,
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const syncAzureContainer = async (token, { container, regionSlug } = {}) => {
  try {
    const params = {};
    if (regionSlug) params.region_slug = regionSlug;
    else if (container) params.container = container;
    const response = await apiClient.post("/storage/sync/azure", {}, {
      params,
      headers: { Authorization: `Bearer ${token}` },
    });
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

export const scanSecureFile = async (file, token) => {
  const formData = new FormData();
  formData.append("file", file);
  try {
    const response = await apiClient.post("/security/scan", formData, {
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

export const uploadSecureFile = async (
  file,
  encrypt,
  token,
  alwaysAskEncryption = false,
  csp = "AWS",
  {
    skipEncryption = false,
    enableReplication = false,
    replicaRegion = null,
  } = {}
) => {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("encrypt_manual", encrypt);
  formData.append("always_ask_encryption", alwaysAskEncryption);
  formData.append("skip_encryption", skipEncryption);
  formData.append("enable_replication", enableReplication);
  if (replicaRegion) formData.append("replica_region", replicaRegion);
  formData.append("csp", csp);

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

export const listSecureFiles = async (token, { bucket, region } = {}) => {
  try {
    const params = {};
    if (bucket) params.bucket = bucket;
    if (region && region !== "all") params.region = region;
    const response = await apiClient.get("/security/list-secure", {
      params,
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const getSecureDownloadUrl = async (filename, token, { bucket } = {}) => {
  try {
    const params = {};
    if (bucket) params.bucket = bucket;
    const response = await apiClient.get(`/security/download/${filename}`, {
      params,
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const deleteSecureFile = async (filename, token, { bucket } = {}) => {
  try {
    const params = {};
    if (bucket) params.bucket = bucket;
    await apiClient.delete(`/security/delete/${filename}`, {
      params,
      headers: { Authorization: `Bearer ${token}` },
    });
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const syncSecureVault = async (token, csp, { bucket, region, container } = {}) => {
  try {
    const params = {};
    if (bucket) params.bucket = bucket;
    if (container) params.container = container;
    if (region && region !== "all") params.region = region;
    const response = await apiClient.post(
      `/security/sync/${encodeURIComponent(csp)}`,
      {},
      {
        params,
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

/** @deprecated Use syncSecureVault(token, "AWS", opts) */
export const syncAwsSecureBucket = async (token, opts = {}) =>
  syncSecureVault(token, "AWS", opts);

export const uploadClientEncrypted = async (
  encryptedBlob,
  originalFilename,
  isSensitive,
  token,
  { csp = "AWS", enableReplication = false } = {}
) => {
  const formData = new FormData();
  formData.append("file", encryptedBlob, `${originalFilename}.enc`);
  formData.append("original_filename", originalFilename);
  formData.append("is_sensitive", isSensitive ? "true" : "false");
  formData.append("csp", csp);
  formData.append("enable_replication", enableReplication ? "true" : "false");

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

export const downloadClientCiphertext = async (filename, token, { bucket } = {}) => {
  try {
    const params = {};
    if (bucket) params.bucket = bucket;
    const response = await apiClient.get(
      `/security/download-ciphertext/${encodeURIComponent(filename)}`,
      {
        params,
        headers: { Authorization: `Bearer ${token}` },
        responseType: "blob",
      }
    );
    return response.data;
  } catch (error) {
    throw error.response?.data || error;
  }
};

export const chooseEncryption = async (
  filename,
  encryptionMethod,
  password,
  token,
  { csp, enableReplication = false, replicaRegion } = {}
) => {
  try {
    const response = await apiClient.post(
      "/security/choose-encryption",
      {
        filename,
        encryption_method: encryptionMethod,
        password: password || null,
        csp: csp || null,
        enable_replication: enableReplication,
        replica_region: replicaRegion || null,
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

// Disable 2FA (code required when 2FA is already enabled)
export const disable2FA = async (token, code) => {
  try {
    const body = code ? { code } : {};
    const response = await apiClient.post(
      "/2fa/disable-2fa",
      body,
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

// Export apiClient as default for convenience
export default apiClient;
