import yt_dlp
import os

print("=" * 60)
print("Youtube OAuth2 Authenticator cho Dubify")
print("=" * 60)
print("Chương trình này sẽ kết nối yt-dlp với tài khoản YouTube của bạn.")
print("Hãy làm theo các bước sau:\n")
print("1. Một đường link Google sẽ hiện ra bên dưới cùng với một ĐOẠN MÃ (CODE).")
print("2. Copy mã đó, mở link trên trình duyệt và dán mã vào.")
print("3. Đăng nhập tài khoản Google của bạn và bấm Cho phép (Allow).")
print("\nBắt đầu lấy mã...\n")

ydl_opts = {
    'username': 'oauth2',
    'password': '',
    'quiet': False,
}

# Thử tải 1 video ngắn để kích hoạt quá trình login
test_url = "https://www.youtube.com/watch?v=aqz-KE-bpKQ"

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("Đang chờ xác thực từ Google... (Hãy làm theo hướng dẫn trên)")
        # Lệnh này sẽ tự động dừng lại chờ bạn nhập code trên web
        info = ydl.extract_info(test_url, download=False)
        print("\n" + "=" * 60)
        print("✅ XÁC THỰC THÀNH CÔNG!")
        print("Tài khoản của bạn đã được liên kết với Dubify/yt-dlp.")
        print("Bạn có thể tắt cửa sổ này và quay lại sử dụng Dubify bình thường.")
        print("=" * 60)
except Exception as e:
    print(f"\n❌ Lỗi: {e}")
