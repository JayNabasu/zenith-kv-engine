"""
In-Memory Key-Value Store with TTL Eviction, Data Types, and Prefix Indexing.
Jerry A. Nabasu (@JayNabasu)
"""

import time
from typing import Dict, Any, Optional, List, Tuple
from src.storage.skiplist import SkipList
from src.storage.trie import PrefixTrie

class MemoryStore:
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._types: Dict[str, str] = {} # 'string', 'hash', 'list', 'zset'
        self._expiry: Dict[str, float] = {} # key -> timestamp in epoch seconds
        self._trie = PrefixTrie()

    def _is_expired(self, key: str) -> bool:
        if key in self._expiry:
            if time.time() > self._expiry[key]:
                self.delete(key)
                return True
        return False

    def set(self, key: str, value: str, ex_seconds: Optional[int] = None) -> str:
        self._data[key] = str(value)
        self._types[key] = 'string'
        self._trie.insert(key)

        if ex_seconds is not None:
            self._expiry[key] = time.time() + ex_seconds
        elif key in self._expiry:
            del self._expiry[key]

        return "OK"

    def get(self, key: str) -> Optional[str]:
        if self._is_expired(key):
            return None
        if key not in self._data:
            return None
        if self._types.get(key) != 'string':
            raise ValueError("WRONGTYPE Operation against a key holding the wrong kind of value")
        return self._data[key]

    def delete(self, key: str) -> int:
        deleted = 0
        if key in self._data:
            del self._data[key]
            deleted = 1
        if key in self._types:
            del self._types[key]
        if key in self._expiry:
            del self._expiry[key]
        self._trie.delete(key)
        return deleted

    def exists(self, key: str) -> int:
        if self._is_expired(key):
            return 0
        return 1 if key in self._data else 0

    def ttl(self, key: str) -> int:
        if self._is_expired(key) or key not in self._data:
            return -2 # Key does not exist
        if key not in self._expiry:
            return -1 # Key exists but has no associated expire
        remaining = int(self._expiry[key] - time.time())
        return max(0, remaining)

    # Hash Operations
    def hset(self, key: str, field: str, value: str) -> int:
        if self._is_expired(key):
            pass
        if key not in self._data:
            self._data[key] = {}
            self._types[key] = 'hash'
            self._trie.insert(key)
        elif self._types.get(key) != 'hash':
            raise ValueError("WRONGTYPE Operation against a key holding the wrong kind of value")

        is_new = 1 if field not in self._data[key] else 0
        self._data[key][field] = str(value)
        return is_new

    def hget(self, key: str, field: str) -> Optional[str]:
        if self._is_expired(key):
            return None
        if key not in self._data or self._types.get(key) != 'hash':
            return None
        return self._data[key].get(field)

    def hgetall(self, key: str) -> Dict[str, str]:
        if self._is_expired(key):
            return {}
        if key not in self._data or self._types.get(key) != 'hash':
            return {}
        return dict(self._data[key])

    # List Operations
    def lpush(self, key: str, *values: str) -> int:
        if self._is_expired(key):
            pass
        if key not in self._data:
            self._data[key] = []
            self._types[key] = 'list'
            self._trie.insert(key)
        elif self._types.get(key) != 'list':
            raise ValueError("WRONGTYPE Operation against a key holding the wrong kind of value")

        for val in values:
            self._data[key].insert(0, str(val))
        return len(self._data[key])

    def rpush(self, key: str, *values: str) -> int:
        if self._is_expired(key):
            pass
        if key not in self._data:
            self._data[key] = []
            self._types[key] = 'list'
            self._trie.insert(key)
        elif self._types.get(key) != 'list':
            raise ValueError("WRONGTYPE Operation against a key holding the wrong kind of value")

        for val in values:
            self._data[key].append(str(val))
        return len(self._data[key])

    def lrange(self, key: str, start: int, stop: int) -> List[str]:
        if self._is_expired(key) or key not in self._data or self._types.get(key) != 'list':
            return []
        lst = self._data[key]
        n = len(lst)
        # Normalize negative indices
        if start < 0: start = max(0, n + start)
        if stop < 0: stop = max(0, n + stop)
        return lst[start:stop + 1]

    # Sorted Set Operations (SkipList backed)
    def zadd(self, key: str, score: float, member: str) -> int:
        if self._is_expired(key):
            pass
        if key not in self._data:
            self._data[key] = SkipList()
            self._types[key] = 'zset'
            self._trie.insert(key)
        elif self._types.get(key) != 'zset':
            raise ValueError("WRONGTYPE Operation against a key holding the wrong kind of value")

        sl: SkipList = self._data[key]
        added = sl.insert(float(score), str(member))
        return 1 if added else 0

    def zrange(self, key: str, start: int = 0, stop: int = -1) -> List[Tuple[str, float]]:
        if self._is_expired(key) or key not in self._data or self._types.get(key) != 'zset':
            return []
        sl: SkipList = self._data[key]
        return sl.range_all(start, stop)

    def keys(self, pattern: str = "*") -> List[str]:
        """Supports exact, prefix wildcard (e.g. 'user:*'), and full match '*'."""
        # Purge any expired keys before reporting
        expired_keys = [k for k in self._expiry if time.time() > self._expiry[k]]
        for k in expired_keys:
            self.delete(k)

        if pattern == "*":
            return sorted(list(self._data.keys()))
        elif pattern.endswith("*"):
            prefix = pattern[:-1]
            return sorted(self._trie.find_by_prefix(prefix))
        else:
            return [pattern] if pattern in self._data else []

    def dbsize(self) -> int:
        return len(self._data)
