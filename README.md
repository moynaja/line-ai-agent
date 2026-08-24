# Minimum Starter Kit — เอกสารตัวอย่างสมบูรณ์

โฟลเดอร์นี้เป็น **ตัวอย่างเอกสารที่เขียนสมบูรณ์แล้ว** (ไม่ใช่ template เปล่า) ตามหลักการ [Minimum Recommended Documents](../99_templates/documentation/minimum_reccomend.md) ของ KBiz ใช้ product สมมติชื่อ **BookNow** (แพลตฟอร์มจองนัดหมายสำหรับธุรกิจบริการ เช่น ร้านทำผม คลินิก ร้านซ่อม) เพื่อให้เห็นว่าเอกสารแต่ละชิ้น "เมื่อเขียนเสร็จจริง" ควรมีเนื้อหาละเอียดแค่ไหน

**ไม่ใช่ธุรกิจจริง — ใช้เป็นแม่แบบสำหรับก็อปปี้ไปเริ่มโปรเจกต์อื่น**

---

## เอกสารทั้ง 5 ชุด (Minimum Set)

| # | เอกสาร | ไฟล์ | ตอบคำถาม |
|---|---|---|---|
| 1 | Product Context | [00_overview/product_context.md](00_overview/product_context.md) | เราทำอะไร เพื่อใคร ทำไม |
| 2 | PRD | [03_product/prd/prd.md](03_product/prd/prd.md) | MVP ต้องทำอะไร scope คืออะไร |
| 3 | Requirements + Business Rules | [04_requirements/](04_requirements/) (4 ไฟล์) | ระบบต้องทำตามอะไร กฎอะไร |
| 4 | UX/UI Flow + Screen Spec | [05_design/](05_design/) (8 ไฟล์) | ผู้ใช้กดอะไร เห็นอะไร |
| 5 | Technical Spec | [06_engineering/](06_engineering/) (4 ไฟล์) | dev ต้องสร้างอย่างไร |

---

## Source Code อ้างอิง (เพิ่มใหม่)

เพื่อให้เอกสาร 00-06 สามารถอ้างอิง implementation จริงได้ มีการเพิ่มโฟลเดอร์:

- [07_sourcecode/](07_sourcecode/) — เก็บ source snapshot ของโปรเจกต์ `line-ai-agent`
- ไฟล์แนะนำการอ่านอยู่ที่ [07_sourcecode/README.md](07_sourcecode/README.md)

> หมายเหตุ: โค้ดใน `07_sourcecode/line-ai-agent` เป็น snapshot ที่คัดลอกจาก
> `https://github.com/moynaja/line-ai-agent.git` (ไม่รวมโฟลเดอร์ `.git`)
> เพื่อใช้อ่าน/อ้างอิงเชิงสถาปัตยกรรมและการพัฒนา

รายละเอียดไฟล์ทั้งหมด:

```
minimum_starter_kit/
├── 00_overview/
│   └── product_context.md
├── 03_product/prd/
│   └── prd.md
├── 04_requirements/
│   ├── functional_requirements.md
│   ├── business_rules.md
│   ├── permission_requirements.md
│   └── ai_requirements.md          ← ตัวอย่างเมื่อ AI ยังไม่อยู่ใน MVP
├── 05_design/
│   ├── 00_design_brief/design_brief.md
│   ├── 01_user_flows/
│   │   ├── booking_flow.md
│   │   ├── cancellation_flow.md
│   │   └── staff_schedule_flow.md
│   ├── 02_information_architecture/web_ia.md
│   ├── 04_screen_specs/
│   │   ├── screen_spec_public_booking_page.md
│   │   └── screen_spec_owner_dashboard.md
│   └── 06_prototypes/prototype_notes.md
└── 06_engineering/
    ├── backend_architecture/backend_architecture.md
    ├── database/database_schema.md
    ├── api/api_spec.md
    └── web/web_architecture.md

└── 07_sourcecode/
    ├── README.md
    └── line-ai-agent/
        ├── app/
        ├── assets/
        ├── docs/
        ├── liff/
        ├── scripts/
        ├── tools/
        ├── main.py
        ├── requirements.txt
        ├── PLAN.md
        └── CLAUDE.md
```

---

## ลำดับการอ่าน (Minimum Workflow)

