#!/usr/bin/env python3
"""
API Monitoring Dashboard
Kullanıcı kullanımını izleme ve raporlama sistemi
"""

import asyncio
import aiohttp
import sqlite3
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import json
import time

@dataclass
class UsageRecord:
    """Kullanım kaydı"""
    user_id: str
    timestamp: datetime
    model: str
    tokens_used: int
    request_count: int
    response_time: float
    success: bool
    cost_usd: float

@dataclass
class UserStats:
    """Kullanıcı istatistikleri"""
    user_id: str
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_response_time: float
    success_rate: float
    last_activity: datetime
    daily_requests: int
    daily_tokens: int
    monthly_requests: int
    monthly_tokens: int

class UsageMonitor:
    """Kullanım izleme sınıfı"""
    
    def __init__(self, db_path: str = "usage_monitor.db"):
        self.db_path = db_path
        self.init_database()
        
        # Model maliyetleri (USD/1M token)
        self.model_costs = {
            "gpt-4": 45.0,  # ortalama input/output
            "gpt-4-turbo": 20.0,
            "gpt-3.5-turbo": 1.0,
            "claude-3-opus": 45.0,
            "claude-3-sonnet": 9.0,
            "claude-3-haiku": 0.75,
            "claude-4-haiku": 3.0,
            "claude-4-sonnet": 45.0,
            "autox": 3.0,  # Claude-4 Haiku tahmini
            "sonnet-4-x": 45.0,  # Claude-4 Sonnet tahmini
            "sonnet-4-5-x": 45.0
        }
    
    def init_database(self):
        """Veritabanını başlat"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                model TEXT NOT NULL,
                tokens_used INTEGER NOT NULL,
                request_count INTEGER DEFAULT 1,
                response_time REAL NOT NULL,
                success BOOLEAN NOT NULL,
                cost_usd REAL NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_timestamp 
            ON usage_logs(user_id, timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON usage_logs(timestamp)
        ''')
        
        conn.commit()
        conn.close()
    
    def log_usage(self, record: UsageRecord):
        """Kullanım kaydı ekle"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO usage_logs 
            (user_id, timestamp, model, tokens_used, request_count, 
             response_time, success, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.user_id,
            record.timestamp,
            record.model,
            record.tokens_used,
            record.request_count,
            record.response_time,
            record.success,
            record.cost_usd
        ))
        
        conn.commit()
        conn.close()
    
    def get_user_stats(self, user_id: str, days: int = 30) -> Optional[UserStats]:
        """Kullanıcı istatistiklerini getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Tarih aralıkları
        now = datetime.now()
        month_ago = now - timedelta(days=days)
        day_ago = now - timedelta(days=1)
        
        # Toplam istatistikler
        cursor.execute('''
            SELECT 
                COUNT(*) as total_requests,
                SUM(tokens_used) as total_tokens,
                SUM(cost_usd) as total_cost,
                AVG(response_time) as avg_response_time,
                AVG(CASE WHEN success THEN 1.0 ELSE 0.0 END) as success_rate,
                MAX(timestamp) as last_activity
            FROM usage_logs 
            WHERE user_id = ? AND timestamp >= ?
        ''', (user_id, month_ago))
        
        result = cursor.fetchone()
        if not result or result[0] == 0:
            conn.close()
            return None
        
        # Günlük istatistikler
        cursor.execute('''
            SELECT 
                COUNT(*) as daily_requests,
                SUM(tokens_used) as daily_tokens
            FROM usage_logs 
            WHERE user_id = ? AND timestamp >= ?
        ''', (user_id, day_ago))
        
        daily_result = cursor.fetchone()
        
        # Aylık istatistikler
        cursor.execute('''
            SELECT 
                COUNT(*) as monthly_requests,
                SUM(tokens_used) as monthly_tokens
            FROM usage_logs 
            WHERE user_id = ? AND timestamp >= ?
        ''', (user_id, month_ago))
        
        monthly_result = cursor.fetchone()
        
        conn.close()
        
        return UserStats(
            user_id=user_id,
            total_requests=result[0] or 0,
            total_tokens=result[1] or 0,
            total_cost=result[2] or 0.0,
            avg_response_time=result[3] or 0.0,
            success_rate=(result[4] or 0.0) * 100,
            last_activity=datetime.fromisoformat(result[5]) if result[5] else now,
            daily_requests=daily_result[0] or 0,
            daily_tokens=daily_result[1] or 0,
            monthly_requests=monthly_result[0] or 0,
            monthly_tokens=monthly_result[1] or 0
        )
    
    def get_all_users_stats(self, days: int = 30) -> List[UserStats]:
        """Tüm kullanıcıların istatistiklerini getir"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Aktif kullanıcıları bul
        cursor.execute('''
            SELECT DISTINCT user_id 
            FROM usage_logs 
            WHERE timestamp >= ?
        ''', (datetime.now() - timedelta(days=days),))
        
        user_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        stats = []
        for user_id in user_ids:
            user_stats = self.get_user_stats(user_id, days)
            if user_stats:
                stats.append(user_stats)
        
        return sorted(stats, key=lambda x: x.total_cost, reverse=True)
    
    def generate_report(self, days: int = 30) -> Dict[str, Any]:
        """Detaylı rapor oluştur"""
        all_stats = self.get_all_users_stats(days)
        
        if not all_stats:
            return {"error": "Veri bulunamadı"}
        
        # Toplam istatistikler
        total_users = len(all_stats)
        total_requests = sum(s.total_requests for s in all_stats)
        total_tokens = sum(s.total_tokens for s in all_stats)
        total_cost = sum(s.total_cost for s in all_stats)
        avg_response_time = sum(s.avg_response_time for s in all_stats) / total_users
        avg_success_rate = sum(s.success_rate for s in all_stats) / total_users
        
        # En aktif kullanıcılar
        top_users_by_requests = sorted(all_stats, key=lambda x: x.total_requests, reverse=True)[:10]
        top_users_by_cost = sorted(all_stats, key=lambda x: x.total_cost, reverse=True)[:10]
        
        # Model kullanım istatistikleri
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                model,
                COUNT(*) as request_count,
                SUM(tokens_used) as total_tokens,
                SUM(cost_usd) as total_cost
            FROM usage_logs 
            WHERE timestamp >= ?
            GROUP BY model
            ORDER BY total_cost DESC
        ''', (datetime.now() - timedelta(days=days),))
        
        model_stats = cursor.fetchall()
        conn.close()
        
        return {
            "report_period_days": days,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_users": total_users,
                "total_requests": total_requests,
                "total_tokens": total_tokens,
                "total_cost_usd": round(total_cost, 2),
                "avg_response_time": round(avg_response_time, 3),
                "avg_success_rate": round(avg_success_rate, 1),
                "cost_per_user": round(total_cost / total_users, 2) if total_users > 0 else 0,
                "requests_per_user": round(total_requests / total_users, 0) if total_users > 0 else 0
            },
            "top_users_by_requests": [
                {
                    "user_id": s.user_id,
                    "requests": s.total_requests,
                    "tokens": s.total_tokens,
                    "cost": round(s.total_cost, 2)
                } for s in top_users_by_requests
            ],
            "top_users_by_cost": [
                {
                    "user_id": s.user_id,
                    "cost": round(s.total_cost, 2),
                    "requests": s.total_requests,
                    "tokens": s.total_tokens
                } for s in top_users_by_cost
            ],
            "model_usage": [
                {
                    "model": row[0],
                    "requests": row[1],
                    "tokens": row[2],
                    "cost": round(row[3], 2),
                    "avg_cost_per_request": round(row[3] / row[1], 4) if row[1] > 0 else 0
                } for row in model_stats
            ]
        }
    
    def check_user_limits(self, user_id: str, limits: Dict[str, int]) -> Dict[str, Any]:
        """Kullanıcı limitlerini kontrol et"""
        stats = self.get_user_stats(user_id, 30)
        
        if not stats:
            return {
                "user_id": user_id,
                "within_limits": True,
                "usage": {},
                "limits": limits
            }
        
        # Limit kontrolü
        daily_requests_ok = stats.daily_requests <= limits.get("daily_requests", float('inf'))
        daily_tokens_ok = stats.daily_tokens <= limits.get("daily_tokens", float('inf'))
        monthly_requests_ok = stats.monthly_requests <= limits.get("monthly_requests", float('inf'))
        monthly_tokens_ok = stats.monthly_tokens <= limits.get("monthly_tokens", float('inf'))
        
        within_limits = all([daily_requests_ok, daily_tokens_ok, monthly_requests_ok, monthly_tokens_ok])
        
        return {
            "user_id": user_id,
            "within_limits": within_limits,
            "usage": {
                "daily_requests": stats.daily_requests,
                "daily_tokens": stats.daily_tokens,
                "monthly_requests": stats.monthly_requests,
                "monthly_tokens": stats.monthly_tokens,
                "total_cost": round(stats.total_cost, 2)
            },
            "limits": limits,
            "limit_status": {
                "daily_requests": "OK" if daily_requests_ok else "EXCEEDED",
                "daily_tokens": "OK" if daily_tokens_ok else "EXCEEDED",
                "monthly_requests": "OK" if monthly_requests_ok else "EXCEEDED",
                "monthly_tokens": "OK" if monthly_tokens_ok else "EXCEEDED"
            }
        }

def simulate_usage_data():
    """Test için örnek kullanım verisi oluştur"""
    monitor = UsageMonitor()
    
    # 10 test kullanıcısı için 30 günlük veri
    users = [f"user_{i:03d}" for i in range(1, 11)]
    models = ["autox", "sonnet-4-x", "sonnet-4-5-x"]
    
    print("📊 Test verisi oluşturuluyor...")
    
    for day in range(30):
        date = datetime.now() - timedelta(days=day)
        
        for user in users:
            # Her kullanıcı günde 5-50 istek yapar
            daily_requests = __import__('random').randint(5, 50)
            
            for _ in range(daily_requests):
                model = __import__('random').choice(models)
                tokens = __import__('random').randint(100, 2000)
                response_time = __import__('random').uniform(0.5, 5.0)
                success = __import__('random').random() > 0.05  # %95 başarı oranı
                
                cost = (tokens / 1_000_000) * monitor.model_costs.get(model, 10.0)
                
                record = UsageRecord(
                    user_id=user,
                    timestamp=date,
                    model=model,
                    tokens_used=tokens,
                    request_count=1,
                    response_time=response_time,
                    success=success,
                    cost_usd=cost
                )
                
                monitor.log_usage(record)
    
    print("✅ Test verisi oluşturuldu!")
    return monitor

def main():
    """Ana fonksiyon"""
    print("=" * 80)
    print("📊 API MONITORING DASHBOARD")
    print("=" * 80)
    
    # Test verisi oluştur
    monitor = simulate_usage_data()
    
    # Rapor oluştur
    report = monitor.generate_report(30)
    
    print("\n📋 GENEL ÖZET (Son 30 Gün)")
    print("-" * 60)
    summary = report["summary"]
    print(f"👥 Toplam kullanıcı: {summary['total_users']}")
    print(f"📊 Toplam istek: {summary['total_requests']:,}")
    print(f"🎯 Toplam token: {summary['total_tokens']:,}")
    print(f"💰 Toplam maliyet: ${summary['total_cost_usd']:.2f}")
    print(f"⚡ Ortalama yanıt süresi: {summary['avg_response_time']:.3f}s")
    print(f"✅ Başarı oranı: %{summary['avg_success_rate']:.1f}")
    print(f"💵 Kullanıcı başına maliyet: ${summary['cost_per_user']:.2f}")
    print(f"📈 Kullanıcı başına istek: {summary['requests_per_user']}")
    
    print("\n🏆 EN AKTİF KULLANICILAR (İstek Sayısına Göre)")
    print("-" * 60)
    for i, user in enumerate(report["top_users_by_requests"][:5], 1):
        print(f"{i}. {user['user_id']}: {user['requests']:,} istek, ${user['cost']:.2f}")
    
    print("\n💸 EN YÜKSEK MALİYETLİ KULLANICILAR")
    print("-" * 60)
    for i, user in enumerate(report["top_users_by_cost"][:5], 1):
        print(f"{i}. {user['user_id']}: ${user['cost']:.2f}, {user['requests']:,} istek")
    
    print("\n🤖 MODEL KULLANIM İSTATİSTİKLERİ")
    print("-" * 60)
    for model in report["model_usage"]:
        print(f"• {model['model']}: {model['requests']:,} istek, ${model['cost']:.2f}")
    
    # Örnek kullanıcı limit kontrolü
    print("\n⚡ ÖRNEK LİMİT KONTROLÜ")
    print("-" * 60)
    
    # Balanced senaryodan limitler (önceki hesaplamadan)
    limits = {
        "daily_requests": 100,
        "daily_tokens": 50000,
        "monthly_requests": 3000,
        "monthly_tokens": 1500000
    }
    
    # İlk 3 kullanıcıyı kontrol et
    for user_id in ["user_001", "user_002", "user_003"]:
        limit_check = monitor.check_user_limits(user_id, limits)
        status = "✅ OK" if limit_check["within_limits"] else "❌ LIMIT AŞILDI"
        usage = limit_check["usage"]
        
        print(f"\n{user_id}: {status}")
        print(f"  Günlük: {usage['daily_requests']}/{limits['daily_requests']} istek")
        print(f"  Aylık: {usage['monthly_requests']}/{limits['monthly_requests']} istek")
        print(f"  Maliyet: ${usage['total_cost']:.2f}")

if __name__ == "__main__":
    main()
