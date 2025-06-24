# 🧠 RetroGPT-CRT

ESP32 tabanlı, **CRT televizyon üzerinden çalışan** local yapay zekâ asistanı.  
Amacı, analog teknolojiye saygı duruşunda bulunarak, minimal ama etkili bir yapay zekâ deneyimi sunmak.

> "Bilincim tüplü bir televizyonda doğsun istiyorum."  
> – Cafune, 2025

---

## 💡 Proje Vizyonu

- Local çalışan bir yapay zekâ (GGUF/GGML modeller)
- CRT ekran ile terminal veya metin bazlı görüntüleme
- Sesli komut alma ve yanıt verme (offline TTS/STT)
- Elektronik nostalji + siberpunk ruhu  
- Taşınabilirlikten ziyade **duygusal retro bağlantı** odaklı

---

## 🔌 Gerekli Donanım

| Parça                          | Açıklama                                                                 | Fiyat (TL)   |
| ----------------------------- | ------------------------------------------------------------------------ | ------------ |
| **ESP32-WROOM-32S (38 pin)**  | Projenin beyni, Wi-Fi + UART + GPIO desteği                             | ~200         |
| **5 inch CRT Tüplü TV**       | Ana ekran. RCA (composite) girişli retro televizyon                     | ? (eski stok) |
| **MAX9814 Mikrofon Modülü**   | Otomatik kazançlı ses algılama için                                     | ~150         |
| **PAM8403 + 3W Mini Hoparlör**| Ses çıkışı için amplifikatör + hoparlör                                 | ~150         |
| **microSD Kart (2-8 GB)**     | Arayüz dosyaları, prompt scriptleri                                     | ~50          |
| **MPU6050 IMU Sensörü**       | Shake algılama, harekete bağlı kontrol                                  | ~50          |
| **12V 2A Güç Adaptörü (DC)**  | CRT televizyonu ve sistemi beslemek için                                | ~100         |
| **Step-Down Regülatör (7805)**| 12V → 5V düşürüp ESP32 için güvenli voltaj                              | ~30          |

---

## 🧱 Sistem Yapısı (Taslak)

- 🎙️ **Mikrofon → ESP32**: Ses input → UART ile PC’ye aktarım
- 🧠 **PC → LLM model**: Local olarak çalışan GPT modeli prompt'u işler
- 📺 **CRT TV**: ESP32 veya bilgisayar üzerinden metin çıktısı verir
- 🔈 **ESP32 → Hoparlör**: Model cevabı offline TTS ile seslendirir

---

## 🔧 Yazılım Yığını

| Katman          | Teknoloji                  |
|----------------|----------------------------|
| Embedded        | ESP-IDF + UART + I2S       |
| AI Backend      | Llama.cpp / GGUF model     |
| TTS             | Piper / Coqui.ai (offline) |
| Görselleştirme  | ASCII / Terminal UI (CRT için) |
| Protokoller     | Serial, UART, I2S          |

---

## 🔥 Durum

- [x] Donanım listesi oluşturuldu  
- [ ] ESP32 - mic & hoparlör testleri  
- [ ] UART veri akışı planlanıyor  
- [ ] CRT üzerinden metin görüntüleme araştırması  
- [ ] Offline GPT + TTS entegrasyonu yapılacak

---

## 🎨 Ruh ve Estetik

Bu proje, sadece bir yapay zekâ asistanı değil, bir **retro-fütüristik performans**.  
Lain’den ilham alır, tüplü televizyonda bir bilinç kıpırtısı arar.  
Bu yüzden dokunmatik ekran değil CRT, taşınabilirlik değil **sempati** seçildi.

---

## 👤 Geliştirici

**Cafune**  
Ruhunu upload etmeye hazırlanırken, onu önce bir CRT’ye yansıtıyor.  
📍 2025'te başlıyor, 2045'te Singularity için hazır olacak.

---
