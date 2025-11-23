import os, uuid, requests
from urllib3.exceptions import InsecureRequestWarning
import urllib3

urllib3.disable_warnings(InsecureRequestWarning)  # убираем ворнинг в консоли

AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
SCOPE = "GIGACHAT_API_PERS"

auth_key_b64 = os.getenv("GIGA_AI_API_KEY", "").strip()
headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "Accept": "application/json",
    "RqUID": str(uuid.uuid4()),
    "Authorization": f"Basic {auth_key_b64}",
}
data = {"scope": SCOPE}

r = requests.post(AUTH_URL, headers=headers, data=data, timeout=30, verify=False)  # <— ключевое
print(r.status_code, r.text)
