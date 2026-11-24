import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import project


@unittest.skipUnless(os.name == "nt", "Windows file-sharing behavior")
class AtomicWindowsWriteTests(unittest.TestCase):
    def test_transient_reader_lock_retries_without_truncating_previous_data(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/"evidence.json"
            path.write_text("old",encoding="utf-8")
            replace = os.replace
            calls = []
            def busy_once(source,target):
                calls.append((source,target))
                self.assertEqual(path.read_text(encoding="utf-8"),"old")
                if len(calls)==1:
                    error = PermissionError("fixture reader lock")
                    error.winerror=32
                    raise error
                replace(source,target)
            with patch.object(project.os,"replace",side_effect=busy_once), patch.object(project.time,"sleep"):
                project.write_text(path,"new")
            self.assertEqual(path.read_text(encoding="utf-8"),"new")
            self.assertEqual(len(calls),2)

    def test_persistent_denial_keeps_the_previous_artifact(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary)/"evidence.json"
            path.write_text("old",encoding="utf-8")
            error = PermissionError("fixture permission denial")
            error.winerror=5
            with patch.object(project.os,"replace",side_effect=error), patch.object(project.time,"sleep"):
                with self.assertRaises(PermissionError):
                    project.write_text(path,"new")
            self.assertEqual(path.read_text(encoding="utf-8"),"old")
            self.assertEqual(list(Path(temporary).glob("*.tmp")),[])
