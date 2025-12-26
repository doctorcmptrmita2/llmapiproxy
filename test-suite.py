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
import requests
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
    
    def cache_test(self, model: str = "autox", token_sizes: List[int] = None) -> Dict[str, Any]:
        """Cache performans testi - Zorlu versiyon - Farklı token boyutları"""
        if token_sizes is None:
            token_sizes = [2500, 5000, 15000, 40000, 60000]
        
        print(f"\n💾 CACHE TESTİ BAŞLIYOR - Model: {model}")
        print(f"📊 Token boyutları: {token_sizes}")
        
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        
        results_by_token = {}
        
        for max_tokens in token_sizes:
            print(f"\n  🔄 Token boyutu: {max_tokens:,} token testi başlıyor...")
            
            # Büyük içerik oluştur (token sayısına göre)
            content_size = max_tokens // 2  # Yaklaşık token sayısı için karakter hesabı
            test_content = f"Cache test mesajı - {max_tokens} token limiti. " + ("Bu bir test mesajıdır. " * (content_size // 20))
            
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": test_content[:5000]}],  # İçerik sınırı
                "max_tokens": max_tokens
            }
            
            cache_times = []
            non_cache_times = []
            
            # Her token boyutu için 2 iterasyon
            for iteration in range(2):
                # İlk istek (cache'e yazacak)
                start1 = time.time()
                try:
                    response1 = requests.post(url, headers=headers, json=payload, timeout=120)
                    time1 = time.time() - start1
                    non_cache_times.append(time1)
                    
                    if response1.status_code != 200:
                        print(f"    ⚠️  İlk istek {response1.status_code} - Token: {max_tokens}")
                except Exception as e:
                    print(f"    ❌ İlk istek hatası (Token: {max_tokens}): {str(e)[:50]}")
                    non_cache_times.append(999)  # Hata için yüksek değer
                
                # İkinci istek (cache'den okuyacak)
                start2 = time.time()
                try:
                    response2 = requests.post(url, headers=headers, json=payload, timeout=120)
                    time2 = time.time() - start2
                    cache_times.append(time2)
                    
                    if response2.status_code != 200:
                        print(f"    ⚠️  İkinci istek {response2.status_code} - Token: {max_tokens}")
                except Exception as e:
                    print(f"    ❌ İkinci istek hatası (Token: {max_tokens}): {str(e)[:50]}")
                    cache_times.append(999)  # Hata için yüksek değer
                
                if iteration == 0:
                    valid_times = [t for t in non_cache_times if t < 999]
                    valid_cache = [t for t in cache_times if t < 999]
                    if valid_times and valid_cache:
                        print(f"    📊 İterasyon {iteration+1}: Non-cache={valid_times[0]:.3f}s, Cache={valid_cache[0]:.3f}s")
            
            # Geçerli süreleri hesapla
            valid_non_cache = [t for t in non_cache_times if t < 999]
            valid_cache = [t for t in cache_times if t < 999]
            
            avg_non_cache = statistics.mean(valid_non_cache) if valid_non_cache else 0
            avg_cache = statistics.mean(valid_cache) if valid_cache else 0
            cache_hit = avg_cache < avg_non_cache * 0.3 if avg_non_cache > 0 else False
            
            results_by_token[max_tokens] = {
                "avg_non_cache_time": avg_non_cache,
                "avg_cache_time": avg_cache,
                "cache_working": cache_hit,
                "speed_improvement": ((avg_non_cache - avg_cache) / avg_non_cache * 100) if avg_non_cache > 0 else 0
            }
        
        # Genel ortalama hesapla
        all_non_cache = []
        all_cache = []
        for token_size, result in results_by_token.items():
            if result["avg_non_cache_time"] > 0:
                all_non_cache.append(result["avg_non_cache_time"])
            if result["avg_cache_time"] > 0:
                all_cache.append(result["avg_cache_time"])
        
        overall_avg_non_cache = statistics.mean(all_non_cache) if all_non_cache else 0
        overall_avg_cache = statistics.mean(all_cache) if all_cache else 0
        overall_cache_hit = overall_avg_cache < overall_avg_non_cache * 0.3 if overall_avg_non_cache > 0 else False
        
        return {
            "model": model,
            "token_sizes": token_sizes,
            "results_by_token": results_by_token,
            "avg_non_cache_time": overall_avg_non_cache,
            "avg_cache_time": overall_avg_cache,
            "cache_working": overall_cache_hit,
            "speed_improvement": ((overall_avg_non_cache - overall_avg_cache) / overall_avg_non_cache * 100) if overall_avg_non_cache > 0 else 0
        }
    
    def rate_limit_test(self, model: str = "autox", token_sizes: List[int] = None, requests_per_minute: int = 60) -> Dict[str, Any]:
        """Rate limit testi - Zorlu versiyon - Farklı token boyutları"""
        if token_sizes is None:
            token_sizes = [2500, 5000, 15000, 40000, 60000]
        
        print(f"\n⚡ RATE LİMİT TESTİ - Model: {model}, {requests_per_minute} req/min (ZORLU)")
        print(f"📊 Token boyutları: {token_sizes}")
        
        url = f"{self.config.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}"
        }
        
        # Her token boyutu için istek sayısı
        requests_per_token = requests_per_minute // len(token_sizes)
        
        results_by_token = {}
        
        for max_tokens in token_sizes:
            print(f"\n  🔄 Token boyutu: {max_tokens:,} token - {requests_per_token} istek gönderiliyor...")
            
            successful = 0
            rate_limited = 0
            failed = 0
            timeout_errors = 0
            response_times = []
            start_time = time.time()
            
            for i in range(requests_per_token):
                # Büyük içerik oluştur
                content_size = max_tokens // 2
                test_content = f"Rate limit test - {max_tokens} token - istek {i+1}. " + ("Test içeriği. " * (content_size // 20))
                
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": test_content[:5000]}],  # İçerik sınırı
                    "max_tokens": max_tokens
                }
                
                try:
                    req_start = time.time()
                    response = requests.post(url, headers=headers, json=payload, timeout=180)  # Büyük token için daha uzun timeout
                    req_time = time.time() - req_start
                    response_times.append(req_time)
                    
                    if response.status_code == 200:
                        successful += 1
                    elif response.status_code == 429:  # Too Many Requests
                        rate_limited += 1
                    else:
                        failed += 1
                        if i % 5 == 0:
                            print(f"    ⚠️  Status {response.status_code} - İstek {i+1}")
                    
                    if (i + 1) % 5 == 0:
                        print(f"    📊 {i+1}/{requests_per_token} - Başarılı: {successful}, Rate Lim: {rate_limited}, Başarısız: {failed}")
                    
                except requests.exceptions.Timeout:
                    timeout_errors += 1
                    failed += 1
                    if (i + 1) % 5 == 0:
                        print(f"    ⏱️  Timeout hatası: {timeout_errors}")
                except Exception as e:
                    failed += 1
                    if (i + 1) % 5 == 0:
                        print(f"    ❌ Hata: {str(e)[:50]}")
                
                # Dakikada eşit dağıtım için bekleme
                time.sleep(60 / requests_per_minute)
            
            total_time = time.time() - start_time
            
            results_by_token[max_tokens] = {
                "total_requests": requests_per_token,
                "successful_requests": successful,
                "rate_limited_requests": rate_limited,
                "failed_requests": failed,
                "timeout_errors": timeout_errors,
                "avg_response_time": statistics.mean(response_times) if response_times else 0,
                "min_response_time": min(response_times) if response_times else 0,
                "max_response_time": max(response_times) if response_times else 0,
                "actual_rps": successful / total_time if total_time > 0 else 0,
                "test_duration": total_time
            }
        
        # Genel toplamlar
        total_successful = sum(r["successful_requests"] for r in results_by_token.values())
        total_rate_limited = sum(r["rate_limited_requests"] for r in results_by_token.values())
        total_failed = sum(r["failed_requests"] for r in results_by_token.values())
        total_timeout = sum(r["timeout_errors"] for r in results_by_token.values())
        all_response_times = []
        for r in results_by_token.values():
            all_response_times.extend([r["avg_response_time"]] * r["successful_requests"])
        
        return {
            "model": model,
            "token_sizes": token_sizes,
            "total_requests": requests_per_minute,
            "successful_requests": total_successful,
            "rate_limited_requests": total_rate_limited,
            "failed_requests": total_failed,
            "timeout_errors": total_timeout,
            "results_by_token": results_by_token,
            "avg_response_time": statistics.mean(all_response_times) if all_response_times else 0,
            "min_response_time": min([r["min_response_time"] for r in results_by_token.values() if r["min_response_time"] > 0]) if any(r["min_response_time"] > 0 for r in results_by_token.values()) else 0,
            "max_response_time": max([r["max_response_time"] for r in results_by_token.values() if r["max_response_time"] > 0]) if any(r["max_response_time"] > 0 for r in results_by_token.values()) else 0,
            "actual_rps": total_successful / sum(r["test_duration"] for r in results_by_token.values()) if sum(r["test_duration"] for r in results_by_token.values()) > 0 else 0
        }

async def main():
    """Ana test fonksiyonu"""
    config = TestConfig()
    tester = APITester(config)
    
    print("=" * 80)
    print("🧪 LiteLLM PROXY API TEST SÜİTİ - BÜYÜK TOKEN BOYUTLARI İLE ZORLU TEST")
    print("=" * 80)
    
    # Test edilecek modeller
    models = ["autox", "sonnet-4-x", "sonnet-4-5-x"]
    
    # Token boyutları
    token_sizes = [2500, 5000, 15000, 40000, 60000]
    
    # Tüm sonuçları sakla
    all_cache_results = []
    all_rate_results = []
    
    # Her model için testleri çalıştır
    for model in models:
        print(f"\n{'='*80}")
        print(f"🔄 {model.upper()} MODELİ İÇİN TESTLER BAŞLIYOR")
        print(f"{'='*80}")
        
        # 1. Cache Testi (Farklı token boyutları)
        cache_result = tester.cache_test(model=model, token_sizes=token_sizes)
        all_cache_results.append(cache_result)
        
        if "error" not in cache_result:
            print(f"\n  📊 GENEL SONUÇLAR:")
            print(f"  ✅ Ortalama non-cache süresi: {cache_result['avg_non_cache_time']:.3f}s")
            print(f"  ✅ Ortalama cache süresi: {cache_result['avg_cache_time']:.3f}s")
            print(f"  {'✅' if cache_result['cache_working'] else '❌'} Cache çalışıyor: {cache_result['cache_working']}")
            print(f"  📈 Hız artışı: %{cache_result['speed_improvement']:.1f}")
            
            print(f"\n  📊 TOKEN BOYUTU BAZINDA SONUÇLAR:")
            for token_size, result in cache_result.get('results_by_token', {}).items():
                status = "✅" if result['cache_working'] else "❌"
                print(f"    {status} {token_size:,} token: Non-cache={result['avg_non_cache_time']:.3f}s, Cache={result['avg_cache_time']:.3f}s, Artış=%{result['speed_improvement']:.1f}")
        else:
            print(f"  ❌ Hata: {cache_result.get('error', 'Bilinmeyen hata')}")
        
        # 2. Rate Limit Testi (Farklı token boyutları - 60 istek/dakika)
        print(f"\n📍 RATE LİMİT TESTİ BAŞLIYOR (60 istek/dakika - ZORLU)...")
        rate_result = tester.rate_limit_test(model=model, token_sizes=token_sizes, requests_per_minute=60)
        all_rate_results.append(rate_result)
        
        print(f"\n  📊 GENEL SONUÇLAR:")
        print(f"  ✅ Başarılı istek: {rate_result['successful_requests']}")
        print(f"  ⚠️  Rate limited: {rate_result['rate_limited_requests']}")
        print(f"  ❌ Başarısız: {rate_result['failed_requests']}")
        print(f"  ⏱️  Timeout hatası: {rate_result['timeout_errors']}")
        print(f"  📊 Ortalama yanıt süresi: {rate_result['avg_response_time']:.3f}s")
        print(f"  📊 Min/Max yanıt süresi: {rate_result['min_response_time']:.3f}s / {rate_result['max_response_time']:.3f}s")
        print(f"  📊 Gerçek RPS: {rate_result['actual_rps']:.2f}")
        
        print(f"\n  📊 TOKEN BOYUTU BAZINDA SONUÇLAR:")
        for token_size, result in rate_result.get('results_by_token', {}).items():
            print(f"    📦 {token_size:,} token: Başarılı={result['successful_requests']}, Rate Lim={result['rate_limited_requests']}, Başarısız={result['failed_requests']}, Ort.Süre={result['avg_response_time']:.3f}s")
    
    # Özet rapor
    print(f"\n{'='*80}")
    print("📊 ÖZET RAPOR - CACHE TESTLERİ (BÜYÜK TOKEN BOYUTLARI)")
    print(f"{'='*80}")
    print(f"{'Model':<20} {'Non-Cache':<15} {'Cache':<15} {'Durum':<15} {'Hız Artışı':<15}")
    print("-" * 80)
    for result in all_cache_results:
        if "error" not in result:
            cache_status = "✅ ÇALIŞIYOR" if result['cache_working'] else "❌ ÇALIŞMIYOR"
            print(f"{result['model']:<20} {result['avg_non_cache_time']:<15.3f} {result['avg_cache_time']:<15.3f} {cache_status:<15} {result['speed_improvement']:<15.1f}%")
        else:
            print(f"{result['model']:<20} {'HATA':<15} {'HATA':<15} {'N/A':<15} {'N/A':<15}")
    
    # Token boyutu bazında detaylı rapor
    print(f"\n{'='*80}")
    print("📊 DETAYLI RAPOR - TOKEN BOYUTU BAZINDA CACHE TESTLERİ")
    print(f"{'='*80}")
    for result in all_cache_results:
        if "error" not in result and "results_by_token" in result:
            print(f"\n  🔹 {result['model'].upper()} Modeli:")
            print(f"  {'Token':<15} {'Non-Cache':<15} {'Cache':<15} {'Durum':<15} {'Hız Artışı':<15}")
            print("  " + "-" * 75)
            for token_size, token_result in result['results_by_token'].items():
                status = "✅ ÇALIŞIYOR" if token_result['cache_working'] else "❌ ÇALIŞMIYOR"
                print(f"  {str(token_size)+' token':<15} {token_result['avg_non_cache_time']:<15.3f} {token_result['avg_cache_time']:<15.3f} {status:<15} {token_result['speed_improvement']:<15.1f}%")
    
    print(f"\n{'='*80}")
    print("📊 ÖZET RAPOR - RATE LİMİT TESTLERİ (BÜYÜK TOKEN BOYUTLARI - 60 req/min)")
    print(f"{'='*80}")
    print(f"{'Model':<20} {'Başarılı':<12} {'Rate Lim':<12} {'Başarısız':<12} {'Timeout':<10} {'Ort.Süre':<12} {'RPS':<10}")
    print("-" * 80)
    for result in all_rate_results:
        print(f"{result['model']:<20} {result['successful_requests']:<12} {result['rate_limited_requests']:<12} {result['failed_requests']:<12} {result['timeout_errors']:<10} {result['avg_response_time']:<12.3f} {result['actual_rps']:<10.2f}")
    
    # Token boyutu bazında detaylı rapor
    print(f"\n{'='*80}")
    print("📊 DETAYLI RAPOR - TOKEN BOYUTU BAZINDA RATE LİMİT TESTLERİ")
    print(f"{'='*80}")
    for result in all_rate_results:
        if "results_by_token" in result:
            print(f"\n  🔹 {result['model'].upper()} Modeli:")
            print(f"  {'Token':<15} {'Başarılı':<12} {'Rate Lim':<12} {'Başarısız':<12} {'Timeout':<10} {'Ort.Süre':<12} {'RPS':<10}")
            print("  " + "-" * 85)
            for token_size, token_result in result['results_by_token'].items():
                print(f"  {str(token_size)+' token':<15} {token_result['successful_requests']:<12} {token_result['rate_limited_requests']:<12} {token_result['failed_requests']:<12} {token_result['timeout_errors']:<10} {token_result['avg_response_time']:<12.3f} {token_result['actual_rps']:<10.2f}")
    
    print("\n" + "=" * 80)
    print("✅ TÜM TESTLER TAMAMLANDI - BÜYÜK TOKEN BOYUTLARI İLE ZORLU TEST")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
