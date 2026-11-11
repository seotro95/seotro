# Thành phần bên thứ ba

- Whisper/faster-whisper: https://github.com/SYSTRAN/faster-whisper (MIT);model theo trang phát hành HuggingFace tương ứng. Nhận dạng chạy cục bộ sau khi tải model.
- CLIP gốc: https://github.com/openai/CLIP (MIT). Bản ONNX: https://huggingface.co/Xenova/clip-vit-base-patch32, revision6b7c523703ae26e39be4b03774966f8571c7f523. Trọng số được tải riêng;không đổi giấy phép của model. Kiểm SHA256 hai file ONNX trước khi chạy.
- ONNX Runtime,tokenizers,numpy,Pillow,CTranslate2,PyAV,huggingface_hub: xem giấy phép đi kèm từng package trong bản đóng gói và dự án nguồn. Build không dùng PyTorch.
- FFmpeg/ffprobe bản Windows từ FFmpeg-Builds: https://github.com/FFmpeg-Builds/FFmpeg-Builds. Bản gpl dùng libx264;Tool tải trực tiếp về máy người dùng ở lần đầu,kiểm SHA256và giữ LICENSE/NOTICE,không tái đóng gói FFmpeg trong ZIP phần mềm. Nguồn FFmpeg https://ffmpeg.org/download.html và script build tương ứng https://github.com/BtbN/FFmpeg-Builds. Công cụ gọi FFmpeg bằng tiến trình riêng,không sửa mã FFmpeg.
- Giao diện dùng Tkinter/Tcl/Tk của Python. Bản Windows đóng gói bằng PyInstaller;điều khoản ngoại lệ bootloader cho phép đóng gói ứng dụng,giữ giấy phép thành phần bên thứ ba.

Model Whisper/CLIP lớn, cache và media của người dùng không đóng gói trong bản phát hành. Model VAD nhỏ silero_vad_v6.onnx là tài nguyên runtime bắt buộc, được đóng gói kèm giấy phép Silero VAD/faster-whisper.

- langid.py 1.1.6: https://github.com/saffsd/langid.py (BSD). Ước lượng ngôn ngữ phụ đề khi đã có SRT; không thay thế nhận dạng voice của Whisper.
