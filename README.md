# ⚡ Zenith: Distributed In-Memory KV Engine & Raft Consensus

> High-performance in-memory key-value database built from scratch with Write-Ahead Logging (WAL) durability, SkipList sorted sets, and the Raft distributed consensus protocol.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![Raft](https://img.shields.io/badge/Consensus-Raft%20Protocol-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-10%20Passing-brightgreen.svg)]()
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 📌 Architectural Overview

**Zenith** is a distributed, ACID-compliant in-memory storage engine engineered from first principles without relying on third-party database systems. It explores the foundational primitives of high-throughput storage engines: memory-efficient data structures, append-only crash resilience, wire-level protocol serialization, and distributed quorum replication.

```
                  ┌─────────────────────────────────────────────────┐
                  │            Client / Web Dashboard               │
                  └────────────────────────┬────────────────────────┘
                                           │ HTTP REST / RESP Protocol
                                           ▼
                  ┌─────────────────────────────────────────────────┐
                  │             Active Raft Leader Node             │
                  ├────────────────────────┬────────────────────────┤
                  │  MemoryStore (RAM)     │   Write-Ahead Log(WAL) │
                  │  • SkipList (ZSet)     │   • CRC32 Framed Disk  │
                  │  • Prefix Trie (Keys)  │   • Fsync Durability   │
                  │  • Dict + TTL Evict    │   • AOF Compactor      │
                  └────────────┬───────────────────────┬────────────┘
                               │ Heartbeat & Log Repl  │
                               ▼                       ▼
                  ┌────────────────────────┐  ┌────────────────────────┐
                  │ Raft Follower (Node 2) │  │ Raft Follower (Node 3) │
                  │ State: FOLLOWER        │  │ State: FOLLOWER        │
                  └────────────────────────┘  └────────────────────────┘
```

---

## 🚀 Key Technical Highlights

### 1. Advanced Data Structures
- **Probabilistic SkipList**: Backs sorted sets (`ZADD`, `ZRANGE`, `ZRANGEBYSCORE`) with $O(\log n)$ insertion and range queries, bypassing the rebalancing overhead of red-black trees.
- **Prefix Trie**: Accelerates wildcard prefix searches (`KEYS user:*`) with linear $O(k)$ prefix traversal.
- **Time-to-Live (TTL)**: Supports millisecond-precision active and passive key expiration (`SETEX`, `TTL`).

### 2. Durability & Crash Recovery (WAL Engine)
- **Framed Append-Only Log**: Each entry is serialized with binary headers:
  `[CRC32: 4 bytes] [Length: 4 bytes] [Payload: JSON / UTF-8]`
- **Atomic Log Compaction**: A background compactor snapshots current memory states into a clean log, safely pruning redundant historical mutations (`WALCompactor`).

### 3. Distributed Raft Consensus Protocol
- **Leader Election**: Dynamic transition between `FOLLOWER`, `CANDIDATE`, and `LEADER` with randomized election timers (200ms–400ms).
- **Quorum Log Replication**: Writes are only committed once acknowledged by a majority ($\lfloor N/2 \rfloor + 1$) of nodes.
- **Split-Brain Partition Defense**: Simulates network partitions (isolating minority nodes). Minority leaders automatically fail write proposals without quorum, while majority partitions cleanly elect new leaders.

---

## 🛠️ Project Layout

```
zenith-kv-engine/
├── api/
│   └── server.py           # FastAPI REST endpoints & static web mount
├── src/
│   ├── protocol/
│   │   └── resp.py         # Redis Serialization Protocol (RESP2) serializer
│   ├── storage/
│   │   ├── memory_store.py # Key-value engine with TTL eviction
│   │   ├── skiplist.py     # O(log n) probabilistic SkipList
│   │   └── trie.py         # Prefix trie for wildcard keys
│   ├── wal/
│   │   ├── wal.py          # Write-Ahead Log with CRC32 checksums
│   │   └── compactor.py    # AOF log snapshot compactor
│   └── raft/
│       ├── node.py         # Raft node state machine (Follower/Candidate/Leader)
│       └── cluster.py      # Multi-node cluster with network partition simulation
├── web/
│   ├── index.html          # Interactive Raft cluster topology & REPL
│   ├── style.css           # Glassmorphism dark-mode styling
│   └── app.js              # Real-time polling client & partition toggles
├── tests/
│   ├── test_storage.py     # SkipList, Trie, and TTL unit tests
│   ├── test_wal.py         # WAL durability & compaction tests
│   └── test_raft.py        # Consensus election & split-brain tests
├── requirements.txt
└── README.md
```

---

## ⚡ Quickstart

### 1. Clone Repository & Install Dependencies
```bash
git clone https://github.com/JayNabasu/zenith-kv-engine.git
cd zenith-kv-engine
pip install -r requirements.txt
```

### 2. Run Test Suite
```bash
python -m pytest tests/ -v
```

### 3. Launch Web Dashboard & Cluster API
```bash
python api/server.py
# Open browser at http://127.0.0.1:8007
```

---

## 👤 Author
**Jerry A. Nabasu**  
- GitHub: [@JayNabasu](https://github.com/JayNabasu)  
- Email: [jerrynabasu@gmail.com](mailto:jerrynabasu@gmail.com)
