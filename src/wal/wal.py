"""
Write-Ahead Logging (WAL) Engine with CRC32 Verification & Fsync Semantics.
Jerry A. Nabasu (@JayNabasu)
"""

import os
import json
import zlib
import time
import struct
from pathlib import Path
from typing import List, Dict, Any, Optional

# Frame layout:
# [CRC32: 4 bytes uint32] [Payload Length: 4 bytes uint32] [Payload: N bytes UTF-8 JSON]
HEADER_FORMAT = "!II"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)

class WALEntry:
    def __init__(self, command: str, args: List[Any], timestamp: Optional[float] = None):
        self.command = command.upper()
        self.args = args
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> dict:
        return {
            "cmd": self.command,
            "args": self.args,
            "ts": self.timestamp
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'WALEntry':
        return cls(d["cmd"], d["args"], d.get("ts"))

class WriteAheadLog:
    def __init__(self, filepath: str = "zenith.wal", auto_fsync: bool = True):
        self.filepath = Path(filepath).resolve()
        self.auto_fsync = auto_fsync
        self._file = open(self.filepath, "a+b")
        self.entry_count = 0
        self._count_existing_entries()

    def _count_existing_entries(self):
        try:
            self._file.seek(0)
            count = 0
            while True:
                header = self._file.read(HEADER_SIZE)
                if len(header) < HEADER_SIZE:
                    break
                crc, length = struct.unpack(HEADER_FORMAT, header)
                payload = self._file.read(length)
                if len(payload) == length and zlib.crc32(payload) == crc:
                    count += 1
                else:
                    break
            self.entry_count = count
            self._file.seek(0, os.SEEK_END)
        except Exception:
            self.entry_count = 0

    def append(self, entry: WALEntry):
        payload = json.dumps(entry.to_dict()).encode("utf-8")
        crc = zlib.crc32(payload)
        length = len(payload)
        header = struct.pack(HEADER_FORMAT, crc, length)

        self._file.write(header + payload)
        if self.auto_fsync:
            self._file.flush()
            os.fsync(self._file.fileno())
        self.entry_count += 1

    def replay(self) -> List[WALEntry]:
        """Reads and validates all WAL entries from the start of the file."""
        entries = []
        self._file.seek(0)
        while True:
            header = self._file.read(HEADER_SIZE)
            if len(header) < HEADER_SIZE:
                break
            crc, length = struct.unpack(HEADER_FORMAT, header)
            payload = self._file.read(length)
            if len(payload) != length:
                print(f"[WAL WARN] Corrupted or incomplete record at EOF.")
                break

            actual_crc = zlib.crc32(payload)
            if actual_crc != crc:
                print(f"[WAL ERROR] CRC32 mismatch! Expected {crc}, got {actual_crc}. Discarding remainder.")
                break

            entry_dict = json.loads(payload.decode("utf-8"))
            entries.append(WALEntry.from_dict(entry_dict))

        self._file.seek(0, os.SEEK_END)
        return entries

    def truncate(self):
        self._file.close()
        self._file = open(self.filepath, "w+b")
        self.entry_count = 0

    def close(self):
        if not self._file.closed:
            self._file.flush()
            self._file.close()
