# Gap Checklist (เอกสาร ↔ โค้ด)

ไฟล์นี้ใช้ตรวจว่า requirement/design ในเอกสาร `00-06` ถูก implement ในโค้ด `07_sourcecode/line-ai-agent` แล้วหรือยัง

สถานะที่ใช้:
- `✅ ครบ` = มีในโค้ดและพฤติกรรมตรงตามเอกสาร
- `🟡 บางส่วน` = มีบางส่วน/ยังไม่ครบ edge cases
- `❌ ยังไม่มี` = ยังไม่พบ implementation
- `⚪ ไม่อยู่ในขอบเขต` = ตั้งใจไม่ทำในรอบนี้

---

## 1) Product Context / PRD

| รายการตรวจ | เอกสารอ้างอิง | โค้ดอ้างอิง | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| ระบบเป็น LINE OA + AI Assistant สำหรับจัดการงาน | `00_overview/product_context.md` | `line-ai-agent/CLAUDE.md`, `line-ai-agent/app/main.py` | `✅ ครบ` | |
| รองรับ MVP use cases ตาม PRD | `03_product/prd/prd.md` | `line-ai-agent/app/handlers/webhook_handler.py`, `line-ai-agent/app/services/gemini_service.py` | `🟡 บางส่วน` | ตรวจทีละ use case |
| ขอบเขตที่ไม่ทำใน MVP ถูกระบุชัดเจน | `03_product/prd/prd.md` | `line-ai-agent/PLAN.md`, `line-ai-agent/docs/design-ai-agent-improvements.md` | `🟡 บางส่วน` | |

---

## 2) Functional Requirements

| รายการตรวจ | เอกสารอ้างอิง | โค้ดอ้างอิง | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| รับ webhook จาก LINE และตรวจ signature | `04_requirements/functional_requirements.md` | `line-ai-agent/app/main.py` | `✅ ครบ` | |
| ส่งข้อความตอบกลับผู้ใช้ในแต่ละ event | `04_requirements/functional_requirements.md` | `line-ai-agent/app/services/line_service.py`, `line-ai-agent/app/handlers/webhook_handler.py` | `✅ ครบ` | |
| เรียก AI เพื่อแปล intent เป็นคำสั่งงาน | `04_requirements/functional_requirements.md` | `line-ai-agent/app/services/gemini_service.py` | `✅ ครบ` | |
| เชื่อมระบบงานภายนอก (dh-task/klive) | `04_requirements/functional_requirements.md` | `line-ai-agent/app/services/klive_service.py`, `line-ai-agent/tools/klive_tasks_api.py` | `✅ ครบ` | |
| รองรับฟีเจอร์โน้ต/เตือนความจำ | `04_requirements/functional_requirements.md` | `line-ai-agent/app/services/notes_service.py`, `line-ai-agent/app/services/reminder_service.py` | `✅ ครบ` | |

---

## 3) Business Rules

| รายการตรวจ | เอกสารอ้างอิง | โค้ดอ้างอิง | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| ผู้ใช้ใหม่ต้องผ่าน flow verify/approval | `04_requirements/business_rules.md` | `line-ai-agent/app/handlers/liff_handler.py`, `line-ai-agent/app/services/access_service.py` | `✅ ครบ` | |
| คำสั่งเสี่ยง (ลบ/แก้ไข) ต้องยืนยันก่อนรันจริง | `04_requirements/business_rules.md` | `line-ai-agent/app/services/pending_action_service.py`, `line-ai-agent/app/handlers/webhook_handler.py`, `line-ai-agent/app/services/gemini_service.py` | `✅ ครบ` | |
| ยกเลิกคำสั่งที่หมดเวลา confirm | `04_requirements/business_rules.md` | `line-ai-agent/app/services/pending_action_service.py` | `🟡 บางส่วน` | ตรวจ TTL จริง |
| กฎ fallback เมื่อ Firestore มีปัญหา | `04_requirements/business_rules.md` | `line-ai-agent/app/services/*.py`, `line-ai-agent/app/handlers/webhook_handler.py` | `✅ ครบ` | fail-open pattern |

---

## 4) Permission Requirements

| รายการตรวจ | เอกสารอ้างอิง | โค้ดอ้างอิง | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| แยกสิทธิ์ Admin vs User ปกติ | `04_requirements/permission_requirements.md` | `line-ai-agent/app/config.py`, `line-ai-agent/app/services/access_service.py` | `✅ ครบ` | |
| Admin อนุมัติ/ปฏิเสธผู้ใช้ผ่าน postback | `04_requirements/permission_requirements.md` | `line-ai-agent/app/handlers/webhook_handler.py` | `✅ ครบ` | |
| endpoint dashboard มีการ gate ด้วย user_id/status | `04_requirements/permission_requirements.md` | `line-ai-agent/app/main.py` | `✅ ครบ` | |

