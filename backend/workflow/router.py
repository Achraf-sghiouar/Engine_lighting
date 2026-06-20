from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid

from workflow.graph import app_graph

router = APIRouter(prefix="/workflow", tags=["workflow"])

class WorkflowRunRequest(BaseModel):
    line_id: str
    pro_data: dict

class ResumeRequest(BaseModel):
    decision: str # e.g. 'approved', 'rejected'
    selected_sku: str = None

@router.post("/runs")
async def start_workflow(req: WorkflowRunRequest):
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}
    
    state_input = {
        "line_id": req.line_id,
        "pro": req.pro_data,
        "db": None, # In a real app, inject the session properly here or inside the node
        "status": "processing"
    }
    
    # Run the graph until the first interrupt
    async for event in app_graph.astream(state_input, config):
        pass # Stream events if needed
        
    state = await app_graph.aget_state(config)
    return {"thread_id": thread_id, "status": "paused_or_finished", "next": state.next}

@router.get("/runs/{thread_id}/state")
async def get_workflow_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = await app_graph.aget_state(config)
    
    if not state:
        raise HTTPException(status_code=404, detail="Run not found")
        
    return {
        "thread_id": thread_id,
        "values": state.values,
        "next": state.next, # Will be empty if finished
        "is_finished": len(state.next) == 0
    }

@router.post("/runs/{thread_id}/resume")
async def resume_workflow(thread_id: str, req: ResumeRequest):
    config = {"configurable": {"thread_id": thread_id}}
    state = await app_graph.aget_state(config)
    
    if not state or len(state.next) == 0:
        raise HTTPException(status_code=400, detail="Run not found or already finished")
        
    # Inject user's human_approval_gate decision
    resume_data = {
        "human_selection": req.selected_sku,
        "status": req.decision
    }
    
    # Resume the graph
    async for event in app_graph.astream(resume_data, config, as_node="human_approval_gate"): # Assuming human_approval_gate is next
        pass
        
    new_state = await app_graph.aget_state(config)
    return {"thread_id": thread_id, "status": "resumed", "next": new_state.next}
