import re
import requests
import io
from pymongo import MongoClient
from app.celery_worker import celery_app
from app.utils.config import settings
from app.utils.logger import setup_logger
from app.storage.cloud_credentials import resolve_secure_aws_storage
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
    storage = resolve_secure_aws_storage(owner_username)
    s3_client_primary = storage.primary_client
    bucket_name = storage.primary_bucket

    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    db = mongo_client['CloudResourceOptimizationDB']
    files_db = db["secure_files"]

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
            response = s3_client_primary.get_object(Bucket=bucket_name, Key=s3_key)
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

        if encrypt_manual:
            logger.info(f"File '{s3_key}' was manually marked for encryption. Status already set in DB.")
            update_payload = {
                "$set": {
                    "is_sensitive": True if is_sensitive else True
                }
            }
        else:
            needs_encryption = is_sensitive
            
            if needs_encryption:
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
    """
    storage = resolve_secure_aws_storage(owner_username)
    s3_client_primary = storage.primary_client
    s3_client_replica = storage.replica_client
    bucket_name = storage.primary_bucket
    replica_bucket = storage.replica_bucket
    
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    db = mongo_client['CloudResourceOptimizationDB']
    files_db = db["secure_files"]
    
    logger.info(f"Applying {encryption_method} encryption to '{s3_key}'")
    
    try:
        if encryption_method == "server-side":
            logger.info(f"Applying server-side encryption to '{s3_key}'")
            
            s3_client_primary.copy_object(
                Bucket=bucket_name,
                Key=s3_key,
                CopySource={'Bucket': bucket_name, 'Key': s3_key},
                ServerSideEncryption='AES256',
                MetadataDirective='REPLACE'
            )
            
            if s3_client_replica and replica_bucket:
                s3_client_replica.copy_object(
                    Bucket=replica_bucket,
                    Key=s3_key,
                    CopySource={'Bucket': bucket_name, 'Key': s3_key},
                )
            
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
            if not password:
                raise ValueError("Password required for client-side encryption")
            
            logger.info(f"Applying client-side encryption to '{s3_key}'")
            
            response = s3_client_primary.get_object(Bucket=bucket_name, Key=s3_key)
            original_content = response['Body'].read()
            
            encrypted_content, salt, iv = encrypt_file_client_side(original_content, password)
            final_encrypted_data = prepare_encrypted_file_for_storage(encrypted_content, salt, iv)
            
            s3_client_primary.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=final_encrypted_data,
                Metadata={
                    'encryption': 'client-side',
                    'algorithm': 'AES-256-CBC'
                }
            )
            
            if s3_client_replica and replica_bucket:
                s3_client_replica.put_object(
                    Bucket=replica_bucket,
                    Key=s3_key,
                    Body=final_encrypted_data,
                    Metadata={
                        'encryption': 'client-side',
                        'algorithm': 'AES-256-CBC'
                    }
                )
            
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
        
        try:
            requests.post(f"http://localhost:8000/ws/notify/{owner_username}")
            logger.debug(f"WebSocket notification sent for user {owner_username}")
        except Exception as e:
            logger.warning(f"Could not notify WebSocket for user {owner_username}: {e}")
            
    except Exception as e:
        logger.error(f"Error applying encryption to {s3_key}: {e}")
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
