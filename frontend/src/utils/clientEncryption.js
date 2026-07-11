/**
 * Browser zero-knowledge encryption — matches backend encryption_handler format:
 * [16-byte salt][16-byte IV][AES-256-CBC ciphertext] with PBKDF2-HMAC-SHA256 (100k iter).
 */

const SALT_LENGTH = 16;
const IV_LENGTH = 16;
const PBKDF2_ITERATIONS = 100_000;

async function deriveAesKey(password, salt) {
  const enc = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    enc.encode(password),
    "PBKDF2",
    false,
    ["deriveKey"]
  );
  return crypto.subtle.deriveKey(
    {
      name: "PBKDF2",
      salt,
      iterations: PBKDF2_ITERATIONS,
      hash: "SHA-256",
    },
    keyMaterial,
    { name: "AES-CBC", length: 256 },
    false,
    ["encrypt", "decrypt"]
  );
}

/**
 * @param {File|Blob} file
 * @param {string} password
 * @returns {Promise<Blob>}
 */
export async function encryptFileInBrowser(file, password) {
  if (!password || password.length < 8) {
    throw new Error("Password must be at least 8 characters.");
  }
  const plainBuffer = await file.arrayBuffer();
  const salt = crypto.getRandomValues(new Uint8Array(SALT_LENGTH));
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));
  const key = await deriveAesKey(password, salt);
  const cipherBuffer = await crypto.subtle.encrypt(
    { name: "AES-CBC", iv },
    key,
    plainBuffer
  );
  const cipherBytes = new Uint8Array(cipherBuffer);
  const packed = new Uint8Array(SALT_LENGTH + IV_LENGTH + cipherBytes.length);
  packed.set(salt, 0);
  packed.set(iv, SALT_LENGTH);
  packed.set(cipherBytes, SALT_LENGTH + IV_LENGTH);
  return new Blob([packed], { type: "application/octet-stream" });
}

/**
 * @param {Blob|ArrayBuffer} encryptedPayload
 * @param {string} password
 * @returns {Promise<Blob>}
 */
export async function decryptBlobInBrowser(encryptedPayload, password) {
  const buffer =
    encryptedPayload instanceof ArrayBuffer
      ? encryptedPayload
      : await encryptedPayload.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  if (bytes.length < SALT_LENGTH + IV_LENGTH + 1) {
    throw new Error("Invalid encrypted file format.");
  }
  const salt = bytes.slice(0, SALT_LENGTH);
  const iv = bytes.slice(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
  const ciphertext = bytes.slice(SALT_LENGTH + IV_LENGTH);
  const key = await deriveAesKey(password, salt);
  try {
    const plain = await crypto.subtle.decrypt(
      { name: "AES-CBC", iv },
      key,
      ciphertext
    );
    return new Blob([plain]);
  } catch {
    throw new Error("Incorrect password or corrupted file.");
  }
}

/**
 * Trigger browser download of a decrypted file.
 */
export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.style.display = "none";
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
