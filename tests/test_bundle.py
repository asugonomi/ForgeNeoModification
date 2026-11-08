import csv
from contextlib import closing
import gzip
import io
import json
from pathlib import Path
import runpy
import sqlite3
import tempfile
import unittest

from fnm.engine import Package, digest

ROOT = Path(__file__).resolve().parents[1]


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.package = Package(ROOT)
        self.files = self.package.components['tagcomplete']['files']

    def content(self, suffix):
        operation = next(op for op in self.files if op['path'].endswith(suffix))
        return self.package.transform(operation, None)

    def test_dictionaries_match_manifest_and_csv_shape(self):
        metadata = json.loads(self.content('DICTIONARIES.json'))
        for info in metadata['files']:
            data = self.content(info['file'])
            self.assertEqual(digest(data), info['sha256'])
            rows = list(csv.reader(io.StringIO(data.decode('utf-8-sig'))))
            self.assertEqual(len(rows), info['rows'])
            self.assertTrue(all(len(row) == info['columns'] for row in rows))

    def builder(self):
        operation = next(op for op in self.files if op['path'].endswith('build_related_index.py'))
        return runpy.run_path(str(ROOT / operation['payload']))['build']

    def test_related_index_supports_gzip_and_retains_existing_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tags = root / 'tags.csv'
            tags.write_text('tag,category,count,alias\na,0,100,alpha\nb,0,80,beta\n')
            pairs = root / 'pairs.csv.gz'
            pairs.write_bytes(gzip.compress(b'tag_a,tag_b,count\na,b,40.0\n'))
            target = root / 'related.sqlite3'
            self.builder()(tags, pairs, target)
            with closing(sqlite3.connect(target)) as database:
                self.assertEqual(database.execute('select n from pairs where a=?', ('a',)).fetchone()[0], 40)
                self.assertEqual(database.execute('pragma integrity_check').fetchone()[0], 'ok')
            original = target.read_bytes()
            with self.assertRaises(FileExistsError):
                self.builder()(tags, pairs, target)
            self.assertEqual(target.read_bytes(), original)

    def test_invalid_index_input_leaves_no_partial_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tags = root / 'tags.csv'
            tags.write_text('tag,category,count,alias\na,0,invalid,alpha\n')
            pairs = root / 'pairs.csv'
            pairs.write_text('tag_a,tag_b,count\n')
            target = root / 'related.sqlite3'
            with self.assertRaises(ValueError):
                self.builder()(tags, pairs, target)
            self.assertFalse(target.exists())
            self.assertEqual(list(root.glob('.related-*')), [])


if __name__ == '__main__':
    unittest.main()
