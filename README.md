# segmentedlock

纯 Python 标准库的 segmentedlock：分段哈希表内核，支持渐进式扩容与快照恢复。

## 用法

    from segmentedlock import Table

    table = Table(buckets=4, segments=2)
    table.put("a", "1")            # 写操作永远落在当前代（新表）
    table.get("a")                 # -> {"value": "1"}；迁移期间先查新表再查旧表
    table.segment_of("a")          # 键的哈希段号（同键恒定同段）

    table.resize()                 # 扩容：桶数翻倍，O(1) 指针切换，不当场搬数据
    table.step_migrate(1)          # 渐进迁移：每轮最多搬 count 个旧桶，
                                   # 返回 {"migrated": 累计键数, "remaining": ..., "done": ...}

    blob = table.persist()         # 快照：新旧两表、桶数、迁移游标
    Table().restore(blob)          # 重启恢复，未完成的迁移可接着做

`kvapi.KV` 是对外门面，老接口 `put` / `get` 保持不变。

## 测试

    python3 -m unittest discover -s tests -v

## 场景自检

    python3 check_sample.py