1. อ่าน [Product Context](00_overview/product_context.md) เพื่อเข้าใจทิศทาง
2. อ่าน [PRD](03_product/prd/prd.md) เพื่อรู้ว่า MVP ต้องทำอะไร
3. อ่าน [Requirements + Business Rules](04_requirements/) ให้ครบทั้ง 4 ไฟล์
4. อ่าน [UX/UI Flow + Screen Spec](05_design/) เพื่อเห็นว่าผู้ใช้ใช้งานอย่างไร
5. อ่าน [Technical Spec](06_engineering/) เพื่อดูว่า dev ต้องสร้างอย่างไร

เอกสารทุกไฟล์ลิงก์ข้ามกันด้วย relative markdown link — เริ่มจาก Product Context แล้วไล่ตามลิงก์ไปเรื่อยๆ ได้เลย

---

## วิธีนำไปใช้กับโปรเจกต์อื่น

1. **Copy ทั้งโฟลเดอร์** `minimum_starter_kit/` ไปตั้งเป็นจุดเริ่มต้นของโปรเจกต์ใหม่ (เปลี่ยนชื่อโฟลเดอร์ตามชื่อโปรเจกต์ หรือรวมเข้ากับโครงสร้าง 00-09 เดิมถ้าใช้ template เดียวกับ KBiz)
2. **แทนที่เนื้อหา BookNow ทีละไฟล์** ตามลำดับในหัวข้อ "ลำดับการอ่าน" ข้างบน — อย่าข้ามไปเขียน Technical Spec ก่อน Product Context เพราะเอกสารทุกชั้นอ้างอิงชั้นก่อนหน้า
3. **คงโครงสร้างหัวข้อของแต่ละไฟล์ไว้** (เช่น Status table, Acceptance Criteria แบบ Given/When/Then, Permission Matrix) เพราะโครงสร้างนี้ถูกออกแบบให้ตอบคำถามที่ทีมอื่น (design, dev, QA) ต้องใช้จริง ไม่ใช่แค่ format สวยๆ
4. **ไฟล์ [ai_requirements.md](04_requirements/ai_requirements.md) เป็นตัวอย่างสำคัญ** — ถ้าโปรเจกต์ใหม่ไม่มี AI ใน MVP ก็ให้เขียนแบบนี้ (ระบุ "Not in MVP" พร้อมเหตุผลและแนวทางอนาคต) **อย่าลบไฟล์ทิ้ง** เพราะทีมถัดไปจะไม่รู้ว่าตั้งใจไม่ทำ หรือแค่ลืมทำ
5. **เมื่อเริ่ม build จริง** ให้เพิ่มเอกสารชุด operational (product_backlog, decision_log, change_request_log, qa test plan) ตามที่ระบุใน [Minimum Recommended Documents § Documents That Can Wait](../99_templates/documentation/minimum_reccomend.md#documents-that-can-wait) — ไม่ต้องทำทั้งหมดตั้งแต่วันแรก

## สิ่งที่ตัวอย่างนี้ตั้งใจสาธิต

- **ความสอดคล้องข้ามเอกสาร** — role, business rule, entity เดียวกัน (เช่น cutoff time 2 ชม., grace period 15 นาที, Owner/Staff/Customer) ถูกอ้างอิงตรงกันทุกไฟล์ ไม่ขัดแย้งกันเอง
- **การตัดสินใจที่มีเหตุผลกำกับ** — ทุกจุดที่เลือกทำ/ไม่ทำ (เช่น เลือก PostgreSQL ไม่ใช่ MongoDB เพราะ booking เป็นข้อมูลเชิงสัมพันธ์, เลือกไม่ทำ native mobile app ใน MVP) มีคำอธิบายว่าทำไม ไม่ใช่แค่บอกว่า "ทำ" หรือ "ไม่ทำ"
- **Business Rule แยกจาก Functional Requirement อย่างชัดเจน** — FR บอกว่าระบบทำอะไรได้ BR บอกว่าเมื่อเกิดเงื่อนไข ระบบต้องตัดสินใจอย่างไร
- **Permission ผูกกับ Business Rule** — permission_requirements.md อ้างอิงกลับไปที่ business_rules.md และ technical spec (database/api) บังคับใช้กฎเดียวกันที่ระดับ constraint/endpoint ไม่ใช่แค่ UI

## เอกสารต้นแบบอ้างอิง

โครงสร้างและแนวทางนี้อ้างอิงจาก [99_templates/documentation/minimum_reccomend.md](../99_templates/documentation/minimum_reccomend.md) ของ KBiz — ถ้าต้องการดูเอกสารชุดเต็ม (14 sessions ครอบคลุมทุกด้านของโปรเจกต์จริง) ดูตัวอย่างได้จากเอกสาร Warmilio ในโฟลเดอร์หลักของ KBiz
