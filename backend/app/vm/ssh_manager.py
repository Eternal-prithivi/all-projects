# backend/app/vm/ssh_manager.py

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import base64
from typing import Tuple

def generate_ssh_keypair() -> Tuple[str, str]:
    """
    Generate an RSA SSH key pair.
    
    Returns:
        Tuple[str, str]: (private_key_pem, public_key_openssh)
    """
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Get private key in PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Get public key in OpenSSH format
    public_key = private_key.public_key()
    public_key_openssh = public_key.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH
    ).decode('utf-8')
    
    return private_key_pem, public_key_openssh


def format_ssh_metadata(username: str, public_key: str) -> str:
    """
    Format SSH public key for GCP metadata.
    
    Args:
        username: Username for SSH access
        public_key: Public key in OpenSSH format
        
    Returns:
        str: Formatted string for GCP metadata
    """
    # GCP expects format: username:ssh-rsa AAAAB3... username
    return f"{username}:{public_key} {username}"


def encrypt_private_key(private_key: str, encryption_key: str) -> str:
    """
    Simple base64 encoding for storage (you can enhance with real encryption later).
    
    Args:
        private_key: Private key in PEM format
        encryption_key: Encryption key (can use JWT secret)
        
    Returns:
        str: Encrypted/encoded private key
    """
    # For now, just base64 encode. In production, use Fernet or AES encryption
    return base64.b64encode(private_key.encode('utf-8')).decode('utf-8')


def decrypt_private_key(encrypted_key: str, encryption_key: str) -> str:
    """
    Decrypt the stored private key.
    
    Args:
        encrypted_key: Encrypted/encoded private key
        encryption_key: Encryption key
        
    Returns:
        str: Decrypted private key in PEM format
    """
    return base64.b64decode(encrypted_key.encode('utf-8')).decode('utf-8')
