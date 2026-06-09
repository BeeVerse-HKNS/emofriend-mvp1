"""
MasterAgentDashboard — Web Dashboard + WebSocket 實時更新

基於 FastAPI 的 Web Dashboard，提供：
- 項目狀態視覺化
- Bug 偵測結果展示
- 實時更新（WebSocket）
- 手動掃描觸發

公式：log(D * W) — 抽象化 Dashboard × WebSocket
"""

import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


@dataclass
class ProjectStatus:
    name: str
    status: str
    last_update: Optional[str]
    has_agents_md: bool
    bug_count: int
    alert_count: int


@dataclass
class DashboardState:
    last_scan_time: Optional[str] = None
    scan_interval_seconds: int = 300
    projects: list[ProjectStatus] = field(default_factory=list)
    total_bugs: int = 0
    total_alerts: int = 0
    recent_findings: list[dict[str, Any]] = field(default_factory=list)
    scan_history: list[dict[str, Any]] = field(default_factory=list)


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict[str, Any]):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


class MasterAgentDashboard:
    def __init__(
        self,
        auto_scan_scheduler=None,
        bug_detection_engine=None,
        project_scanner=None,
        port: int = 11436,
    ):
        self.port = port
        self.auto_scan_scheduler = auto_scan_scheduler
        self.bug_detection_engine = bug_detection_engine
        self.project_scanner = project_scanner
        
        self.app = FastAPI(title="Master Agent Dashboard")
        self.manager = ConnectionManager()
        self.state = DashboardState()
        
        self._setup_routes()

    def _setup_routes(self):
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_page():
            return self._get_html_template()
        
        @self.app.get("/api/status")
        async def get_status():
            return JSONResponse(content=self._get_status_dict())
        
        @self.app.get("/api/projects")
        async def get_projects():
            return JSONResponse(content=self._get_projects_list())
        
        @self.app.get("/api/bugs")
        async def get_bugs():
            return JSONResponse(content=self._get_bugs_list())
        
        @self.app.get("/api/alerts")
        async def get_alerts():
            return JSONResponse(content=self._get_alerts_list())
        
        @self.app.get("/api/stats")
        async def get_stats():
            return JSONResponse(content=self._get_stats_dict())
        
        @self.app.post("/api/scan")
        async def trigger_scan():
            result = await self._trigger_manual_scan()
            return JSONResponse(content=result)
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await self.manager.connect(websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                self.manager.disconnect(websocket)

    def _get_html_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Agent Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', system-ui, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 30px; }
        .header h1 { font-size: 24px; color: #00d4ff; }
        .status-badge { padding: 5px 15px; border-radius: 20px; font-size: 12px; }
        .status-running { background: #00ff88; color: #000; }
        .status-stopped { background: #ff4444; color: #fff; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: #16213e; border-radius: 10px; padding: 20px; border: 1px solid #0f3460; }
        .card h2 { font-size: 16px; color: #00d4ff; margin-bottom: 15px; }
        .stat-value { font-size: 36px; font-weight: bold; color: #fff; }
        .stat-label { font-size: 12px; color: #888; }
        .project-list { list-style: none; }
        .project-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #0f3460; }
        .project-name { font-weight: 500; }
        .project-status { font-size: 12px; padding: 3px 8px; border-radius: 10px; }
        .bug-list { list-style: none; max-height: 300px; overflow-y: auto; }
        .bug-item { padding: 10px; margin: 5px 0; background: #0f3460; border-radius: 5px; }
        .bug-critical { border-left: 3px solid #ff4444; }
        .bug-high { border-left: 3px solid #ff8800; }
        .bug-medium { border-left: 3px solid #ffcc00; }
        .bug-low { border-left: 3px solid #00ff88; }
        .btn { background: #00d4ff; color: #000; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: 500; }
        .btn:hover { background: #00a8cc; }
        .chart-container { height: 200px; }
        .last-update { font-size: 12px; color: #888; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎯 Master Agent Dashboard</h1>
        <div>
            <span class="status-badge status-running" id="status-badge">Running</span>
            <button class="btn" onclick="triggerScan()">🔄 Scan Now</button>
        </div>
    </div>
    
    <div class="grid">
        <div class="card">
            <h2>📊 Overview</h2>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px;">
                <div>
                    <div class="stat-value" id="total-projects">0</div>
                    <div class="stat-label">Total Projects</div>
                </div>
                <div>
                    <div class="stat-value" id="total-bugs">0</div>
                    <div class="stat-label">Bugs Found</div>
                </div>
                <div>
                    <div class="stat-value" id="total-alerts">0</div>
                    <div class="stat-label">Alerts</div>
                </div>
                <div>
                    <div class="stat-value" id="scan-interval">300s</div>
                    <div class="stat-label">Scan Interval</div>
                </div>
            </div>
            <div class="last-update" id="last-update">Last update: --</div>
        </div>
        
        <div class="card">
            <h2>📁 Projects</h2>
            <ul class="project-list" id="project-list">
                <li class="project-item"><span>Loading...</span></li>
            </ul>
        </div>
        
        <div class="card">
            <h2>🐛 Bug Detection</h2>
            <div class="chart-container">
                <canvas id="bug-chart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h2>🔍 Recent Findings</h2>
            <ul class="bug-list" id="bug-list">
                <li class="bug-item">No findings yet</li>
            </ul>
        </div>
    </div>
    
    <script>
        let bugChart;
        
        function initChart() {
            const ctx = document.getElementById('bug-chart').getContext('2d');
            bugChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['Critical', 'High', 'Medium', 'Low', 'Info'],
                    datasets: [{
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: ['#ff4444', '#ff8800', '#ffcc00', '#00ff88', '#888888']
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } }
                }
            });
        }
        
        async function fetchData() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateDashboard(data);
            } catch (e) {
                console.error('Failed to fetch data:', e);
            }
        }
        
        function updateDashboard(data) {
            document.getElementById('total-projects').textContent = data.projects?.length || 0;
            document.getElementById('total-bugs').textContent = data.total_bugs || 0;
            document.getElementById('total-alerts').textContent = data.total_alerts || 0;
            document.getElementById('scan-interval').textContent = (data.scan_interval_seconds || 300) + 's';
            document.getElementById('last-update').textContent = 'Last update: ' + (data.last_scan_time || '--');
            
            const projectList = document.getElementById('project-list');
            if (data.projects && data.projects.length > 0) {
                projectList.innerHTML = data.projects.slice(0, 10).map(p => `
                    <li class="project-item">
                        <span class="project-name">${p.name}</span>
                        <span class="project-status" style="background: ${getStatusColor(p.status)}">${p.status}</span>
                    </li>
                `).join('');
            }
            
            const bugList = document.getElementById('bug-list');
            if (data.recent_findings && data.recent_findings.length > 0) {
                bugList.innerHTML = data.recent_findings.slice(0, 10).map(f => `
                    <li class="bug-item bug-${f.severity}">
                        <strong>${f.title}</strong><br>
                        <small>${f.file_path || 'N/A'}${f.line_number ? ':' + f.line_number : ''}</small>
                    </li>
                `).join('');
            }
            
            if (bugChart && data.bug_summary) {
                bugChart.data.datasets[0].data = [
                    data.bug_summary.critical || 0,
                    data.bug_summary.high || 0,
                    data.bug_summary.medium || 0,
                    data.bug_summary.low || 0,
                    data.bug_summary.info || 0
                ];
                bugChart.update();
            }
        }
        
        function getStatusColor(status) {
            const colors = {
                'active': '#00ff88',
                'stalled': '#ffcc00',
                'error': '#ff4444',
                'unknown': '#888888'
            };
            return colors[status] || '#888888';
        }
        
        async function triggerScan() {
            try {
                const response = await fetch('/api/scan', { method: 'POST' });
                const data = await response.json();
                console.log('Scan triggered:', data);
                fetchData();
            } catch (e) {
                console.error('Failed to trigger scan:', e);
            }
        }
        
        function connectWebSocket() {
            const ws = new WebSocket(`ws://${window.location.host}/ws`);
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                if (data.type === 'update') {
                    updateDashboard(data.payload);
                }
            };
            ws.onclose = function() {
                setTimeout(connectWebSocket, 3000);
            };
        }
        
        initChart();
        fetchData();
        connectWebSocket();
        setInterval(fetchData, 30000);
    </script>
</body>
</html>"""

    def _get_status_dict(self) -> dict[str, Any]:
        return {
            "last_scan_time": self.state.last_scan_time,
            "scan_interval_seconds": self.state.scan_interval_seconds,
            "projects": [asdict(p) for p in self.state.projects],
            "total_bugs": self.state.total_bugs,
            "total_alerts": self.state.total_alerts,
            "recent_findings": self.state.recent_findings[:20],
            "bug_summary": {
                "critical": sum(1 for f in self.state.recent_findings if f.get("severity") == "critical"),
                "high": sum(1 for f in self.state.recent_findings if f.get("severity") == "high"),
                "medium": sum(1 for f in self.state.recent_findings if f.get("severity") == "medium"),
                "low": sum(1 for f in self.state.recent_findings if f.get("severity") == "low"),
                "info": sum(1 for f in self.state.recent_findings if f.get("severity") == "info"),
            }
        }

    def _get_projects_list(self) -> list[dict[str, Any]]:
        return [asdict(p) for p in self.state.projects]

    def _get_bugs_list(self) -> list[dict[str, Any]]:
        return self.state.recent_findings

    def _get_alerts_list(self) -> list[dict[str, Any]]:
        return []

    def _get_stats_dict(self) -> dict[str, Any]:
        if self.auto_scan_scheduler:
            return self.auto_scan_scheduler.get_stats()
        return {}

    async def _trigger_manual_scan(self) -> dict[str, Any]:
        if self.auto_scan_scheduler:
            result = self.auto_scan_scheduler.trigger_manual_scan()
            return {
                "success": True,
                "projects_scanned": result.projects_scanned,
                "bugs_found": result.bugs_found,
                "alerts_generated": result.alerts_generated,
            }
        return {"success": False, "message": "AutoScanScheduler not configured"}

    def update_state(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)

    def add_finding(self, finding: dict[str, Any]):
        self.state.recent_findings.append(finding)
        if len(self.state.recent_findings) > 100:
            self.state.recent_findings = self.state.recent_findings[-100:]

    async def broadcast_update(self, data: dict[str, Any]):
        await self.manager.broadcast({"type": "update", "payload": data})

    def run(self):
        import uvicorn
        uvicorn.run(self.app, host="0.0.0.0", port=self.port)
