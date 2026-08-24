# 07_sourcecode

โฟลเดอร์นี้ใช้เก็บ **source code อ้างอิงจริง** เพื่อประกบกับเอกสารวิเคราะห์ใน `00_overview` ถึง `06_engineering`

## ที่มาของโค้ด

- Repository ต้นทาง: `https://github.com/moynaja/line-ai-agent.git`
- โฟลเดอร์ที่ดึงมา: `07_sourcecode/line-ai-agent`
- รูปแบบการนำเข้า: snapshot source code (ไม่รวม `.git`)

## แนะนำลำดับการอ่าน

1. อ่านภาพรวมระบบที่ `line-ai-agent/CLAUDE.md`
2. ดูโครงสร้าง FastAPI ที่ `line-ai-agent/app/main.py`
3. ดู logic webhook ที่ `line-ai-agent/app/handlers/webhook_handler.py`
4. ดู service หลัก (Gemini, dh-task, LINE) ใน `line-ai-agent/app/services/`
5. ดูการ deploy ที่ `line-ai-agent/render.yaml`

## โครงสร้างย่อ

- `line-ai-agent/app/` — FastAPI app, handlers, services
- `line-ai-agent/liff/` — หน้า LIFF (verify / project)
- `line-ai-agent/assets/` — รูปและไฟล์ที่ใช้กับ Rich Menu/Flex
- `line-ai-agent/tools/klive_tasks_api.py` — ตัวช่วยเชื่อม dh-task
- `line-ai-agent/requirements.txt` — dependencies ของโปรเจกต์

## หมายเหตุการใช้งาน

- โค้ดในโฟลเดอร์นี้ตั้งใจให้ใช้ **อ่าน/วิเคราะห์/อ้างอิง** เป็นหลัก
- หากต้องการพัฒนาต่อจริง แนะนำทำงานแยกใน repo ต้นทางพร้อมประวัติ git

## Mapping: เอกสาร 00-06 → โค้ดจริง

| เอกสาร | เนื้อหาที่ครอบคลุม | ไฟล์โค้ดที่ควรเปิดคู่กัน |
|---|---|---|
| `00_overview/product_context.md` | ภาพรวมผลิตภัณฑ์และขอบเขตระบบ | `line-ai-agent/CLAUDE.md`, `line-ai-agent/PLAN.md` |
| `03_product/prd/prd.md` | ขอบเขต MVP, user intent, use cases | `line-ai-agent/app/handlers/webhook_handler.py`, `line-ai-agent/app/services/gemini_service.py` |
| `04_requirements/functional_requirements.md` | ฟังก์ชันหลักที่ผู้ใช้ต้องทำได้ | `line-ai-agent/app/handlers/webhook_handler.py`, `line-ai-agent/app/services/*.py` |
| `04_requirements/business_rules.md` | กฎธุรกิจ/เงื่อนไขการตัดสินใจ | `line-ai-agent/app/services/access_service.py`, `line-ai-agent/app/services/pending_action_service.py`, `line-ai-agent/app/services/mode_service.py` |
| `04_requirements/permission_requirements.md` | สิทธิ์ผู้ใช้และการอนุมัติ | `line-ai-agent/app/services/access_service.py`, `line-ai-agent/app/handlers/webhook_handler.py`, `line-ai-agent/app/handlers/liff_handler.py` |
| `04_requirements/ai_requirements.md` | พฤติกรรม AI/Tool calling | `line-ai-agent/app/services/gemini_service.py`, `line-ai-agent/docs/klive-tasks-SKILL.md` |
| `05_design/01_user_flows/*.md` | user flow การใช้งานในแชตและเมนู | `line-ai-agent/app/handlers/webhook_handler.py`, `line-ai-agent/scripts/setup_richmenu.sh` |
| `05_design/04_screen_specs/*.md` | รายละเอียดหน้าจอและองค์ประกอบ UI | `line-ai-agent/liff/verify/index.html`, `line-ai-agent/liff/project/index.html`, `line-ai-agent/flex_builder.py` |
| `06_engineering/backend_architecture/backend_architecture.md` | สถาปัตยกรรม backend | `line-ai-agent/app/main.py`, `line-ai-agent/app/handlers/*.py`, `line-ai-agent/app/services/*.py` |
| `06_engineering/api/api_spec.md` | สเปก endpoint และสัญญา API | `line-ai-agent/app/main.py` |
| `06_engineering/database/database_schema.md` | โครงสร้างข้อมูลและการ persist state | `line-ai-agent/app/services/access_service.py`, `line-ai-agent/app/services/notes_service.py`, `line-ai-agent/app/services/reminder_service.py`, `line-ai-agent/app/services/pending_action_service.py` |
| `06_engineering/web/web_architecture.md` | ฝั่งเว็บ/LIFF/asset flow | `line-ai-agent/liff/`, `line-ai-agent/assets/`, `line-ai-agent/app/handlers/liff_handler.py` |

### วิธีใช้ mapping นี้ให้เร็ว

1. เปิดเอกสารที่ต้องการจากโฟลเดอร์ `00-06`
2. เปิดไฟล์โค้ดจากคอลัมน์ขวาคู่กันทีละไฟล์
3. ตรวจว่า requirement/design ในเอกสารถูก implement ครบหรือยัง
4. จด gap หรือ mismatch แล้วย้อนกลับไปอัปเดตเอกสาร/โค้ดให้ตรงกัน
