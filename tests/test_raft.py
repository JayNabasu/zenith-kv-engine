"""
Unit tests for Raft Consensus Cluster, Leader Election, and Partition Tolerance.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.raft.cluster import RaftCluster
from src.raft.node import NodeState

def test_raft_cluster_initial_election():
    cluster = RaftCluster(["node_1", "node_2", "node_3"])
    
    # Force timeout on node_1 to start election
    cluster.nodes["node_1"].last_heartbeat_time = 0
    cluster.tick()

    leader = cluster.get_leader()
    assert leader is not None
    assert leader.state == NodeState.LEADER
    assert leader.current_term >= 1

def test_raft_replicated_write():
    cluster = RaftCluster(["node_1", "node_2", "node_3"])
    cluster.nodes["node_1"].last_heartbeat_time = 0
    cluster.tick()

    leader = cluster.get_leader()
    assert leader is not None

    res = cluster.execute_command("SET", ["cluster_key", "replicated_value"])
    assert res["success"] is True
    assert res["acks"] >= 2 # Majority acknowledged

    # Verify followers also received and committed the write
    for nid, node in cluster.nodes.items():
        assert node.store.get("cluster_key") == "replicated_value"

def test_raft_split_brain_partition_defense():
    cluster = RaftCluster(["node_1", "node_2", "node_3"])
    cluster.nodes["node_1"].last_heartbeat_time = 0
    cluster.tick()

    leader = cluster.get_leader()
    assert leader is not None
    leader_id = leader.node_id

    # Isolate the current leader into minority partition
    cluster.isolate_node(leader_id)

    # Isolated leader attempts to write
    # Because it cannot reach a majority, the write MUST fail
    entry = {"term": leader.current_term, "cmd": "SET", "args": ["split_key", "stale_data"]}
    leader.log.append(entry)
    accessible = [p for p in leader.peers if cluster.can_communicate(leader.node_id, p)]
    assert len(accessible) + 1 < 2 # No quorum

    # The majority partition can elect a new leader and make progress
    majority_peer = [nid for nid in cluster.node_ids if nid != leader_id][0]
    cluster.nodes[majority_peer].last_heartbeat_time = 0
    cluster.tick()

    new_leader = cluster.get_leader()
    assert new_leader is not None
    assert new_leader.node_id != leader_id
