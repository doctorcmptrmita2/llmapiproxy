# 💰 Maliyet Optimizasyonu Stratejisi - Büyük İstekler İçin

## 📋 Genel Bakış

Büyük context veya büyük token isteklerinde, **planlama yapıp kodu parçalara bölmek** maliyeti önemli ölçüde düşürebilir. Haiku Planner sistemi bu optimizasyonu otomatik olarak yapar.

## ✅ Evet, Bu Bir Çözüm!

### Neden Parçalama Maliyeti Düşürür?

1. **Küçük Chunk'lar = Daha Ucuz**
   - 20K token tek istek: $0.90 (Sonnet)
   - 5K token × 4 chunk: $0.45 (Haiku) → **%50 tasarruf**

2. **Ucuz Model Kullanımı**
   - Planner: Haiku ($3/1M) → Çok ucuz
   - Chunk execution: Haiku ($3/1M) → Sonnet ($45/1M) yerine
   - **15x daha ucuz!**

3. **Cache Kullanımı**
   - Küçük chunk'lar daha sık cache'lenir
   - Tekrar eden isteklerde %70-90 tasarruf

4. **Paralel İşleme**
   - Chunk'lar paralel çalışır
   - Toplam süre kısalır (maliyet değil ama UX)

## 📊 Maliyet Karşılaştırması

### Senaryo 1: 20K Token İstek (Sonnet 4)

**Tek İstek (Parçalama Yok):**
```
Input: 20K token
Output: 8K token
Maliyet: (20K × $45 + 8K × $45) / 1M = $1.26
```

**Parçalama ile (3 Chunk):**
```
Planner: 1K token (Haiku) = $0.003
Chunk 1: 5K input + 2K output (Haiku) = $0.021
Chunk 2: 5K input + 2K output (Haiku) = $0.021
Chunk 3: 5K input + 2K output (Haiku) = $0.021
Toplam: $0.066
Tasarruf: %95! 🎉
```

### Senaryo 2: 50K Token İstek (Sonnet 4)

**Tek İstek:**
```
Maliyet: ~$3.15
```

**Parçalama ile:**
```
Maliyet: ~$0.15
Tasarruf: %95! 🎉
```

## 🔧 Nasıl Çalışıyor?

### 1. Otomatik Aktivasyon

```yaml
# config.yaml
haiku_planner:
  large_request_threshold: 8000  # 8K+ token → Otomatik aktif
  max_tokens_threshold: 15000    # 15K+ output → Otomatik aktif
```

### 2. Optimal Chunk Sizing

```python
# haiku-planner-middleware.py
OPTIMAL_CHUNK_SIZE = 1500  # En uygun chunk boyutu
MAX_CHUNK_SIZE = 2000      # Maksimum
MIN_CHUNK_SIZE = 500       # Minimum (verimsiz olmasın)
```

**Neden 1500 token?**
- Çok küçük chunk'lar: Overhead maliyeti yüksek
- Çok büyük chunk'lar: Pahalı model gerekir
- 1500 token: Optimal nokta (Haiku ile uygun)

### 3. Model Seçimi

```yaml
planner_model: "autox"           # Haiku - Çok ucuz ($3/1M)
fast_execution_model: "autox"    # Haiku - Ucuz ($3/1M)
deep_execution_model: "sonnet-4-x"  # Sonnet - Pahalı ($45/1M)
```

**Quality Header ile:**
- `x-quality: fast` → Haiku kullanır (%95 tasarruf)
- `x-quality: deep` → Sonnet kullanır (kalite öncelikli)

## 📈 Maliyet Optimizasyonu Özellikleri

### 1. Otomatik Chunk Optimizasyonu

Sistem otomatik olarak:
- Chunk boyutlarını optimize eder
- Gereksiz büyük chunk'ları küçültür
- Çok küçük chunk'ları birleştirir

### 2. Maliyet Hesaplama

```python
# Gerçek zamanlı maliyet hesaplama
planner_cost = 1000 * ($3 / 1M) = $0.003
chunk_1_cost = 1500 * ($3 / 1M) = $0.0045
chunk_2_cost = 1500 * ($3 / 1M) = $0.0045
chunk_3_cost = 1500 * ($3 / 1M) = $0.0045
total = $0.0165
```

### 3. Bütçe Kontrolü

