import boto3
import re
import requests
from pymongo import MongoClient
from app.celery_worker import celery_app
from app.utils.config import settings
# We no longer import the global mongodb_client to prevent connection sharing issues.

@celery_app.task
def process_secure_file(s3_key: str, owner_username: str, encrypt_manual: bool):
    """
    Celery task to process a secure file: scan for sensitive data, encrypt if necessary,
    replicate to a backup bucket, and update the database.
    """
    # --- DEFINITIVE FIX: Initialize ALL clients *inside* the task ---
    # This ensures each worker process gets its own fresh, stable connection to S3 and MongoDB,
    # which is the correct and robust way to prevent the SIGSEGV crash.
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
    
    # A new, isolated MongoDB client and collection is created for this task only.
    mongo_client = MongoClient(settings.MONGO_CONNECTION_STRING)
    db = mongo_client['CloudResourceOptimizationDB']
    files_db = db["secure_files"]

    # --- FIX: Corrected the typo from s_key to s3_key ---
    print(f"\n[DEBUG 1] Task received for s3_key='{s3_key}', owner='{owner_username}', encrypt_manual={encrypt_manual}")
    
    is_sensitive = False
    is_encrypted = False

    try:
        scannable_extensions = ('.txt', '.json', '.csv', '.py', '.js', '.md', '.html', '.xml', '.log')
        filename = s3_key.split('/')[-1]

        is_scannable = filename.lower().endswith(scannable_extensions)
        print(f"[DEBUG 2] Filename: '{filename}'. Is scannable? {is_scannable}. Not encrypt_manual? {not encrypt_manual}.")

        if not encrypt_manual and is_scannable:
            print("[DEBUG 3] Condition met. Proceeding to download and scan file from S3.")
            response = s3_client_primary.get_object(Bucket=settings.SECURE_S3_BUCKET_NAME, Key=s3_key)
            content_bytes = response['Body'].read()
            content_str = content_bytes.decode('utf-8', errors='ignore')

            print(f"[DEBUG 4] File content sample (first 200 chars):\n---\n{content_str[:200]}\n---")

            credit_card_pattern = r'\b(?:\d[ -]*?){13,16}\b'
            secret_keywords_pattern = r'(?i)\b(password|secret|key|pwd|token|credentials|apikeys|private_key|auth_token)\b'

            cc_match = re.search(credit_card_pattern, content_str)
            keyword_match = re.search(secret_keywords_pattern, content_str)

            print(f"[DEBUG 5] RegEx Scan Results - CC Match: {cc_match}, Keyword Match: {keyword_match}")

            if cc_match or keyword_match:
                is_sensitive = True

        print(f"[DEBUG 6] Status before encryption block - is_sensitive: {is_sensitive}, encrypt_manual: {encrypt_manual}")

        if is_sensitive or encrypt_manual:
            is_encrypted = True
            if encrypt_manual:
                is_sensitive = True
            
            print(f"[DEBUG 7] Encrypting and replicating '{s3_key}'...")
            s3_client_primary.copy_object(
                Bucket=settings.SECURE_S3_BUCKET_NAME,
                Key=s3_key,
                CopySource={'Bucket': settings.SECURE_S3_BUCKET_NAME, 'Key': s3_key},
                # --- FIX: Corrected the encryption algorithm from AES26 to AES256 ---
                ServerSideEncryption='AES256',
                MetadataDirective='REPLACE'
            )

            s3_client_replica.copy_object(
                Bucket=settings.REPLICA_S3_BUCKET_NAME,
                Key=s3_key,
                CopySource={'Bucket': settings.SECURE_S3_BUCKET_NAME, 'Key': s3_key},
            )
            print(f"Successfully encrypted and replicated {s3_key} to replica bucket.")

        update_payload = {"$set": {"is_sensitive": is_sensitive, "is_encrypted": is_encrypted}}
        print(f"[DEBUG 8] Updating MongoDB for s3_key='{s3_key}' with payload: {update_payload}")

        files_db.update_one({"s3_key": s3_key}, update_payload)
        
        print(f"Finished processing {s3_key}. Final Status - Sensitive: {is_sensitive}, Encrypted: {is_encrypted}")

    except Exception as e:
        print(f"!!! An ERROR occurred while processing {s3_key}: {e}")

    finally:
        # It's good practice to close the manually created client connection.
        if 'mongo_client' in locals():
            mongo_client.close()
        
        try:
            requests.post(f"http://localhost:8000/ws/notify/{owner_username}")
        except Exception as e:
            print(f"Could not notify WebSocket for user {owner_username}: {e}")

