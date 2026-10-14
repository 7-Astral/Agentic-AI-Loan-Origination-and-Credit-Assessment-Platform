import asyncio
import sys
import threading

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_loop = asyncio.new_event_loop()
threading.Thread(target=_loop.run_forever, name="agent-sync-runner", daemon=True).start()


def run(coro, timeout: float | None = 300):
    return asyncio.run_coroutine_threadsafe(coro, _loop).result(timeout)
