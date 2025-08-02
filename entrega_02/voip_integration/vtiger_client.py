import requests
import hashlib
from config import settings

class VtigerClient:
    def __init__(self):
        self.base = settings.VTIGER_URL.rstrip("/")
        self.session_name = None

    def login(self):
        # 1. getchallenge
        r = requests.get(self.base, params={
            "operation": "getchallenge",
            "username": settings.VTIGER_USERNAME
        }, timeout=10)
        r.raise_for_status()
        result = r.json().get("result", {})
        token = result.get("token")
        if not token:
            raise RuntimeError("No challenge token received from Vtiger")

        # 2. calcular accessKey
        access_key = hashlib.md5((token + settings.VTIGER_ACCESS_KEY).encode()).hexdigest()
        # 3. login
        r2 = requests.post(self.base, data={
            "operation": "login",
            "username": settings.VTIGER_USERNAME,
            "accessKey": access_key
        }, timeout=10)
        r2.raise_for_status()
        login_result = r2.json().get("result", {})
        self.session_name = login_result.get("sessionName")
        if not self.session_name:
            raise RuntimeError("Login failed to get sessionName")

    def query(self, soql: str):
        resp = requests.get(self.base, params={
            "operation": "query",
            "sessionName": self.session_name,
            "query": soql
        }, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def create(self, element_type: str, element: dict):
        payload = {
            "operation": "create",
            "sessionName": self.session_name,
            "elementType": element_type,
            "element": __import__("json").dumps(element)
        }
        r = requests.post(self.base, data=payload, timeout=10)
        r.raise_for_status()
        return r.json()

    def update(self, element_type: str, element: dict):
        payload = {
            "operation": "update",
            "sessionName": self.session_name,
            "elementType": element_type,
            "element": __import__("json").dumps(element)
        }
        r = requests.post(self.base, data=payload, timeout=10)
        r.raise_for_status()
        return r.json()
