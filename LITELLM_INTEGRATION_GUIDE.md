# 🔗 LiteLLM Entegrasyonu - Haiku Planner

## 📋 Önemli Bilgi

**LiteLLM'in kendi içinde büyük istekleri parçalama özelliği YOK!**

Bu özellik **Haiku Planner Middleware** ile sağlanıyor. LiteLLM sadece normal API proxy görevi görüyor.

## 🏗️ Mimari

```
┌─────────────────────────────────────────────────┐
│  Kullanıcı İsteği                                │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Haiku Proxy (litellm-haiku-proxy.py)            │
│  Port: 8000                                      │
│  - Request'i analiz eder                         │
│  - Büyük istek mi kontrol eder                  │
│  - Haiku Planner'a yönlendirir                  │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
        ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│ Büyük İstek      │   │ Küçük İstek      │
│ (>8K token)      │   │ (<8K token)      │
└──────────────────┘   └──────────────────┘
        │                       │
        ▼                       ▼
┌──────────────────┐   ┌──────────────────┐
│ Haiku Planner    │   │ LiteLLM Proxy    │
│ Middleware       │   │ (Normal akış)    │
│ - Plan oluştur   │   │ Port: 4000       │
│ - Chunk'lara böl │   │                  │
│ - Execute et     │   │                  │
└──────────────────┘   └──────────────────┘
        │                       │
        └───────────┬───────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  LiteLLM Proxy (config.yaml ile)                 │
│  - Model routing                                 │
│  - Rate limiting                                 │
│  - Cache                                         │
│  - Multi-org API key failover                   │
└─────────────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────┐
│  Anthropic API (Claude modelleri)               │
└─────────────────────────────────────────────────┘
```

## ✅ Nasıl Çalışıyor?

### 1. Config.yaml Ayarları

**ÖNEMLİ:** Config.yaml'daki `haiku_planner` ayarları artık middleware tarafından okunuyor!

```yaml
haiku_planner:
  enabled: true
  auto_enable: true
  large_request_threshold: 8000
  max_tokens_threshold: 15000
  max_chunks: 3
  optimal_chunk_size: 1500  # ← Middleware bunu okuyor!
  cost_optimization_enabled: true  # ← Middleware bunu okuyor!
  planner_model: "autox"
  fast_execution_model: "autox"
  deep_execution_model: "sonnet-4-x"
  max_cost_per_request: 1.0
  cost_safety_margin: 0.2
```

### 2. Middleware Config Okuma

Middleware artık config.yaml'ı otomatik olarak okuyor:

```python
# haiku-planner-middleware.py
def __init__(self, litellm_base_url: str, master_key: str, config_path: str = None):
    # Config dosyasını yükle
    config = self._load_config(config_path)
    haiku_config = config.get('haiku_planner', {})
    
    # Config'den değerleri al
    self.OPTIMAL_CHUNK_SIZE = haiku_config.get('optimal_chunk_size', 1500)
    self.COST_OPTIMIZATION_ENABLED = haiku_config.get('cost_optimization_enabled', True)
    # ... vs
```

### 3. LiteLLM Proxy (config.yaml)

LiteLLM kendi config.yaml'ını kullanıyor:
- Model listesi
- Router ayarları
- Rate limiting
- Cache ayarları
- Multi-org API key failover

**LiteLLM'in yaptığı:**
- ✅ Model routing
- ✅ Rate limiting
- ✅ Cache
- ✅ Fallback
- ❌ Büyük istekleri parçalama (YOK!)

**Haiku Planner'ın yaptığı:**
- ✅ Büyük istekleri algılama
- ✅ Planlama
- ✅ Parçalama (chunking)
- ✅ Maliyet optimizasyonu
- ✅ Chunk execution

## 🔧 Kurulum

### 1. Docker Compose

```yaml
# docker-compose.yml
services:
  litellm:
    # LiteLLM proxy - config.yaml kullanıyor
    command: ["--config", "/app/config.yaml", "--port", "4000"]
    
  haiku-proxy:
    # Haiku Planner - config.yaml'ı okuyor
    environment:
      CONFIG_YAML_PATH: /app/config.yaml
```

### 2. Environment Variables

```bash
# Haiku Proxy için
CONFIG_YAML_PATH=config.yaml  # Varsayılan, opsiyonel
LITELLM_PROXY_URL=http://litellm:4000
LITELLM_MASTER_KEY=sk-your-key
```

### 3. Config Dosyası Yolu

Middleware şu sırayla config dosyasını arar:

