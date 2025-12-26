#!/usr/bin/env python3
"""
LiteLLM Proxy API Test Suite
Kapsamlı test mekanizması - API satışı için hazırlanmış
"""

import asyncio
import aiohttp
import time
import json
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Any
import concurrent.futures
import threading

@dataclass
class TestConfig:
    """Test konfigürasyonu"""
    base_url: str = "https://proxyapison-litellmproxyv1.lc58dd.easypanel.host"
    api_key: str = "sk-super-gizli-admin-sifren"
    models: List[str] = None
    
    def __post_init__(self):
        if self.models is None:
            self.models = ["autox", "sonnet-4-x", "sonnet-4-5-x"]

@dataclass
class TestResult:
    """Test sonucu"""
    success: bool
    response_time: float
    status_code: int
    error_message: str = ""
    tokens_used: int = 0
    model_used: str = ""

class APITester:
    """API Test Sınıfı"""
    
    def __init__(self, config: TestConfig):
        self.config = config
        self.results: List[TestResult] = []
        self.lock = threading.Lock()
    
    async def single_request(self, session: aiohttp.ClientSession, model: str, 
                           message: str, test_id: int) -> TestResult:
        """Tek API isteği"""
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": message}],
            "max_tokens": 150
        }
        
        start_time = time.time()
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                end_time = time.time()
                response_time = end_time - start_time
                
                if response.status == 200:
                    data = await response.json()
                    tokens = data.get('usage', {}).get('total_tokens', 0)
                    return TestResult(
                        success=True,
                        response_time=response_time,
                        status_code=response.status,
                        tokens_used=tokens,
                        model_used=model
                    )
                else:
                    error_text = await response.text()
                    return TestResult(
                        success=False,
                        response_time=response_time,
                        status_code=response.status,
                        error_message=error_text,
                        model_used=model
                    )
        except Exception as e:
            return TestResult(
                success=False,
                response_time=time.time() - start_time,
                status_code=0,
                error_message=str(e),
                model_used=model
            )
    
    async def load_test(self, concurrent_users: int, requests_per_user: int, 
                       model: str = "autox") -> Dict[str, Any]:
        """Yük testi"""
        print(f"\n🚀 YÜK TESTİ BAŞLIYOR")
        print(f"👥 Eşzamanlı kullanıcı: {concurrent_users}")
        print(f"📊 Kullanıcı başına istek: {requests_per_user}")
        print(f"🤖 Model: {model}")
        
        messages = [
            "Merhaba, nasılsın?",
            "Python ile basit bir hesap makinesi yaz",
            "React ile bir todo uygulaması nasıl yapılır?",
            "SQL injection nedir ve nasıl korunulur?",
            "Machine learning temel kavramları nelerdir?"
        ]
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300)) as session:
            tasks = []
            for user in range(concurrent_users):
                for req in range(requests_per_user):
                    message = messages[req % len(messages)]
                    task = self.single_request(session, model, message, user * requests_per_user + req)
                    tasks.append(task)
            
            print(f"⏳ {len(tasks)} istek gönderiliyor...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Sonuçları analiz et
        valid_results = [r for r in results if isinstance(r, TestResult)]
        successful = [r for r in valid_results if r.success]
        failed = [r for r in valid_results if not r.success]
        
        if successful:
            response_times = [r.response_time for r in successful]
            total_tokens = sum(r.tokens_used for r in successful)
        else:
            response_times = []
            total_tokens = 0
        
        return {
            "total_requests": len(valid_results),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "success_rate": len(successful) / len(valid_results) * 100 if valid_results else 0,
            "avg_response_time": statistics.mean(response_times) if response_times else 0,
            "min_response_time": min(response_times) if response_times else 0,
            "max_response_time": max(response_times) if response_times else 0,
            "median_response_time": statistics.median(response_times) if response_times else 0,
            "total_tokens": total_tokens,
            "tokens_per_request": total_tokens / len(successful) if successful else 0,
            "requests_per_second": len(successful) / sum(response_times) if response_times else 0
        }
    
    def cache_test(self) -> Dict[str, Any]:
        """Cache performans testi"""
        print("\n💾 CACHE TESTİ BAŞLIYOR")
        
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        payload = {
            "model": "autox",
            "messages": [{"role": "user", "content": "Cache test mesajı - aynı içerik"}]
        }
        
        # İlk istek (cache'e yazacak)
        start1 = time.time()
        response1 = requests.post(url, headers=headers, json=payload)
        time1 = time.time() - start1
        
        # İkinci istek (cache'den okuyacak)
        start2 = time.time()
        response2 = requests.post(url, headers=headers, json=payload)
        time2 = time.time() - start2
        
        cache_hit = time2 < time1 * 0.3  # %70 daha hızlıysa cache çalışıyor
        
        return {
            "first_request_time": time1,
            "second_request_time": time2,
            "cache_working": cache_hit,
            "speed_improvement": ((time1 - time2) / time1 * 100) if time1 > 0 else 0
        }
    
    def rate_limit_test(self, requests_per_minute: int = 100) -> Dict[str, Any]:
        """Rate limit testi"""
        print(f"\n⚡ RATE LİMİT TESTİ - {requests_per_minute} req/min")
        
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        payload = {
            "model": "autox",
            "messages": [{"role": "user", "content": "Rate limit test"}]
        }
        
        successful = 0
        rate_limited = 0
        start_time = time.time()
        
        for i in range(requests_per_minute):
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=10)
                if response.status_code == 200:
                    successful += 1
                elif response.status_code == 429:  # Too Many Requests
                    rate_limited += 1
                
                if i % 10 == 0:
                    print(f"  📊 {i+1}/{requests_per_minute} - Başarılı: {successful}, Rate Limited: {rate_limited}")
                
                # Dakikada eşit dağıtım için bekleme
                time.sleep(60 / requests_per_minute)
                
            except Exception as e:
                print(f"  ❌ Hata: {e}")
        
        total_time = time.time() - start_time
        
        return {
            "total_requests": requests_per_minute,
            "successful_requests": successful,
            "rate_limited_requests": rate_limited,
            "actual_rps": successful / total_time,
            "test_duration": total_time
        }

