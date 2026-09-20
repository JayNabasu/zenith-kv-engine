"""
Unit tests for SkipList, PrefixTrie, and MemoryStore.
"""

import time
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.storage.skiplist import SkipList
from src.storage.trie import PrefixTrie
from src.storage.memory_store import MemoryStore

def test_skiplist_sorting_and_range():
    sl = SkipList()
    sl.insert(100.0, "alice")
    sl.insert(50.0, "bob")
    sl.insert(150.0, "charlie")
    sl.insert(75.0, "david")

    assert sl.size == 4
    items = sl.range_all()
    members = [m for m, s in items]
    assert members == ["bob", "david", "alice", "charlie"]

    by_score = sl.range_by_score(60.0, 120.0)
    assert [m for m, s in by_score] == ["david", "alice"]

def test_prefix_trie_search():
    trie = PrefixTrie()
    trie.insert("user:101")
    trie.insert("user:102")
    trie.insert("user:profile:101")
    trie.insert("order:999")

    results = trie.find_by_prefix("user:")
    assert len(results) == 3
    assert "user:101" in results
    assert "order:999" not in results

def test_memory_store_strings_and_ttl():
    store = MemoryStore()
    store.set("greeting", "hello world", ex_seconds=10)
    assert store.get("greeting") == "hello world"
    assert store.ttl("greeting") > 0

    # Expired key test
    store.set("temp", "bye", ex_seconds=0)
    time.sleep(0.01)
    assert store.get("temp") is None

def test_memory_store_hashes_and_lists():
    store = MemoryStore()
    store.hset("user:1", "name", "Jerry")
    store.hset("user:1", "role", "Architect")
    assert store.hget("user:1", "name") == "Jerry"
    assert store.hgetall("user:1") == {"name": "Jerry", "role": "Architect"}

    store.rpush("queue", "taskA", "taskB", "taskC")
    assert store.lrange("queue", 0, -1) == ["taskA", "taskB", "taskC"]

def test_memory_store_zset():
    store = MemoryStore()
    store.zadd("leaderboard", 950.0, "player1")
    store.zadd("leaderboard", 1200.0, "player2")
    store.zadd("leaderboard", 800.0, "player3")
    res = store.zrange("leaderboard")
    assert [m for m, s in res] == ["player3", "player1", "player2"]
