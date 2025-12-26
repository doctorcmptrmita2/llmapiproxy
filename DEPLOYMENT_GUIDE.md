# 🚀 API Satışı Deployment Rehberi

## 📊 Hızlı Özet

**50 Kullanıcı × 800 TL/ay = 40,000 TL/ay Gelir**

### ✅ Önerilen Limitler (Balanced Senaryo)

| Metrik | Değer | Açıklama |
|--------|-------|----------|
| **Dakikada İstek** | 2 | Rahat çalışma için yeterli |
| **Saatte İstek** | 120 | Günde 2,880 istek kapasitesi |
| **Günde İstek** | 100 | Ortalama kullanıcı ihtiyacı |
| **Aylık İstek** | 3,000 | Kullanıcı başına |
| **Dakikada Token** | 833 | Ortalama 400 token/istek |
| **Günde Token** | 50,000 | Yeterli ve ekonomik |
| **Aylık Token** | 1,500,000 | Kullanıcı başına |
| **Aylık Bütçe** | $348 | 50 kullanıcı için toplam |

---

## 🧪 Test Mekanizması

### 1. Temel Test (test-cache.py)
```bash
python test-cache.py
```
- Redis cache performansını test eder
- İlk istek vs cache hit karşılaştırması
- Beklenen: 2. istek 0.5s altında

### 2. Kapsamlı Test Suite (test-suite.py)
```bash
python test-suite.py
```

**Testler:**
- ✅ Cache performans testi
- ✅ Yük testi (10 kullanıcı × 5 istek)
- ✅ Rate limit testi (30 istek/dakika)

**Çıktı Örneği:**
```
💾 CACHE SONUÇLARI:
  İlk istek: 2.345s
  İkinci istek: 0.123s
  Cache çalışıyor: ✅
  Hız artışı: %94.8

🚀 YÜK TESTİ SONUÇLARI:
  Toplam istek: 50
  Başarılı: 50
  Başarı oranı: %100.0
  Ortalama süre: 1.234s
  Saniyede istek: 8.1
```

### 3. Fiyatlandırma Hesaplayıcı (pricing-calculator.py)
```bash
python pricing-calculator.py
```

**Çıktı:**
- 4 farklı senaryo analizi
- Model karışımı önerileri
- LiteLLM config önerileri
- Bütçe analizi

### 4. Monitoring Dashboard (monitoring-dashboard.py)
```bash
python monitoring-dashboard.py
```

**Özellikler:**
- Kullanıcı istatistikleri
- Model kullanım analizi
- Limit kontrol sistemi
- Detaylı raporlama

---

## 🔧 Kurulum Adımları

### 1. Konfigürasyon Dosyasını Güncelle
```bash
# Mevcut config.yaml yerine production-config.yaml kullan
cp production-config.yaml config.yaml
```

### 2. Environment Variables Ayarla
```bash
# .env dosyasına ekle
LITELLM_MASTER_KEY=sk-your-master-key
DATABASE_URL=postgresql://user:pass@localhost/litellm
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# API Keys
ANTHROPIC_KEY_HAIKU=sk-ant-...
ANTHROPIC_KEY_SONNETX=sk-ant-...
ANTHROPIC_KEY_SONNET=sk-ant-...
OPENAI_API_KEY=sk-...

# Monitoring
MONITORING_WEBHOOK_URL=https://your-webhook.com
ADMIN_EMAIL=admin@example.com
```

### 3. Docker Compose Başlat
```bash
docker-compose up -d
```

### 4. Testleri Çalıştır
```bash
# Sırasıyla çalıştır
python test-cache.py
python test-suite.py
python pricing-calculator.py
python monitoring-dashboard.py
```

---

## 📈 Kullanıcı Yönetimi

### Kullanıcı Oluşturma
```bash
curl -X POST http://localhost:4000/user/new \
  -H "Authorization: Bearer sk-your-master-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "user_email": "user@example.com",
    "max_budget": 23.19,
    "budget_duration": "30d"
  }'
```

### Kullanıcı Limitlerini Ayarla
```bash
curl -X POST http://localhost:4000/user/update \
  -H "Authorization: Bearer sk-your-master-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "tpm_limit": 833,
    "rpm_limit": 2,
    "max_requests_per_day": 100,
    "max_tokens_per_day": 50000
  }'
```

### Kullanıcı Grubu Oluşturma (Premium)
```bash
curl -X POST http://localhost:4000/user/update \
  -H "Authorization: Bearer sk-your-master-key" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "premium_user_001",
    "max_budget": 46.38,
    "tpm_limit": 1666,
    "rpm_limit": 4,
    "max_requests_per_day": 200,
    "max_tokens_per_day": 100000
  }'
```

