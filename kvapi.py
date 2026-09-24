"""kvapi.py：对外门面（老接口 put/get 不能改）。"""
from __future__ import annotations

from segmentedlock import Table


class KV:
    def __init__(self, buckets: int = 4, segments: int = 2):
        self.table = Table(buckets, segments)

    def put(self, key: str, value: str) -> dict:
        return self.table.put(key, value)

    def get(self, key: str) -> dict:
        return self.table.get(key)

    def resize(self) -> dict:
        return self.table.resize()

    def step_migrate(self, count: int) -> dict:
        return self.table.step_migrate(count)

    def snapshot(self) -> bytes:
        return self.table.persist()

    def rebuild(self, blob: bytes = None) -> dict:
        return self.table.restore(blob)
