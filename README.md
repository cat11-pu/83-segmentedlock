# segmentedlock

纯 Python 标准库的分段锁哈希表：分段锁、倍增扩容、渐进式迁移（新旧双表路由）、快照与恢复。

## 用法

    from segmentedlock import Table

    table = Table(buckets=4, segments=2)
    table.put("a", "1")            # 写操作只在新表落位
    table.get("a")                 # {"value": "1"}；迁移期间先查新表再查旧表
    table.segment_of("a")          # 键的段号（同一个键必得同一个段号）

    table.resize()                 # 桶数翻倍，旧桶保留，迁移游标归零
    table.step_migrate(1)          # 每轮最多迁移 1 个旧桶，返回累计已迁移键数

    blob = table.persist()         # 快照落盘（含新旧两表、桶数、迁移游标）
    table.restore(blob)            # 重启恢复，未完成的迁移可接着做

对外门面见 `kvapi.py`（`KV` 包装 `Table`，老接口 `put`/`get` 不变）。

## 测试

    python3 -m unittest discover -s tests -v

## 场景自检

    python3 check_sample.py
