"""
Raft Consensus Node State Machine.
Jerry A. Nabasu (@JayNabasu)
"""

import time
import random
from typing import Dict, List, Any, Optional
from src.storage.memory_store import MemoryStore
from src.wal.wal import WriteAheadLog, WALEntry

class NodeState:
    FOLLOWER = "FOLLOWER"
    CANDIDATE = "CANDIDATE"
    LEADER = "LEADER"

class RaftNode:
    def __init__(self, node_id: str, peers: List[str], wal_path: Optional[str] = None):
        self.node_id = node_id
        self.peers = peers # List of peer node_ids
        self.state = NodeState.FOLLOWER
        
        # Persistent state
        self.current_term = 0
        self.voted_for: Optional[str] = None
        self.log: List[Dict[str, Any]] = [] # [{'term': int, 'cmd': str, 'args': list}]
        
        # Volatile state
        self.commit_index = -1
        self.last_applied = -1
        self.leader_id: Optional[str] = None
        
        # Timers
        self.last_heartbeat_time = time.time()
        self.election_timeout = random.uniform(0.2, 0.4) # 200ms - 400ms
        self.votes_received = set()

        # Local storage & WAL
        self.store = MemoryStore()
        wal_file = wal_path or f"node_{node_id}.wal"
        self.wal = WriteAheadLog(wal_file, auto_fsync=False)

    def is_election_timeout_expired(self) -> bool:
        return (time.time() - self.last_heartbeat_time) > self.election_timeout

    def reset_election_timeout(self):
        self.last_heartbeat_time = time.time()
        self.election_timeout = random.uniform(0.2, 0.4)

    def start_election(self):
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self.votes_received = {self.node_id}
        self.reset_election_timeout()

    def handle_request_vote(self, term: int, candidate_id: str, last_log_index: int, last_log_term: int) -> Dict[str, Any]:
        if term > self.current_term:
            self.current_term = term
            self.state = NodeState.FOLLOWER
            self.voted_for = None

        vote_granted = False
        if term == self.current_term and (self.voted_for is None or self.voted_for == candidate_id):
            # Check log up-to-date
            my_last_term = self.log[-1]["term"] if self.log else 0
            my_last_index = len(self.log) - 1

            if last_log_term > my_last_term or (last_log_term == my_last_term and last_log_index >= my_last_index):
                vote_granted = True
                self.voted_for = candidate_id
                self.reset_election_timeout()

        return {
            "term": self.current_term,
            "vote_granted": vote_granted,
            "responder_id": self.node_id
        }

    def handle_append_entries(self, term: int, leader_id: str, prev_log_index: int, prev_log_term: int, entries: List[Dict[str, Any]], leader_commit: int) -> Dict[str, Any]:
        if term > self.current_term:
            self.current_term = term
            self.state = NodeState.FOLLOWER
            self.voted_for = None

        if term < self.current_term:
            return {"term": self.current_term, "success": False, "responder_id": self.node_id}

        self.state = NodeState.FOLLOWER
        self.leader_id = leader_id
        self.reset_election_timeout()

        # Check prev_log_index consistency
        if prev_log_index >= 0:
            if prev_log_index >= len(self.log):
                return {"term": self.current_term, "success": False, "responder_id": self.node_id}
            if self.log[prev_log_index]["term"] != prev_log_term:
                return {"term": self.current_term, "success": False, "responder_id": self.node_id}

        # Insert new entries
        insert_idx = prev_log_index + 1
        for entry in entries:
            if insert_idx < len(self.log):
                if self.log[insert_idx]["term"] != entry["term"]:
                    self.log = self.log[:insert_idx]
                    self.log.append(entry)
            else:
                self.log.append(entry)
            insert_idx += 1

        # Advance commit_index
        if leader_commit > self.commit_index:
            self.commit_index = min(leader_commit, len(self.log) - 1)
            self._apply_committed_entries()

        return {"term": self.current_term, "success": True, "responder_id": self.node_id}

    def _apply_committed_entries(self):
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log[self.last_applied]
            cmd = entry["cmd"].upper()
            args = entry["args"]

            # Log to WAL
            self.wal.append(WALEntry(cmd, args))

            # Apply state to memory store
            if cmd == "SET":
                key, val = args[0], args[1]
                ex = args[2] if len(args) > 2 else None
                self.store.set(key, val, ex)
            elif cmd == "DEL":
                self.store.delete(args[0])
            elif cmd == "HSET":
                self.store.hset(args[0], args[1], args[2])
            elif cmd == "LPUSH":
                self.store.lpush(args[0], *args[1:])
            elif cmd == "RPUSH":
                self.store.rpush(args[0], *args[1:])
            elif cmd == "ZADD":
                self.store.zadd(args[0], float(args[1]), args[2])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "state": self.state,
            "term": self.current_term,
            "leader_id": self.leader_id,
            "log_length": len(self.log),
            "commit_index": self.commit_index,
            "last_applied": self.last_applied,
            "keys_count": self.store.dbsize()
        }
