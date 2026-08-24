# PRD — BookNow MVP

> ตัวอย่างเอกสารสมบูรณ์ (product สมมติ) — ใช้เป็นแม่แบบสำหรับโปรเจกต์อื่น

## Status

| Field | Value |
|---|---|
| Document Status | Approved |
| Owner | Product Owner |
| Reviewer | Founder, UX/UI Designer, Tech Lead |
| Last Updated | 2026-01-18 |
| Related | [Product Context](../../00_overview/product_context.md) |

---

## 1. MVP Scope

เป้าหมาย MVP: ทำให้ธุรกิจบริการ 1 สาขา เปลี่ยนจากการนัดด้วยโทรศัพท์/สมุดจด มาใช้ระบบจองออนไลน์ได้ภายใน 1 วัน โดยไม่ต้องเทรนพนักงานนาน

**In Scope (MVP):**

1. สมัครธุรกิจและตั้งค่าโปรไฟล์ (ชื่อร้าน, ที่อยู่, เวลาทำการ)
2. จัดการรายการบริการ (ชื่อบริการ, ระยะเวลา, ราคา)
3. เชิญพนักงานเข้าร้าน และกำหนดว่าพนักงานให้บริการอะไรได้บ้าง
4. หน้าจองนัดสาธารณะสำหรับลูกค้า (เลือกบริการ → เลือกพนักงาน/เวลาว่าง → ยืนยันนัด)
5. จัดการนัด: ดูรายการนัด, เลื่อนนัด, ยกเลิกนัด (โดยลูกค้า, พนักงาน, หรือ owner)
6. แจ้งเตือนอัตโนมัติก่อนนัด (อีเมล/SMS) ที่ 24 ชม. และ 1 ชม. ก่อนถึงเวลา
7. แดชบอร์ดสรุปนัดวันนี้/พรุ่งนี้ สำหรับ Owner และ Staff
8. Audit log สำหรับการเปลี่ยนแปลงนัด (สร้าง/เลื่อน/ยกเลิก/no-show)

**Out of Scope (MVP):**

| รายการ | เหตุผลที่ยังไม่ทำ |
|---|---|
| การชำระเงิน/มัดจำออนไลน์ | เพิ่มความซับซ้อนด้าน compliance (PCI) — รอดูว่า MVP ตอบโจทย์เรื่องตารางก่อน |
| ธุรกิจหลายสาขา | MVP ต้อง simple ที่สุด, multi-location เปลี่ยน data model มาก |
| Native mobile app | Web responsive ตอบโจทย์ทั้งลูกค้าและพนักงานได้ในระยะแรก |
| Marketplace / ค้นหาธุรกิจ | ลูกค้าเข้าถึงร้านผ่านลิงก์ตรง/QR code ที่ร้านแจกเอง ยังไม่ต้องมี discovery |
| โปรแกรมสะสมแต้ม/Loyalty | ไม่ใช่ปัญหาหลักที่ MVP ต้องแก้ |
| Group booking / คลาสรวม | MVP รองรับ 1-ต่อ-1 เท่านั้น |

## 2. User Roles

| Role | คำอธิบาย |
|---|---|
| Business Owner | ผู้ดูแลธุรกิจ มีสิทธิ์เต็มในบริการ พนักงาน และนัดทั้งหมด |
| Staff | พนักงาน/ช่างที่ให้บริการ เห็นและจัดการเฉพาะนัดของตัวเอง |
| Customer | ลูกค้าที่จองนัด จัดการเฉพาะนัดของตัวเอง |

รายละเอียดสิทธิ์แต่ละ role → [Permission Requirements](../../04_requirements/permission_requirements.md)

## 3. Core Use Cases

