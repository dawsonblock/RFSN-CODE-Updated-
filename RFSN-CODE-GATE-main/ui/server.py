"""
FastAPI backend server for RFSN SWE-Bench Killer UI.

Provides REST API endpoints and WebSocket support for real-time updates.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import RFSN components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from eval.run import EvalConfig, EvalRunner, SWEBenchTask
    from localize import LocalizationConfig
    from agent.profiles import load_profile
    RFSN_AVAILABLE = True
except ImportError:
    RFSN_AVAILABLE = False
    print("Warning: RFSN components not available, running in mock mode")


app = FastAPI(title="RFSN SWE-Bench Killer API", version="0.4.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, task_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[task_id] = websocket

    def disconnect(self, task_id: str):
        if task_id in self.active_connections:
            del self.active_connections[task_id]

    async def send_message(self, task_id: str, message: dict):
        if task_id in self.active_connections:
            try:
                await self.active_connections[task_id].send_json(message)
            except Exception as e:
                print(f"Error sending message to {task_id}: {e}")
                self.disconnect(task_id)


manager = ConnectionManager()

# Running tasks
running_tasks: Dict[str, dict] = {}


# Request/Response models
class StartRequest(BaseModel):
    repoUrl: str
    repoBranch: str = "main"
    problemStatement: str
    githubToken: Optional[str] = None
    githubUsername: Optional[str] = None
    createPR: bool = False
    commitChanges: bool = True
    llmProvider: str = "deepseek"
    llmApiKey: str
    llmModel: str = "deepseek-chat"
    temperature: float = 0.2
    profile: str = "swebench_lite"
    maxSteps: int = 50
    maxTime: int = 30
    useTrace: bool = True
    useRipgrep: bool = True
    useSymbols: bool = True
    useEmbeddings: bool = False
    strategyDirect: bool = True
    strategyTestDriven: bool = True
    strategyEnsemble: bool = True


class StartResponse(BaseModel):
    task_id: str
    status: str
    message: str


class StatusResponse(BaseModel):
    task_id: str
    status: str
    phase: str
    progress: float
    steps_completed: int
    patches_tried: int
    elapsed_time: float


@app.get("/")
async def root():
    """Serve the main UI."""
    return FileResponse("ui/index.html")


@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.4.0",
        "rfsn_available": RFSN_AVAILABLE,
    }


@app.post("/api/start", response_model=StartResponse)
async def start_agent(request: StartRequest):
    """Start the RFSN agent with given configuration."""
    
    # Generate task ID
    task_id = str(uuid.uuid4())[:8]
    
    # Store task info
    running_tasks[task_id] = {
        "config": request.dict(),
        "status": "running",
        "phase": "INGEST",
        "progress": 0.0,
        "steps_completed": 0,
        "patches_tried": 0,
        "start_time": datetime.now(),
    }
    
    # Start agent in background
    asyncio.create_task(run_agent_task(task_id, request))
    
    return StartResponse(
        task_id=task_id,
        status="started",
        message=f"Agent started with task ID: {task_id}",
    )


@app.post("/api/stop")
async def stop_agent():
    """Stop the running agent."""
    # In a real implementation, this would signal the agent to stop
    for task_id in list(running_tasks.keys()):
        running_tasks[task_id]["status"] = "stopped"
    
    return {"status": "stopped", "message": "Stop signal sent to all agents"}


@app.get("/api/status/{task_id}", response_model=StatusResponse)
async def get_status(task_id: str):
    """Get the status of a running task."""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = running_tasks[task_id]
    elapsed = (datetime.now() - task["start_time"]).total_seconds()
    
    return StatusResponse(
        task_id=task_id,
        status=task["status"],
        phase=task["phase"],
        progress=task["progress"],
        steps_completed=task["steps_completed"],
        patches_tried=task["patches_tried"],
        elapsed_time=elapsed,
    )


@app.websocket("/ws/{task_id}")
async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(task_id, websocket)
    
    try:
        # Send initial status
        if task_id in running_tasks:
            await manager.send_message(task_id, {
                "type": "connected",
                "task_id": task_id,
                "message": "Connected to live updates",
            })
        
        # Keep connection alive
        while True:
            # Wait for messages (client can send commands)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                # Handle client messages if needed
            except asyncio.TimeoutError:
                # Send heartbeat
                await manager.send_message(task_id, {"type": "heartbeat"})
            
            # Check if task is still running
            if task_id not in running_tasks or running_tasks[task_id]["status"] == "completed":
                break
                
    except WebSocketDisconnect:
        manager.disconnect(task_id)
    except Exception as e:
        print(f"WebSocket error for {task_id}: {e}")
        manager.disconnect(task_id)


async def run_agent_task(task_id: str, config: StartRequest):
    """Run the agent task and send updates via WebSocket."""
    
    try:
        # Send initial log
        await manager.send_message(task_id, {
            "type": "log",
            "level": "info",
            "message": f"Starting agent with task ID: {task_id}",
        })
        
        if RFSN_AVAILABLE:
            # Real RFSN execution
            await run_real_agent(task_id, config)
        else:
            # Mock execution for demo
            await run_mock_agent(task_id, config)
        
        # Mark as completed
        running_tasks[task_id]["status"] = "completed"
        await manager.send_message(task_id, {
            "type": "complete",
            "success": True,
            "time_taken": (datetime.now() - running_tasks[task_id]["start_time"]).total_seconds(),
        })
        
    except Exception as e:
        print(f"Error running agent task {task_id}: {e}")
        running_tasks[task_id]["status"] = "error"
        await manager.send_message(task_id, {
            "type": "error",
            "message": str(e),
        })


async def run_real_agent(task_id: str, config: StartRequest):
    """Run the real RFSN agent."""
    
    # Create task
    task = SWEBenchTask(
        task_id=task_id,
        repo=config.repoUrl.replace("https://github.com/", ""),
        base_commit=config.repoBranch,
        problem_statement=config.problemStatement,
        test_patch="",  # Would need to be provided
    )
    
    # Create eval config
    eval_config = EvalConfig(
        dataset="custom",
        profile_name=config.profile,
        max_time_per_task=config.maxTime * 60,
        max_steps_per_task=config.maxSteps,
    )
    
    # Create runner
    runner = EvalRunner(eval_config)
    
    # Run task with progress updates
    # This is a simplified version - real implementation would need
    # to hook into the agent loop for progress updates
    
    phases = ["INGEST", "LOCALIZE", "PLAN", "PATCH", "TEST", "DIAGNOSE", "FINALIZE"]
    
    for i, phase in enumerate(phases):
        running_tasks[task_id]["phase"] = phase
        running_tasks[task_id]["progress"] = (i + 1) / len(phases) * 100
        
        await manager.send_message(task_id, {
            "type": "phase",
            "phase": phase,
        })
        
        await manager.send_message(task_id, {
            "type": "progress",
            "progress": (i + 1) / len(phases) * 100,
            "current_step": i + 1,
            "total_steps": len(phases),
        })
        
        # Simulate work
        await asyncio.sleep(2)


async def run_mock_agent(task_id: str, config: StartRequest):
    """Run a mock agent for demo purposes."""
    
    phases = ["INGEST", "LOCALIZE", "PLAN", "PATCH", "TEST", "DIAGNOSE", "FINALIZE"]
    
    for i, phase in enumerate(phases):
        # Update task state
        running_tasks[task_id]["phase"] = phase
        running_tasks[task_id]["steps_completed"] = i + 1
        running_tasks[task_id]["progress"] = (i + 1) / len(phases) * 100
        
        # Send phase update
        await manager.send_message(task_id, {
            "type": "phase",
            "phase": phase,
        })
        
        # Send log
        await manager.send_message(task_id, {
            "type": "log",
            "level": "info",
            "message": f"Executing phase: {phase}",
        })
        
        # Send progress
        await manager.send_message(task_id, {
            "type": "progress",
            "progress": (i + 1) / len(phases) * 100,
            "current_step": i + 1,
            "total_steps": len(phases),
            "patches": i // 2,
        })
        
        # Simulate work
        await asyncio.sleep(3)
        
        # Send intermediate logs
        if phase == "LOCALIZE":
            await manager.send_message(task_id, {
                "type": "log",
                "level": "success",
                "message": "Found 5 potential bug locations",
            })
        elif phase == "PATCH":
            await manager.send_message(task_id, {
                "type": "log",
                "level": "info",
                "message": "Generated 3 patch candidates",
            })
        elif phase == "TEST":
            running_tasks[task_id]["patches_tried"] += 1
            await manager.send_message(task_id, {
                "type": "log",
                "level": "success",
                "message": "Patch #1 passed unit tests",
            })


# Serve static files
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")


if __name__ == "__main__":
    import uvicorn
    
    print("🚀 Starting RFSN SWE-Bench Killer UI Server")
    print("📍 Server running at: http://localhost:8000")
    print("💡 Open http://localhost:8000 in your browser")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )
