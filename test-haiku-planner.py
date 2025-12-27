#!/usr/bin/env python3
"""
Haiku Planner Test Script
Large Request Decomposition testleri
"""

import asyncio
import aiohttp
import json
import time

# Test ayarları
HAIKU_PROXY_URL = "http://localhost:8000"
LITELLM_URL = "http://localhost:4000"
API_KEY = "sk-your-master-key"  # Gerçek key'i buraya yazın

async def test_normal_request():
    """Normal request testi (decomposition olmamalı)"""
    print("\n" + "="*60)
    print("🧪 TEST 1: Normal Request (No Decomposition)")
    print("="*60)
    
    url = f"{HAIKU_PROXY_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "autox",
        "messages": [
            {"role": "user", "content": "Write a simple hello world function in Python."}
        ],
        "max_tokens": 200
    }
    
    start = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            duration = time.time() - start
            result = await response.json()
            
            print(f"✅ Status: {response.status}")
            print(f"⏱️ Duration: {duration:.2f}s")
            print(f"📊 Response keys: {list(result.keys())}")
            
            if "haiku_planner" in result:
                print(f"🧠 Decomposed: {result['haiku_planner'].get('decomposed', False)}")
            else:
                print("➡️ Forwarded to LiteLLM (no decomposition)")

async def test_large_request_auto():
    """Büyük request testi (otomatik decomposition)"""
    print("\n" + "="*60)
    print("🧪 TEST 2: Large Request (Auto Decomposition)")
    print("="*60)
    
    url = f"{HAIKU_PROXY_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Büyük request (8000+ token)
    large_content = """Create a complete e-commerce platform with the following features:

1. User Authentication System
   - JWT-based authentication
   - OAuth2 integration (Google, GitHub)
   - Password reset functionality
   - Email verification
   - Two-factor authentication

2. Product Management
   - Product catalog with categories
   - Advanced search and filtering
   - Product reviews and ratings
   - Inventory management
   - Product variants (size, color, etc.)

3. Shopping Cart & Checkout
   - Add/remove items from cart
   - Cart persistence
   - Multiple payment methods (Stripe, PayPal)
   - Shipping calculation
   - Order confirmation

4. Order Management
   - Order history
   - Order tracking
   - Refund processing
   - Invoice generation

5. Admin Dashboard
   - User management
   - Product management
   - Order management
   - Analytics and reports
   - Settings configuration

6. Frontend (React)
   - Responsive design
   - State management (Redux)
   - Routing (React Router)
   - Form validation
   - Error handling

7. Backend (Node.js + Express)
   - RESTful API
   - Database models (MongoDB/PostgreSQL)
   - Middleware for auth, validation
   - Error handling
   - Logging

8. Additional Features
   - Email notifications
   - Redis caching
   - Docker containerization
   - CI/CD pipeline
   - Unit and integration tests
   - API documentation

Please implement all components with proper error handling, validation, security measures, and comprehensive testing."""
    
    payload = {
        "model": "sonnet-4-x",
        "messages": [
            {"role": "user", "content": large_content}
        ],
        "max_tokens": 4000
    }
    
    start = time.time()
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600)) as session:
        async with session.post(url, headers=headers, json=payload) as response:
            duration = time.time() - start
            result = await response.json()
            
            print(f"✅ Status: {response.status}")
            print(f"⏱️ Duration: {duration:.2f}s")
            
            if "error" in result:
                print(f"❌ Error: {result['error'].get('message', 'Unknown error')}")
            elif "haiku_planner" in result:
                planner_info = result["haiku_planner"]
                print(f"🧠 Decomposed: {planner_info.get('decomposed', False)}")
                print(f"📦 Chunks executed: {planner_info.get('chunks_executed', 0)}")
                print(f"✅ Chunks successful: {planner_info.get('chunks_successful', 0)}")
                print(f"💰 Total cost: ${planner_info.get('total_cost', 0):.4f}")
                print(f"⏱️ Execution time: {planner_info.get('execution_time', 0):.2f}s")
                
                # Response content preview
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    print(f"\n📄 Response preview (first 500 chars):")
                    print(content[:500] + "...")
            else:
                print("➡️ Forwarded to LiteLLM (no decomposition)")

