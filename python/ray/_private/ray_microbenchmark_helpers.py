import os
import time
from contextlib import contextmanager
from typing import List, Optional, Tuple

import numpy as np

import ray

# Only run tests matching this filter pattern.

filter_pattern = os.environ.get("TESTS_TO_RUN", "")
skip_pattern = os.environ.get("TESTS_TO_SKIP", "")


def timeit(
    name, fn, multiplier=1, warmup_time_sec=10
) -> List[Optional[Tuple[str, float, float]]]:
    if filter_pattern and filter_pattern not in name:
        return [None]
    if skip_pattern and skip_pattern in name:
        return [None]
    # sleep for a while to avoid noisy neigbhors.
    # related issue: https://github.com/ray-project/ray/issues/22045
    time.sleep(warmup_time_sec)
    # warmup
    start = time.perf_counter()
    count = 0
    while time.perf_counter() - start < 1:
        fn()
        count += 1
    # real run
    step = count // 10 + 1
    stats = []
    for _ in range(4):
        start = time.perf_counter()
        count = 0
        while time.perf_counter() - start < 2:
            for _ in range(step):
                fn()
            count += step
        end = time.perf_counter()
        stats.append(multiplier * count / (end - start))

    mean = np.mean(stats)
    sd = np.std(stats)
    print(name, "per second", round(mean, 2), "+-", round(sd, 2))
    return [(name, mean, sd)]


async def asyncio_timeit(
    name, async_fn, multiplier=1, warmup_time_sec=10
) -> List[Optional[Tuple[str, float, float]]]:
    if filter_pattern and filter_pattern not in name:
        return [None]
    if skip_pattern and skip_pattern in name:
        return [None]
    # sleep for a while to avoid noisy neigbhors.
    # related issue: https://github.com/ray-project/ray/issues/22045
    time.sleep(warmup_time_sec)
    # warmup
    start = time.perf_counter()
    count = 0
    while time.perf_counter() - start < 1:
        await async_fn()
        count += 1
    # real run
    step = count // 10 + 1
    stats = []
    for _ in range(4):
        start = time.perf_counter()
        count = 0
        while time.perf_counter() - start < 2:
            for _ in range(step):
                await async_fn()
            count += step
        end = time.perf_counter()
        stats.append(multiplier * count / (end - start))

    mean = np.mean(stats)
    sd = np.std(stats)
    print(name, "per second", round(mean, 2), "+-", round(sd, 2))
    return [(name, mean, sd)]


@contextmanager
def ray_setup_and_teardown(**init_args):
    ray.init(**init_args)
    try:
        yield None
    finally:
        ray.shutdown()
