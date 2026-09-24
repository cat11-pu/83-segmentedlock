"""segmentedlock.py：分段锁哈希表（基线：单锁、固定桶数）。"""
from __future__ import annotations


class Table:
    def __init__(self, buckets: int = 4, segments: int = 2):
        self.buckets = buckets
        self.segments = segments
        self.data = {}
        self.migrated = 0
        self.resizes = 0
        self.reads = 0

    def put(self, key: str, value: str) -> dict:
        """基线：直接放进单一字典。"""
        self.data[key] = value
        return {"size": len(self.data)}

    def get(self, key: str) -> dict:
        self.reads += 1
        return {"value": self.data.get(key)}

    def resize(self) -> dict:
        raise NotImplementedError("扩容还没实现")

    def step_migrate(self, count: int) -> dict:
        raise NotImplementedError("渐进迁移还没实现")

    def segment_of(self, key: str) -> int:
        raise NotImplementedError("分段归属还没实现")

    def persist(self) -> bytes:
        raise NotImplementedError("快照还没实现")

    def restore(self, blob: bytes = None) -> dict:
        raise NotImplementedError("重启恢复还没实现")

    def stats(self) -> dict:
        return {"buckets": self.buckets, "segments": self.segments, "size": len(self.data),
                "migrated": self.migrated, "resizes": self.resizes, "reads": self.reads}