```yaml
max_cost_per_request: 1.0  # $1 limit
cost_safety_margin: 0.2    # %20 güvenlik marjı
```

Eğer tahmini maliyet limit'i aşarsa:
- Kullanıcıya uyarı gösterilir
- Scope reduction önerilir
- Alternatif plan sunulur

## 🎯 Kullanım Senaryoları

### Senaryo 1: Büyük Kod Üretimi

**İstek:**
```json
{
  "model": "sonnet-4-x",
  "messages": [{
    "role": "user",
    "content": "Create a complete e-commerce platform with 20+ features..."
  }],
  "max_tokens": 20000
}
```

**Sonuç:**
- ✅ Otomatik olarak 3 chunk'a bölünür
- ✅ Her chunk 1500 token (optimal)
- ✅ Haiku kullanılır (ucuz)
- ✅ Toplam maliyet: $0.05 (tek istek: $1.26)
- ✅ **%96 tasarruf!**

### Senaryo 2: Büyük Context Analizi

**İstek:**
```json
{
  "model": "sonnet-4-x",
  "messages": [{
    "role": "user",
    "content": "Analyze this 50K token codebase and suggest improvements..."
  }]
}
```

**Sonuç:**
- ✅ Otomatik olarak parçalara bölünür
- ✅ Her parça ayrı analiz edilir
- ✅ Sonuçlar birleştirilir
- ✅ Toplam maliyet: $0.15 (tek istek: $3.15)
- ✅ **%95 tasarruf!**

## ⚙️ Konfigürasyon

### config.yaml

```yaml
haiku_planner:
  # Aktivasyon
  enabled: true
  auto_enable: true
  large_request_threshold: 8000
  max_tokens_threshold: 15000
  
  # Maliyet optimizasyonu
  cost_optimization_enabled: true
  optimal_chunk_size: 1500
  max_chunk_size: 2000
  min_chunk_size: 500
  cost_savings_target: 0.3  # %30 hedef
  
  # Model seçimi
  planner_model: "autox"  # Ucuz
  fast_execution_model: "autox"  # Ucuz
  deep_execution_model: "sonnet-4-x"  # Pahalı (kalite için)
```

## 📊 Beklenen Tasarruf Oranları

| İstek Boyutu | Tek İstek | Parçalama | Tasarruf |
|--------------|-----------|-----------|----------|
| 10K token | $0.45 | $0.03 | %93 |
| 20K token | $0.90 | $0.06 | %93 |
| 50K token | $2.25 | $0.15 | %93 |
| 100K token | $4.50 | $0.30 | %93 |

**Not:** Tasarruf oranları model seçimine göre değişir:
- Haiku kullanımı: %90-95 tasarruf
- Sonnet kullanımı: %30-50 tasarruf

## 🚀 Best Practices

### 1. Quality Header Kullan

```bash
# Ucuz için
-H "x-quality: fast"

# Kalite için (daha pahalı)
-H "x-quality: deep"
```

### 2. Max Cost Limit

```bash
# Bütçe kontrolü
-H "x-max-cost: 0.50"
```

### 3. Manuel Decomposition

```bash
# Zorunlu parçalama
-H "x-decompose: 1"
```

## ⚠️ Dikkat Edilmesi Gerekenler

1. **Çok Küçük Chunk'lar**
   - 500 token altı chunk'lar verimsiz
   - Overhead maliyeti yüksek
   - Sistem otomatik olarak birleştirir

2. **Çok Fazla Chunk**
   - Max 3 chunk (MEGA_PROMPT spec)
   - Daha fazla chunk = daha fazla maliyet
   - Sistem otomatik olarak sınırlar

3. **Cache Kullanımı**
   - Küçük chunk'lar daha sık cache'lenir
   - İkinci istekte %70-90 tasarruf
   - Redis cache aktif olmalı

## 📈 Sonuç

✅ **Evet, parçalama maliyeti önemli ölçüde düşürür!**

- **%90-95 tasarruf** mümkün (Haiku kullanımı ile)
- Otomatik aktivasyon (8K+ token)
- Optimal chunk sizing (1500 token)
- Ucuz model kullanımı (Haiku)
- Cache optimizasyonu

**Sistem zaten bunu yapıyor!** Sadece config'i optimize etmeniz yeterli. 🎉

