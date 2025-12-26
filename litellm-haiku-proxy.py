#!/usr/bin/env python3
"""
LiteLLM Proxy with Haiku Planner Integration
FastAPI middleware for Large Request Decomposition
"""

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import httpx
import asyncio
import json
import os
from typing import Optional, Dict, Any
import logging
import sys
import os

# Import middleware (dosya adına göre)
try:
    # Önce normal import dene
    from haiku_planner_middleware import HaikuPlannerMiddleware
except ImportError:
    # Alternatif: dosyadan direkt import
    import importlib.util
    middleware_path = os.path.join(os.path.dirname(__file__), "haiku-planner-middleware.py")
    if os.path.exists(middleware_path):
        spec = importlib.util.spec_from_file_location(
            "haiku_planner_middleware",
            middleware_path
        )
        haiku_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(haiku_module)
        HaikuPlannerMiddleware = haiku_module.HaikuPlannerMiddleware
    else:
        raise ImportError(f"haiku-planner-middleware.py not found at {middleware_path}")

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="LiteLLM Proxy with Haiku Planner")

# Haiku Planner instance
haiku_planner = None

@app.on_event("startup")
async def startup_event():
    """Startup event"""
    global haiku_planner
    
    litellm_url = os.getenv("LITELLM_PROXY_URL", "http://localhost:4000")
    master_key = os.getenv("LITELLM_MASTER_KEY", "sk-default-key")
    
    haiku_planner = HaikuPlannerMiddleware(
        litellm_base_url=litellm_url,
        master_key=master_key
    )
    
    logger.info("✅ Haiku Planner initialized")

@app.post("/chat/completions")
async def chat_completions(
    request: Request,
    x_decompose: Optional[str] = Header(None),
    x_quality: Optional[str] = Header("fast"),
    x_max_cost: Optional[float] = Header(None)
):
    """
    Chat completions endpoint with Haiku Planner support
    
    Headers:
    - x-decompose: "1" to force decomposition
    - x-quality: "fast" (default) or "deep"
    - x-max-cost: maximum cost in USD
    """
    
    try:
        # Request body'yi oku
        body = await request.json()
        
        # MVP: Streaming'i kapat (stream=false)
        if "stream" not in body:
            body["stream"] = False
        
        # Headers'ı dict'e dönüştür
        headers = {
            "x-decompose": x_decompose or "0",
            "x-quality": x_quality or "fast",
            "x-max-cost": str(x_max_cost) if x_max_cost else None
        }
        
        # Decomposition kontrolü
        should_decompose = haiku_planner.should_decompose(body, headers)
        
        logger.info(f"📨 Request received - Decompose: {should_decompose}, Stream: {body.get('stream', False)}")
        
        if should_decompose:
            # Haiku Planner ile işle
            logger.info("🧠 Using Haiku Planner for large request")
            result = await haiku_planner.process_request(body, headers)
            
            if "error" in result:
                return JSONResponse(
                    status_code=400,
                    content=result
                )
            
            return JSONResponse(content=result)
        
        else:
            # Normal LiteLLM proxy'ye yönlendir
            logger.info("➡️ Forwarding to LiteLLM proxy")
            return await forward_to_litellm(body, request.headers)
    
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"error": {"message": "Invalid JSON", "type": "invalid_request"}}
        )
    except Exception as e:
        logger.error(f"❌ Error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": {"message": str(e), "type": "internal_error"}}
        )

async def forward_to_litellm(body: Dict[str, Any], headers) -> JSONResponse:
    """LiteLLM proxy'ye request'i yönlendir (MVP: Timeout uyumlu)"""
    
    litellm_url = os.getenv("LITELLM_PROXY_URL", "http://localhost:4000")
    
    # MVP: Büyük istekler için timeout (600 saniye = 10 dakika)
    max_tokens = body.get("max_tokens", 0)
    if max_tokens >= 15000:
        timeout_value = 600.0  # 10 dakika
    else:
        timeout_value = 300.0  # 5 dakika
    
    try:
        async with httpx.AsyncClient(timeout=timeout_value) as client:
            response = await client.post(
                f"{litellm_url}/chat/completions",
                json=body,
                headers={
                    "Authorization": headers.get("authorization", ""),
                    "Content-Type": "application/json"
                }
            )
            
            return JSONResponse(
                status_code=response.status_code,
                content=response.json()
            )
    
    except Exception as e:
        logger.error(f"❌ LiteLLM forward error: {str(e)}")
        return JSONResponse(
            status_code=502,
            content={"error": {"message": f"LiteLLM error: {str(e)}", "type": "proxy_error"}}
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "haiku_planner": "enabled" if haiku_planner else "disabled",
        "timestamp": __import__('datetime').datetime.now().isoformat()
    }

@app.get("/haiku-planner/stats")
async def haiku_stats():
    """Haiku Planner istatistikleri"""
    return {
        "enabled": True,
        "large_request_threshold": 8000,
        "max_chunks": 3,
        "max_internal_calls": 4,
        "planner_model": "autox",
        "max_cost_per_request": 1.0
    }

@app.post("/haiku-planner/test")
async def test_haiku_planner(request: Request):
    """Haiku Planner test endpoint"""
    
    try:
        body = await request.json()
        headers = {"x-decompose": "1", "x-quality": "fast"}
        
        result = await haiku_planner.process_request(body, headers)
        
        return JSONResponse(content=result)
    
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

# Diğer endpoints (pass-through)
@app.post("/completions")
async def completions(request: Request):
    """Completions endpoint"""
    body = await request.json()
    return await forward_to_litellm(body, request.headers)

@app.post("/embeddings")
async def embeddings(request: Request):
    """Embeddings endpoint"""
    body = await request.json()
    return await forward_to_litellm(body, request.headers)

@app.get("/models")
async def list_models():
    """List available models"""
    litellm_url = os.getenv("LITELLM_PROXY_URL", "http://localhost:4000")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{litellm_url}/models")
            return response.json()
    except Exception as e:
        return JSONResponse(
            status_code=502,
            content={"error": str(e)}
        )

if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PROXY_PORT", 8000))
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        workers=4,
        log_level="info"
    )