---

## 5) AI Requirements

| รายการตรวจ | เอกสารอ้างอิง | โค้ดอ้างอิง | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| ใช้ model Gemini ผ่าน SDK | `04_requirements/ai_requirements.md` | `line-ai-agent/app/services/gemini_service.py`, `line-ai-agent/requirements.txt` | `✅ ครบ` | |
| มี function/tool calling สำหรับคำสั่งงาน | `04_requirements/ai_requirements.md` | `line-ai-agent/app/services/gemini_service.py` | `✅ ครบ` | |
| มี guardrail สำหรับคำสั่งเสี่ยง | `04_requirements/ai_requirements.md` | `line-ai-agent/app/services/gemini_service.py`, `line-ai-agent/app/services/pending_action_service.py` | `✅ ครบ` | |
| จัดการกรณี AI ใช้งานไม่ได้ (degrade gracefully) | `04_requirements/ai_requirements.md` | `line-ai-agent/app/services/gemini_service.py` | `✅ ครบ` | |

---

## 6) Design / UX Flow

| รายการตรวจ | เอกสารอ้างอิง | โค้ดอ้างอิง | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| flow การใช้งานผ่าน Rich Menu | `05_design/01_user_flows/*.md` | `line-ai-agent/scripts/setup_richmenu.sh`, `line-ai-agent/app/handlers/webhook_handler.py` | `✅ ครบ` | |
| หน้าจอ LIFF verify ทำงานเชื่อม backend | `05_design/04_screen_specs/screen_spec_public_booking_page.md` | `line-ai-agent/liff/verify/index.html`, `line-ai-agent/app/main.py` | `🟡 บางส่วน` | ชื่อสเปกอาจต่างโดเมน |
| หน้าจอ dashboard แบบ full-screen | `05_design/04_screen_specs/screen_spec_owner_dashboard.md` | `line-ai-agent/liff/project/index.html`, `line-ai-agent/app/main.py`, `line-ai-agent/app/services/dashboard_view.py` | `✅ ครบ` | |
| Flex message แสดงข้อมูลโปรเจกต์/งาน | `05_design/04_screen_specs/*.md` | `line-ai-agent/flex_builder.py` | `✅ ครบ` | |

---

## 7) Engineering Spec

| รายการตรวจ | เอกสารอ้างอิง | โค้ดอ้างอิง | สถานะ | หมายเหตุ |
|---|---|---|---|---|
| backend architecture ตรงกับ implementation | `06_engineering/backend_architecture/backend_architecture.md` | `line-ai-agent/app/main.py`, `line-ai-agent/app/handlers/`, `line-ai-agent/app/services/` | `✅ ครบ` | |
| API spec ตรงกับ route ที่เปิดใช้งานจริง | `06_engineering/api/api_spec.md` | `line-ai-agent/app/main.py` | `🟡 บางส่วน` | ควรเทียบพารามิเตอร์ละเอียด |
| database schema ตรงกับข้อมูลที่ persist จริง | `06_engineering/database/database_schema.md` | `line-ai-agent/app/services/access_service.py`, `line-ai-agent/app/services/notes_service.py`, `line-ai-agent/app/services/reminder_service.py` | `🟡 บางส่วน` | ควรเทียบ field-by-field |
| web architecture ตรงกับ LIFF + assets จริง | `06_engineering/web/web_architecture.md` | `line-ai-agent/liff/`, `line-ai-agent/assets/`, `line-ai-agent/app/handlers/liff_handler.py` | `✅ ครบ` | |

---

## 8) Action List (เติมระหว่างรีวิว)

| ลำดับ | ประเด็นที่พบ | ระดับความสำคัญ | เจ้าของ | สถานะ |
|---|---|---|---|---|
| 1 | | High / Medium / Low | | Open |
| 2 | | High / Medium / Low | | Open |
| 3 | | High / Medium / Low | | Open |

---

## วิธีใช้งานแนะนำ

1. รีวิวทีละชุดเอกสารจาก `00` ไป `06`
2. อัปเดตสถานะในตารางจาก `🟡` ให้ชัดขึ้นเป็น `✅` หรือ `❌`
3. ทุก gap ที่พบให้ลงใน Action List ทันที
4. ปิดรอบโดยสรุปเฉพาะหัวข้อที่ยัง `❌` หรือ `🟡`
