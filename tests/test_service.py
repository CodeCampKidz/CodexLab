import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from app import service, store
from app.schemas import TaskStatus


class TaskServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.data_file = Path(self.temp_dir.name) / "tasks.json"
        self.tasks = [
            {"id": 1, "title": "Launch plan", "description": "Draft summary",
             "status": "open", "completed_at": None},
            {"id": 2, "title": "Archive notes", "description": "Review LAUNCH results",
             "status": "done", "completed_at": "2026-02-21T09:15:00+00:00"},
            {"id": 3, "title": "Fix redirect", "description": "",
             "status": "open", "completed_at": None},
        ]
        self.data_file.write_text(json.dumps(self.tasks), encoding="utf-8")
        patcher = patch.object(store, "DATA_FILE", self.data_file)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_no_filters_returns_all_tasks(self):
        self.assertEqual(service.list_tasks(), self.tasks)

    def test_status_filters(self):
        for status, expected in [(TaskStatus.open, [1, 3]), (TaskStatus.done, [2])]:
            with self.subTest(status=status):
                self.assertEqual([task["id"] for task in service.list_tasks(status=status)], expected)

    def test_search_matches_title_and_description_substrings_ignoring_case(self):
        self.assertEqual([task["id"] for task in service.list_tasks(q="aUnCh")], [1, 2])

    def test_search_and_status_are_combined(self):
        for status, expected in [("open", [1]), ("done", [2])]:
            with self.subTest(status=status):
                self.assertEqual(
                    [task["id"] for task in service.list_tasks(status=status, q="launch")],
                    expected,
                )

    def test_search_without_matches_returns_empty_list(self):
        self.assertEqual(service.list_tasks(q="missing"), [])

    def test_completion_persists_status_and_timestamp(self):
        completed = service.complete_task(1)
        self.assertEqual(completed["status"], "done")
        self.assertIsNotNone(datetime.fromisoformat(completed["completed_at"]).tzinfo)
        self.assertEqual(service.get_task(1), completed)
        stored = json.loads(self.data_file.read_text(encoding="utf-8"))
        self.assertEqual(stored[0], completed)
        self.assertEqual(stored[1:], self.tasks[1:])

    def test_missing_task_completion_does_not_change_storage(self):
        before = self.data_file.read_bytes()
        self.assertIsNone(service.complete_task(999))
        self.assertEqual(self.data_file.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
