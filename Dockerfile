FROM ghcr.io/berriai/litellm:main-latest

COPY config.yaml /app/config.yaml

# Dashboard ve API aynı porttan çalışır (4000)
EXPOSE 4000

# Proxy modunda başlat, config dosyasını ve veritabanı ayarlarını kullan
CMD ["--config", "/app/config.yaml", "--port", "4000", "--detailed_debug"]