1. **Owner ตั้งค่าร้านครั้งแรก** — สมัคร → ตั้งชื่อร้าน/เวลาทำการ → เพิ่มบริการ → เชิญพนักงาน → ได้ลิงก์จองนัดสาธารณะ
2. **Customer จองนัด** — เปิดลิงก์ร้าน → เลือกบริการ → เลือกพนักงาน (หรือ "คนไหนก็ได้") → เลือกเวลาว่าง → กรอกชื่อ/เบอร์โทร → ยืนยันนัด → ได้รับ SMS/อีเมลยืนยัน
3. **Customer เลื่อน/ยกเลิกนัด** — เปิดลิงก์จัดการนัดจาก SMS/อีเมล → เลือกเลื่อนหรือยกเลิก → ระบบเช็ค cutoff time → อัปเดตสถานะ → แจ้งพนักงาน/owner
4. **Staff ดูตารางวันนี้** — login → เห็นเฉพาะนัดที่ตัวเองรับผิดชอบ → กด mark "มาแล้ว" หรือ "no-show" หลังเวลานัด
5. **Owner ดูภาพรวมร้าน** — login → เห็นนัดทั้งร้านของทุกพนักงาน → เห็นสรุป no-show/ยกเลิกของสัปดาห์นี้

## 4. Feature List (MVP)

| Feature | Priority |
|---|---|
| Business signup & profile setup | Must |
| Service catalog management | Must |
| Staff invite & role assignment | Must |
| Public booking page (customer-facing) | Must |
| Time slot availability engine (ตาม service duration + staff schedule) | Must |
| Booking management (view/reschedule/cancel) | Must |
| Automated reminder notification (email/SMS) | Must |
| No-show tracking | Must |
| Owner/Staff dashboard | Must |
| Audit log (booking changes) | Should |
| Business working-hours exceptions (วันหยุด/ปิดร้านชั่วคราว) | Should |
| Customer booking history | Could |

## 5. Success Metrics

| Metric | Target (ภายใน 3 เดือนหลังเปิดใช้จริง) |
|---|---|
| Business Activation Rate (สมัครแล้วตั้งค่าเสร็จและมี booking แรกภายใน 7 วัน) | 50%+ |
| Booking ที่จองผ่านระบบเทียบกับที่จองผ่านโทรศัพท์เดิม (สำหรับร้านที่ใช้จริง) | 60%+ ของนัดใหม่ผ่านระบบ |
| No-show rate ลดลงเทียบก่อนใช้ระบบ (เพราะมี reminder) | ลดลง 20%+ |
| Weekly Active Business (login เข้าดูแดชบอร์ดอย่างน้อย 1 ครั้ง/สัปดาห์) | 70%+ |

## 6. Roadmap (ภาพรวม)

| Phase | โฟกัส |
|---|---|
| Phase 0 — Discovery | สัมภาษณ์เจ้าของธุรกิจบริการ 10-15 ราย, ยืนยัน pain point, ทำ clickable prototype |
| Phase 1 — MVP Launch | Feature ตามรายการข้อ 4, เปิดใช้กับธุรกิจ pilot 5-10 ร้าน |
| Phase 2 — Payment & Multi-staff scheduling ขั้นสูง | มัดจำออนไลน์, กฎการจัดคิวพนักงานอัตโนมัติ, customer mobile app |
| Phase 3 — Multi-location & Marketplace | รองรับธุรกิจหลายสาขา, ระบบค้นหาธุรกิจสำหรับลูกค้าใหม่ |

## 7. Open Questions

- Cutoff time สำหรับยกเลิกนัดฟรีควรเป็นกี่ชั่วโมงก่อนนัด (ตั้งเป็นค่ามาตรฐานหรือให้ owner กำหนดเอง) — ดู [Business Rules](../../04_requirements/business_rules.md) BR-002
- ควรบังคับลูกค้ายืนยันเบอร์โทรด้วย OTP ก่อนจองไหม หรือรับความเสี่ยงนัดปลอมใน MVP ก่อน
- SMS provider ที่จะใช้จริงในตลาดที่เปิดให้บริการ (ต้นทุนต่อข้อความต่างกันมากในแต่ละประเทศ)

## 8. Linked Docs

- [Product Context](../../00_overview/product_context.md)
- [Functional Requirements](../../04_requirements/functional_requirements.md)
- [Business Rules](../../04_requirements/business_rules.md)
- [Permission Requirements](../../04_requirements/permission_requirements.md)
- [Design Brief](../../05_design/00_design_brief/design_brief.md)
- [Backend Architecture](../../06_engineering/backend_architecture/backend_architecture.md)
