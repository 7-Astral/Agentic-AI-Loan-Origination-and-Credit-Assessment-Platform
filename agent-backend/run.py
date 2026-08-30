import asyncio
import selectors
import sys

import uvicorn


async def main():
    config = uvicorn.Config("app.backend:app", host="127.0.0.1", port=8000)
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.run(main(), loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()))
    else:
        asyncio.run(main())