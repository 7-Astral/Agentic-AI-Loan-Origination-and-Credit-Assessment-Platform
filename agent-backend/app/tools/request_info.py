import argparse
import asyncio
import sys
import uuid

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import select

from app.core.db import async_session
from app.models.application import Application, InformationRequest


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("message")
    parser.add_argument("--session")
    parser.add_argument("--document")
    parser.add_argument("--by", default="Credit Manager")
    args = parser.parse_args()

    async with async_session() as db:
        if args.session:
            application = await db.get(Application, uuid.UUID(args.session))
        else:
            result = await db.execute(
                select(Application)
                .where(Application.platform_application_id.is_not(None))
                .order_by(Application.updated_at.desc())
                .limit(1)
            )
            application = result.scalar_one_or_none()
        if application is None or application.platform_application_id is None:
            print("No submitted application found")
            return

        db.add(InformationRequest(
            id=uuid.uuid4(),
            application_id=application.id,
            kind="document" if args.document else "information",
            message=args.message,
            document_code=args.document if args.document and args.document != "other" else None,
            requested_by=args.by,
            status="open",
        ))
        await db.commit()
        print(f"Request added to application {application.id}")


if __name__ == "__main__":
    asyncio.run(main())
