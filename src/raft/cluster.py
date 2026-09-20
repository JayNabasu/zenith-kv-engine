"""
Raft Multi-Node Consensus Cluster Simulator with Network Partitioning.
Jerry A. Nabasu (@JayNabasu)
"""

import time
from typing import Dict, List, Set, Any, Optional
from src.raft.node import RaftNode, NodeState

class RaftCluster:
    def __init__(self, node_ids: Optional[List[str]] = None):
        if node_ids is None:
            node_ids = ["node_1", "node_2", "node_3"]
        self.node_ids = node_ids
        self.nodes: Dict[str, RaftNode] = {}
        for nid in node_ids:
            peers = [p for p in node_ids if p != nid]
            self.nodes[nid] = RaftNode(nid, peers)

        # Network partitioning: isolated groups of nodes
        # If empty, all nodes can communicate freely
        self.partitions: List[Set[str]] = []

    def can_communicate(self, from_id: str, to_id: str) -> bool:
        if not self.partitions:
            return True
        for group in self.partitions:
            if from_id in group and to_id in group:
                return True
        return False

    def isolate_node(self, node_id: str):
        """Partitions node_id from the rest of the cluster."""
        remaining = set(self.node_ids) - {node_id}
        self.partitions = [{node_id}, remaining]

    def heal_partitions(self):
        """Restores full network connectivity."""
        self.partitions = []

    def get_leader(self) -> Optional[RaftNode]:
        """Returns the active leader with the highest term."""
        leaders = [n for n in self.nodes.values() if n.state == NodeState.LEADER]
        if not leaders:
            return None
        leaders.sort(key=lambda n: n.current_term, reverse=True)
        return leaders[0]

    def tick(self):
        """Simulates one consensus tick: election checks, heartbeats, and replication."""
        # 1. Check for election timeouts
        for n in self.nodes.values():
            if n.state != NodeState.LEADER and n.is_election_timeout_expired():
                n.start_election()
                # Broadcast RequestVote to accessible peers
                for peer_id in n.peers:
                    if self.can_communicate(n.node_id, peer_id):
                        peer = self.nodes[peer_id]
                        last_term = n.log[-1]["term"] if n.log else 0
                        res = peer.handle_request_vote(n.current_term, n.node_id, len(n.log) - 1, last_term)
                        if res["vote_granted"]:
                            n.votes_received.add(peer_id)

                # Check if majority achieved
                majority = (len(self.node_ids) // 2) + 1
                if len(n.votes_received) >= majority:
                    n.state = NodeState.LEADER
                    n.leader_id = n.node_id
                    # Immediately send initial empty heartbeat
                    self._broadcast_heartbeat(n)

        # 2. Leaders send heartbeats
        for n in self.nodes.values():
            if n.state == NodeState.LEADER:
                self._broadcast_heartbeat(n)

    def _broadcast_heartbeat(self, leader: RaftNode):
        for peer_id in leader.peers:
            if self.can_communicate(leader.node_id, peer_id):
                peer = self.nodes[peer_id]
                prev_idx = len(leader.log) - 1
                prev_term = leader.log[prev_idx]["term"] if prev_idx >= 0 else 0
                peer.handle_append_entries(
                    leader.current_term,
                    leader.node_id,
                    prev_idx,
                    prev_term,
                    entries=[],
                    leader_commit=leader.commit_index
                )

    def execute_command(self, cmd: str, args: List[Any]) -> Dict[str, Any]:
        """Proposes a command to the active leader and replicates to majority."""
        self.tick()
        leader = self.get_leader()
        if not leader:
            # Trigger election step
            self.tick()
            leader = self.get_leader()
            if not leader:
                return {"success": False, "error": "No active Raft leader elected yet. Please retry."}

        # Check if leader can communicate with a majority
        accessible_peers = [p for p in leader.peers if self.can_communicate(leader.node_id, p)]
        cluster_accessible_count = len(accessible_peers) + 1
        majority = (len(self.node_ids) // 2) + 1

        if cluster_accessible_count < majority:
            return {"success": False, "error": "Split-brain partition: Leader cannot reach quorum."}

        # Append entry to leader log
        entry = {"term": leader.current_term, "cmd": cmd.upper(), "args": args}
        leader.log.append(entry)
        entry_idx = len(leader.log) - 1

        # Replicate to accessible peers
        acks = 1 # Leader itself
        for peer_id in accessible_peers:
            peer = self.nodes[peer_id]
            prev_idx = entry_idx - 1
            prev_term = leader.log[prev_idx]["term"] if prev_idx >= 0 else 0
            res = peer.handle_append_entries(
                leader.current_term,
                leader.node_id,
                prev_idx,
                prev_term,
                entries=[entry],
                leader_commit=leader.commit_index
            )
            if res["success"]:
                acks += 1

        if acks >= majority:
            # Commit entry
            leader.commit_index = entry_idx
            leader._apply_committed_entries()

            # Inform peers of new commit index
            self._broadcast_heartbeat(leader)

            # Get result from leader store
            cmd_upper = cmd.upper()
            val = None
            if cmd_upper == "GET":
                val = leader.store.get(args[0])
            elif cmd_upper == "KEYS":
                val = leader.store.keys(args[0] if args else "*")
            elif cmd_upper == "HGETALL":
                val = leader.store.hgetall(args[0])
            elif cmd_upper == "LRANGE":
                val = leader.store.lrange(args[0], int(args[1]), int(args[2]))
            elif cmd_upper == "ZRANGE":
                val = leader.store.zrange(args[0])
            else:
                val = "OK"

            return {
                "success": True,
                "leader_id": leader.node_id,
                "term": leader.current_term,
                "commit_index": leader.commit_index,
                "acks": acks,
                "result": val
            }
        else:
            return {"success": False, "error": "Quorum write replication failed."}

    def status(self) -> Dict[str, Any]:
        return {
            "node_count": len(self.node_ids),
            "partitions": [list(p) for p in self.partitions],
            "nodes": [n.to_dict() for n in self.nodes.values()]
        }
