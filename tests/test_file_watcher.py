import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from whiscode.file_watcher import AudioFileHandler, FileWatcher


class TestAudioFileHandler:
    def test_ignores_directories(self):
        pending = []
        lock = MagicMock()
        handler = AudioFileHandler(pending, lock)

        event = MagicMock()
        event.is_directory = True
        event.src_path = "/some/dir"

        handler.on_created(event)
        assert pending == []

    def test_adds_ogg_files(self):
        pending = []
        lock = MagicMock()
        lock.__enter__ = MagicMock(return_value=None)
        lock.__exit__ = MagicMock(return_value=None)
        handler = AudioFileHandler(pending, lock)

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.ogg"

        handler.on_created(event)
        assert pending == ["/path/to/file.ogg"]

    def test_adds_wav_files(self):
        pending = []
        lock = MagicMock()
        lock.__enter__ = MagicMock(return_value=None)
        lock.__exit__ = MagicMock(return_value=None)
        handler = AudioFileHandler(pending, lock)

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.wav"

        handler.on_created(event)
        assert pending == ["/path/to/file.wav"]

    def test_ignores_non_audio_files(self):
        pending = []
        lock = MagicMock()
        handler = AudioFileHandler(pending, lock)

        event = MagicMock()
        event.is_directory = False
        event.src_path = "/path/to/file.txt"

        handler.on_created(event)
        assert pending == []


class TestFileWatcher:
    def test_scan_existing_adds_files_in_mtime_order(self, tmp_path):
        watcher = FileWatcher(tmp_path)

        # Create files with different mtimes
        file1 = tmp_path / "first.ogg"
        file2 = tmp_path / "second.wav"
        file3 = tmp_path / "third.mp3"

        file1.write_text("dummy")
        time.sleep(0.01)
        file2.write_text("dummy")
        time.sleep(0.01)
        file3.write_text("dummy")

        watcher.scan_existing()

        assert watcher.get_next_file() == str(file1)
        assert watcher.get_next_file() == str(file2)
        assert watcher.get_next_file() == str(file3)
        assert watcher.get_next_file() is None

    def test_get_next_file_returns_none_when_empty(self, tmp_path):
        watcher = FileWatcher(tmp_path)
        assert watcher.get_next_file() is None
