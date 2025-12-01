import boto3
import re
import requests
import io
from pymongo import MongoClient
from app.celery_worker import celery_app
from app.utils.config import settings
from app.utils.logger import setup_logger
from app.security.encryption_handler import (
    encrypt_file_client_side,
    prepare_encrypted_file_for_storage
)
# We no longer import the global mongodb_client to prevent connection sharing issues.

logger = setup_logger(__name__)

@celery_app.task
def process_secure_file(s3_key: str, owner_username: str, encrypt_manual: bool):
    """
    Celery task to process a secure file: scan for sensitive data, 
    and determine if encryption is needed. If encryption is needed,
    mark file as awaiting user's encryption choice.
    """
    # --- DEFINITIVE FIX: Initialize ALL clients *inside* the task ---
    # This ensures each worker process gets its own fresh, stable connection to S3 and MongoDB,
    # which is the correct and robust way to prevent the SIGSEGV crash.
    s3_client_primary = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    
    # A new, isolated MongoDB client and collection is created for this task only.
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    db = mongo_client['CloudResourceOptimizationDB']
    files_db = db["secure_files"]

    # --- FIX: Corrected the typo from s_key to s3_key ---
    logger.debug(f"Task received for s3_key='{s3_key}', owner='{owner_username}', encrypt_manual={encrypt_manual}")
    
    is_sensitive = False
    needs_encryption = False

    try:
        scannable_extensions = ('.txt', '.json', '.csv', '.py', '.js', '.md', '.html', '.xml', '.log')
        filename = s3_key.split('/')[-1]

        is_scannable = filename.lower().endswith(scannable_extensions)
        logger.debug(f"Filename: '{filename}'. Is scannable? {is_scannable}. Not encrypt_manual? {not encrypt_manual}")

        if not encrypt_manual and is_scannable:
            logger.debug("Condition met. Proceeding to download and scan file from S3")
            response = s3_client_primary.get_object(Bucket=settings.SECURE_S3_BUCKET_NAME, Key=s3_key)
            content_bytes = response['Body'].read()
            content_str = content_bytes.decode('utf-8', errors='ignore')

            logger.debug(f"File content sample (first 200 chars): {content_str[:200]}")

            credit_card_pattern = r'\b(?:\d[ -]*?){13,16}\b'
            secret_keywords_pattern = r'(?i)\b(password|secret|key|pwd|token|credentials|apikeys|private_key|auth_token)\b'

            cc_match = re.search(credit_card_pattern, content_str)
            keyword_match = re.search(secret_keywords_pattern, content_str)

            logger.debug(f"RegEx Scan Results - CC Match: {cc_match}, Keyword Match: {keyword_match}")

            if cc_match or keyword_match:
                is_sensitive = True

        logger.debug(f"Status before encryption block - is_sensitive: {is_sensitive}, encrypt_manual: {encrypt_manual}")

        # If manual encryption was requested, it's already set in the database - don't override
        if encrypt_manual:
            logger.info(f"File '{s3_key}' was manually marked for encryption. Status already set in DB.")
            # Just update sensitivity based on scan, but don't change encryption status
            update_payload = {
                "$set": {
                    "is_sensitive": True if is_sensitive else True  # Mark as sensitive if manual encrypt
                }
            }
        else:
            # Determine if encryption is needed based on scan results
            needs_encryption = is_sensitive
            
            if needs_encryption:
                # Mark file as awaiting user's encryption choice
                logger.info(f"File '{s3_key}' needs encryption. Awaiting user choice.")
                update_payload = {
                    "$set": {
                        "is_sensitive": True,
                        "is_encrypted": False,
                        "encryption_status": "awaiting_choice",
                        "awaiting_encryption_choice": True,
                        "encryption_method": "none"
                    }
                }
            else:
                # File doesn't need encryption
                logger.info(f"File '{s3_key}' does not need encryption.")
                update_payload = {
                    "$set": {
                        "is_sensitive": False,
                        "is_encrypted": False,
                        "encryption_status": "none",
                        "awaiting_encryption_choice": False,
                        "encryption_method": "none"
                    }
                }

        logger.debug(f"Updating MongoDB for s3_key='{s3_key}' with payload: {update_payload}")
        files_db.update_one({"s3_key": s3_key}, update_payload)
        
        logger.info(f"Finished processing {s3_key}. Sensitive: {is_sensitive}, Needs Encryption: {needs_encryption}")
        
        # Notify user via WebSocket that processing is complete
        try:
            requests.post(f"http://localhost:8000/ws/notify/{owner_username}")
            logger.debug(f"WebSocket notification sent for user {owner_username}")
        except Exception as ws_error:
            logger.warning(f"Could not notify WebSocket for user {owner_username}: {ws_error}")

    except Exception as e:
        logger.error(f"Error processing {s3_key}: {e}")
    finally:
        if 'mongo_client' in locals():
            mongo_client.close()


