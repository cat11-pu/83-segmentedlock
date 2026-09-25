"""segmentedlock.py：分段锁哈希表（渐进式扩容 + 快照恢复）。

设计要点：
- 数据按"代"组织：当前代 self.data（新表）+ 迁移中的旧桶列表 self.old。
- resize 只做 O(1) 的指针切换：旧桶保留、游标归零，绝不当场全表搬迁。
- step_migrate 按桶粒度渐进迁移，每轮最多搬 count 个旧桶，
  单轮复杂度 O(该轮桶数 × 桶内键数)。
- 迁移期间：读先查新表、未命中再查旧表；写只落新表，并把键从旧桶摘除，
  保证任何时刻键只存在于一侧（不丢不重、不读到过期值）。
- persist/restore 快照新旧两表、桶数与迁移游标，崩溃后可接着续迁。
"""
from __future__ import annotations

import pickle
import zlib


class Table:
    def __init__(self, buckets: int = 4, segments: int = 2):
        self.buckets = buckets
        self.segments = segments
        self.data = {}          # 当前代（新表）
        self.old = []           # 旧桶列表：待迁移的桶（基线表整体算一个桶）
        self.cursor = 0         # 迁移游标：下一个待迁移的旧桶下标
        self.migrated = 0       # 本轮扩容已累计迁移的键数
        self.resizes = 0
        self.reads = 0

    @staticmethod
    def _hash(key: str) -> int:
        return zlib.crc32(str(key).encode("utf-8"))

    def _size(self) -> int:
        return len(self.data) + sum(len(bucket) for bucket in self.old[self.cursor:])

    def segment_of(self, key: str) -> int:
        """按键的哈希把键分到 segments 个段之一（同键恒定同段）。"""
        return self._hash(key) % self.segments

    def put(self, key: str, value: str) -> dict:
        """写操作在新表落位；若键还在旧桶，顺手摘除，避免旧值稍后覆盖新值。"""
        if self.old:
            for bucket in self.old[self.cursor:]:
                if key in bucket:
                    del bucket[key]
                    break
        self.data[key] = value
        return {"size": self._size()}

    def get(self, key: str) -> dict:
        """读操作先查新表，未命中再查旧表。"""
        self.reads += 1
        if key in self.data:
            return {"value": self.data[key]}
        for bucket in self.old[self.cursor:]:
            if key in bucket:
                return {"value": bucket[key]}
        return {"value": None}

    def resize(self) -> dict:
        """扩容：桶数翻倍，旧桶保留（不立刻搬数据），迁移游标归零。"""
        pending = self.old[self.cursor:]  # 上一轮没迁完的旧桶（如有）继续保留
        self.old = pending + [self.data]
        self.data = {}
        self.buckets *= 2
        self.cursor = 0
        self.migrated = 0
        self.resizes += 1
        return {"buckets": self.buckets, "pending": sum(len(b) for b in self.old)}

    def step_migrate(self, count: int) -> dict:
        """渐进式迁移：每轮最多迁移 count 个旧桶，返回累计已迁移键数。"""
        stop = min(self.cursor + max(int(count), 0), len(self.old))
        while self.cursor < stop:
            bucket = self.old[self.cursor]
            for key, value in bucket.items():
                self.data[key] = value
                self.migrated += 1
            bucket.clear()
            self.cursor += 1
        remaining = sum(len(bucket) for bucket in self.old[self.cursor:])
        done = remaining == 0
        if done:
            self.old = []
            self.cursor = 0
        return {"migrated": self.migrated, "remaining": remaining, "done": done}

    def persist(self) -> bytes:
        """快照落盘：新旧两表、桶数、迁移游标全部带走。"""
        snapshot = {
            "buckets": self.buckets,
            "segments": self.segments,
            "data": self.data,
            "old": self.old,
            "cursor": self.cursor,
            "migrated": self.migrated,
            "resizes": self.resizes,
            "reads": self.reads,
        }
        return pickle.dumps(snapshot)

    def restore(self, blob: bytes = None) -> dict:
        """重启恢复：回到快照时的状态，未完成的迁移可以接着做。"""
        if blob:
            snapshot = pickle.loads(blob)
            self.buckets = snapshot["buckets"]
            self.segments = snapshot["segments"]
            self.data = snapshot["data"]
            self.old = snapshot["old"]
            self.cursor = snapshot["cursor"]
            self.migrated = snapshot["migrated"]
            self.resizes = snapshot["resizes"]
            self.reads = snapshot["reads"]
        return {"size": self._size(), "buckets": self.buckets,
                "segments": self.segments, "migrated": self.migrated,
                "resizes": self.resizes}

    def stats(self) -> dict:
        return {"buckets": self.buckets, "segments": self.segments, "size": self._size(),
                "migrated": self.migrated, "resizes": self.resizes, "reads": self.reads}
