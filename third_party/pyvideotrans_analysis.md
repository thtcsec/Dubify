# Phân Tích & Bóc Tách: pyvideotrans

Tài liệu này ghi chú lại cấu trúc và các mô-đun quan trọng nhất được bóc tách từ kho lưu trữ `pyvideotrans` (`third_party/pyvideotrans`), phục vụ cho việc nâng cấp hệ thống Dubify.

## 1. Module Nhận diện & Tách người nói (ASR & Diarization)
**Đường dẫn:** `third_party/pyvideotrans/videotrans/recognition/`

Trong thư mục này, repo sử dụng mô hình thiết kế Strategy Pattern để bọc các loại API/Mô hình ASR khác nhau.

* **`_whispernet.py` (Faster-Whisper):** 
  - Đây là nền tảng cốt lõi giống với cái `ASRService` của Dubify đang dùng. Tuy nhiên, họ quản lý việc "chia chunk" audio rất tốt bằng cách sử dụng `vad_filter=True` và `chunk_length=30`. Điều này giúp bộ nhớ VRAM không bị tràn với các file audio cực dài.
* **`_whisperx.py` (WhisperX):**
  - Được dùng để xử lý **Speaker Diarization** (Phân biệt giọng nói của nhiều người).
  - Nó sử dụng pipeline `pyannote/speaker-diarization-3.1` thông qua token HuggingFace.
  - **Ứng dụng cho Dubify:** Nếu muốn Dubify có khả năng lồng tiếng 2 giọng nam/nữ khác nhau cho 1 video phỏng vấn, chúng ta cần import thư viện `whisperx` và học cách ghép (align) timestamps từ `faster-whisper` với nhãn speaker từ `pyannote` giống như logic trong file này.
* **`_funasr.py` / `_qwen3asr.py`:** Các mô hình chuyên trị tiếng Trung xuất sắc từ Alibaba.

## 2. Module Tổng hợp & Nhái giọng (TTS & Voice Cloning)
**Đường dẫn:** `third_party/pyvideotrans/videotrans/tts/`

Đây là "mỏ vàng" để Dubify nâng cấp từ giọng đọc AI vô hồn lên giọng đọc clone chân thực.

* **`_clone.py` (Logic gốc của Voice Cloning):**
  - Chứa logic quản lý tệp mẫu âm thanh (reference audio) được cắt ra từ đoạn gốc của người nói để làm input cho các mô hình Zero-shot TTS.
* **`_f5tts.py` (F5-TTS):**
  - Mô hình SOTA hiện nay về nhái giọng đa ngôn ngữ. 
  - Cách nó hoạt động: Cần 1 đoạn tệp âm thanh mẫu `.wav` (tầm 3-5 giây) + văn bản (text) của đoạn mẫu đó + văn bản cần đọc.
  - Phụ thuộc: Đòi hỏi server phải cài đặt module `f5-tts` hoặc gọi qua API nếu được host ở nơi khác.
* **`_cosyvoice.py`:**
  - Mô hình tương tự của Alibaba, xử lý nhái giọng tiếng Trung và tiếng Anh cực kỳ mượt mà. Đòi hỏi cấu hình phần cứng tương tự F5.
* **`_gptsovits.py`:** 
  - Hệ thống nhái giọng mã nguồn mở nổi tiếng nhất (nhưng phức tạp trong việc fine-tune). Trong repo này, họ gọi thông qua API của một backend GPT-SoVITS cục bộ.
* **`_edgetts.py`:** Bản nâng cấp của cách chúng ta đang gọi Edge-TTS. Họ xử lý rất tốt việc rate-limiting.

## 3. Quản lý xử lý Audio/Video (FFmpeg Wrapper)
**Đường dẫn:** `third_party/pyvideotrans/videotrans/util/` và `videotrans/process/`

* **Audio Speed Stretching:** Thay vì chỉ dùng 1 bộ lọc `atempo` như Dubify, họ dùng thư viện **Rubberband** hoặc bộ lọc `rubberband` của FFmpeg để bóp giãn âm thanh mà không làm thay đổi cao độ quá nhiều (pitch-shifting). Nếu âm thanh cần kéo dài/thu ngắn quá 30%, `rubberband` sẽ cho chất lượng cao hơn hẳn so với `atempo`.
* **Vocal Separation:** Có logic gọi `demucs` hoặc `UVR5` để tách riêng biệt nhạc nền (BGM) và giọng nói gốc. Đây là tính năng Dubify đang rất cần để bản lồng tiếng nghe tự nhiên như phim chiếu rạp.

---
## Lộ Trình Nâng Cấp Đề Xuất Cho Dubify

Dựa trên việc bóc tách này, lộ trình được đề xuất:

1. **Phase 1: BGM Retention (Giữ Nhạc Nền)**
   - Viết thêm script gọi `demucs` (tham khảo `pyvideotrans`) trước khi gọi ASR.
   - Trích xuất 2 track: Giọng nói (đưa vào Whisper) và Nhạc nền (giữ lại).
   - Ở bước cuối (Video Merge), ghép cả TTS Audio và Nhạc Nền lại với nhau.
2. **Phase 2: Diarization (Nhiều Giọng Đọc)**
   - Thay `faster-whisper` bằng `whisperx` trong `ASRService`.
   - Phân biệt người nói thành `SPEAKER_00`, `SPEAKER_01`.
   - Cho phép chọn nhiều giọng Edge-TTS khác nhau tương ứng với mỗi Speaker.
3. **Phase 3: F5-TTS Integration (Nhái Giọng)**
   - Triển khai một microservice riêng để chạy F5-TTS (tránh làm nặng worker chính).
   - Gửi yêu cầu gồm: Audio Segment (cắt từ video) làm mẫu + Câu dịch Text => Nhận về audio đã được nhái giọng.