@celery_app.task
def apply_encryption_to_file(s3_key: str, owner_username: str, encryption_method: str, password: str = None):
    """
    Celery task to apply encryption to a file based on user's choice.
    
    Args:
        s3_key: S3 object key
        owner_username: File owner
        encryption_method: "server-side" or "client-side"
        password: User's password for client-side encryption (required if client-side)
    """
    s3_client_primary = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )
    s3_client_replica = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.REPLICA_S3_REGION
    )
    
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    db = mongo_client['CloudResourceOptimizationDB']
    files_db = db["secure_files"]
    
    logger.info(f"Applying {encryption_method} encryption to '{s3_key}'")
    
    try:
        if encryption_method == "server-side":
            # Server-side encryption: AWS manages the keys
            logger.info(f"Applying server-side encryption to '{s3_key}'")
            
            # Apply AES-256 encryption on S3
            s3_client_primary.copy_object(
                Bucket=settings.SECURE_S3_BUCKET_NAME,
                Key=s3_key,
                CopySource={'Bucket': settings.SECURE_S3_BUCKET_NAME, 'Key': s3_key},
                ServerSideEncryption='AES256',
                MetadataDirective='REPLACE'
            )
            
            # Replicate to backup bucket
            s3_client_replica.copy_object(
                Bucket=settings.REPLICA_S3_BUCKET_NAME,
                Key=s3_key,
                CopySource={'Bucket': settings.SECURE_S3_BUCKET_NAME, 'Key': s3_key},
            )
            
            # Update database
            files_db.update_one(
                {"s3_key": s3_key},
                {
                    "$set": {
                        "is_encrypted": True,
                        "encryption_method": "server-side",
                        "encryption_status": "encrypted",
                        "awaiting_encryption_choice": False,
                        "client_side_encrypted": False
                    }
                }
            )
            logger.info(f"Server-side encryption applied to '{s3_key}'")
            
        elif encryption_method == "client-side":
            # Client-side encryption: User controls the key
            if not password:
                raise ValueError("Password required for client-side encryption")
            
            logger.info(f"Applying client-side encryption to '{s3_key}'")
            
            # Download the file from S3
            response = s3_client_primary.get_object(
                Bucket=settings.SECURE_S3_BUCKET_NAME,
                Key=s3_key
            )
            original_content = response['Body'].read()
            
            # Encrypt the file with user's password
            encrypted_content, salt, iv = encrypt_file_client_side(original_content, password)
            
            # Prepare for storage (combine salt, iv, and encrypted content)
            final_encrypted_data = prepare_encrypted_file_for_storage(encrypted_content, salt, iv)
            
            # Upload encrypted file back to S3 (replacing original)
            s3_client_primary.put_object(
                Bucket=settings.SECURE_S3_BUCKET_NAME,
                Key=s3_key,
                Body=final_encrypted_data,
                Metadata={
                    'encryption': 'client-side',
                    'algorithm': 'AES-256-CBC'
                }
            )
            
            # Replicate encrypted file to backup bucket
            s3_client_replica.put_object(
                Bucket=settings.REPLICA_S3_BUCKET_NAME,
                Key=s3_key,
                Body=final_encrypted_data,
                Metadata={
                    'encryption': 'client-side',
                    'algorithm': 'AES-256-CBC'
                }
            )
            
            # Update database
            files_db.update_one(
                {"s3_key": s3_key},
                {
                    "$set": {
                        "is_encrypted": True,
                        "encryption_method": "client-side",
                        "encryption_status": "encrypted",
                        "awaiting_encryption_choice": False,
                        "client_side_encrypted": True
                    }
                }
            )
            logger.info(f"Client-side encryption applied to '{s3_key}'")
        
        # Notify user via WebSocket
        try:
            requests.post(f"http://localhost:8000/ws/notify/{owner_username}")
            logger.debug(f"WebSocket notification sent for user {owner_username}")
        except Exception as e:
            logger.warning(f"Could not notify WebSocket for user {owner_username}: {e}")
            
    except Exception as e:
        logger.error(f"Error applying encryption to {s3_key}: {e}")
        # Mark encryption as failed
        files_db.update_one(
            {"s3_key": s3_key},
            {
                "$set": {
                    "encryption_status": "failed",
                    "awaiting_encryption_choice": False
                }
            }
        )
    finally:
        if 'mongo_client' in locals():
            mongo_client.close()

