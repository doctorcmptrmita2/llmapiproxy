import time
import requests
import json

# --- AYARLAR ---
# Easypanel'deki Domain adresini buraya yaz (https:// ile başlasın, sonunda / olmasın)
BASE_URL = "https://proxyapison-litellmproxyv1.lc58dd.easypanel.host" 

# Easypanel'deki LITELLM_MASTER_KEY
API_KEY = "sk-super-gizli-admin-sifren"

# Test edilecek model (Config dosyasında tanımladığımız isim)
MODEL = "autox" 
# ----------------

def ask_ai(iteration):
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": "Bana İstanbul hakkında 1 cümlelik bilgi ver."}
        ]
    }

    print(f"\n[{iteration}. İSTEK] Gönderiliyor...")
    start_time = time.time()
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        end_time = time.time()
        duration = end_time - start_time
        
        if response.status_code == 200:
            print(f"✅ Başarılı! Cevap: {response.json()['choices'][0]['message']['content'][:50]}...")
            print(f"⏱️ Süre: {duration:.4f} saniye")
            return duration
        else:
            print(f"❌ Hata: {response.text}")
            return 999
    except Exception as e:
        print(f"❌ Bağlantı Hatası: {e}")
        return 999

# --- TEST BAŞLIYOR ---
print("--- REDIS CACHE TESTİ BAŞLIYOR ---")

# 1. İstek (Cache'e yazacak - Yavaş olmalı)
time1 = ask_ai(1)

# 2. İstek (Cache'den okuyacak - Şimşek gibi olmalı)
time2 = ask_ai(2)

print("\n--- SONUÇ ---")
if time2 < 0.5:
    print(f"🚀 MÜKEMMEL! İkinci istek {time2:.4f} saniyede geldi.")
    print("✅ Redis Cache Sorunsuz Çalışıyor.")
else:
    print(f"⚠️ YAVAŞ. İkinci istek {time2:.4f} saniye sürdü.")
    print("❌ Cache çalışmıyor veya config ayarlarında sorun var.")