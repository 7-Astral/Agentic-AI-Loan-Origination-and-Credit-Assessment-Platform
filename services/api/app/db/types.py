from cryptography.fernet import Fernet
from sqlalchemy.types import String, TypeDecorator

from app.core.config import settings

_fernet = Fernet(settings.fernet_key.encode())


class EncryptedString(TypeDecorator):
    """Transparently encrypts/decrypts a string column with Fernet (symmetric encryption).

    Use for sensitive PII: national ID, income, etc. Values are stored encrypted at
    rest and decrypted automatically on read — application code just sees plain strings.
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return _fernet.encrypt(str(value).encode()).decode()

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return _fernet.decrypt(value.encode()).decode()
