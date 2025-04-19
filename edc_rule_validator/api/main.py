"""
FastAPI App for Turing-level Validator (Production Ready)
- Exposes endpoints for rule upload, validation, graph exploration, and explanations
- Integrates GoT reasoning, knowledge graph, symbolic validation
- Includes logging, error handling, and config
"""
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import logging
import uuid
import os
import tempfile
import json
from typing import List, Optional, Dict, Any

from edc_rule_validator.reasoning.got_reasoning import GoTGraph, ThoughtNode
from edc_rule_validator.reasoning.knowledge_graph import KnowledgeGraph
from edc_rule_validator.reasoning.symbolic_validation import SymbolicValidator
# Dummy LLMReasoner for chat endpoint
def dummy_llm_response(prompt):
    return f"[LLM Explanation] {prompt} (demo)"

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("validator")

# App and core modules
app = FastAPI(title="Turing-level Validator API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
knowledge_graph = KnowledgeGraph()
symbolic_validator = SymbolicValidator()

# In-memory storage for uploaded rules, studies, and results (for demo)
rules_store = {}      # rule_id -> file_path
study_store = {}      # study_id -> file_path
results_store = {}    # (rule_id, study_id) -> result

# Models
class RuleUpload(BaseModel):
    rule_content: str
    rule_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.post("/api/v1/rule/upload")
async def upload_rule_file(file: UploadFile = File(...)):
    # Accepts rule/spec file upload
    rule_id = str(uuid.uuid4())
    tmp = tempfile.NamedTemporaryFile(delete=False)
    content = await file.read()
    tmp.write(content)
    tmp.close()
    rules_store[rule_id] = tmp.name
    logger.info(f"Rule file uploaded: {rule_id}")
    return {"rule_id": rule_id, "status": "uploaded"}

@app.post("/api/v1/study/upload")
async def upload_study_file(file: UploadFile = File(...)):
    # Accepts study/context file upload
    study_id = str(uuid.uuid4())
    tmp = tempfile.NamedTemporaryFile(delete=False)
    content = await file.read()
    tmp.write(content)
    tmp.close()
    study_store[study_id] = tmp.name
    logger.info(f"Study file uploaded: {study_id}")
    return {"study_id": study_id, "status": "uploaded"}

@app.get("/api/v1/study/list")
async def list_studies():
    # List uploaded studies (demo: just IDs)
    return {"studies": list(study_store.keys())}

class ValidationRequest(BaseModel):
    rule_id: str
    study_id: str

@app.post("/api/v1/rule/validate")
async def validate_rule_file(req: ValidationRequest):
    rule_id = req.rule_id
    study_id = req.study_id
    # Validate rule with study context (demo: treat both as text)
    if rule_id not in rules_store:
        raise HTTPException(status_code=404, detail="Rule file not found")
    if study_id not in study_store:
        raise HTTPException(status_code=404, detail="Study file not found")
    with open(rules_store[rule_id], "r") as f:
        rule_content = f.read()
    with open(study_store[study_id], "r") as f:
        study_content = f.read()
    # Pass both to symbolic validator (extend as needed)
    result = symbolic_validator.validate(rule_content, study_content)
    results_store[(rule_id, study_id)] = result
    knowledge_graph.add_rule(rule_id, rule_content, {"validation": result, "study_id": study_id})
    return result

@app.get("/api/v1/rule/results")
async def get_rule_results(rule_id: str, study_id: str):
    # Retrieve validation results for a rule+study
    key = (rule_id, study_id)
    if key not in results_store:
        raise HTTPException(status_code=404, detail="Results not found")
    return {"rule_id": rule_id, "study_id": study_id, "result": results_store[key]}

@app.get("/api/v1/graph/rule/{rule_id}")
def get_rule_graph(rule_id: str):
    rule = knowledge_graph.get_rule(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    deps = knowledge_graph.get_dependencies(rule_id)
    return {"rule": rule, "dependencies": deps}

@app.get("/api/v1/got/demo")
def got_demo():
    # Demo GoT graph for explanation
    graph = GoTGraph()
    root = ThoughtNode("Validate Rule X", "validation")
    graph.add_node(root)
    hypo = ThoughtNode("Hypothesis: Rule X is consistent", "hypothesis")
    graph.add_node(hypo)
    graph.add_edge(root, hypo, "leads_to")
    return {"nodes": [{"id": n.id, "content": n.content, "type": n.node_type} for n in graph.nodes.values()]}

@app.post("/api/v1/chat")
async def chat_llm(request: Request):
    data = await request.json()
    prompt = data.get("prompt", "")
    answer = dummy_llm_response(prompt)
    return {"answer": answer}

@app.get("/api/v1/rule/report")
async def get_report(rule_id: str, study_id: str, fmt: str = "json"):
    # Downloadable report stub (json or html)
    key = (rule_id, study_id)
    if key not in results_store:
        raise HTTPException(status_code=404, detail="Results not found")
    if fmt == "json":
        fd, path = tempfile.mkstemp(suffix=".json")
        with open(path, "w") as f:
            json.dump(results_store[key], f)
        return FileResponse(path, filename=f"validation_{rule_id}_{study_id}.json")
    elif fmt == "html":
        fd, path = tempfile.mkstemp(suffix=".html")
        with open(path, "w") as f:
            f.write(f"<html><body><h3>Validation Report for {rule_id} (Study: {study_id})</h3><pre>{json.dumps(results_store[key], indent=2)}</pre></body></html>")
        return FileResponse(path, filename=f"validation_{rule_id}_{study_id}.html")
    else:
        raise HTTPException(status_code=400, detail="Invalid format")

@app.exception_handler(Exception)
def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"error": str(exc)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("edc_rule_validator.api.main:app", host="0.0.0.0", port=8000, reload=True)
