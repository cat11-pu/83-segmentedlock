import unittest

from kvapi import KV
from segmentedlock import Table


class TestTable(unittest.TestCase):
    def test_put_counts(self):
        self.assertEqual(Table().put("a", "1")["size"], 1)

    def test_get_value(self):
        table = Table()
        table.put("a", "1")
        self.assertEqual(table.get("a")["value"], "1")

    def test_get_missing(self):
        self.assertIsNone(Table().get("nope")["value"])

    def test_stats_shape(self):
        self.assertIn("buckets", Table().stats())

    def test_kv_wraps_table(self):
        kv = KV()
        kv.put("a", "1")
        self.assertEqual(kv.table.stats()["size"], 1)


if __name__ == "__main__":
    unittest.main()
