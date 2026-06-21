from typing import Dict, Any, List, TypedDict
from langgraph.graph import StateGraph, END   # ← IMPORT OBLIGATOIRE
from models.schemas import PRO
from models.domain import Product
from matching.hard_filter import apply_hard_filters
from matching.soft_scoring import score_candidates
from matching.overlay import apply_overlay
from langgraph.checkpoint.memory import MemorySaver

class GraphState(TypedDict):
    project_id: str
    line_id: str
    pro: PRO
    candidates: List[Product]
    filtered_candidates: List[Product]
    scored_candidates: List[Dict[str, Any]]
    final_candidates: List[Dict[str, Any]]
    traces: List[Dict[str, Any]]
    human_selection: str
    manager_approval_required: bool
    status: str
    final_bom: Dict[str, Any]

async def spec_parser(state: GraphState):
    return state

async def hard_constraint_filter(state: GraphState):
    candidates = state.get("candidates", [])
    filtered, traces = apply_hard_filters(candidates, state["pro"])
    state["candidates"] = candidates
    state["filtered_candidates"] = filtered
    state["traces"] = traces
    if not filtered:
        state["status"] = "no_match"
    return state

async def match_brain(state: GraphState):
    if state["status"] == "no_match":
        return state
    scored = score_candidates(state["filtered_candidates"], state["pro"])
    state["scored_candidates"] = scored
    return state

async def tier_strategist(state: GraphState):
    if state["status"] == "no_match":
        return state
    final = await apply_overlay(state["scored_candidates"], state["pro"])
    state["final_candidates"] = final[:5]
    return state

async def compliance_guardian(state: GraphState):
    return state

def should_human_review(state: GraphState):
    if state.get("status") == "no_match":
        return END
    return "human_approval_gate"

async def human_approval_gate(state: GraphState):
    return state

async def finalize_bom(state: GraphState):
    selected = state.get("human_selection")
    candidate_data = None
    for c in state.get("final_candidates", []):
        if c.get("product") and c["product"].sku == selected:
            candidate_data = c
            break
    if candidate_data:
        qty = state.get("pro", {}).get("commercial", {}).get("quantity", 1)
        prod = candidate_data["product"]
        margin = candidate_data.get("margin", prod.margin)
        wattage = prod.lumens / (prod.efficacy or 100) if prod.lumens else 20
        annual_hours = 3000
        co2_emissions_kg = (wattage * annual_hours / 1000) * 0.4
        state["final_bom"] = {
            "sku": prod.sku,
            "quantity": qty,
            "unit_margin": margin,
            "co2_emissions_kg": co2_emissions_kg * qty
        }
    return state

# ========== Construction du graphe ==========
workflow = StateGraph(GraphState)

workflow.add_node("spec_parser", spec_parser)
workflow.add_node("hard_constraint_filter", hard_constraint_filter)
workflow.add_node("match_brain", match_brain)
workflow.add_node("tier_strategist", tier_strategist)
workflow.add_node("compliance_guardian", compliance_guardian)
workflow.add_node("human_approval_gate", human_approval_gate)
workflow.add_node("finalize_bom", finalize_bom)

workflow.set_entry_point("spec_parser")
workflow.add_edge("spec_parser", "hard_constraint_filter")
workflow.add_edge("hard_constraint_filter", "match_brain")
workflow.add_edge("match_brain", "tier_strategist")
workflow.add_edge("tier_strategist", "compliance_guardian")
workflow.add_conditional_edges(
    "compliance_guardian",
    should_human_review,
    {"human_approval_gate": "human_approval_gate", END: END}
)
workflow.add_edge("human_approval_gate", "finalize_bom")
workflow.add_edge("finalize_bom", END)

# ========== Checkpointer (mémoire pour le développement) ==========
checkpointer = MemorySaver()

app_graph = workflow.compile(checkpointer=checkpointer)