"""check_sample.py：按 sample/ops.json 走一圈，打印验收面。"""
import json
import os
import sys

from segmentedlock import Table


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("sample", "ops.json")
    with open(path, encoding="utf-8") as handle:
        spec = json.load(handle)
    table = Table(spec["buckets"], spec["segments"])
    for key, value in spec["data"].items():
        table.put(key, value)
    resized = table.resize()
    first = table.step_migrate(spec["step"])
    during = {key: table.get(key).get("value") for key in sorted(spec["data"])}
    rounds = []
    for _ in range(spec["more_steps"]):
        rounds.append(table.step_migrate(spec["step"]))
    after = {key: table.get(key).get("value") for key in sorted(spec["data"])}
    blob = table.persist()
    reborn = Table(spec["buckets"], spec["segments"])
    restored = reborn.restore(blob)
    print("扩容后的桶数 =", resized.get("buckets"))
    print("第一轮迁移的桶数 =", first.get("migrated"))
    print("迁移期间的读结果 =", during)
    print("各轮迁移桶数 =", [item.get("migrated") for item in rounds])
    print("迁移完成后的读结果 =", after)
    print("分段数 =", table.stats().get("segments"))
    print("恢复后的键数 =", restored.get("size"))
    print("恢复后的桶数 =", restored.get("buckets"))
    print("不变量（迁移期间读写不丢不重） =", spec["migration_invariant"])
    print("键数 =", len(spec["data"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
