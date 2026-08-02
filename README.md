# STV Lost & Found 🚨✨
ระบบศูนย์กลางข้อมูลและแจ้งเตือนของหายได้คืนสำหรับนักเรียน โรงเรียนสิชลคุณาธารวิทยา

โปรเจกต์นี้แบ่งออกเป็น 2 ส่วนหลักคือ **Backend (FastAPI)** และ **Frontend (HTML/CSS/JS)** โดยเชื่อมต่อข้อมูลกับ **Supabase** และระบบส่งการแจ้งเตือนประกาศใหม่ผ่าน **LINE Official Account (LINE OA) Broadcast** รวมถึงรองรับการอัปโหลดรูปภาพผ่าน **Cloudflare R2**// ทำอะไรกับฐานข้อมูลติดต่อกัส เดียวเชื่อมให้

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)

```text
lost-and-found-master/
├── backend/                  # ส่วนของเซิร์ฟเวอร์ระบบหลังบ้าน (Python FastAPI)
│   ├── database.py           # เชื่อมต่อกับฐานข้อมูล Supabase
│   ├── main.py               # API Endpoints (Auth, Posts, Upload, Admin, LINE OA)
│   ├── models.py             # Data Schemas (Pydantic models)
│   └── requirements.txt      # แพ็กเกจ Python ที่ต้องติดตั้ง
├── frontend/                 # ส่วนของหน้าเว็บระะบบหน้าบ้าน (HTML/CSS/JS)
│   ├── index.html            # หน้าแรก (แสดงประกาศล่าสุด)
│   ├── search.html           # หน้าค้นหาและกรองประเภทสิ่งของ
│   ├── create-post.html      # หน้าสร้างประกาศใหม่ (รองรับบีบอัดภาพและอัปโหลด)
│   ├── post-detail.html      # หน้าแสดงรายละเอียดประกาศและช่องทางติดต่อ
│   ├── profile.html          # หน้าโปรไฟล์ส่วนตัวและประวัติการลงประกาศ
│   ├── login.html            # หน้าเข้าสู่ระบบ (Email หรือ LINE Login)
│   ├── register.html         # หน้าลงทะเบียนผู้ใช้งานใหม่
│   ├── chat.html             # หน้าแสดงรายการแชท (Mockup เท่านั้น)
│   ├── chat-room.html        # หน้าห้องแชทจำลอง (Mockup เท่านั้น)
│   ├── admin/                # แผงควบคุมสำหรับผู้ดูแลระบบ
│   │   ├── posts.html        # หน้าจัดการประกาศ (สำหรับ Admin)
│   │   └── super.html        # หน้าจัดการบทบาทผู้ใช้และลบผู้ใช้ (สำหรับ Super Admin)
│   ├── css/
│   │   └── style.css         # ไฟล์สไตล์หลักของเว็บ
│   ├── js/                   # โฟลเดอร์ JavaScript (ย้ายมาตำแหน่งที่ถูกต้องเรียบร้อยแล้ว)
│   │   ├── api.js            # ฟังก์ชันเรียกใช้งาน API ของหลังบ้าน
│   │   └── app.js            # ฟังก์ชันควบคุมหน้าบ้านและแสดงผลข้อมูล
│   └── picture/              # โฟลเดอร์เก็บรูปภาพโลโก้และรูปภาพระบบ
├── vercel.json               # สำหรับการตั้งค่าเพื่อ Deploy ขึ้น Vercel
└── .gitignore                # ตั้งค่าเพื่อไม่ให้ Git ติดตามไฟล์ที่ไม่จำเป็น (เช่น .env)
```

---

## 🛠️ เทคโนโลยีที่ใช้ (Tech Stack)

* **Frontend**: HTML5, Vanilla CSS, Tailwind CSS (via CDN), Lucide Icons, SweetAlert2
* **Backend**: FastAPI (Python), Uvicorn
* **Database & Auth**: Supabase (PostgreSQL, GoTrue for Authentication)
* **Storage**: Cloudflare R2 (S3-Compatible Storage) หรือ Supabase Storage
* **Notification**: LINE Messaging API (Flex Message Broadcast)

---

## 🚀 วิธีรันระบบหลังบ้าน (Backend Server Setup)

### 1. การเตรียมสภาพแวดล้อมและติดตั้งแพ็กเกจ
แนะนำให้ติดตั้งผ่าน Python 3.9 ขึ้นไป โดยสร้าง Virtual Environment เพื่อความสะอาดของระบบ:

```bash
# 1. เข้าไปที่โฟลเดอร์หลังบ้าน
cd backend

# 2. สร้าง Virtual Environment (ทำเฉพาะครั้งแรก)
python -m venv venv

# 3. เปิดใช้งาน Virtual Environment
# สำหรับ Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# สำหรับ macOS/Linux:
source venv/bin/activate

# 4. ติดตั้งแพ็กเกจที่จำเป็น
pip install -r requirements.txt
```

