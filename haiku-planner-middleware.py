#!/usr/bin/env python3
"""
Large Request Decomposition (Haiku Planner) Middleware
MEGA_PROMPT.md spesifikasyonuna göre geliştirilmiş
"""

import json
import asyncio
import aiohttp
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import tiktoken
import re
from datetime import datetime

@dataclass
class ChunkPlan:
    """Chunk planı"""
    title: str
    goal: str
    inputs_needed: List[str]
    expected_output: str
    max_tokens: int = 2000

@dataclass
class DecompositionPlan:
    """Decomposition planı"""
    summary: str
    chunks: List[ChunkPlan]
    safety: Dict[str, int]
    estimated_cost: float
    total_tokens_estimate: int

@dataclass
class ChunkResult:
    """Chunk execution sonucu"""
    chunk_id: int
    title: str
    success: bool
    content: str
    tokens_used: int
    cost: float
    execution_time: float
    error_message: str = ""

class HaikuPlannerMiddleware:
    """Haiku Planner Middleware Sınıfı"""
    
    def __init__(self, litellm_base_url: str, master_key: str):
        self.litellm_base_url = litellm_base_url.rstrip('/')
        self.master_key = master_key
        
        # Konfigürasyon
        self.LARGE_REQUEST_THRESHOLD = 8000  # token threshold
        self.MAX_CHUNKS = 3  # MEGA_PROMPT: max 3 chunk
        self.MAX_INTERNAL_CALLS = 4  # 1 planner + 3 chunks
        self.PLANNER_MODEL = "autox"  # Haiku 4.5 (hızlı ve ucuz)
        
        # Token encoder
        self.encoder = tiktoken.get_encoding("cl100k_base")
        
        # Model maliyetleri (USD/1M token)
        self.model_costs = {
            "autox": 3.0,  # Claude-4 Haiku
            "sonnet-4-x": 45.0,  # Claude-4 Sonnet
            "sonnet-4-5-x": 45.0,  # Claude-4.5 Sonnet
            "claude-3-5-x": 15.0,  # Claude 3.5 Sonnet
            "gpt-4-turbo-backup": 20.0
        }
    
    def count_tokens(self, text: str) -> int:
        """Token sayısını hesapla"""
        try:
            return len(self.encoder.encode(text))
        except:
            # Fallback: karakter sayısının 1/4'ü
            return len(text) // 4
    
    def should_decompose(self, request_data: Dict[str, Any], headers: Dict[str, str]) -> bool:
        """İsteğin decompose edilip edilmeyeceğini kontrol et (MVP: Otomatik büyük istekler için)"""
        
        # Header kontrolü (manuel override)
        if headers.get('x-decompose') == '1':
            return True
        
        # Header ile devre dışı bırakma
        if headers.get('x-decompose') == '0':
            return False
        
        # MVP: max_tokens threshold kontrolü (büyük output için)
        max_tokens = request_data.get('max_tokens', 0)
        if max_tokens >= 15000:  # 15K+ token output isteği
            return True
        
        # Token threshold kontrolü (input için)
        messages = request_data.get('messages', [])
        total_tokens = 0
        
        for message in messages:
            content = message.get('content', '')
            if isinstance(content, str):
                total_tokens += self.count_tokens(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        total_tokens += self.count_tokens(item.get('text', ''))
        
        # MVP: 8000+ token input veya büyük istekler için otomatik aktif
        return total_tokens > self.LARGE_REQUEST_THRESHOLD
    
    async def create_plan(self, original_request: Dict[str, Any]) -> DecompositionPlan:
        """Haiku ile decomposition planı oluştur"""
        
        # Orijinal mesajları analiz et
        messages = original_request.get('messages', [])
        user_content = ""
        
        for message in messages:
            if message.get('role') == 'user':
                content = message.get('content', '')
                if isinstance(content, str):
                    user_content += content + "\n"
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get('type') == 'text':
                            user_content += item.get('text', '') + "\n"
        
        # Planner prompt
        planner_prompt = f"""Analyze this large coding request and create a decomposition plan.

ORIGINAL REQUEST:
{user_content[:4000]}...

Create a JSON plan with this exact structure:
{{
  "summary": "Brief description of the task (max 10 lines)",
  "chunks": [
    {{
      "title": "Chunk 1 title",
      "goal": "What this chunk should accomplish",
      "inputs_needed": ["file1.py", "config.yaml"],
      "expected_output": "Description of expected diff patches",
      "max_tokens": 2000
    }}
  ],
  "safety": {{
    "max_files_touched": 5,
    "max_tokens_per_chunk": 2000,
    "estimated_total_tokens": 6000
  }}
}}

CONSTRAINTS:
- Maximum 3 chunks
- Each chunk must produce unified diff patches only
- Focus on the most critical parts first
- Estimate tokens conservatively
- If request is too complex, suggest scope reduction

Return ONLY the JSON, no other text."""

        # Planner çağrısı (MVP: stream=false)
        planner_request = {
            "model": self.PLANNER_MODEL,
            "messages": [
                {"role": "user", "content": planner_prompt}
            ],
            "max_tokens": 1000,
            "temperature": 0.1,
            "stream": False  # MVP: Streaming kapalı
        }
        
        # MVP: Planner için timeout (60 saniye)
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{self.litellm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.master_key}",
                    "Content-Type": "application/json"
                },
                json=planner_request
            ) as response:
                
                if response.status != 200:
                    raise Exception(f"Planner call failed: {response.status}")
                
                result = await response.json()
                plan_text = result['choices'][0]['message']['content']
                
                # JSON parse
                try:
                    # JSON'u temizle
                    plan_text = plan_text.strip()
                    if plan_text.startswith('```json'):
                        plan_text = plan_text[7:]
                    if plan_text.endswith('```'):
                        plan_text = plan_text[:-3]
                    
                    plan_data = json.loads(plan_text)
                    
                    # ChunkPlan objelerine dönüştür
                    chunks = []
                    for chunk_data in plan_data.get('chunks', [])[:self.MAX_CHUNKS]:
                        chunks.append(ChunkPlan(
                            title=chunk_data.get('title', ''),
                            goal=chunk_data.get('goal', ''),
                            inputs_needed=chunk_data.get('inputs_needed', []),
                            expected_output=chunk_data.get('expected_output', ''),
                            max_tokens=min(chunk_data.get('max_tokens', 2000), 2000)
                        ))
                    
                    safety = plan_data.get('safety', {})
                    estimated_tokens = safety.get('estimated_total_tokens', 6000)
                    
                    # Maliyet hesapla
                    model = original_request.get('model', 'autox')
                    cost_per_token = self.model_costs.get(model, 10.0) / 1_000_000
                    estimated_cost = estimated_tokens * cost_per_token
                    
                    return DecompositionPlan(
                        summary=plan_data.get('summary', ''),
                        chunks=chunks,
                        safety=safety,
                        estimated_cost=estimated_cost,
                        total_tokens_estimate=estimated_tokens
                    )
                    
                except json.JSONDecodeError as e:
                    raise Exception(f"Invalid JSON from planner: {e}")
    
    async def execute_chunk(self, chunk: ChunkPlan, chunk_id: int, 
                          original_request: Dict[str, Any], 
                          quality_header: str = "fast") -> ChunkResult:
        """Tek chunk'ı execute et"""
        
        start_time = time.time()
        
        # Model seçimi (quality header'a göre)
        if quality_header == "deep":
            model = original_request.get('model', 'sonnet-4-x')
        else:
            model = self.PLANNER_MODEL  # Fast için Haiku
        
        # Chunk-specific prompt
        chunk_prompt = f"""Execute this specific part of a larger coding task:

CHUNK GOAL: {chunk.goal}

REQUIRED INPUTS: {', '.join(chunk.inputs_needed)}

EXPECTED OUTPUT: {chunk.expected_output}

INSTRUCTIONS:
1. Focus ONLY on this chunk's goal
2. Return ONLY unified diff patches
3. Be concise and precise
4. Maximum {chunk.max_tokens} tokens

Generate the code changes as unified diff patches."""

        # Chunk request (MVP: stream=false, timeout uyumlu)
        chunk_request = {
            "model": model,
            "messages": [
                {"role": "user", "content": chunk_prompt}
            ],
            "max_tokens": chunk.max_tokens,
            "temperature": 0.3,
            "stream": False  # MVP: Streaming kapalı
        }
        
        try:
            # MVP: Büyük chunk'lar için timeout (120 saniye)
            timeout = aiohttp.ClientTimeout(total=180)  # 3 dakika per chunk
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    f"{self.litellm_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.master_key}",
                        "Content-Type": "application/json"
                    },
                    json=chunk_request
                ) as response:
                    
                    execution_time = time.time() - start_time
                    
                    if response.status != 200:
                        error_text = await response.text()
                        return ChunkResult(
                            chunk_id=chunk_id,
                            title=chunk.title,
                            success=False,
                            content="",
                            tokens_used=0,
                            cost=0.0,
                            execution_time=execution_time,
                            error_message=f"HTTP {response.status}: {error_text}"
                        )
                    
                    result = await response.json()
                    content = result['choices'][0]['message']['content']
                    tokens_used = result.get('usage', {}).get('total_tokens', 0)
                    
                    # Maliyet hesapla
                    cost_per_token = self.model_costs.get(model, 10.0) / 1_000_000
                    cost = tokens_used * cost_per_token
                    
                    return ChunkResult(
                        chunk_id=chunk_id,
                        title=chunk.title,
                        success=True,
                        content=content,
                        tokens_used=tokens_used,
                        cost=cost,
                        execution_time=execution_time
                    )
                    
        except Exception as e:
            return ChunkResult(
                chunk_id=chunk_id,
                title=chunk.title,
                success=False,
                content="",
                tokens_used=0,
                cost=0.0,
                execution_time=time.time() - start_time,
                error_message=str(e)
            )
    
    def check_budget_limits(self, estimated_cost: float, max_cost: Optional[float]) -> Tuple[bool, str]:
        """Bütçe limitlerini kontrol et"""
        if max_cost and estimated_cost > max_cost:
            return False, f"Estimated cost ${estimated_cost:.4f} exceeds limit ${max_cost:.4f}"
        return True, ""
    
    def combine_results(self, plan: DecompositionPlan, 
                       chunk_results: List[ChunkResult]) -> Dict[str, Any]:
        """Chunk sonuçlarını birleştir"""
        
        # Toplam istatistikler
        total_tokens = sum(r.tokens_used for r in chunk_results)
        total_cost = sum(r.cost for r in chunk_results)
        successful_chunks = [r for r in chunk_results if r.success]
        
        # Response content oluştur
        content_parts = [
            f"# DECOMPOSITION PLAN",
            f"**Summary:** {plan.summary}",
            f"**Chunks:** {len(chunk_results)}",
            f"**Success Rate:** {len(successful_chunks)}/{len(chunk_results)}",
            f"**Total Cost:** ${total_cost:.4f}",
            f"**Total Tokens:** {total_tokens:,}",
            "",
            "---",
            ""
        ]
        
        # Her chunk için sonuçlar
        for result in chunk_results:
            content_parts.extend([
                f"## CHUNK {result.chunk_id + 1}: {result.title}",
                f"**Status:** {'✅ Success' if result.success else '❌ Failed'}",
                f"**Tokens:** {result.tokens_used:,}",
                f"**Cost:** ${result.cost:.4f}",
                f"**Time:** {result.execution_time:.2f}s",
                ""
            ])
            
            if result.success:
                content_parts.extend([
                    "**Generated Patches:**",
                    "```diff",
                    result.content,
                    "```",
                    ""
                ])
            else:
                content_parts.extend([
                    f"**Error:** {result.error_message}",
                    ""
                ])
            
            content_parts.append("---\n")
        
        # OpenAI-style response
        return {
            "id": f"chatcmpl-haiku-{int(time.time())}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "haiku-planner",
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "\n".join(content_parts)
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": plan.total_tokens_estimate,
                "completion_tokens": total_tokens,
                "total_tokens": plan.total_tokens_estimate + total_tokens
            },
            "haiku_planner": {
                "decomposed": True,
                "chunks_executed": len(chunk_results),
                "chunks_successful": len(successful_chunks),
                "total_cost": total_cost,
                "execution_time": sum(r.execution_time for r in chunk_results)
            }
        }
    
    async def process_request(self, request_data: Dict[str, Any], 
                            headers: Dict[str, str]) -> Dict[str, Any]:
        """Ana request processing fonksiyonu"""
        
        try:
            # 1. Plan oluştur
            print("🧠 Creating decomposition plan...")
            plan = await self.create_plan(request_data)
            
            # 2. Bütçe kontrolü
            max_cost = request_data.get('max_cost')
            budget_ok, budget_msg = self.check_budget_limits(plan.estimated_cost, max_cost)
            
            if not budget_ok:
                return {
                    "error": {
                        "message": f"Budget exceeded. {budget_msg}. Please narrow the scope.",
                        "type": "budget_exceeded",
                        "estimated_cost": plan.estimated_cost,
                        "plan_summary": plan.summary
                    }
                }
            
            # 3. Chunk'ları execute et
            print(f"⚡ Executing {len(plan.chunks)} chunks...")
            quality = headers.get('x-quality', 'fast')
            
            chunk_tasks = []
            for i, chunk in enumerate(plan.chunks):
                task = self.execute_chunk(chunk, i, request_data, quality)
                chunk_tasks.append(task)
            
            # Paralel execution
            chunk_results = await asyncio.gather(*chunk_tasks, return_exceptions=True)
            
            # Exception handling
            valid_results = []
            for i, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    valid_results.append(ChunkResult(
                        chunk_id=i,
                        title=plan.chunks[i].title,
                        success=False,
                        content="",
                        tokens_used=0,
                        cost=0.0,
                        execution_time=0.0,
                        error_message=str(result)
                    ))
                else:
                    valid_results.append(result)
            
            # 4. Sonuçları birleştir
            print("🔄 Combining results...")
            return self.combine_results(plan, valid_results)
            
        except Exception as e:
            return {
                "error": {
                    "message": f"Haiku Planner error: {str(e)}",
                    "type": "planner_error"
                }
            }

