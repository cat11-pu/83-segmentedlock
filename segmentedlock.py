"""segmentedlock.py：分段锁哈希表。

功能迭代：分段锁、倍增扩容、渐进式迁移（新旧双表路由）、快照与恢复。
纯 Python 标准库实现。
"""
from __future__ import annotations

import json
import threading
import zlib


class Table:
    def __init__(self, buckets: int = 4, segments: int = 2):
        self.buckets = buckets
        self.segments = segments
        # 当前（新）表：物理桶列表。初始为遗留单桶（基线的单一字典，
        # 名义桶数从未真正分桶），首次扩容迁移后才变成真正的多桶结构。
        self.data = [dict()]
        self.old = None          # 旧表桶列表，仅迁移期间存在
        self.old_buckets = 0     # 旧表桶数
        self.cursor = 0          # 迁移游标：下一个待迁移的旧桶编号
        self.migrated = 0        # 累计已迁移键数
        self.resizes = 0
        self.reads = 0
        self._locks = [threading.Lock() for _ in range(segments)]
        self._migrate_lock = threading.RLock()

    @staticmethod
    def _hash(key: str) -> int:
        return zlib.crc32(key.encode("utf-8"))

    def _size(self) -> int:
        total = sum(len(bucket) for bucket in self.data)
        if self.old is not None:
            total += sum(len(bucket) for bucket in self.old)
        return total

    def segment_of(self, key: str) -> int:
        """按键的哈希把键分到 segments 个段之一（同一个键必得同一个段号）。"""
        return self._hash(key) % self.segments

    def put(self, key: str, value: str) -> dict:
        """写操作只在新表落位；若键还躺在旧表，顺手摘除，免得日后迁回过期值。"""
        with self._locks[self.segment_of(key)]:
            index = self._hash(key) % len(self.data)
            self.data[index][key] = value
            if self.old is not None:
                old_index = self._hash(key) % len(self.old)
                if key in self.old[old_index]:
                    del self.old[old_index][key]
                    self.migrated += 1
            return {"size": self._size()}

    def get(self, key: str) -> dict:
        """读操作先查新表，未命中再查旧表（迁移期间两边都可能命中）。"""
        self.reads += 1
        with self._locks[self.segment_of(key)]:
            index = self._hash(key) % len(self.data)
            if key in self.data[index]:
                return {"value": self.data[index][key]}
            if self.old is not None:
                old_index = self._hash(key) % len(self.old)
                if key in self.old[old_index]:
                    return {"value": self.old[old_index][key]}
            return {"value": None}

    def resize(self) -> dict:
        """扩容：桶数翻倍，旧桶保留（不立刻搬数据），迁移游标归零。"""
        with self._migrate_lock:
            if self.old is not None:
                raise RuntimeError("上一次迁移还没完成，不能再扩容")
            self.old = self.data
            self.old_buckets = len(self.data)
            self.buckets *= 2
            self.data = [dict() for _ in range(self.buckets)]
            self.cursor = 0
            self.migrated = 0
            self.resizes += 1
            return {"buckets": self.buckets}

    def step_migrate(self, count: int) -> dict:
        """渐进式迁移：每轮最多迁移 count 个旧桶（按新旧桶映射重新分配）。

        每轮代价为 O(该轮桶数 x 桶内键数)，不一次全表搬迁；
        返回累计已迁移键数 migrated。
        """
        with self._migrate_lock:
            if self.old is None:
                return {"migrated": self.migrated, "done": True}
            steps = max(0, count)
            while steps > 0 and self.cursor < self.old_buckets:
                bucket = self.old[self.cursor]
                for key, value in bucket.items():
                    index = self._hash(key) % len(self.data)
                    # setdefault：迁移期间新写入的值不被旧值覆盖
                    self.data[index].setdefault(key, value)
                    self.migrated += 1
                bucket.clear()
                self.cursor += 1
                steps -= 1
            if self.cursor >= self.old_buckets:
                self.old = None
                self.old_buckets = 0
                self.cursor = 0
            return {"migrated": self.migrated, "done": self.old is None}

    def persist(self) -> bytes:
        """快照落盘：新旧两表、桶数与迁移游标全部序列化，未完成的迁移可接着做。"""
        with self._migrate_lock:
            snapshot = {
                "buckets": self.buckets,
                "segments": self.segments,
                "resizes": self.resizes,
                "reads": self.reads,
                "migrated": self.migrated,
                "cursor": self.cursor,
                "old_buckets": self.old_buckets,
                "data": self.data,
                "old": self.old,
            }
            return json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode("utf-8")

    def restore(self, blob: bytes = None) -> dict:
        """重启恢复：从快照还原新旧两表、桶数与迁移游标。"""
        with self._migrate_lock:
            if blob is None:
                return {"size": self._size(), "buckets": self.buckets}
            if isinstance(blob, (bytes, bytearray)):
                blob = blob.decode("utf-8")
            snapshot = json.loads(blob)
            self.buckets = snapshot["buckets"]
            self.segments = snapshot["segments"]
            self.resizes = snapshot["resizes"]
            self.reads = snapshot["reads"]
            self.migrated = snapshot["migrated"]
            self.cursor = snapshot["cursor"]
            self.old_buckets = snapshot["old_buckets"]
            self.data = [dict(bucket) for bucket in snapshot["data"]]
            self.old = ([dict(bucket) for bucket in snapshot["old"]]
                        if snapshot["old"] is not None else None)
            self._locks = [threading.Lock() for _ in range(self.segments)]
            return {"size": self._size(), "buckets": self.buckets}

    def stats(self) -> dict:
        return {"buckets": self.buckets, "segments": self.segments, "size": self._size(),
                "migrated": self.migrated, "resizes": self.resizes, "reads": self.reads}
