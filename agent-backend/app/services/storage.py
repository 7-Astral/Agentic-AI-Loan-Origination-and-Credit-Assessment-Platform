import uuid
from pathlib import Path

UPLOAD_ROOT = Path("uploads")


class LocalDiskStorage:
    async def save(self, session_id: str, filename: str, content: bytes) -> str:
        session_dir = UPLOAD_ROOT / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(filename).suffix
        stored_name = f"{uuid.uuid4()}{ext}"
        path = session_dir / stored_name
        path.write_bytes(content)
        return str(path)

    async def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()


storage = LocalDiskStorage()