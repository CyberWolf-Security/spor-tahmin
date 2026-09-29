# Spor Maç Tahmin

Canlı veri çeken, Monte Carlo simülasyonu ile maç tahmini yapan program.

## Özellikler

- **Canlı veri** — FlashScore (Süper Lig, anahtarsız) + OpenLigaDB (Avrupa)
- **Monte Carlo simülasyon** — 10.000 maç tekrarı
- **Tahminler**: Kazanan olasılığı, beklenen skor, en olası skorlar, üst/alt, karşılıklı gol
- **Canlı animasyon** — maç dakika dakika akar
- **Puan tablosu**

## Çalıştırma (kaynak)

```bash
pip install flask requests
python app.py
```

Tarayıcı: http://127.0.0.1:8090

## Windows EXE

GitHub Actions otomatik derler → Actions sekmesi → Artifacts → SporTahmin.exe

## Veri Kaynakları

| Kaynak | Lig | Anahtar |
|---|---|---|
| FlashScore | Süper Lig (171 maç) | Gerekmez |
| OpenLigaDB | Bundesliga, UCL, DFB | Gerekmez |
