/**
 * Zenith KV Engine Web Dashboard & REPL Client.
 * Jerry A. Nabasu (@JayNabasu)
 */

const nodesContainer = document.getElementById('nodesContainer');
const quorumStatus = document.getElementById('quorumStatus');
const terminalOutput = document.getElementById('terminalOutput');
const replForm = document.getElementById('replForm');
const replInput = document.getElementById('replInput');
const healBtn = document.getElementById('healBtn');
const compactBtn = document.getElementById('compactBtn');

async function fetchStatus() {
    try {
        const res = await fetch('/api/v1/cluster/status');
        if (!res.ok) return;
        const data = await res.json();
        renderCluster(data);
    } catch (err) {
        console.error("Cluster poll error:", err);
    }
}

function renderCluster(data) {
    const isPartitioned = data.partitions && data.partitions.length > 0;
    quorumStatus.textContent = isPartitioned ? `PARTITION ACTIVE (${data.partitions.length} Segments)` : `QUORUM HEALTHY (${data.node_count}/${data.node_count})`;
    quorumStatus.style.borderColor = isPartitioned ? 'var(--rose)' : 'var(--green)';
    quorumStatus.style.color = isPartitioned ? 'var(--rose)' : 'var(--green)';

    nodesContainer.innerHTML = data.nodes.map(node => {
        const isLeader = node.state === 'LEADER';
        const roleClass = isLeader ? 'role-leader' : (node.state === 'CANDIDATE' ? 'role-candidate' : 'role-follower');
        return `
            <div class="card node-card ${isLeader ? 'leader' : ''}">
                <div class="node-top">
                    <span class="node-title">${node.node_id.toUpperCase()}</span>
                    <span class="node-role-badge ${roleClass}">${node.state}</span>
                </div>
                <div class="node-stats-grid">
                    <div>Term: <span class="node-stat-val">${node.term}</span></div>
                    <div>Leader: <span class="node-stat-val">${node.leader_id || 'None'}</span></div>
                    <div>Log Index: <span class="node-stat-val">${node.commit_index}</span></div>
                    <div>Stored Keys: <span class="node-stat-val">${node.keys_count}</span></div>
                </div>
                <div style="margin-top: 6px;">
                    <button class="btn btn-secondary" style="font-size: 0.7rem; width: 100%;" onclick="isolateNode('${node.node_id}')">
                        ⚡ Isolate Node
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

window.isolateNode = async function(nodeId) {
    try {
        const res = await fetch('/api/v1/cluster/partition', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: nodeId })
        });
        const d = await res.json();
        appendTerminal(`[NETWORK] ${d.message}`, 'text-amber');
        fetchStatus();
    } catch (e) {
        appendTerminal(`[ERROR] Partition request failed`, 'text-rose');
    }
};

healBtn.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/v1/cluster/partition', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ node_id: null })
        });
        const d = await res.json();
        appendTerminal(`[NETWORK] ${d.message}`, 'text-green');
        fetchStatus();
    } catch (e) {
        appendTerminal(`[ERROR] Heal request failed`, 'text-rose');
    }
});

compactBtn.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/v1/wal/compact', { method: 'POST' });
        const d = await res.json();
        appendTerminal(`[WAL] ${d.message || d.error}`, d.success ? 'text-green' : 'text-rose');
    } catch (e) {
        appendTerminal(`[ERROR] Compaction failed`, 'text-rose');
    }
});

function appendTerminal(text, className = '') {
    const line = document.createElement('div');
    line.className = `terminal-line ${className}`;
    line.textContent = text;
    terminalOutput.appendChild(line);
    terminalOutput.scrollTop = terminalOutput.scrollHeight;
}

replForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const raw = replInput.value.trim();
    if (!raw) return;
    replInput.value = '';

    appendTerminal(`> ${raw}`, 'text-accent');

    // Parse command words
    const parts = raw.match(/(?:[^\s"']+|"[^"]*"|'[^']*')+/g) || [];
    if (parts.length === 0) return;

    const cmd = parts[0].toUpperCase();
    const args = parts.slice(1).map(p => p.replace(/^["']|["']$/g, ''));

    try {
        const res = await fetch('/api/v1/kv/execute', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: cmd, args: args })
        });
        const data = await res.json();
        if (data.success) {
            appendTerminal(typeof data.result === 'object' ? JSON.stringify(data.result, null, 2) : String(data.result), 'text-green');
        } else {
            appendTerminal(`(error) ${data.error}`, 'text-rose');
        }
        fetchStatus();
    } catch (err) {
        appendTerminal(`(error) Network connection failed`, 'text-rose');
    }
});

// Polling interval
fetchStatus();
setInterval(fetchStatus, 1500);