---

## 💰 Maliyet Analizi

### Aylık Bütçe Dağılımı
```
Toplam Gelir: 40,000 TL (~$1,160)
Maliyet Marjı: %30 = $348/ay

Model Kullanımı:
├─ Claude-4 Haiku (autox): 40% = $139.20
├─ Claude-4 Sonnet: 30% = $104.40
└─ Claude-4.5 Sonnet: 30% = $104.40

Aylık Token Kapasitesi: ~115M token
Kullanıcı Başına: ~2.3M token
```

### Maliyet Tasarrufu Stratejileri
1. **Cache Kullanımı**: %50-70 maliyet tasarrufu
2. **Haiku Modeli**: Basit görevler için %90 tasarrufu
3. **Fallback Stratejisi**: Pahalı model başarısız olursa ucuz model kullan
4. **Batch Processing**: Toplu istekler için indirim

---

## ⚡ Rate Limiting Detayları

### Kullanıcı Başına Limitler
```
Dakikada:
  - 2 istek (RPM)
  - 833 token (TPM)

Saatte:
  - 120 istek
  - 50,000 token

Günde:
  - 100 istek
  - 50,000 token

Ayda:
  - 3,000 istek
  - 1,500,000 token
```

### Global Limitler (Tüm Kullanıcılar)
```
autox (Claude-4 Haiku):
  - 800 istek/dakika
  - 400,000 token/dakika

sonnet-4-x:
  - 480 istek/dakika
  - 240,000 token/dakika

sonnet-4-5-x:
  - 480 istek/dakika
  - 240,000 token/dakika
```

---

## 🔍 Monitoring ve Raporlama

### Günlük Rapor Örneği
```
📊 GENEL ÖZET (Son 30 Gün)
├─ Toplam kullanıcı: 50
├─ Toplam istek: 150,000
├─ Toplam token: 75,000,000
├─ Toplam maliyet: $348.00
├─ Ortalama yanıt süresi: 1.234s
├─ Başarı oranı: %99.5
├─ Kullanıcı başına maliyet: $6.96
└─ Kullanıcı başına istek: 3,000

🏆 EN AKTİF KULLANICILAR
1. user_001: 5,000 istek, $70.00
2. user_002: 4,500 istek, $63.00
3. user_003: 4,200 istek, $58.80
```

### Limit Aşımı Uyarıları
```
⚠️ LIMIT AŞILDI
user_001:
  ├─ Günlük istek: 150/100 ❌
  ├─ Aylık token: 1,600,000/1,500,000 ❌
  └─ Maliyet: $70.00/$23.19 ❌
```

---

## 🛡️ Güvenlik Kontrol Listesi

- [ ] Master key güvenli şekilde saklanıyor
- [ ] Database şifreli bağlantı kullanıyor
- [ ] Redis şifre korumalı
- [ ] API keys environment variables'da
- [ ] CORS ayarları konfigüre edildi
- [ ] Rate limiting aktif
- [ ] Monitoring webhook ayarlandı
- [ ] Backup stratejisi tanımlandı
- [ ] SSL/TLS sertifikası kurulu
- [ ] Firewall kuralları ayarlandı

---

## 🚨 Sorun Giderme

### Cache Çalışmıyor
```bash
# Redis bağlantısını kontrol et
redis-cli ping
# Çıktı: PONG

# Redis config kontrol et
redis-cli CONFIG GET maxmemory
```

### Rate Limit Çok Katı
```bash
# Limitleri artır (production-config.yaml)
default_user_rpm_limit: 3  # 2'den 3'e
default_user_tpm_limit: 1250  # 833'ten 1250'ye
```

### Yüksek Maliyet
```bash
# Haiku modelinin ağırlığını artır
autox:
  weight: 50  # 40'tan 50'ye
sonnet-4-x:
  weight: 25  # 30'dan 25'e
```

---

## 📞 Destek ve İletişim

- **Monitoring**: `monitoring-dashboard.py` günlük çalıştır
- **Raporlar**: `ADMIN_EMAIL` adresine otomatik gönderilir
- **Uyarılar**: Webhook URL'sine POST istekleri gönderilir
- **Loglar**: `docker logs litellm-proxy` ile kontrol et

---

## 📝 Notlar

- Limitler kullanıcı deneyimini bozmayacak şekilde ayarlanmıştır
- Cache kullanımı maliyeti %50-70 azaltır
- Fallback stratejisi hizmet sürekliliğini sağlar
- Monitoring sistemi otomatik uyarılar gönderir
- Aylık bütçe %30 maliyet marjı ile hesaplanmıştır
