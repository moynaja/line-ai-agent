# แผนการพัฒนา LINE Bot (FastAPI + Gemini AI + dh-task)

โปรเจกต์นี้จะสร้าง LINE Official Account Bot ที่ใช้ **FastAPI** เป็น Webhook Server, **Gemini AI** เป็นสมองในการเข้าใจภาษาธรรมชาติ และเชื่อมต่อเข้ากับสคริปต์ **`klive_tasks_api.py`** เพื่อให้ผู้ใช้สามารถสอบถามและสั่งงานในระบบ **dh-task** ได้โดยตรงผ่านไลน์

---

## 🏗️ โครงสร้างสถาปัตยกรรม (Architecture)

```
[ LINE App ] 
     │
     ▼ (Webhook POST /webhook)
[ FastAPI Server (main.py) ]
     │
     ├───► [ Gemini API ] (วิเคราะห์คำสั่งผ่าน Function Calling หรือ NLP)
     │
     └───► [ Subprocess Run: ~/tools/klive_tasks_api.py ] (เรียกใช้งาน API ของ dh-task)
             │
             ▼
       [ dh-task Server ]
```

---

## 📁 โครงสร้างโปรเจกต์ (Project Directory Structure)

```
PJ-LineBOT/
├── .env                  # ไฟล์ตั้งค่าตัวแปรระบบ (API Keys, Secrets)
├── .gitignore            # ป้องกันไฟล์สำคัญหลุดเข้า git
├── PLAN.md               # แผนงานและการออกแบบระบบ (ไฟล์นี้)
├── requirements.txt      # รายการ Python dependencies
└── main.py               # โค้ดหลักของ FastAPI Server
```

---

## 🛠️ รายละเอียดการติดตั้งและส่วนประกอบ (Components)

### 1. `requirements.txt`
เราจะใช้ Library ที่ทันสมัยและปลอดภัย:
* `fastapi`: ความรวดเร็วในการรัน API
* `uvicorn[standard]`: ASGI Server สำหรับรัน FastAPI
* `line-bot-sdk`: SDK อย่างเป็นทางการของ LINE เพื่อจัดการข้อความและการส่งข้อความกลับ
* `google-generativeai`: SDK ของ Google สำหรับเชื่อมต่อใช้งานโมเดล Gemini
* `python-dotenv`: อ่านค่า `.env` เข้ามาใน Environment
* `httpx` หรือ `requests`: เผื่อใช้เรียก API อื่นๆ เพิ่มเติม

### 2. `.env`
เก็บความลับทั้งหมดให้ปลอดภัย:
```env
# LINE Configurations
LINE_CHANNEL_SECRET=your_line_channel_secret_here
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token_here

# Gemini AI Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# dh-task API Configuration (ดึงมาจาก ~/.zshrc)
KLIVE_API_URL=https://tasks.dohome.technology/api
KLIVE_TASKS_API_URL=https://tasks.dohome.technology/api
KLIVE_API_TOKEN=pat_c60f112e6dc54ea9bbad4c14c935d6f3
```

### 3. `main.py`
การทำงานภายใน Webhook ของ FastAPI:
* **Webhook Verification:** ตรวจสอบ Signature `X-Line-Signature` ทุกครั้งที่ได้ Request จาก LINE เพื่อความปลอดภัย
* **Event Router:** ตรวจสอบข้อความตัวอักษร (Text Message) ที่ส่งเข้ามา
* **Gemini Processor:** 
  * ส่งข้อความเข้าไปที่ Gemini พร้อมกับ System Instruction บอกบทบาทว่า *"คุณเป็นผู้ช่วยจัดการงาน dh-task ในไลน์..."*
  * เปิดใช้งาน **Function Calling (Tools)** เพื่อแปลงคำพูดธรรมชาติของผู้ใช้ไปเป็นพารามิเตอร์การเรียกใช้งาน เช่น:
    * *"ขอดูงานทั้งหมดหน่อย"* ➡️ เรียกคำสั่ง `k-list`
    * *"สร้างทาสก์ใหม่ให้หน่อย ชื่องาน: แก้บั๊กพิมพ์ใบเสร็จ"* ➡️ เรียกคำสั่ง `k-create --title "แก้บั๊กพิมพ์ใบเสร็จ"`
* **dh-task Executor:** 
  * นำพารามิเตอร์รันคำสั่งโดยอ้อมผ่าน `subprocess.run(["python3", "/Users/moynaja/tools/klive_tasks_api.py", ...])`
  * ข้อดีของการทำแบบนี้คือ **ประหยัด Token, มีความเสถียรสูง และไม่ต้องเขียนโค้ดเรียก API 800+ บรรทัดซ้ำซ้อน**
* **Reply Handler:** ส่งผลลัพธ์ที่เป็น Markdown สวยงามกลับไปทางไลน์ในรูปแบบ Text หรือใช้ Flex Message

---

## 🚀 ขั้นตอนการดำเนินการ (Execution Steps)

1. **เขียนไฟล์ `requirements.txt`** และติดตั้ง dependencies
2. **สร้างไฟล์ `.env`** ด้วยข้อมูลที่สมบูรณ์
3. **สร้างไฟล์ `main.py`** พร้อมกับเขียนระบบ Webhook, การดึงคำสั่งผ่าน Gemini AI และการเรียกรันคำสั่ง `klive_tasks_api.py`
4. **สอนวิธีทดสอบในเครื่องตัวเองด้วย `ngrok`** เพื่อทดลองพิมพ์คุยกับ LINE OA จริงๆ
