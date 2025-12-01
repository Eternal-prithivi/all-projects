"""
Client-side and Server-side encryption handler for secure files.
Uses AES-256 for client-side encryption with user-provided password.
"""
import hashlib
import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import base64


def derive_key_from_password(password: str, salt: bytes = None) -> tuple:
    """
    Derives a 32-byte AES key from a password using PBKDF2.
    Returns (key, salt) tuple.
    """
    if salt is None:
        salt = os.urandom(16)  # 16 bytes salt
    
    # Use PBKDF2 with 100,000 iterations for key derivation
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return key, salt


def encrypt_file_client_side(file_content: bytes, password: str) -> tuple:
    """
    Encrypts file content using AES-256-CBC with user's password.
    Returns (encrypted_content, salt, iv) tuple.
    
    Args:
        file_content: The raw file bytes to encrypt
        password: User's password for encryption
        
    Returns:
        tuple: (encrypted_bytes, salt, iv) - all needed for decryption
    """
    # Derive encryption key from password
    key, salt = derive_key_from_password(password)
    
    # Generate random IV (Initialization Vector)
    iv = os.urandom(16)  # AES block size is 16 bytes
    
    # Pad the data to AES block size (16 bytes)
    padder = padding.PKCS7(128).padder()  # 128 bits = 16 bytes
    padded_data = padder.update(file_content) + padder.finalize()
    
    # Encrypt using AES-256-CBC
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()
    encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
    
    return encrypted_data, salt, iv


def decrypt_file_client_side(encrypted_content: bytes, password: str, salt: bytes, iv: bytes) -> bytes:
    """
    Decrypts file content using AES-256-CBC with user's password.
    
    Args:
        encrypted_content: The encrypted file bytes
        password: User's password (same as used for encryption)
        salt: Salt used during key derivation
        iv: Initialization vector used during encryption
        
    Returns:
        bytes: Decrypted file content
    """
    # Derive the same key using password and salt
    key, _ = derive_key_from_password(password, salt)
    
    # Decrypt using AES-256-CBC
    cipher = Cipher(
        algorithms.AES(key),
        modes.CBC(iv),
        backend=default_backend()
    )
    decryptor = cipher.decryptor()
    decrypted_padded_data = decryptor.update(encrypted_content) + decryptor.finalize()
    
    # Unpad the data
    unpadder = padding.PKCS7(128).unpadder()
    decrypted_data = unpadder.update(decrypted_padded_data) + unpadder.finalize()
    
    return decrypted_data


def prepare_encrypted_file_for_storage(encrypted_content: bytes, salt: bytes, iv: bytes) -> bytes:
    """
    Combines encrypted content with salt and IV for storage.
    Format: [16 bytes salt][16 bytes IV][encrypted content]
    
    This allows us to store everything in one file and extract it later.
    """
    return salt + iv + encrypted_content


def extract_encrypted_file_components(stored_content: bytes) -> tuple:
    """
    Extracts salt, IV, and encrypted content from stored file.
    
    Returns:
        tuple: (salt, iv, encrypted_content)
    """
    salt = stored_content[:16]
    iv = stored_content[16:32]
    encrypted_content = stored_content[32:]
    
    return salt, iv, encrypted_content
