# Business Rules — BookNow

> ตัวอย่างเอกสารสมบูรณ์ (product สมมติ) — ใช้เป็นแม่แบบสำหรับโปรเจกต์อื่น
> Business Rule ต่างจาก Functional Requirement: FR บอกว่า "ระบบทำอะไรได้" ส่วน Business Rule บอกว่า "เมื่อเกิดเงื่อนไข X ระบบต้องตัดสินใจอย่างไร"

## Status

| Field | Value |
|---|---|
| Document Status | Approved |
| Owner | Product Owner |
| Reviewer | Tech Lead, UX/UI Designer, QA |
| Last Updated | 2026-01-20 |
| Related | [Functional Requirements](functional_requirements.md), [Permission Requirements](permission_requirements.md) |

---

## Rule Groups

- **Booking Integrity** — BR-001, BR-005
- **Cancellation & No-show** — BR-002, BR-003, BR-004
- **Data Lifecycle** — BR-006, BR-007
- **Notification** — BR-008, BR-009

---

## BR-001 — ห้ามจองชนกัน (Double Booking)

พนักงาน 1 คนต้องมี booking ที่สถานะ active (`confirmed`) ทับซ้อนกันไม่ได้ในช่วงเวลาเดียวกัน ระบบต้องตรวจสอบที่ระดับ database (unique constraint / transaction) ไม่ใช่แค่ที่ UI เพื่อป้องกัน race condition เมื่อลูกค้าสองคนจองพร้อมกัน

## BR-002 — Cutoff Time สำหรับยกเลิก/เลื่อนนัดฟรี

ลูกค้ายกเลิกหรือเลื่อนนัดได้โดยไม่มีผลเสียหากทำก่อนเวลานัด **อย่างน้อย 2 ชั่วโมง** (ค่า default ที่ Owner ปรับได้ต่อธุรกิจ) หากยกเลิกหลังจากนั้นให้บันทึกเป็น `late_cancellation` และนับรวมในสถิติของลูกค้ารายนั้น (ยังไม่มีการหักค่าธรรมเนียมใน MVP เพราะยังไม่มีระบบชำระเงิน — ดู PRD Out of Scope)

## BR-003 — No-show อัตโนมัติหลัง Grace Period

หาก booking ผ่านเวลานัดไปแล้ว **15 นาที** และไม่มีการ mark สถานะเป็น `completed` โดยพนักงาน ระบบต้องตั้งสถานะเป็น `no_show` โดยอัตโนมัติผ่าน background job และแจ้งเตือน Owner ทันที (grace period ปรับได้ต่อธุรกิจ เช่นเดียวกับ BR-002)

## BR-004 — Staff เห็น/แก้ไขได้เฉพาะนัดของตัวเอง

Staff ไม่สามารถดูหรือแก้ไข booking ที่ assign ให้พนักงานคนอื่น เว้นแต่ได้รับสิทธิ์ `view_all_bookings` จาก Owner อย่างชัดเจน (ดู [Permission Requirements](permission_requirements.md)) กฎนี้บังคับที่ระดับ API ไม่ใช่แค่ซ่อนใน UI

## BR-005 — Availability ต้องคำนวณจากเวลาทำการ + Booking ที่มีอยู่เสมอ

ช่วงเวลาที่แสดงให้ลูกค้าเลือกในหน้าจองต้องตัดช่วงที่ (ก) อยู่นอกเวลาทำการของร้าน (ข) ทับกับ booking ที่สถานะ active ของพนักงานคนนั้น (ค) เหลือเวลาไม่พอสำหรับระยะเวลาบริการที่เลือก ห้าม cache availability ไว้นานเกิน 60 วินาที เพื่อลดโอกาส double booking จากข้อมูลเก่า

## BR-006 — ห้ามลบข้อมูลที่มี Booking ผูกอยู่ (Soft Delete)

การ "ลบ" บริการ (service) หรือปิดการใช้งานพนักงาน ต้องเป็น soft delete (`isActive = false`) เท่านั้น ห้ามลบ record จริงจากฐานข้อมูล เพื่อให้ booking ประวัติเก่ายังอ้างอิงชื่อบริการ/พนักงานได้ถูกต้อง

## BR-007 — Audit Log เป็น Append-only

ทุก booking event (create, reschedule, cancel, no_show, complete) ต้องเขียนเป็น audit log ที่ห้าม update หรือ delete ผ่าน API ใดๆ หลังบันทึกแล้ว หากต้องแก้ไขข้อมูลผิดพลาด ให้เขียน event ใหม่เพื่อ "แก้ไข" แทนการย้อนไปแก้ event เดิม

## BR-008 — Reminder ต้องหยุดทันทีเมื่อ Booking ถูกยกเลิก

หาก booking ถูกยกเลิกหรือเลื่อนก่อนถึงเวลาที่ระบบจะส่ง reminder (24 ชม. หรือ 1 ชม.) ระบบต้องไม่ส่ง reminder สำหรับ booking เดิมนั้นอีก ป้องกันลูกค้าได้รับข้อความแจ้งเตือนนัดที่ยกเลิกไปแล้ว

## BR-009 — Notification ใช้ข้อมูลเท่าที่จำเป็น (Minimum Necessary)

ข้อความแจ้งเตือนถึงลูกค้าแสดงเฉพาะ ชื่อร้าน วันเวลา และชื่อบริการ ไม่ส่งข้อมูลพนักงานคนอื่นหรือรายละเอียดนัดของลูกค้ารายอื่นแม้จะอยู่ในธุรกิจเดียวกัน

## Open Decisions (ยังไม่สรุป)

| หัวข้อ | รายละเอียด | ผู้ตัดสินใจที่ต้องเคาะ |
|---|---|---|
| Cutoff time เริ่มต้น | 2 ชั่วโมงเหมาะกับทุกประเภทธุรกิจหรือไม่ (เทียบร้านทำผมกับคลินิก) | Product Owner + ข้อมูลจาก pilot |
| Late-cancellation ควรมีผลอะไรต่อลูกค้าไหม | เช่น บล็อกลูกค้าที่ late-cancel เกิน N ครั้ง | Product Owner (รอ Phase 2 เมื่อมีระบบชำระเงิน) |
| Grace period no-show ควรปรับตามประเภทบริการไหม | บริการ 15 นาทีกับบริการ 2 ชั่วโมง อาจต้อง grace period ต่างกัน | Tech Lead + Product Owner |
