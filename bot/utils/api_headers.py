import hashlib
import json
import time
from typing import Optional
from urllib.parse import quote

def get_headers(
    api_key: str,
    payload: Optional[dict] = None
) -> dict:
    timestamp = int(time.time())
    
    if payload:
        body_string = json.dumps(payload, separators=(',', ':'))
    else:
        body_string = ""
    
    raw_string = f"{timestamp}_{body_string}"
    
    encoded_string = quote(raw_string, safe="~()*!.'-_")
    
    api_hash = hashlib.md5(encoded_string.encode()).hexdigest()
    
    return {
        "Api-Key": api_key,
        "Api-Time": str(timestamp),
        "Api-Hash": api_hash,
        "Content-Type": "application/json"
    }