"""
Append-Only Log Compactor for Zenith KV Engine.
Jerry A. Nabasu (@JayNabasu)
"""

import os
from pathlib import Path
from src.wal.wal import WriteAheadLog, WALEntry
from src.storage.memory_store import MemoryStore

class WALCompactor:
    @staticmethod
    def compact(store: MemoryStore, current_wal: WriteAheadLog) -> WriteAheadLog:
        """Creates a compacted snapshot of all active keys and atomically replaces current WAL."""
        compact_path = current_wal.filepath.with_suffix(".wal.tmp")
        temp_wal = WriteAheadLog(str(compact_path), auto_fsync=True)

        for key in store.keys("*"):
            val_type = store._types.get(key)
            if val_type == 'string':
                val = store.get(key)
                ttl = store.ttl(key)
                if ttl > 0:
                    temp_wal.append(WALEntry("SET", [key, val, ttl]))
                else:
                    temp_wal.append(WALEntry("SET", [key, val]))
            elif val_type == 'hash':
                h = store.hgetall(key)
                for f, v in h.items():
                    temp_wal.append(WALEntry("HSET", [key, f, v]))
            elif val_type == 'list':
                items = store.lrange(key, 0, -1)
                for item in items:
                    temp_wal.append(WALEntry("RPUSH", [key, item]))
            elif val_type == 'zset':
                pairs = store.zrange(key, 0, -1)
                for member, score in pairs:
                    temp_wal.append(WALEntry("ZADD", [key, score, member]))

        current_wal.close()
        temp_wal.close()

        # Atomic file rename
        target_path = current_wal.filepath
        if target_path.exists():
            target_path.unlink()
        compact_path.rename(target_path)

        return WriteAheadLog(str(target_path), auto_fsync=True)
