from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import numpy as np
import json
import os

app = FastAPI()

# Broad CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "q-vercel-latency.json")
TELEMETRY_LIST = []

if os.path.exists(DATA_PATH):
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        TELEMETRY_LIST = json.load(f)

class RequestPayload(BaseModel):
    regions: Optional[List[str]] = []
    threshold_ms: Optional[float] = 180.0

@app.middleware("http")
async def add_cors_header(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=200)
    else:
        response = await call_next(request)
    
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

@app.post("/")
@app.post("/api")
@app.post("/api/latency")
def process_telemetry(payload: RequestPayload):
    threshold = payload.threshold_ms if payload.threshold_ms is not None else 180.0
    requested_regions = payload.regions if payload.regions else []

    res_data = {}
    
    for r in requested_regions:
        region_data = [item for item in TELEMETRY_LIST if item.get("region") == r]
        
        if region_data:
            latencies = [item["latency_ms"] for item in region_data if "latency_ms" in item]
            uptimes = [item["uptime_pct"] for item in region_data if "uptime_pct" in item]
            
            avg_lat = float(np.mean(latencies)) if latencies else 0.0
            p95_lat = float(np.percentile(latencies, 95)) if latencies else 0.0
            avg_up = float(np.mean(uptimes)) if uptimes else 0.0
            breaches = int(sum(1 for l in latencies if l > threshold))
            
            res_data[r] = {
                "avg_latency": avg_lat,
                "p95_latency": p95_lat,
                "avg_uptime": avg_up,
                "breaches": breaches
            }
        else:
            res_data[r] = {
                "avg_latency": 0.0,
                "p95_latency": 0.0,
                "avg_uptime": 0.0,
                "breaches": 0
            }

    # Include both direct keys AND "regions" key to guarantee compatibility
    return {
        "regions": res_data,
        **res_data
    }