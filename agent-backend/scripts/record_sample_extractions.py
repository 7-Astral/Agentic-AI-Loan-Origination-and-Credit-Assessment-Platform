import argparse
import asyncio
import json
import mimetypes
from datetime import datetime, timezone

from app.agents.document.process import process_document
from app.agents.document.sample_docs import SAMPLES, recording_file, sample_file
from app.core.config import get_settings


async def record(sample: dict) -> None:
    path = sample_file(sample)
    content_type = mimetypes.guess_type(path.name)[0] or "image/png"
    result = await process_document(sample["verification_type"], path.read_bytes(), content_type, {})
    if not result["matches_claimed_type"]:
        raise SystemExit(f"{sample['id']}: model did not recognise the document ({result['notes']}); not saving")

    recording = {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "model": get_settings().model_for("document"),
        "result": {k: result[k] for k in ("matches_claimed_type", "fields", "notes")},
    }
    recording_file(sample).write_text(json.dumps(recording, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"recorded {sample['id']} -> {recording_file(sample).name}")


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=[s["id"] for s in SAMPLES])
    args = parser.parse_args()
    for sample in SAMPLES:
        if args.only in (None, sample["id"]):
            await record(sample)


asyncio.run(main())
