# Build và phát hành SNVideo

Mã nguồn dùng **Cherri 2.4.0** và tạo Apple Shortcut từ `src/SNVideo.cherri`.

## Cấu trúc

- `src/SNVideo.cherri`: metadata, tiếp nhận đầu vào và router chính.
- `src/config.cherri`: phiên bản, build và endpoint cố định.
- `src/lib/`: các module `common`, `tikwm`, `video`, `slideshow`, `audio`, `cobalt`, `update`.
- `tests/test_source_contract.py`: kiểm tra các bất biến kiến trúc và bảo mật.
- `scripts/install-cherri.sh`: clone tag, xác minh commit và build compiler Cherri dùng chung cho local/CI.
- `.github/workflows/build-shortcut.yml`: kiểm tra trên Linux, sau đó build và ký trên macOS.

## Build cục bộ trên macOS

Yêu cầu Git và Go 1.24 trở lên. Cherri được clone từ tag `v2.4.0`, xác minh commit đã pin rồi build cục bộ vì upstream không thể cài bằng `go install ...@v2.4.0`:

```bash
bash scripts/install-cherri.sh v2.4.0
mkdir -p dist
"$(go env GOPATH)/bin/cherri" src/SNVideo.cherri \
  --share=anyone \
  --comments \
  --derive-uuids \
  --output=dist/SNVideo.shortcut
```

Cherri gọi cơ chế ký native của macOS. Không dùng `--skip-sign` cho file phát hành vì iOS không nhập Shortcut chưa ký.

## GitHub Actions

Workflow có hai job:

1. `validate`: chạy unit test và biên dịch không ký trên Ubuntu để phát hiện lỗi cú pháp nhanh.
2. `build-macos`: chỉ chạy sau khi validate thành công, biên dịch và ký file `SNVideo.shortcut` với chế độ chia sẻ `anyone`, rồi upload artifact cùng SHA-256.

Có thể chạy thủ công tại **Actions → Build SNVideo Shortcut → Run workflow**. Khi push tag dạng `v1.0.0`, workflow còn tạo GitHub Release và đính kèm file đã ký.

## Bật kiểm tra cập nhật

Mặc định `MANIFEST_URL` để trống nên mục kiểm tra cập nhật chỉ thông báo chưa cấu hình. Đây là trạng thái an toàn trước phát hành.

Sau khi có repository công khai và một liên kết iCloud đã thử trên thiết bị:

1. Sao chép `manifest.example.json` thành `manifest.json`.
2. Thay `shortcut_icloud_url` bằng liên kết thật có hostname `www.icloud.com`.
3. Đặt `MANIFEST_URL` trong `src/config.cherri` thành URL dạng:

   ```text
   https://raw.githubusercontent.com/OWNER/SNVideo/main/manifest.json
   ```

4. Tăng đồng thời `SNVIDEO_VERSION`, `SNVIDEO_BUILD` và các trường tương ứng trong manifest.
5. Chạy workflow, cài artifact lên iPhone thử nghiệm và hoàn tất Gate A–D trong `README.md` trước khi tạo tag ổn định.

## Giới hạn cần hiểu đúng

- Runner GitHub là **macOS**, không phải máy ảo iOS. Nó có thể biên dịch/ký Shortcut nhưng không thay thế kiểm thử trên iPhone thật.
- Lỗi mạng cứng của action `Get Contents of URL` có thể dừng Shortcut trước khi thông báo tùy biến chạy.
- Bộ đếm ảnh lỗi chỉ phản ánh URL bị loại bởi kiểm tra mềm; nếu action tải/lưu gặp lỗi cứng, iOS có thể dừng cả luồng.
- Audio bị tắt mặc định bằng `ENABLE_AUDIO = false`. Chỉ đổi thành `true` sau khi Gate B xác minh `data.music`, kiểu media và luồng lưu trên thiết bị thật.
- `#define version 18` là baseline metadata của compiler, không phải bằng chứng cho phiên bản iOS tối thiểu; `minimum_ios` vẫn phải giữ `TBD` đến khi thử trên thiết bị.
