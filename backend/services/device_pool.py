"""
DevicePool - 把"真机"显式建模为容量可配的串行资源

一部手机 = 容量 1：AutoGLM 同一时刻只能操作一块屏幕，所以并发的多源 / 多用户
搜索必须在此排队。这把原先隐式的模块级锁升级为**可观测**（in_use / waiting）、
**可扩容**（多设备 / 模拟器把容量调大 → 真并行）的资源池。

诚实边界：容量 1 时设备访问是串行的；并发只发生在编排层与非设备步骤。
"""
import os
import threading
from contextlib import contextmanager
from typing import Dict


class DevicePool:
    """信号量资源池：acquire() 阻塞直到拿到设备；stats() 暴露占用与排队数。"""

    def __init__(self, capacity: int = 1):
        if capacity < 1:
            raise ValueError("DevicePool capacity must be >= 1")
        self.capacity = capacity
        self._sem = threading.Semaphore(capacity)
        self._lock = threading.Lock()
        self._in_use = 0
        self._waiting = 0

    @contextmanager
    def acquire(self):
        """获取一个设备槽；阻塞期间计入 waiting，持有期间计入 in_use。"""
        with self._lock:
            self._waiting += 1
        try:
            self._sem.acquire()
        finally:
            with self._lock:
                self._waiting -= 1
        with self._lock:
            self._in_use += 1
        try:
            yield
        finally:
            with self._lock:
                self._in_use -= 1
            self._sem.release()

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {
                "capacity": self.capacity,
                "in_use": self._in_use,
                "waiting": self._waiting,
                "available": self.capacity - self._in_use,
            }


# 全局共享实例：taobao / jd 等所有真机技能争用同一部手机，必须共用一个池。
# 容量由 DEVICE_POOL_SIZE 控制（默认 1）；多设备时调大即获得真并行。
device_pool = DevicePool(int(os.getenv("DEVICE_POOL_SIZE", "1")))
