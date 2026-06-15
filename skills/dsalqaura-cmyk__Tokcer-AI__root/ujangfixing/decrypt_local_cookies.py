#!/usr/bin/env python3
import base64
import json
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def decrypt_cookies():
    file_path = "ujangfixing/tiktok_cookies.json"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found.")
        return
        
    # 1. Load the encrypted file
    with open(file_path, "r") as f:
        encrypted_obj = json.load(f)
    
    # 2. Extract values
    ciphertext_b64 = encrypted_obj["data"]
    ciphertext_bytes = base64.b64decode(ciphertext_b64)
    
    password = b"123"
    salt = b"123123"
    iterations = 1024 # 2^10
    
    # 3. Derive key using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations
    )
    key = kdf.derive(password)
    
    # 4. Decrypt using AES-GCM
    iv = ciphertext_bytes[:12]
    payload = ciphertext_bytes[12:]
    
    aesgcm = AESGCM(key)
    try:
        decrypted_bytes = aesgcm.decrypt(iv, payload, None)
        decrypted_str = decrypted_bytes.decode("utf-8")
        
        # 5. Overwrite the file with the raw decrypted JSON list
        decrypted_json = json.loads(decrypted_str)
        with open(file_path, "w") as f:
            json.dump(decrypted_json, f, indent=2)
            
        print("SUCCESS: Cookies successfully decrypted and written in place!")
    except Exception as e:
        import traceback
        print(f"Failed to decrypt: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    decrypt_cookies()