### 📦 รายชื่อแพ็กเกจที่ใช้งาน (ใน `requirements.txt`)
| แพ็กเกจ | ประโยชน์ |
| :--- | :--- |
| `fastapi` | เฟรมเวิร์กสำหรับสร้าง REST APIs |
| `uvicorn` | ASGI Web Server เพื่อรัน FastAPI |
| `supabase` | SDK สำหรับเชื่อมต่อฐานข้อมูลและการล็อกอินของ Supabase |
| `pydantic` | ตรวจสอบและระบุรูปแบบของข้อมูลรับ-ส่ง |
| `python-multipart` | รองรับการรับไฟล์รูปภาพผ่านฟอร์ม (Form Data) |
| `python-dotenv` | โหลดค่ากำหนดในไฟล์ `.env` เข้ามาเป็น Environment Variables |
| `line-bot-sdk` | เชื่อมต่อกับระบบส่งแจ้งเตือนและ Broadcast ผ่าน LINE OA |
| `boto3` & `botocore` | เชื่อมต่อเพื่อบันทึกไฟล์รูปภาพไปยัง Cloudflare R2 |
| `httpx` | ใช้ทำ HTTP Request ในโค้ดแบบ Async (สำหรับระบบ LINE Login) |

### 2. การตั้งค่า Environment Variables (ไฟล์ `.env`)
ให้สร้างไฟล์ชื่อ `.env` ไว้ในโฟลเดอร์ `backend/` แล้วกรอกข้อมูลดังนี้:

```env
# Supabase Configuration
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_role_key

# LINE Login & Broadcast Configuration
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CLIENT_ID=your_line_login_client_id
LINE_CHANNEL_SECRET=your_line_login_channel_secret
LINE_CALLBACK_URL=http://127.0.0.1:8000/auth/callback/line

# Cloudflare R2 (หากไม่ตั้งค่า จะใช้ระบบอัปโหลดของ Supabase Storage เป็นค่าเริ่มต้น)
R2_ACCOUNT_ID=your_cloudflare_account_id
R2_ACCESS_KEY_ID=your_r2_access_key
R2_SECRET_ACCESS_KEY=your_r2_secret_key
R2_BUCKET_NAME=your_r2_bucket_name
R2_PUBLIC_URL=https://pub-xxxx.r2.dev
```

### 3. รันเซิร์ฟเวอร์
```bash
python main.py
```
เซิร์ฟเวอร์จะเริ่มต้นทำงานที่ลิ้งก์ `http://127.0.0.1:8000` โดยสามารถเข้าไปดูเอกสาร API ได้ที่ `http://127.0.0.1:8000/docs`

---

## 🌐 วิธีรันระบบหน้าบ้าน (Frontend Setup)

เนื่องจากระบบหน้าบ้านเป็น Static HTML ผู้ใช้งานสามารถรันโดยตรงได้เลยผ่านเว็บเซิร์ฟเวอร์จำลอง:

1. แนะนำให้ใช้โปรแกรม **VS Code** และติดตั้ง Extension **Live Server**
2. คลิกขวาที่ไฟล์ `frontend/index.html` แล้วเลือก **Open with Live Server**
3. หน้าเว็บจะรันขึ้นมาที่พอร์ต `http://127.0.0.1:5500/frontend/index.html` หรือพอร์ตที่ตั้งค่าไว้

> 🚨 **ข้อควรระวังเรื่องเส้นทางลิ้งก์ (Path)**:
> ในโค้ดหลังบ้าน (`backend/main.py` บรรทัดที่ 211) มีการกำหนดปลายทางหลังจาก Login ผ่าน LINE สำเร็จไว้ที่:
> `http://127.0.0.1:5500/lost-and-found/frontend/index.html#access_token=...`
> หากคุณเปิดหน้าบ้านด้วย Live Server โดยมีโครงสร้างพอร์ตที่ต่างออกไป ให้ไปแก้ไข URL ปลายทางตรงจุดนี้ใน `main.py` เพื่อให้ระบบนำทางกลับมาได้อย่างถูกต้อง

---

## 📊 สถานะของแต่ละฟังก์ชันระบบ (Feature Status)

