#!/usr/bin/env python3
"""
API Fiyatlandırma ve Limit Hesaplayıcısı
50 kullanıcı x 800 TL/ay için optimal limitler
"""

from dataclasses import dataclass
from typing import Dict, Any
import json

@dataclass
class ModelPricing:
    """Model fiyatlandırması (USD/1M token)"""
    input_price: float
    output_price: float
    name: str

@dataclass
class UsageLimits:
    """Kullanım limitleri"""
    monthly_requests: int
    daily_requests: int
    hourly_requests: int
    minute_requests: int
    monthly_tokens: int
    daily_tokens: int

class PricingCalculator:
    """Fiyatlandırma hesaplayıcısı"""
    
    def __init__(self):
        # Güncel model fiyatları (USD/1M token)
        self.model_prices = {
            "gpt-4": ModelPricing(30.0, 60.0, "GPT-4"),
            "gpt-4-turbo": ModelPricing(10.0, 30.0, "GPT-4 Turbo"),
            "gpt-3.5-turbo": ModelPricing(0.5, 1.5, "GPT-3.5 Turbo"),
            "claude-3-opus": ModelPricing(15.0, 75.0, "Claude-3 Opus"),
            "claude-3-sonnet": ModelPricing(3.0, 15.0, "Claude-3 Sonnet"),
            "claude-3-haiku": ModelPricing(0.25, 1.25, "Claude-3 Haiku"),
            "claude-4-haiku": ModelPricing(1.0, 5.0, "Claude-4 Haiku (Tahmini)"),
            "claude-4-sonnet": ModelPricing(15.0, 75.0, "Claude-4 Sonnet (Tahmini)"),
            "gemini-pro": ModelPricing(0.5, 1.5, "Gemini Pro"),
            "mistral-large": ModelPricing(4.0, 12.0, "Mistral Large")
        }
        
        # USD/TRY kuru (güncel)
        self.usd_try_rate = 34.5
        
        # Kullanıcı bilgileri
        self.users_count = 50
        self.monthly_revenue_per_user = 800  # TL
        self.total_monthly_revenue = self.users_count * self.monthly_revenue_per_user  # 40,000 TL
        self.total_monthly_revenue_usd = self.total_monthly_revenue / self.usd_try_rate  # ~1,160 USD
        
        # Maliyet marjı (%30 maliyet, %70 kar)
        self.cost_margin = 0.30
        self.monthly_budget_usd = self.total_monthly_revenue_usd * self.cost_margin  # ~348 USD
    
    def calculate_token_limits(self, model_mix: Dict[str, float]) -> Dict[str, Any]:
        """Token limitlerini hesapla"""
        
        # Ortalama token maliyeti hesapla (input:output = 1:2 oranında)
        weighted_cost = 0
        for model, percentage in model_mix.items():
            if model in self.model_prices:
                price = self.model_prices[model]
                avg_cost = (price.input_price + price.output_price * 2) / 3  # 1:2 oranı
                weighted_cost += avg_cost * percentage
        
        # Aylık toplam token limiti
        monthly_total_tokens = int((self.monthly_budget_usd * 1_000_000) / weighted_cost)
        
        # Kullanıcı başına limitler
        monthly_tokens_per_user = monthly_total_tokens // self.users_count
        daily_tokens_per_user = monthly_tokens_per_user // 30
        hourly_tokens_per_user = daily_tokens_per_user // 24
        
        # İstek limitleri (ortalama 500 token/istek varsayımı)
        avg_tokens_per_request = 500
        monthly_requests_per_user = monthly_tokens_per_user // avg_tokens_per_request
        daily_requests_per_user = daily_tokens_per_user // avg_tokens_per_request
        hourly_requests_per_user = hourly_tokens_per_user // avg_tokens_per_request
        minute_requests_per_user = max(1, hourly_requests_per_user // 60)
        
        return {
            "budget_analysis": {
                "total_monthly_revenue_tl": self.total_monthly_revenue,
                "total_monthly_revenue_usd": self.total_monthly_revenue_usd,
                "monthly_budget_usd": self.monthly_budget_usd,
                "cost_margin_percent": self.cost_margin * 100,
                "weighted_avg_cost_per_1m_tokens": weighted_cost
            },
            "token_limits": {
                "monthly_total_tokens": monthly_total_tokens,
                "monthly_tokens_per_user": monthly_tokens_per_user,
                "daily_tokens_per_user": daily_tokens_per_user,
                "hourly_tokens_per_user": hourly_tokens_per_user
            },
            "request_limits": {
                "monthly_requests_per_user": monthly_requests_per_user,
                "daily_requests_per_user": daily_requests_per_user,
                "hourly_requests_per_user": hourly_requests_per_user,
                "minute_requests_per_user": minute_requests_per_user
            },
            "rate_limits": {
                "requests_per_minute": minute_requests_per_user,
                "requests_per_hour": hourly_requests_per_user,
                "requests_per_day": daily_requests_per_user,
                "tokens_per_minute": hourly_tokens_per_user // 60,
                "tokens_per_hour": hourly_tokens_per_user,
                "tokens_per_day": daily_tokens_per_user
            }
        }
    
    def generate_scenarios(self) -> Dict[str, Any]:
        """Farklı senaryolar için hesaplamalar"""
        
        scenarios = {
            "conservative": {
                "name": "Muhafazakar (Çoğunlukla ucuz modeller)",
                "model_mix": {
                    "gpt-3.5-turbo": 0.4,
                    "claude-3-haiku": 0.3,
                    "gemini-pro": 0.2,
                    "claude-3-sonnet": 0.1
                }
            },
            "balanced": {
                "name": "Dengeli (Karışık kullanım)",
                "model_mix": {
                    "gpt-3.5-turbo": 0.3,
                    "claude-3-haiku": 0.25,
                    "claude-3-sonnet": 0.2,
                    "gpt-4-turbo": 0.15,
                    "gemini-pro": 0.1
                }
            },
            "premium": {
                "name": "Premium (Pahalı modeller ağırlıklı)",
                "model_mix": {
                    "claude-4-sonnet": 0.3,
                    "gpt-4": 0.25,
                    "claude-3-opus": 0.2,
                    "gpt-4-turbo": 0.15,
                    "claude-3-sonnet": 0.1
                }
            },
            "current_config": {
                "name": "Mevcut Konfigürasyon (Claude ağırlıklı)",
                "model_mix": {
                    "claude-4-haiku": 0.4,  # autox
                    "claude-4-sonnet": 0.6   # sonnet-4-x ve sonnet-4-5-x
                }
            }
        }
        
        results = {}
        for scenario_name, scenario in scenarios.items():
            results[scenario_name] = {
                "description": scenario["name"],
                "model_mix": scenario["model_mix"],
                **self.calculate_token_limits(scenario["model_mix"])
            }
        
        return results
    
    def generate_litellm_config(self, scenario_limits: Dict[str, Any]) -> Dict[str, Any]:
        """LiteLLM konfigürasyonu üret"""
        
        limits = scenario_limits["rate_limits"]
        
        return {
            "general_settings": {
                "master_key": "os.environ/LITELLM_MASTER_KEY",
                "database_url": "os.environ/DATABASE_URL",
                "ui_username": "os.environ/UI_USERNAME",
                "ui_password": "os.environ/UI_PASSWORD"
            },
            "litellm_settings": {
                "success_callback": ["langfuse"],
                "failure_callback": ["langfuse"],
                "cache": True,
                "cache_params": {
                    "type": "redis",
                    "host": "os.environ/REDIS_HOST",
                    "port": "os.environ/REDIS_PORT",
                    "password": "os.environ/REDIS_PASSWORD"
                },
                "default_user_max_budget": self.monthly_revenue_per_user / self.usd_try_rate,
                "default_user_budget_duration": "30d"
            },
            "router_settings": {
                "routing_strategy": "least-busy",
                "enable_pre_call_check": True,
                "allowed_fails": 2,
                "cooldown_time": 30,
                "num_retries": 3
            },
            "user_rate_limits": {
                "default_user_tpm_limit": limits["tokens_per_minute"],
                "default_user_rpm_limit": limits["requests_per_minute"],
                "default_user_max_requests_per_day": limits["requests_per_day"],
                "default_user_max_tokens_per_day": limits["tokens_per_day"]
            }
        }

def main():
    """Ana fonksiyon"""
    calculator = PricingCalculator()
    
    print("=" * 80)
    print("💰 API FİYATLANDIRMA VE LİMİT HESAPLAYICISI")
    print("=" * 80)
    print(f"👥 Kullanıcı sayısı: {calculator.users_count}")
    print(f"💵 Kullanıcı başına aylık ücret: {calculator.monthly_revenue_per_user} TL")
    print(f"💰 Toplam aylık gelir: {calculator.total_monthly_revenue:,} TL")
    print(f"💸 Aylık bütçe (USD): ${calculator.monthly_budget_usd:.0f}")
    print(f"📊 Maliyet marjı: %{calculator.cost_margin * 100}")
    
    # Senaryoları hesapla
    scenarios = calculator.generate_scenarios()
    
    print("\n" + "=" * 80)
    print("📋 SENARYO ANALİZLERİ")
    print("=" * 80)
    
    for scenario_name, scenario in scenarios.items():
        print(f"\n🎯 {scenario['description'].upper()}")
        print("-" * 60)
        
        # Model karışımı
        print("📊 Model Karışımı:")
        for model, percentage in scenario['model_mix'].items():
            model_name = calculator.model_prices.get(model, type('obj', (object,), {'name': model})).name
            print(f"  • {model_name}: %{percentage * 100:.0f}")
        
        # Limitler
        limits = scenario['rate_limits']
        print(f"\n⚡ ÖNERİLEN LİMİTLER:")
        print(f"  • Dakikada istek: {limits['requests_per_minute']}")
        print(f"  • Saatte istek: {limits['requests_per_hour']}")
        print(f"  • Günde istek: {limits['requests_per_day']}")
        print(f"  • Dakikada token: {limits['tokens_per_minute']:,}")
        print(f"  • Saatte token: {limits['tokens_per_hour']:,}")
        print(f"  • Günde token: {limits['tokens_per_day']:,}")
        
        # Bütçe analizi
        budget = scenario['budget_analysis']
        print(f"\n💰 BÜTÇE ANALİZİ:")
        print(f"  • Ortalama maliyet: ${budget['weighted_avg_cost_per_1m_tokens']:.2f}/1M token")
        print(f"  • Aylık toplam token: {scenario['token_limits']['monthly_total_tokens']:,}")
        print(f"  • Kullanıcı başına aylık token: {scenario['token_limits']['monthly_tokens_per_user']:,}")
    
    # En uygun senaryoyu öner
    print("\n" + "=" * 80)
    print("🎯 ÖNERİ: BALANCED SENARYOSU")
    print("=" * 80)
    
    balanced = scenarios['balanced']
    limits = balanced['rate_limits']
    
    print("Bu limitlerle kullanıcılarınız:")
    print(f"✅ Dakikada {limits['requests_per_minute']} istek gönderebilir")
    print(f"✅ Günde {limits['requests_per_day']} istek hakkı olur")
    print(f"✅ Aylık {balanced['token_limits']['monthly_tokens_per_user']:,} token kullanabilir")
    print(f"✅ Rate limit takılmadan rahat çalışabilir")
    
    # LiteLLM config üret
    config = calculator.generate_litellm_config(balanced)
    
    print(f"\n📝 LiteLLM Config Dosyası:")
    print("Aşağıdaki ayarları config.yaml dosyanıza ekleyin:")
    print("-" * 60)
    print(json.dumps(config, indent=2))

if __name__ == "__main__":
    main()
