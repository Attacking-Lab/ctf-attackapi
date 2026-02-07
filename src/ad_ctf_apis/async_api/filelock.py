import asyncio
import contextlib
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from filelock import BaseFileLock


@asynccontextmanager
async def acquire_filelock(fl: BaseFileLock, timeout: float = 10, interval: float = 0.01) -> AsyncGenerator[None, None]:
    """
    Acquire filelock, async_api implementation.
    Adapted from https://github.com/tox-dev/filelock/issues/78#issuecomment-1966513766
    """
    for _ in range(int(timeout / interval)):
        with contextlib.suppress(TimeoutError):
            try:
                fl.acquire(blocking=False)
                # We want to have the exclusive lock
                if fl.lock_counter <= 1:
                    yield
                    break
            finally:
                fl.release()
        await asyncio.sleep(interval)
    else:
        raise TimeoutError("Could not obtain file lock")