async def test_forced_decomposition():
    """Zorunlu decomposition testi (header ile)"""
    print("\n" + "="*60)
    print("🧪 TEST 3: Forced Decomposition (x-decompose: 1)")
    print("="*60)
    
    url = f"{HAIKU_PROXY_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "x-decompose": "1",
        "x-quality": "fast"
    }
    
    payload = {
        "model": "autox",
        "messages": [
            {"role": "user", "content": "Create a REST API with authentication, CRUD operations, and testing."}
        ],
        "max_tokens": 2000
    }
    
    start = time.time()
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
        async with session.post(url, headers=headers, json=payload) as response:
            duration = time.time() - start
            result = await response.json()
            
            print(f"✅ Status: {response.status}")
            print(f"⏱️ Duration: {duration:.2f}s")
            
            if "haiku_planner" in result:
                planner_info = result["haiku_planner"]
                print(f"🧠 Decomposed: {planner_info.get('decomposed', False)}")
                print(f"📦 Chunks: {planner_info.get('chunks_executed', 0)}")
                print(f"💰 Cost: ${planner_info.get('total_cost', 0):.4f}")
            else:
                print("⚠️ No decomposition info in response")

async def test_budget_limit():
    """Bütçe limiti testi"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Budget Limit Test")
    print("="*60)
    
    url = f"{HAIKU_PROXY_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "x-decompose": "1",
        "x-max-cost": "0.01"  # Çok düşük limit
    }
    
    payload = {
        "model": "sonnet-4-x",
        "messages": [
            {"role": "user", "content": "Create a massive enterprise application with 100+ features."}
        ],
        "max_tokens": 10000
    }
    
    start = time.time()
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post(url, headers=headers, json=payload) as response:
            duration = time.time() - start
            result = await response.json()
            
            print(f"✅ Status: {response.status}")
            print(f"⏱️ Duration: {duration:.2f}s")
            
            if "error" in result:
                error = result["error"]
                print(f"❌ Error type: {error.get('type', 'unknown')}")
                print(f"📝 Message: {error.get('message', 'No message')}")
                if "estimated_cost" in error:
                    print(f"💰 Estimated cost: ${error['estimated_cost']:.4f}")
            else:
                print("⚠️ Budget limit not enforced")

async def test_health_check():
    """Health check testi"""
    print("\n" + "="*60)
    print("🧪 TEST 5: Health Check")
    print("="*60)
    
    url = f"{HAIKU_PROXY_URL}/health"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            result = await response.json()
            
            print(f"✅ Status: {response.status}")
            print(f"📊 Response: {json.dumps(result, indent=2)}")

async def test_stats():
    """Stats endpoint testi"""
    print("\n" + "="*60)
    print("🧪 TEST 6: Haiku Planner Stats")
    print("="*60)
    
    url = f"{HAIKU_PROXY_URL}/haiku-planner/stats"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            result = await response.json()
            
            print(f"✅ Status: {response.status}")
            print(f"📊 Stats: {json.dumps(result, indent=2)}")

async def main():
    """Ana test fonksiyonu"""
    print("="*60)
    print("🚀 HAIKU PLANNER TEST SUITE")
    print("="*60)
    print(f"📍 Haiku Proxy URL: {HAIKU_PROXY_URL}")
    print(f"📍 LiteLLM URL: {LITELLM_URL}")
    
    # Health check
    await test_health_check()
    await test_stats()
    
    # Normal request
    await test_normal_request()
    
    # Forced decomposition
    await test_forced_decomposition()
    
    # Large request (auto)
    # await test_large_request_auto()  # Yorum satırı - uzun sürebilir
    
    # Budget limit
    await test_budget_limit()
    
    print("\n" + "="*60)
    print("✅ TÜM TESTLER TAMAMLANDI")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(main())

