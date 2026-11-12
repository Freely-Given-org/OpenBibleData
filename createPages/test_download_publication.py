#!/usr/bin/env -S uv run
# SPDX-License-Identifier: CC0-1.0
"""Downloads survive real directory cleanup and promotion operations.

CHANGELOG:
    2026-11-06 Cover download preservation, promotion and staging isolation.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from downloadPublication import cleanVersionFolder, moveGeneratedEntry


class DownloadPublicationTests(unittest.TestCase):
    def test_cleanup_and_promotion_preserve_pdf_bytes_inode_and_timestamp(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            live = root / 'live/OET'
            (live / 'Downloads').mkdir(parents=True)
            pdf = live / 'Downloads/book.pdf'
            pdf.write_bytes(b'published PDF')
            before = pdf.stat()
            (live / 'old.htm').write_text('stale page')
            (live / 'byC').mkdir()
            (live / 'byC/old.htm').write_text('stale chapter')
            cleanVersionFolder(live, keepDownloads=True)
            self.assertEqual(list(live.iterdir()), [live / 'Downloads'])
            staged = root / 'staging/OET'
            (staged / 'byDoc').mkdir(parents=True)
            (staged / 'byDoc/RUT.htm').write_text('new page')
            moveGeneratedEntry(staged, live.parent)
            self.assertFalse(staged.exists())
            self.assertEqual((live / 'byDoc/RUT.htm').read_text(), 'new page')
            self.assertEqual(pdf.read_bytes(), b'published PDF')
            self.assertEqual((pdf.stat().st_ino, pdf.stat().st_mtime_ns), (before.st_ino, before.st_mtime_ns))

    def test_staging_cleanup_does_not_retain_old_downloads(self):
        with TemporaryDirectory() as temp:
            folder = Path(temp) / 'OET'
            (folder / 'Downloads').mkdir(parents=True)
            cleanVersionFolder(folder)
            self.assertFalse(folder.exists())

    def test_accidental_staged_downloads_cannot_replace_published_files(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'live/OET/Downloads').mkdir(parents=True)
            (root / 'staging/OET/Downloads').mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, 'must not overwrite'):
                moveGeneratedEntry(root / 'staging/OET', root / 'live')
            self.assertTrue((root / 'live/OET/Downloads').is_dir())


if __name__ == '__main__':
    unittest.main()
