import hmac
import hashlib
from config import settings

def verify_hmac_signature(payload_bytes: bytes, signature: str) -> bool:
    expected = hmac.new(settings.WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
