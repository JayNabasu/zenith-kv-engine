"""
Unit tests for Write-Ahead Log (WAL) and AOF Compaction.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.wal.wal import WriteAheadLog, WALEntry
from src.wal.compactor import WALCompactor
from src.storage.memory_store import MemoryStore

def test_wal_append_and_replay(tmp_path):
    wal_file = tmp_path / "test.wal"
    wal = WriteAheadLog(str(wal_file), auto_fsync=True)

    wal.append(WALEntry("SET", ["foo", "bar"]))
    wal.append(WALEntry("SET", ["baz", "qux"]))
    wal.append(WALEntry("HSET", ["user:1", "name", "Jerry"]))
    assert wal.entry_count == 3

    # Replay
    entries = wal.replay()
    assert len(entries) == 3
    assert entries[0].command == "SET"
    assert entries[0].args == ["foo", "bar"]
    assert entries[2].command == "HSET"
    wal.close()

def test_wal_compaction(tmp_path):
    wal_file = tmp_path / "active.wal"
    wal = WriteAheadLog(str(wal_file), auto_fsync=True)
    store = MemoryStore()

    # Apply multiple updates to same key
    store.set("counter", "1")
    wal.append(WALEntry("SET", ["counter", "1"]))
    store.set("counter", "2")
    wal.append(WALEntry("SET", ["counter", "2"]))
    store.set("counter", "3")
    wal.append(WALEntry("SET", ["counter", "3"]))
    assert wal.entry_count == 3

    # Compact
    new_wal = WALCompactor.compact(store, wal)
    # The compacted log should have only 1 entry for "counter" (the latest snapshot)
    entries = new_wal.replay()
    assert len(entries) == 1
    assert entries[0].args == ["counter", "3"]
    new_wal.close()
