# Local Run Checklist (LINE OA)

เช็กลำดับนี้เมื่อทัก LINE แล้วบอทไม่ตอบ

## 1) เตรียม env

```bash
cd 07_sourcecode/line-ai-agent
cp .env.example .env
# แล้วแก้ค่าใน .env ให้ครบ โดยเฉพาะ LINE_CHANNEL_SECRET, LINE_CHANNEL_ACCESS_TOKEN, GEMINI_API_KEY
# และตั้ง LLM_PROVIDER=gemini
```

## 2) ติดตั้งและรันเซิร์ฟเวอร์

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

ต้องเห็นหน้า `http://localhost:8000/` และไม่มีข้อความ error ตอน start

## 3) เปิด tunnel ไปเครื่องเรา

ใช้ ngrok หรือ cloudflared ก็ได้ ตัวอย่าง ngrok:

```bash
ngrok http 8000
```

นำ URL มาตั้งใน LINE Developers เป็น:

`https://<your-domain>/webhook`

## 4) ตั้งค่า LINE Developers

- เปิด `Use webhook`
- กด `Verify` ต้องผ่าน (Success)
- ตรวจว่า Channel access token ถูกต้อง (ค่าตรงกับ `.env`)

## 5) ตั้งค่า OA Manager

ระหว่างเทสต์ แนะนำปิด auto-reply/greeting message ชั่วคราว

## 6) Debug เมื่อยังไม่ตอบ

- ถ้า `Verify` ไม่ผ่าน: URL ไม่ถึงเครื่องเรา / endpoint ไม่ถูก
- ถ้าโดน `400 Invalid signature`: secret/token ไม่ตรง
- ถ้าทักแล้วเงียบและ log ไม่มี event เข้า: webhook ยังไม่วิ่งถึง server
- ถ้า event เข้าแต่ตอบไม่ได้: ดู error จาก LINE reply API ใน console log

## 7) ทดสอบขั้นต่ำ

ส่งข้อความ "สวัสดี" จากบัญชีที่ add OA แล้ว

- ถ้า `GEMINI_API_KEY` ถูกต้อง จะได้คำตอบจาก AI
- ถ้า Gemini มีปัญหา ระบบควรตอบข้อความแจ้งเตือนแทน (ไม่ควรเงียบ)
