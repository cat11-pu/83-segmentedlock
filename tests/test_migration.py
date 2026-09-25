import random
import unittest

from segmentedlock import Table


class TestMigration(unittest.TestCase):
    def test_segment_of_stable(self):
        table = Table(buckets=4, segments=2)
        for key in ("a", "b", "c"):
            self.assertEqual(table.segment_of(key), table.segment_of(key))
            self.assertIn(table.segment_of(key), (0, 1))

    def test_resize_keeps_data_and_doubles(self):
        table = Table(buckets=4)
        table.put("a", "1")
        result = table.resize()
        self.assertEqual(result["buckets"], 8)
        self.assertEqual(table.get("a")["value"], "1")
        self.assertEqual(table.stats()["size"], 1)

    def test_migration_invariant_interleaved(self):
        rng = random.Random(42)
        table = Table(buckets=4)
        truth = {}
        for i in range(2000):
            key = f"k{i}"
            truth[key] = str(i)
            table.put(key, str(i))
        table.resize()
        while True:
            for _ in range(rng.randrange(1, 20)):
                key = f"k{rng.randrange(2000)}"
                value = f"v{rng.randrange(10**6)}"
                truth[key] = value
                table.put(key, value)
            for _ in range(rng.randrange(1, 20)):
                key = f"k{rng.randrange(2000)}"
                self.assertEqual(table.get(key)["value"], truth[key])
            if table.step_migrate(1)["done"]:
                break
        for key, value in truth.items():
            self.assertEqual(table.get(key)["value"], value)

    def test_persist_restore_resumes_migration(self):
        table = Table(buckets=4)
        for i in range(100):
            table.put(f"k{i}", str(i))
        table.resize()
        table.step_migrate(0)  # 一个桶都还没迁
        blob = table.persist()
        reborn = Table()
        state = reborn.restore(blob)
        self.assertEqual(state["buckets"], 8)
        self.assertEqual(state["size"], 100)
        while not reborn.step_migrate(1)["done"]:
            pass
        for i in range(100):
            self.assertEqual(reborn.get(f"k{i}")["value"], str(i))

    def test_restore_without_blob_is_noop(self):
        table = Table()
        table.put("a", "1")
        self.assertEqual(table.restore()["size"], 1)


if __name__ == "__main__":
    unittest.main()
