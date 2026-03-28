import httpx
import os
import time
import json

SPECIALIST_SERVICE_URL = "http://3.151.143.108:8080"
auth_token = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJkYW5pZWxAeW9wbWFpbC5jb20iLCJpYXQiOjE3NzQ3NDEwMzMsImV4cCI6MTc3NDgyNzQzM30.GMAAURtwgVQYlsadTgZCVmWK2ETv-uRjeBfGoH1HVuw"

print("Enviando petición...")
start = time.time()
try:
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = httpx.get(
        f"{SPECIALIST_SERVICE_URL}/api/specialist/",
        headers=headers,
        timeout=10.0,
    )
    print(f"Status CODE: {response.status_code}")
    print(f"Time: {time.time() - start:.2f}s")
    print(response.text)
except Exception as e:
    print(f"Error ({type(e).__name__}): {e}")
    print(f"Time: {time.time() - start:.2f}s")
