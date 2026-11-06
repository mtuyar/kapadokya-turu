# Performans raporu (MacBook Air M2, fansiz, 1600x900 pencere)

Yontem: `Tools/prof.sh` (bolge bolge kare suresi, `KHITCH` kare dagilimi, `ProfileGPU`), `Tools/profparse.py`, sicak test.
Testler sessiz, isinlamali, en fazla 5 dakika.

## Bulunan sebepler
| Sebep | Etki | Durum |
|---|---|---|
| Cokmus testlerden kalan 2 `CrashReportClient`, %100 CPU, 7.5 saat | Oyun/render thread yukunu iki katina cikardi, kasayi isitti | Kapatildi, test betikleri artik temizliyor |
| `SetCVar` `ECVF_SetByGameSetting` ile yaziyordu; `DefaultEngine.ini` daha yuksek oncelikli | Dusuk ayarda TAA/Lumen kapatma gibi ayarlar hic uygulanmiyordu | `ECVF_SetByCode` |
| Lumen (yazilimsal) | 13.6 ms ve bazi bolgelerde 19 fps; acik havada gorsel fark kucuk | Dusuk/Orta'da kapali |
| Hacimsel bulut + gercek zamanli gokyuzu yakalama | ~5 ms | Dusuk/Orta'da CC0 HDRI kubbe |
| Uzak bisikletciler ve kucuk bitkiler gunes golgesinde | Nanite olmayan golge 2-4 ms | Mesafeye bagli golge |
| Fansiz kasa: ~50 sn sonra GPU yavaslar | Soguk 60 fps, sicak yarim hiz | Hedef sicak olcum |

Motor notu: `MetalViewport.cpp:1125` pencereli modda ekran senkronunu her zaman acar. Kare 16.6 ms'yi kacirinca sonraki yenilemeyi bekler.
`ProfileGPU` tablosunda "VSM Log Stats" gibi tek bir geciste gorunen 9-25 ms kaynagi dogrulanmadi; toplam kare suresine bakin, tek gecis satirina guvenmeyin.

## Olcumler (Dusuk ayar, 1600x900)
| Durum | Medyan | Takilma |
|---|---|---|
| Ilk durum (editor) | 25 fps | %5 kare 200-400 ms |
| Paketli, dinamik cozunurluk + %25 GPU boslugu, 255 sn, onceden isinmis makine | 60 fps (son 60 sn: 60) | p99 20-21 ms, 15093 karede 6 kare 50 ms ustu |

Ayni test dikkatsiz surucu botuyla: 0 dusme. Tam 13 dakikalik yaris olculmedi.
Dinamik cozunurluk olmadan paket: ~50 sn sonra 22-46 fps'e dusup 54-60'ta oturuyordu.

Diger olcumler (sicak, editor veya eski ayarlar; tam olarak karsilastirilamaz): Orta ~32 fps, tam ekran 1710x1108 ~30 fps.

## Surus duzeltmesi
Gercek tus testi, serit izleyicinin yatis gecikmesini hesaba katmadigini gosterdi (+-4.5 m, sonmeyen salinim).
Yeni `LaneFollowAccel`: durum geri beslemesi + 0.4 sn on kestirim. Oyuncu ve yapay zeka ayni kodu kullanir.

## Kaynaklar
- Apple DTS (Nisan 2026): once profil cikar, MetalFX tek basina buyuk farki kapatmaz. https://developer.apple.com/forums/thread/820650
- Epic: Apple Silicon'da TSR maliyeti diger platformlardan yuksek. https://www.unrealengine.com/en-US/tech-blog/bringing-unreal-engine-on-macos-up-to-feature-parity-with-windowsprogress-report (arama ozeti, sayfa dogrudan acilamadi)
- Gokyuzu: Poly Haven CC0 HDRI (qwantani_morning_puresky, kloofendal_48d_partly_cloudy_puresky, qwantani_sunset_puresky)

## MetaHuman surumu (paketli, Dusuk, 1600x900, 255 sn peloton icinde)
Medyan 59 fps, son 60 sn 64 fps, 12401 karede 98 kare 50 ms ustu, 0 dusme.
Bulgular: alfa maskeli taranmis calilar 10 ms (sayi ve mesafe kisildi); bisiklet Nanite yapildi (golge 8.4 -> 5 ms); arka planda kalan UnrealTraceServer 51-199 % CPU yiyip olcumu bozdu (Oyna.command ve test betikleri kapatir).
Uretim: Tools/mh_gui.sh (MetaHuman, tam editor ve Epic girisi gerekir), Tools/ue_crowd.py (seyirci pisirme), Tools/bl_scan.py + Tools/ue_scan.py (Poly Haven CC0 modeller).
