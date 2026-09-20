"""
FastAPI REST API & Static Mount for Zenith Distributed KV Engine.
Jerry A. Nabasu (@JayNabasu)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Any, Optional
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.raft.cluster import RaftCluster
from src.wal.compactor import WALCompactor

app = FastAPI(
    title="Zenith In-Memory KV Engine & Raft Consensus API",
    description="Distributed In-Memory Key-Value Database with WAL Durability & Raft Consensus Protocol",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

cluster = RaftCluster(["node_1", "node_2", "node_3"])
# Run initial tick to trigger election
cluster.tick()

web_dir = Path(__file__).resolve().parent.parent / "web"
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

@app.get("/")
def get_index():
    index_file = web_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Zenith KV Engine is running. See /docs for Swagger UI."}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "zenith-kv-engine", "nodes": len(cluster.node_ids)}

@app.get("/api/v1/cluster/status")
def get_cluster_status():
    cluster.tick()
    return cluster.status()

class CommandRequest(BaseModel):
    command: str # e.g. "SET", "GET", "DEL", "HSET", "HGETALL", "LPUSH", "LRANGE", "ZADD", "ZRANGE", "KEYS"
    args: List[Any]

@app.post("/api/v1/kv/execute")
def execute_kv_command(req: CommandRequest):
    res = cluster.execute_command(req.command, req.args)
    return res

class PartitionRequest(BaseModel):
    node_id: Optional[str] = None # None means heal

@app.post("/api/v1/cluster/partition")
def set_partition(req: PartitionRequest):
    if req.node_id:
        cluster.isolate_node(req.node_id)
        cluster.tick()
        return {"message": f"Node '{req.node_id}' isolated from cluster quorum.", "partitions": [list(p) for p in cluster.partitions]}
    else:
        cluster.heal_partitions()
        cluster.tick()
        return {"message": "Network partition healed. Full connectivity restored."}

@app.post("/api/v1/wal/compact")
def compact_wal():
    leader = cluster.get_leader()
    if not leader:
        return {"success": False, "error": "No leader available to compact."}
    new_wal = WALCompactor.compact(leader.store, leader.wal)
    leader.wal = new_wal
    return {"success": True, "message": f"Leader {leader.node_id} WAL compacted. Current entries: {new_wal.entry_count}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8007)