async def main():
    """Ana test fonksiyonu"""
    config = TestConfig()
    tester = APITester(config)
    
    print("=" * 60)
    print("🧪 LiteLLM PROXY API TEST SÜİTİ")
    print("=" * 60)
    
    # 1. Cache Testi
    cache_result = tester.cache_test()
    print(f"\n💾 CACHE SONUÇLARI:")
    print(f"  İlk istek: {cache_result['first_request_time']:.3f}s")
    print(f"  İkinci istek: {cache_result['second_request_time']:.3f}s")
    print(f"  Cache çalışıyor: {'✅' if cache_result['cache_working'] else '❌'}")
    print(f"  Hız artışı: %{cache_result['speed_improvement']:.1f}")
    
    # 2. Hafif Yük Testi (10 kullanıcı, 5 istek)
    load_result = await tester.load_test(concurrent_users=10, requests_per_user=5)
    print(f"\n🚀 YÜK TESTİ SONUÇLARI:")
    print(f"  Toplam istek: {load_result['total_requests']}")
    print(f"  Başarılı: {load_result['successful_requests']}")
    print(f"  Başarı oranı: %{load_result['success_rate']:.1f}")
    print(f"  Ortalama süre: {load_result['avg_response_time']:.3f}s")
    print(f"  Saniyede istek: {load_result['requests_per_second']:.1f}")
    print(f"  Toplam token: {load_result['total_tokens']}")
    
    # 3. Rate Limit Testi (30 istek/dakika)
    rate_result = tester.rate_limit_test(30)
    print(f"\n⚡ RATE LİMİT SONUÇLARI:")
    print(f"  Başarılı istek: {rate_result['successful_requests']}")
    print(f"  Rate limited: {rate_result['rate_limited_requests']}")
    print(f"  Gerçek RPS: {rate_result['actual_rps']:.2f}")
    
    print("\n" + "=" * 60)
    print("✅ TÜM TESTLER TAMAMLANDI")
    print("=" * 60)

if __name__ == "__main__":
    import requests
    asyncio.run(main())
