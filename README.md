# Kapadokya Turu

Unreal Engine 5.8 ile yapılmış, peribacaları arasında geçen bisiklet yarışı oyunu.

## Bu depoda ne var

Kaynak kod, ayarlar, varlık üretim betikleri ve dokümanlar. `Content/` ve `RawAssets/` depoda yok: MetaHuman ve Manny Epic lisanslı içeriktir, geri kalanı da betiklerle üretilir veya indirilir. Bu yüzden klonladıktan sonra oyun varlıklar üretilmeden çalışmaz. Temiz bir klondan baştan kurulum henüz denenmedi. MetaHuman adımı için Epic hesabı ve tam editör gerekir (`Tools/mh_gui.sh`).

## Oynamak

`Oyna.command` dosyasına çift tıkla (`Unreal` diski takılı olmalı). İlk açılış shader derlemesi nedeniyle uzun sürebilir.

| Tuş | Görev | Kol |
|---|---|---|
| W | Pedal | Sağ tetik |
| S | Fren | Sol tetik |
| A / D | Yatış ve direksiyon | Sol çubuk |
| Shift | Sprint (rezerv tüketir) | B |
| Boşluk | Aero pozisyon | Sol omuz |
| Q / E | Elle vites | X / sağ omuz |
| R | Otomatik vitese dön | |
| C | Kamera | Y |
| Esc | Mola | Menü |
| Oklar + Enter | Menü | D-pad + A |

## Parkur (7,46 km, tur)

Peri Köyü Çarşısı (cami, çarşı, kemer) → Peribacası Vadisi → Kızılırmak Köprüsü → Kale Tırmanışı (2 km, ortalama %6,9) → Kale Zirvesi → Bağ Yolu → Kervansaray Düzlüğü.

## Fizik

`Source/KapadokyaTuru/Private/BikeDynamics.cpp`: Chaos kullanılmıyor. Watt, aerodinamik, yuvarlanma, eğim, draft, kadans verimi, W' rezervi, ters direksiyonlu tek-iz modeli. Testler: `Automation RunTests Kapadokya.Bike`.

## Varlıkları yeniden üretmek

Her şey `Tools/` altındaki betiklerle üretilir: `Tools/build_all.sh`. Tek tek:

- `gen_world.py`: arazi, yol, rota (`route.py` parkurun tanımı)
- `bl_bike.py`, `bl_props.py`, `bl_extras.py`: Blender modelleri
- `gen_placements.py`: yerleşimler
- `gen_audio.py`: tüm ses ve müzik sentezi
- `ue_materials.py`, `ue_import_world.py`, `ue_import_assets.py`: Unreal'a aktarım
- `shots.sh`, `perf.sh`: otomatik ekran görüntüsü ve performans ölçümü

İlk kurulum: `python3 -m venv Tools/.venv && Tools/.venv/bin/pip install numpy scipy matplotlib pillow`, sonra `Tools/.venv/bin/python Tools/fetch_textures.py`.

## Lisanslar

- Kod ve betikler: MIT (`LICENSE`). Unreal Engine ve Epic içerikleri kendi lisanslarına tabidir.
- Dokular: [Poly Haven](https://polyhaven.com) CC0. Powered by Poly Haven.
- Sporcu iskeleti ve ağı: Unreal Engine şablon içeriği (Manny), Unreal Engine lisansı kapsamında.
- Takım ve sporcu adları kurmacadır.

Araştırma notu: `Docs/ARASTIRMA.md`.

## Paket ve performans
- Oynamak: `Oyna.command` (varsa `Dist/` altindaki paketli oyunu acar). Yeniden paketlemek: `Tools/paketle.sh`.
- Olcum araclari: `Tools/pakettest.sh`, `Tools/pkrapor.py`, `Tools/tustest.sh` (gercek tus), `Tools/menutest.sh`. Ayrinti: `Docs/PERFORMANS.md`.
