# 🔄 Multi-Organization API Key Failover Sistemi

## 📋 Genel Bakış

Sistem, aynı model için farklı organizasyonlardan alınan API key'ler ile otomatik failover (yedekleme) yapabilir. Bir API key rate limit'e takıldığında, LiteLLM otomatik olarak bir sonraki organizasyonun API key'ine geçer.

## ✅ Nasıl Çalışıyor?

### 1. Aynı Model, Farklı API Key'ler

Config dosyasında aynı `model_name` ile birden fazla entry tanımlanabilir:

```yaml
# İlk organizasyon - Ana key
- model_name: autox
  litellm_params:
    model: anthropic/claude-haiku-4-5-20251001
    api_key: os.environ/ANTHROPIC_KEY_HAIKU  # Org 1
  weight: 30

# İkinci organizasyon - Yedek key
- model_name: autox
  litellm_params:
    model: anthropic/claude-haiku-4-5-20251001
    api_key: os.environ/ANTHROPIC_KEY_HAIKU_ORG2  # Org 2
  weight: 20

# Üçüncü organizasyon - Yedek key
- model_name: autox
  litellm_params:
    model: anthropic/claude-haiku-4-5-20251001
    api_key: os.environ/ANTHROPIC_KEY_HAIKU_ORG3  # Org 3
  weight: 10
```

### 2. Otomatik Failover Mekanizması

LiteLLM'in `router_settings` ayarları sayesinde:

- **routing_strategy: least-busy**: En az meşgul olan key'i seçer
- **enable_pre_call_check: true**: Her istek öncesi rate limit kontrolü yapar
- **allowed_fails: 3**: 3 başarısız denemeden sonra bir sonraki key'e geçer
- **cooldown_time: 30**: Rate limit'e takılan key 30 saniye bekler

### 3. Failover Senaryosu

```
1. İstek gelir → autox modeli istenir
2. LiteLLM ilk key'i (ORG1) dener
3. Rate limit hatası (429) alınır
4. LiteLLM otomatik olarak ikinci key'e (ORG2) geçer
5. İkinci key de limit'e takılırsa → üçüncü key'e (ORG3) geçer
6. Tüm key'ler tükenirse → fallback modellere geçer
```

## 🔧 Kurulum

### 1. Environment Variables Ekle

`.env` dosyanıza yeni API key'leri ekleyin:

```bash
# Ana organizasyonlar
ANTHROPIC_KEY_HAIKU=sk-ant-...          # Org 1
ANTHROPIC_KEY_SONNETX=sk-ant-...        # Org 1
ANTHROPIC_KEY_SONNET=sk-ant-...         # Org 1

# İkinci organizasyon (Failover için)
ANTHROPIC_KEY_HAIKU_ORG2=sk-ant-...     # Org 2
ANTHROPIC_KEY_SONNETX_ORG2=sk-ant-...  # Org 2
ANTHROPIC_KEY_SONNET_ORG2=sk-ant-...    # Org 2

# Üçüncü organizasyon (Failover için)
ANTHROPIC_KEY_HAIKU_ORG3=sk-ant-...     # Org 3
```

### 2. Config Dosyası Kontrolü

`config.yaml` dosyasında her model için birden fazla entry olduğundan emin olun.

## 📊 Mevcut Yapılandırma

### autox (Claude Haiku 4.5)
- ✅ Org 1: `ANTHROPIC_KEY_HAIKU` (weight: 30)
- ✅ Org 2: `ANTHROPIC_KEY_HAIKU_ORG2` (weight: 20)
- ✅ Org 3: `ANTHROPIC_KEY_HAIKU_ORG3` (weight: 10)

### sonnet-4-x (Claude Sonnet 4)
- ✅ Org 1: `ANTHROPIC_KEY_SONNETX` (weight: 10)
- ✅ Org 2: `ANTHROPIC_KEY_SONNETX_ORG2` (weight: 5)

### sonnet-4-5-x (Claude Sonnet 4.5)
- ✅ Org 1: `ANTHROPIC_KEY_SONNET` (weight: 10)
- ✅ Org 2: `ANTHROPIC_KEY_SONNET_ORG2` (weight: 5)

### claude-3-5-x (Claude 3.5 Sonnet)
- ✅ Org 1: `ANTHROPIC_KEY_HAIKU` (weight: 7)
- ✅ Org 2: `ANTHROPIC_KEY_HAIKU_ORG2` (weight: 3)

## 🧪 Test Etme

### 1. Rate Limit Simülasyonu

Bir API key'i geçici olarak devre dışı bırakarak test edebilirsiniz:

```bash
# Org 1 key'ini geçici olarak yanlış yap
ANTHROPIC_KEY_HAIKU=sk-invalid-key

# Sistem otomatik olarak Org 2 key'ine geçmeli
```

### 2. Monitoring

LiteLLM dashboard'unda hangi key'in kullanıldığını görebilirsiniz:

```
http://localhost:4000/ui
```

## ⚠️ Önemli Notlar

1. **Weight Dağılımı**: Weight'ler toplam %100'ü geçmemeli (şu an: 30+20+10=60% autox için)

2. **API Key Limitleri**: Her organizasyonun kendi rate limit'leri vardır:
   - Org 1: 50K TPM, 100 RPM
   - Org 2: 50K TPM, 100 RPM
   - Org 3: 50K TPM, 100 RPM
   - **Toplam kapasite**: 150K TPM, 300 RPM (autox için)

3. **Maliyet**: Tüm organizasyonlar aynı fiyatlandırmaya sahip, sadece limit'ler artar

4. **Cooldown**: Rate limit'e takılan key 30 saniye bekler, sonra tekrar denenir

## 🚀 Avantajlar

✅ **Yüksek Kapasite**: 3x daha fazla rate limit
✅ **Otomatik Failover**: Manuel müdahale gerektirmez
✅ **Yüksek Erişilebilirlik**: Bir key tükense bile diğerleri çalışır
✅ **Load Balancing**: En az meşgul key otomatik seçilir

## 📝 Örnek Senaryo

**Durum**: 50 kullanıcı, yoğun kullanım

1. **09:00**: Org 1 key'i %80 kapasitede
2. **09:15**: Org 1 rate limit'e takıldı (100 RPM)
3. **09:15**: LiteLLM otomatik olarak Org 2 key'ine geçti
4. **09:30**: Org 2 de limit'e takıldı
5. **09:30**: LiteLLM otomatik olarak Org 3 key'ine geçti
6. **09:45**: Org 1 cooldown süresi doldu, tekrar kullanılabilir

**Sonuç**: Sistem kesintisiz çalışmaya devam etti! 🎉

