from time import monotonic

import pytest

from dispatcher.utils import LeakyBucket


@pytest.mark.parametrize(
    "size, rpm, hits, min_expected, max_expected",
    [
        [1, 6000, 1, 0, 0.01],
        [2, 6000, 2, 0, 0.01],
        [3, 6000, 3, 0, 0.01],
        [1, 600, 3, 0.15, 0.25],
        [3, 6000, 9, 0.06, 0.07],
    ],
)
async def test_leaky_bucket(size, rpm, hits, min_expected, max_expected):
    bucket = LeakyBucket(size, rpm)

    time1 = monotonic()

    for _ in range(hits):
        async with bucket.throttle():
            pass

    time2 = monotonic()

    assert min_expected <= time2 - time1 < max_expected