1. `config_path` parametresi (constructor'da)
2. `CONFIG_YAML_PATH` environment variable
3. `HAIKU_CONFIG_PATH` environment variable
4. Varsayılan: `config.yaml` (çalışma dizininde)

## 📝 Config.yaml Örnekleri

### Minimal Config

```yaml
haiku_planner:
  enabled: true
  large_request_threshold: 8000
  optimal_chunk_size: 1500
```

### Tam Config

```yaml
haiku_planner:
  enabled: true
  auto_enable: true
  large_request_threshold: 8000
  max_tokens_threshold: 15000
  max_chunks: 3
  optimal_chunk_size: 1500
  max_chunk_size: 2000
  min_chunk_size: 500
  cost_optimization_enabled: true
  planner_model: "autox"
  fast_execution_model: "autox"
  deep_execution_model: "sonnet-4-x"
  max_cost_per_request: 1.0
  cost_safety_margin: 0.2
  planner_timeout: 60
  chunk_timeout: 120
  total_timeout: 600
```

## 🚀 Kullanım

### Otomatik (Config ile)

Config.yaml'da ayarları yapın, sistem otomatik çalışır:

```yaml
haiku_planner:
  large_request_threshold: 8000  # 8K+ token → Otomatik aktif
  optimal_chunk_size: 1500       # Chunk boyutu
```

### Manuel (Header ile)

```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "x-decompose: 1" \
  -H "x-quality: fast" \
  -H "x-max-cost: 0.50"
```

## ⚙️ Config Okuma Detayları

### Middleware Başlatma

```python
# litellm-haiku-proxy.py
haiku_planner = HaikuPlannerMiddleware(
    litellm_base_url="http://localhost:4000",
    master_key="sk-key",
    config_path="config.yaml"  # ← Config yolu
)
```

### Config Yükleme

```python
# haiku-planner-middleware.py
def _load_config(self, config_path: Optional[str] = None):
    # 1. Parametre kontrolü
    if config_path is None:
        config_path = os.getenv('HAIKU_CONFIG_PATH', 'config.yaml')
    
    # 2. Environment variable
    config_path = os.getenv('CONFIG_YAML_PATH', config_path)
    
    # 3. Dosyayı yükle
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
```

## 🔍 Debug

### Config Yükleme Kontrolü

```bash
# Logları kontrol et
docker-compose logs haiku-proxy | grep "Config"

# Beklenen çıktı:
# ✅ Config yüklendi: config.yaml
```

### Config Değerleri Kontrolü

```python
# Middleware başlatıldığında log'da görünür:
print(f"OPTIMAL_CHUNK_SIZE: {self.OPTIMAL_CHUNK_SIZE}")
print(f"COST_OPTIMIZATION_ENABLED: {self.COST_OPTIMIZATION_ENABLED}")
```

## ❓ Sık Sorulan Sorular

### Q: LiteLLM kendi başına parçalama yapıyor mu?

**A: HAYIR!** LiteLLM sadece normal API proxy. Parçalama Haiku Planner middleware ile yapılıyor.

### Q: Config.yaml'daki ayarlar yeterli mi?

**A: EVET!** Artık middleware config.yaml'ı okuyor. Hardcoded değerler yerine config'den alıyor.

### Q: Ek kodlama gerekiyor mu?

**A: HAYIR!** Sadece config.yaml'da ayarları yapmanız yeterli. Middleware otomatik okuyor.

### Q: LiteLLM config.yaml ile Haiku Planner config.yaml aynı mı?

**A: EVET!** Aynı dosya. LiteLLM kendi ayarlarını, Haiku Planner `haiku_planner` bölümünü okuyor.

## 📊 Özet

| Özellik | LiteLLM | Haiku Planner |
|---------|---------|---------------|
| Model routing | ✅ | ❌ |
| Rate limiting | ✅ | ❌ |
| Cache | ✅ | ❌ |
| Büyük istek parçalama | ❌ | ✅ |
| Maliyet optimizasyonu | ❌ | ✅ |
| Config okuma | ✅ (kendi ayarları) | ✅ (haiku_planner bölümü) |

## ✅ Sonuç

**Config.yaml yeterli!** Ek kodlama gerekmiyor. Sadece:

1. ✅ Config.yaml'da `haiku_planner` ayarlarını yapın
2. ✅ Haiku Proxy'yi başlatın (config.yaml'ı otomatik okur)
3. ✅ Sistem otomatik çalışır!

**Artık config.yaml'daki tüm ayarlar middleware tarafından okunuyor!** 🎉