# Test fonksiyonu
async def test_haiku_planner():
    """Test fonksiyonu"""
    
    planner = HaikuPlannerMiddleware(
        litellm_base_url="http://localhost:4000",
        master_key="sk-your-master-key"
    )
    
    # Test request
    test_request = {
        "model": "sonnet-4-x",
        "messages": [
            {
                "role": "user", 
                "content": """Create a complete e-commerce system with the following features:

1. User authentication and authorization system
2. Product catalog with categories, search, and filtering
3. Shopping cart functionality
4. Order management system
5. Payment integration with Stripe
6. Admin dashboard for managing products and orders
7. Email notifications for order confirmations
8. Inventory management system
9. Customer reviews and ratings
10. Responsive frontend with React
11. RESTful API with Node.js and Express
12. Database design with PostgreSQL
13. Redis caching for performance
14. Docker containerization
15. CI/CD pipeline with GitHub Actions

Please implement all components with proper error handling, validation, security measures, and comprehensive testing. Include database migrations, API documentation, and deployment instructions."""
            }
        ],
        "max_tokens": 4000
    }
    
    headers = {"x-decompose": "1", "x-quality": "fast"}
    
    print("🧪 Testing Haiku Planner...")
    result = await planner.process_request(test_request, headers)
    
    if "error" in result:
        print(f"❌ Error: {result['error']['message']}")
    else:
        print("✅ Success!")
        print(f"📊 Chunks: {result.get('haiku_planner', {}).get('chunks_executed', 0)}")
        print(f"💰 Cost: ${result.get('haiku_planner', {}).get('total_cost', 0):.4f}")
        print(f"⏱️ Time: {result.get('haiku_planner', {}).get('execution_time', 0):.2f}s")

if __name__ == "__main__":
    asyncio.run(test_haiku_planner())