### ✅ ฟังก์ชันที่เสร็จสิ้นและใช้งานได้จริง
* [x] **การลงทะเบียนและเข้าสู่ระบบ (Authentication)**: สมัครสมาชิกและล็อกอินผ่านระบบ Email/Password รวมถึงการล็อกอินด้วยบัญชี LINE (LINE OAuth) สำเร็จ
* [x] **การลงประกาศสิ่งของ (Post Management)**: สร้างประกาศสิ่งของตามหา (lost) หรือเจอของ (found) เลือกหมวดหมู่ ระบุสถานที่ วันที่ และรูปภาพได้
* [x] **การบีบอัดและอัปโหลดภาพ (Image Compressor & Upload)**: ระบบหน้าบ้านจะบีบอัดรูปภาพให้มีขนาดเล็กลงก่อนส่งไปเก็บที่เซิร์ฟเวอร์เพื่อความรวดเร็ว และหลังบ้านรองรับการจัดเก็บรูปภาพผ่าน Cloudflare R2 (และ Supabase Storage เป็นตัวสำรอง)
* [x] **หน้าสรุปข้อมูลและโปรไฟล์ (Profile Page)**: แสดงประวัติประกาศของผู้ใช้รายนั้นๆ และสถิติจำนวนของหาย/เจอของ
* [x] **ระบบผู้ดูแลระบบ (Admin & Super Admin Panel)**:
  * **Admin**: ตรวจสอบและเปลี่ยนสถานะประกาศของทุกคนเป็น "รอประกาศ" (pending), "ประกาศแล้ว" (published), หรือ "เจ้าของมารับแล้ว" (claimed) รวมถึงสิทธิ์ในการลบประกาศ
  * **Super Admin**: มีสิทธิ์ในการเปลี่ยนบทบาท (Role) ของผู้ใช้อื่นให้เป็น Admin, แก้ไขชื่อโปรไฟล์ผู้ใช้อื่น และแบน/ปลดแบนสมาชิกได้
* [x] **ระบบแจ้งเตือนผ่านไลน์ (LINE Broadcast)**: เมื่อมีการสร้างประกาศใหม่ที่ยืนยันแล้ว ระบบหลังบ้านจะส่งการแจ้งเตือนด้วยรูปภาพการ์ดข้อมูลสวยงาม (Flex Message) ไปยังห้องแชทของ LINE OA ทันที

### ⚠️ ฟังก์ชันที่เป็นแบบจำลอง (Mockup / ยังไม่เสร็จสิ้น) ????กัสว่าไม่ต้องทำน่ะ
* [ ] **ระบบห้องแชทส่วนตัว (In-App Chat)**:
  * ในหน้าเว็บ `chat.html` และ `chat-room.html` ปัจจุบันเป็นเพียง**หน้าจำลองสไตล์ UI (Mockup)** ที่มีข้อความจำลองและไม่สามารถส่งหรือรับข้อความจริงกับผู้ใช้คนอื่นได้
  * *จุดที่ต้องทำต่อ*: เชื่อมโยงระบบส่งข้อความเข้ากับ API `/messages` ของระบบหลังบ้าน หรือพัฒนาส่วนของ Real-time WebSocket เพิ่มเติมเพื่อให้ใช้งานระบบแชทได้จริง

---

## 🐞 ประเด็นสำคัญที่แก้ไขแล้วและข้อสังเกต (Fixed Issues & Notes)

### 📌 1. แก้ไขตำแหน่งโฟลเดอร์ JavaScript เรียบร้อยแล้ว (Resolved JS Path Bug)
* **เดิม**: หน้าเว็บ HTML ต่างๆ เรียกใช้สคริปต์ควบคุมผ่าน `js/api.js` และ `js/app.js` แต่ไฟล์ย่อยถูกจัดเก็บผิดตำแหน่งอยู่ใน `frontend/css/js/` ทำให้สคริปต์ไม่โหลด
* **แก้ไขแล้ว**: ทางเราได้ทำการย้ายโฟลเดอร์ `js` ขึ้นมาอยู่ภายใต้ `frontend` โดยตรง (`frontend/js/...`) เรียบร้อยแล้ว ตอนนี้สคริปต์และปุ่มในหน้าต่างๆ สามารถเรียกใช้งานและตอบสนองกับ API ได้ปกติทันที

### 📌 2. ปัญหา URL สำหรับเปลี่ยนเส้นทาง LINE Login (Redirect URL Mismatch)
* **ข้อสังเกต**: หากตั้งชื่อโฟลเดอร์หลักต่างออกไป หรือเปิด Live Server จากระดับโฟลเดอร์ที่ต่างกัน URL หลังล็อกอินเสร็จใน `backend/main.py` จะเกิดอาการ 404 (หาหน้าแรกไม่เจอ)
* **วิธีแก้ไข**: ตรวจสอบหน้า URL ของหน้าบ้านที่รันผ่าน Live Server ของคุณ แล้วนำไปอัปเดตค่า URL ตัวแปร `frontend_url` ใน `backend/main.py` (บรรทัดที่ 211) ให้ตรงกัน
