# Araştırma notu (5 Kasım 2026)

Amaç: son dönemde Unreal ile çıkan oyunların yöntemlerini bu oyuna taşımak.

**Kanıtın sınırı:** Son 2-3 haftaya (15 Ekim - 5 Kasım) doğrudan düşen tek kaynak Phantom Blade Zero'nun
Digital Foundry incelemesi (forum kopyası, 28 Ekim) ve PC performans analizleri oldu. Gears: E-Day ve Galactic
Racer ekim başından, MotoGP 26 nisandan. Bu aralıkta çıkan bir bisiklet oyunu bulunamadı. Aşağıdaki oyunlar için
kaynaklar çoğunlukla basın analizleridir; geliştirici teknik yazısı değildir.

## Motor: Unreal Engine 5.8.4 (bu makinede kurulu)

| Özellik | Durum (Epic sürüm notları) | Bu oyundaki kararımız |
|---|---|---|
| MegaLights | Production Ready | Yalnızca PC üst kademede; M2 için deneysel |
| Lumen Lite | Beta, High Lumen'den yaklaşık 2 kat hızlı | Orta kademe adayı, M2'de test edilecek |
| Mesh Terrain | Deneysel | Kullanılmıyor; riskli. Kendi arazi üreticimiz var |
| PCG GPU scatter | Yeni | Kullanılmıyor; yerleşim veriyle üretiliyor |
| Procedural Vegetation Editor | Deneysel | Kullanılmıyor |
| MCP eklentisi | Deneysel, kimlik doğrulaması yok | Kullanılmıyor; Python komut hattı yeterli |

## Oyunlardan alınan dersler

| Oyun | Gözlem | Bizdeki karşılığı |
|---|---|---|
| Gears of War: E-Day (Ekim 2026) | MegaLights kullanan ilk oyun olarak anılıyor; alan geçişlerinde sert kare süresi sıçramaları raporlandı, kaynak bunu World Partition/akış sistemine bağlıyor | Tek parça ve baştan yüklenen harita; yarış sırasında akış yok |
| Phantom Blade Zero (UE 5.7.4) | Temelde yazılımsal Lumen, üstüne isteğe bağlı donanımsal RT; TSR/DLSS/FSR/XeSS seçenekleri. RT'nin oyun içinde açılıp kapanamaması eleştirildi; ilk açılışta shader derlemesi dakikalar sürüyor | Temel kademe yazılımsal Lumen; grafik kademesi oyun içinde değişebilir; PSO ön derleme açık |
| MotoGP 26 (Nisan 2026, UE5) | Sürücü odaklı yol tutuşu öne çıkarılıyor (ayrıntı kaynakta sınırlı) | Eğilme, sürücü ağırlığı ve pedal gücü doğrudan fizikte |
| Star Wars: Galactic Racer (Ekim 2026) | Motor bilgisi aramada UE5 araması altında çıktı, yöntemi doğrulanmadı | Yöntem alınmadı |

## Bisiklet fiziği

- Chaos Vehicles iki tekerli için uygun değil: forum raporlarında dengeleme kısıtlarla zorlanıyor, tekerlek yerden
  kesilince gaz/direksiyon duruyor.
- Motosiklet geliştiricileri Chaos'u bırakıp kendi sistemini yazmış; CycloCARLA da dört tekerli dinamiği iptal edip
  tek-iz modeli kullanıyor.
- Karar: Chaos kullanılmadan C++ tek-iz model + gerçek güç dengesi (watt, CdA, Crr, eğim, draft, W').

## Bu donanımda neler mümkün (Epic macOS gereksinimleri)

MacBook Air M2, 16 GB: asgari düzeyde. Nanite ve sanal gölge haritaları M2+ beta, yazılımsal Lumen destekli,
donanımsal RT ve MegaLights M2+ deneysel. Önerilen 32 GB ve M3. Windows paketi Mac'te üretilemez.

## Varlık kaynakları

- Poly Haven: varlıklar CC0. Canlı API kullanımı için "Powered by Poly Haven" notu isteniyor, oyunun jeneriğine eklenir.
- Bisiklet, mimari, ses ve müzik: Blender ve Python betikleriyle bu projede üretiliyor (`Tools/`).

## Kaynaklar

- [UE 5.8 sürüm notları](https://dev.epicgames.com/documentation/unreal-engine/unreal-engine-5-8-release-notes?lang=en-US)
- [macOS geliştirme gereksinimleri](https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine?lang=en-US)
- [Phantom Blade Zero, Digital Foundry forum kopyası](https://www.neogaf.com/threads/phantom-blade-zero-ps5-ps5-pro-the-digital-foundry-tech-review.1702922/)
- [Phantom Blade Zero, Wccftech ayar rehberi](https://wccftech.com/how-to/phantom-blade-zero-pc-performance-analysis-tuning-guide-how-to-get-the-best-experience-on-pc/)
- [Phantom Blade Zero, DSOGaming](https://www.dsogaming.com/pc-performance-analyses/phantom-blade-zero-benchmarks-pc-performance-analysis/)
- [Gears: E-Day, Wccftech](https://wccftech.com/how-to/gears-of-war-e-day-pc-performance-analysis-tuning-guide-how-to-get-the-best-experience-on-pc/)
- [Gears: E-Day, The FPS Review](https://www.thefpsreview.com/2026/10/03/the-fps-review-weekender-gears-of-war-e-day-is-the-rare-unreal-engine-5-game-that-actually-wants-more-cpu-cores-plus-10-more-hardware-reviews/)
- [MotoGP 26](https://en.wikipedia.org/wiki/MotoGP_26)
- [Star Wars: Galactic Racer](https://en.wikipedia.org/wiki/Star_Wars:_Galactic_Racer)
- [Chaos bisiklet sorunları](https://forums.unrealengine.com/t/chaos-wheeled-vehicle-bicycle-setup-problems/2702564)
- [Özel motosiklet sistemi, 80.lv](https://80.lv/articles/creating-a-custom-motorcycle-system-for-unreal-engine-5)
- [CARLAverse / CycloCARLA](https://arxiv.org/pdf/2609.11478)
- [Poly Haven Public API](https://github.com/Poly-Haven/Public-API)
- [Poly Haven lisansı](https://www.polyhaven.com/license)
