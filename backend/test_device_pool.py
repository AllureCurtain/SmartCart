"""
DevicePool 单测：容量1串行、容量2真并行、waiting 计数与 stats。纯内存，不碰真机。
"""
import threading
import time

import pytest

from services.device_pool import DevicePool, device_pool


def test_invalid_capacity_rejected():
    with pytest.raises(ValueError):
        DevicePool(0)


def test_capacity_one_serializes():
    pool = DevicePool(1)
    order = []

    def worker(name, hold):
        with pool.acquire():
            order.append(f"{name}-in")
            time.sleep(hold)
            order.append(f"{name}-out")

    t1 = threading.Thread(target=worker, args=("a", 0.2))
    t2 = threading.Thread(target=worker, args=("b", 0.0))
    t1.start()
    time.sleep(0.05)  # 确保 a 先拿到设备
    t2.start()
    t1.join()
    t2.join()
    # 容量1：b 必须等 a 释放后才进入
    assert order == ["a-in", "a-out", "b-in", "b-out"]


def test_capacity_two_allows_true_parallel():
    pool = DevicePool(2)
    inside = []
    barrier = threading.Barrier(2, timeout=2)

    def worker():
        with pool.acquire():
            inside.append(1)
            barrier.wait()  # 两者必须同时在临界区内，否则 barrier 超时抛错

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(inside) == 2  # barrier 通过 => 两个槽真的同时被持有


def test_waiting_counter_and_stats():
    pool = DevicePool(1)
    held = threading.Event()
    release = threading.Event()
    entered2 = threading.Event()

    def holder():
        with pool.acquire():
            held.set()
            release.wait(timeout=2)

    def waiter():
        with pool.acquire():
            entered2.set()

    h = threading.Thread(target=holder)
    h.start()
    assert held.wait(1)

    w = threading.Thread(target=waiter)
    w.start()
    time.sleep(0.1)  # 让 waiter 阻塞在 acquire 上

    s = pool.stats()
    assert s["in_use"] == 1 and s["available"] == 0
    assert s["waiting"] == 1
    assert not entered2.is_set()

    release.set()  # holder 释放设备
    assert entered2.wait(1)  # waiter 随即进入
    h.join()
    w.join()
    assert pool.stats() == {"capacity": 1, "in_use": 0, "waiting": 0, "available": 1}


def test_shared_module_pool_exists():
    assert device_pool.capacity >= 1
