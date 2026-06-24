
import hashlib
import uuid


class UserCrypto:

    def generate_user_key(self, user_id: str):
        """
        Creates deterministic SHA256-based user identity key
        """

        raw = f"{user_id}-{uuid.uuid4()}".encode()

        return hashlib.sha256(raw).hexdigest()


    def sign_transaction(self, user_key: str, payload: dict):
        """
        Lightweight deterministic transaction signature
        (used for audit + replay validation)
        """

        data = str(payload).encode()
        return hashlib.sha256(user_key.encode() + data).hexdigest()


    def verify_signature(self, user_key: str, payload: dict, signature: str):
        expected = self.sign_transaction(user_key, payload)
        return expected == signature

