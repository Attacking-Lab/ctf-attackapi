import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from filelock import BaseFileLock, Timeout


@asynccontextmanager
async def acquire_filelock(fl: BaseFileLock, timeout: float = 10, interval: float = 0.01) -> AsyncGenerator[None, None]:
    """
    Acquire filelock, async_api implementation.
    Adapted from https://github.com/tox-dev/filelock/issues/78#issuecomment-1966513766
    """
    for _ in range(int(timeout / interval)):
        try:
            fl.acquire(blocking=False)
        except Timeout:
            await asyncio.sleep(interval)
            continue
        # We want to have the exclusive lock
        if fl.lock_counter <= 1:
            try:
                yield
            finally:
                fl.release()
            return
        # reentrant hold by an outer acquire: back off and retry
        fl.release()
        await asyncio.sleep(interval)
    raise TimeoutError("Could not obtain file lock")
