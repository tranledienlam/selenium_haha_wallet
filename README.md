# AUTOMATION HAHA WALLET với Selenium Python

## ⚠ Lưu ý quan trọng

🔴 **Dự án này có chứa code hint.**

Vui lòng tìm đến **bài ghim** trong kênh [Telegram Channel](https://t.me/+8o9ebAT9ZSFlZGNl) để kiểm tra trước khi sử dụng.

🔴 **Tool sẽ tự tải phiên bản chromium 136.**

Để đảm bảo automation hoạt động ổn định, yêu cầu sử dụng Chrome/Chromium phiên bản 136 hoặc thấp hơn.

Trong trường hợp quá trình tải tự động thất bại, tool sẽ mặc định sử dụng Chrome đã được cài sẵn trên máy tính.

[Nguồn tải chromium](https://github.com/macchrome/winchrome/releases)

---

## 📖 Mục lục
1. [Giới thiệu](#-giới-thiệu)
2. [Video demo](#-video-demo)
3. [Chức năng chính](#-chức-năng-chính)
4. [Yêu cầu ban đầu](#-yêu-cầu-ban-đầu)
5. [Cấu trúc file](#-cấu-trúc-file)
6. [Hướng dẫn cài đặt](#-hướng-dẫn-cài-đặt)
7. [Hướng dẫn sử dụng](#-hướng-dẫn-sử-dụng)
8. [Tùy chỉnh cấu hình](#-tùy-chỉnh-cấu-hình)
9. [Tips](#-tips)
10. [Thông tin liên hệ](#-thông-tin-liên-hệ)

## 🔔 Bật thông báo để theo dõi mã nguồn khi có update

1. Đăng nhập vào GitHub.
2. Nhấn vào biểu tượng 🔔 **Watch** (góc trên bên phải của repository này).
3. Chọn **"All Activity"** để nhận tất cả thông báo hoặc **"Custom" > "Pull Requests"** để nhận thông báo khi có thay đổi trong mã nguồn.

---

## 🌐 Giới thiệu

📌 **Trang dự án**: [cess.network/interstellarairdrop](https://cess.network/interstellarairdrop/?code=3043048)

<p align="center">
    <img src="intro.png" alt="Giới thiệu">
</p>

---

## 🎬 Video demo (Không có)

<!-- <p align="center">
    <a href="https://youtu.be/W92xKrw16Ak">
        <img src="https://img.youtube.com/vi/W92xKrw16Ak/maxresdefault.jpg" alt="Xem video demo">
    </a>
</p> -->

---


## 🚀 Chức năng chính

- **Check-in**: claim phần thưởng hằng ngày.
- **Thực hiện send ETH trên Sepolia**: Gửi ETh đến ví khác trong data.txt (kể cả tự gửi cho ví chính).

---

## 🔧 Yêu cầu ban đầu

- **Haha wallet**: Đăng nhập tài khoản sẵn + đã import seed vào haha wallet. (tool không tự động import ví). Ví có sẵn min 0.05 ETH Sepolia

---

## 📂 Cấu trúc file

| File                             | Mô tả                                      |
| -------------------------------- | ------------------------------------------ |
| `extensions/HaHa-Wallet-Chrome-Web-Store.crx`   | Tiện ích mở rộng Haha Wallet.          |
| `browser_automation.py`          | Code tự động hóa trình duyệt.              |
| `utils.py`                       | Các hàm hỗ trợ chung.                      |
| `index.py`                       | File khởi chạy chương trình chính.         |
| `config_example.txt`             | File cấu hình mẫu cho tool.                |
| `requirements.txt`               | Danh sách các thư viện cần thiết.          |
| `intro.png`                      | Hình ảnh giới thiệu.                       |
| `run_menu.bat`                   | Chạy code với 1 click.                     |
| `run_hidden.vbs`                 | Chạy code với Task scheduler (window).     |

---

## 📌 Hướng dẫn cài đặt

### 1️ Tạo file `data.txt`.

- Mỗi dòng chứa thông tin một profile theo cấu trúc:
  ```plaintext
  <tên_profile>|<mật_khẩu_unlock>|<wallet>|<proxy (tuỳ chọn)>
  ```

  Trong đó:

    - `tên_profile`: Tên của profile.
    - `mật_khẩu_unlock`: Mật khẩu unlock ví Haha wallet.
    - `wallet`: địa chỉ ví (Legacy Wallet)
    - `proxy (tuỳ chọn)`: Có thể là một trong hai dạng sau:
      - `ip:port` → Proxy không có xác thực.
      - `user:pass@ip:port` → Proxy có xác thực bằng tài khoản & mật khẩu.

- Ví dụ:
  ```plaintext
  profile1|12345678|0x....asgc|38.154.227.167:2534              // Đầy đủ
  profile2|12345678|0x....asgc                                  // không proxy
  ```

- **Lưu ý:** Khi sử dụng proxy, trình duyệt có thể **hiển thị cảnh báo "Not Secure"** do vấn đề chứng chỉ bảo mật. Điều này không ảnh hưởng đến hoạt động.

### 2️⃣ Chỉnh sửa cấu hình file `config.txt`.

**Bước 1**: Đổi tên file `config_example.txt` thành `config.txt`

**Bước 2**: Chỉnh sửa file `config.txt` theo hướng dẫn dưới đây:

#### 📱 **Cấu hình Telegram Bot (Khuyến nghị)**
- **Mục đích**: Gửi ảnh chụp màn hình đến Telegram cá nhân trong quá trình thực thi
- **Cách cấu hình**: 
  ```plaintext
  TELE_BOT=<USER_ID>|<BOT_TOKEN>|<ENDPOINT_URL (tùy chọn)>
  ```
- **Ví dụ**:
  ```plaintext
  TELE_BOT=1234567890|1235647890:AAFce0bukTPYase66cr_PH_ahBaCdU36xyc
  ```
- **Lưu ý**: 
  - Có thể thêm nhiều dòng `TELE_BOT` khác nhau
  - Tool sẽ ưu tiên sử dụng bot từ trên xuống
  - `ENDPOINT_URL` chỉ cần thiết khi Telegram bị chặn

  👉 [Hướng dẫn lấy token TELE_BOT và ENDPOINT_URL](#1️⃣-cấu-hình-tele_bot-trong-file-tokentxt-để-theo-dõi-lỗi)

#### 🤖 **Cấu hình AI Bot (Tùy chọn)**
- **Mục đích**: Thực hiện các chức năng đặc biệt (tool này không cần)
- **Cách cấu hình**:
  ```plaintext
  AI_BOT=<AI_BOT_TOKEN>
  ```
- **Ví dụ**:
  ```plaintext
  AI_BOT=AIzjSyAxmkXl_3aixsTcRAJSabUeLmzsSz0ovAg
  ```

  👉 [Hướng dẫn lấy AI_BOT_TOKEN](#2️⃣-cấu-hình-ai_bot-trong-file-tokentxt-khi-tool-cần-thực-hiện-chức-năng-riêng-biệt) (Tool này không cần Bot AI, bỏ qua)

#### 📁 **Cấu hình đường dẫn lưu profile**
- **Mục đích**: Chỉ định nơi lưu trữ dữ liệu profile
- **Cách cấu hình**:
  ```plaintext
  USER_DATA_DIR=<đường_dẫn>
  ```
- **Ví dụ**:
  ```plaintext
  USER_DATA_DIR=E:\profiles\discord
  ```
- **Lưu ý**: Để trống để sử dụng thư mục mặc định (cùng thư mục với tool)

#### 🐍 **Cấu hình đường dẫn Python**
- **Mục đích**: Chỉ định môi trường Python để chạy tool
- **Cách cấu hình**:
  ```plaintext
  PYTHON_PATH=<đường_dẫn_python>
  ```
- **Ví dụ**:
  ```plaintext
  PYTHON_PATH=E:\venv\Scripts\python.exe
  ```
- **Lưu ý**: Để trống để sử dụng Python hệ thống

### 3️ Cài đặt Python & thư viện

Trước tiên, cần cài đặt Python (phiên bản 3.8 trở lên). Nếu chưa có, hãy tải và cài đặt từ [Python Official Site](https://www.python.org/downloads/).

- Kiểm tra phiên bản Python bằng lệnh:
  ```sh
  python --version
  ```
- Cài đặt thư viện yêu cầu:
  ```sh
  pip install -r requirements.txt
  ```

Tuỳ thuộc vào phiên bản và cách cài đặt, có thể gọi python với các lệnh sau: `py`, `python`, `python3`.

---

## ▶ Hướng dẫn sử dụng

### 1️ Chạy chương trình

```sh
python index.py
```

Tuỳ chọn khác

```sh
# Bỏ qua menu và chạy tự động tất cả các profile.
python index.py --auto 

# Chạy tự động ở chế độ ẩn trình duyệt
python index.py --auto --headless

# Chạy ở chế độ tắt GPU vật lý (dùng khi máy tính không có GPU vật lý, ví dụ: VPS, server)
python index.py --disable-gpu
```

### 2️ Các chế độ hoạt động

- **1. Set up**: Chạy chế độ cài đặt ban đầu và chọn profile.
- **2. Chạy Auto**: Chạy chế độ tự động theo cấu hình đã thiết lập.
- **3. Xoá profile**: Chọn xoá profile trong thư mục `user_data` (Nếu có).
- **0. Thoát**: Dừng chương trình.

**💡 Lưu ý:**

- **Lần đầu:** Chạy **Set up (1)** để thiết lập cấu hình cần thiết.
- **Những lần sau:** Chạy **Auto (2)** để tự động thực thi theo luồng đã lập trình.

---

## ⚙ Tùy chỉnh cấu hình

### 🔹 **Thay đổi số lượng profile chạy đồng thời**

```python
browser_manager.run_terminal(
    profiles=PROFILES,
    max_concurrent_profiles=4,
    ...
)
```

Đổi số `4` thành số bất kì

**Lưu ý:** Hầu hết trường hợp bị lỗi là do quá trình load chậm khi chạy nhiều profile cùng lúc. Tuỳ thuộc vào tài nguyên máy tính và tốc độ internet, hãy điều chỉnh con số thích hợp.

### 🔹 **Chặn hình ảnh và video để tăng tốc độ tải trang**

```python
    block_media=True,
```

`True`: không tải hình ảnh và video.

`False`: tải hình ảnh và video (nếu trang web có cloudflare thì bắt buộc phải là `False`).

---

## 🎯 Tips

### 1️⃣ Cấu hình `TELE_BOT` trong file `config.txt` để theo dõi lỗi.

- Mỗi dự án có một bot Telegram riêng, giúp theo dõi lỗi dễ dàng hơn.
- **Hướng dẫn lấy token Telegram:** Truy cập [channel](https://t.me/+8o9ebAT9ZSFlZGNl), tìm bài viết `Cách lấy thông tin cho file config.txt`. ([Video hướng dẫn](https://www.youtube.com/watch?v=2lAiI-s04gY&t=5s))
- **Hướng dẫn lấy ENDPOINT_URL:** ([Video hướng dẫn](https://www.youtube.com/watch?v=2lAiI-s04gY&t=115s))

### 2️⃣ Cấu hình `AI_BOT` trong file `config.txt` khi tool cần thực hiện chức năng riêng biệt.

- **Hướng dẫn lấy token AI bot:**
  - Truy cập [aistudio google](https://aistudio.google.com/apikey)
  - Chọn/Nhấn "Create API Key"
  - Copy "API key"

- **Lưu ý:**
  - Source dùng model `gemini-2.0-flash`.
  - Với gói miễn phí, chạy được khoảng 20-30 dự án/ngày, cho 5-10 profiles/dự án, tương đương khởi chạy **300 lần profile/ngày**

### 3️⃣ Tự động hóa với một cú click (Chỉ áp dụng cho Windows)

Để chạy chương trình đơn giản hơn, bạn có thể sử dụng file `run_menu.bat` bằng cách click đúp chuột trực tiếp vào file, thay vì phải mở code và gõ lệnh trong CMD.

### 4️⃣ Chạy tự động ẩn với Windows Task Scheduler

1. Mở **Task Scheduler** bằng cách tìm kiếm trên Windows.
2. Menu > Action > **Create Task..**.
3. Tab **General**: đặt tên cho task
4. Tab **Triggers**: thiết lập lịch chạy
  - Click **New...**
  - Tại **Begin the task**: chọn **At startup** để chạy khi khởi động Windows, hoặc **On a schedule** để đặt lịch cụ thể.
  - Chọn **Enabled** để kích hoạt trigger.
5. Tab **Actions**: thiết lập chương trình chạy
  - Click **New...**
  - **Action**: chọn **Start a Program**
  - **Program/script**: nhập `wscript.exe`
  - **Add arguments**: dán đường dẫn đầy đủ tới file `run_hidden.vbs`
6. Tab **Conditions** (optional): 
  - Bỏ chọn **Start the task only if the computer is on AC power**
  - Bỏ chọn **Stop if the computer switches to battery power**
7. Tab **Settings** (optional):
  - Chọn **Run task as soon as possible after a scheduled start is missed**
  - Chọn **If the task fails, restart every: 1 minute** và **Attempt to restart up to: 3 times**
8. Click **OK** để lưu task.

Bây giờ, chương trình sẽ tự động chạy ẩn dưới nền window theo lịch trình đặt trước. 🚀

---

## 🔗 Thông tin liên hệ

📢 **Telegram Channel:** [Airdrop Automation](https://t.me/+8o9ebAT9ZSFlZGNl)

💰 **Ủng hộ tác giả:**

- **EVM:** `0x3b3784f7b0fed3a8ecdd46c80097a781a6afdb09`
- **SOL:** `4z3JQNeTnMSHYeg9FjRmXYrQrPHBnPg3zNKisAJjobSP`
- **TON:** `UQDKgC6TesJJU9TilGYoZfj5YYtIzePhdzSDJTctJ-Z27lkR`
- **SUI:** `0x5fb56584bf561a4a0889e35a96ef3e6595c7ebd13294be436ad61eaf04be4b09`
- **APT (APTOS):** `0x557ea46189398da1ddf817a634fa91cfb54a32cfc22cadd98bb0327c880bac19`

🙏 Khi ủng hộ, nếu không thấy phiền, Bạn có thể gửi token chính của mạng. Cám ơn Bạn đã hỗ trợ!