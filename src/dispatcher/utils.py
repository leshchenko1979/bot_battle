import asyncio
import time
from collections import deque
from contextlib import asynccontextmanager


class LeakyBucket:
    def __init__(self, bucket_size: int, requests_per_minute: float):
        self.bucket_size = bucket_size
        self.drip_delay = 60 / requests_per_minute
        self.drips = deque()

    @asynccontextmanager
    async def throttle(self):
        # clean up
        while (
            self.drips
            and self.drips[0] < time.monotonic() - self.drip_delay * self.bucket_size
        ):
            self.drips.popleft()

        # if full then wait till the next drip
        if len(self.drips) >= self.bucket_size:
            await asyncio.sleep(time.monotonic() - self.drips[-1] + self.drip_delay)

        # register drop and yield
        self.drips.append(time.monotonic())
        yield
