# Permission Requirements — BookNow

> ตัวอย่างเอกสารสมบูรณ์ (product สมมติ) — ใช้เป็นแม่แบบสำหรับโปรเจกต์อื่น

## Status

| Field | Value |
|---|---|
| Document Status | Approved |
| Owner | Product Owner |
| Reviewer | Tech Lead, Security |
| Last Updated | 2026-01-20 |
| Related | [Business Rules](business_rules.md), [Functional Requirements](functional_requirements.md) |

---

## Roles

| Role | คำอธิบาย |
|---|---|
| Business Owner | สิทธิ์เต็มในธุรกิจของตัวเอง 1 ธุรกิจ (MVP ไม่รองรับ Owner หลายธุรกิจในบัญชีเดียว) |
| Staff | พนักงานที่สังกัดธุรกิจใดธุรกิจหนึ่ง เห็น/แก้ไขได้เฉพาะนัดของตัวเองเป็น default |
| Customer | ผู้จองนัด ไม่มีบัญชีแบบ login เต็มรูปใน MVP — ยืนยันตัวตนผ่านลิงก์ที่ส่งไปยังเบอร์โทร/อีเมลที่ใช้จอง |

## Core Principle

- ทุก endpoint ที่แก้ไขข้อมูล booking ต้องตรวจสิทธิ์ก่อนเสมอ (fail closed) — ตรวจสิทธิ์ไม่ผ่านหรือระบบตรวจสอบไม่ได้ ให้ปฏิเสธ ไม่ใช่อนุญาตไว้ก่อน
- Staff เห็นข้อมูลเฉพาะที่ตัวเองเกี่ยวข้อง เว้นแต่ Owner มอบสิทธิ์เพิ่มอย่างชัดเจน
- Customer เข้าถึงเฉพาะ booking ของตัวเองผ่าน token ที่ผูกกับ booking นั้น ไม่มีสิทธิ์เห็นรายการ booking ของลูกค้าคนอื่น

## Permission Matrix

| Action | Business Owner | Staff (default) | Staff (with `view_all_bookings`) | Customer |
|---|---|---|---|---|
| สร้าง/แก้ไข business profile | ✅ | ❌ | ❌ | ❌ |
| จัดการ service catalog | ✅ | ❌ | ❌ | ❌ |
| เชิญ/ลบพนักงาน | ✅ | ❌ | ❌ | ❌ |
| กำหนดสิทธิ์พนักงานคนอื่น | ✅ | ❌ | ❌ | ❌ |
| ดู booking ของตัวเอง | ✅ | ✅ | ✅ | ✅ (เฉพาะที่จองไว้) |
| ดู booking ของพนักงานคนอื่น | ✅ | ❌ | ✅ | ❌ |
| เลื่อน/ยกเลิก booking ของตัวเอง | ✅ | ✅ | ✅ | ✅ |
| เลื่อน/ยกเลิก booking ของพนักงานคนอื่น | ✅ | ❌ | ✅ (ถ้าได้รับสิทธิ์เพิ่ม `manage_all_bookings`) | ❌ |
| Mark completed / no-show | ✅ | ✅ (เฉพาะนัดตัวเอง) | ✅ | ❌ |
| ดูแดชบอร์ดสรุปทั้งร้าน | ✅ | ❌ | ✅ (read-only) | ❌ |
| ดู audit log | ✅ | ❌ | ❌ | ❌ |

## Permission Rules

- **PERM-001** — ทุก request ที่แก้ไข booking ต้องตรวจสอบว่า `actor.id` เป็น Owner ของธุรกิจ, เป็น Staff ที่ถูก assign กับ booking นั้น, หรือเป็น Customer ที่ถือ token ของ booking นั้น
- **PERM-002** — สิทธิ์ `view_all_bookings` และ `manage_all_bookings` เป็น per-staff flag ที่ Owner ตั้งค่าได้ ค่า default คือ `false` ทั้งคู่
- **PERM-003** — Customer token ที่ใช้จัดการ booking (เลื่อน/ยกเลิก) ต้องผูกกับ booking ID เดียว หมดอายุอัตโนมัติหลัง booking เสร็จสิ้นหรือถูกยกเลิกไปแล้ว 30 วัน
- **PERM-004** — เมื่อ Owner ลบพนักงานออกจากธุรกิจ สิทธิ์การเข้าถึงทุก endpoint ของพนักงานคนนั้นต้องถูกเพิกถอนทันที (revoke ที่ session/token ไม่ใช่แค่ซ่อนใน UI)
- **PERM-005** — ทุกการเปลี่ยนสิทธิ์ (เชิญ/ลบพนักงาน, ปรับ flag `view_all_bookings`/`manage_all_bookings`) ต้องสร้าง audit log

## Explicitly Not Allowed (ทุก Role)

- ไม่มี role ใดแก้ไข audit log ได้ (append-only)
- Staff แก้ไข service catalog หรือราคาบริการไม่ได้ในทุกกรณี (แม้มี `manage_all_bookings`)
- Customer ไม่สามารถเห็นชื่อ/เบอร์โทรของลูกค้ารายอื่นในธุรกิจเดียวกัน

## Open Questions

- ควรมี role "Manager" แยกจาก Owner ไหม (สิทธิ์เท่า Owner แต่ไม่ใช่เจ้าของบัญชี) — ยังไม่ต้องใน MVP เพราะกลุ่มเป้าหมายเป็นธุรกิจขนาดเล็กที่ Owner ดูแลเอง
