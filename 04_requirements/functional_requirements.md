# Functional Requirements — BookNow

> ตัวอย่างเอกสารสมบูรณ์ (product สมมติ) — ใช้เป็นแม่แบบสำหรับโปรเจกต์อื่น

## Status

| Field | Value |
|---|---|
| Document Status | Approved |
| Owner | Product Owner |
| Reviewer | Tech Lead, UX/UI Designer, QA |
| Last Updated | 2026-01-20 |
| Related | [PRD](../03_product/prd/prd.md), [Business Rules](business_rules.md), [Permission Requirements](permission_requirements.md) |

---

## Naming Convention

- `FR-XXX` = Functional Requirement
- แต่ละ FR มี Acceptance Criteria แบบ Given/When/Then อย่างน้อย 1 ข้อ

---

## FR-001 — Business Signup & Profile Setup

ผู้ใช้ที่สมัครในบทบาท Business Owner ต้องสร้างธุรกิจได้ พร้อมกำหนดชื่อร้าน ที่อยู่ และเวลาทำการ

**Acceptance Criteria:**
- Given ผู้ใช้ใหม่ยังไม่มีธุรกิจ, When กรอกชื่อร้าน + เวลาทำการอย่างน้อย 1 วัน + กด "สร้างธุรกิจ", Then ระบบสร้าง business record และตั้งผู้ใช้เป็น Owner ของธุรกิจนั้น
- Given เวลาทำการยังไม่ได้กรอกสักวัน, When กด "สร้างธุรกิจ", Then ระบบแสดง error และไม่สร้างธุรกิจ

## FR-002 — Service Catalog Management

Owner ต้องเพิ่ม/แก้ไข/ปิดการใช้งานบริการได้ โดยแต่ละบริการมีชื่อ ระยะเวลา (นาที) และราคา

**Acceptance Criteria:**
- Given Owner อยู่ในหน้าจัดการบริการ, When เพิ่มบริการใหม่พร้อมชื่อ+ระยะเวลา+ราคา, Then บริการนั้นแสดงในหน้าจองสาธารณะทันที
- Given บริการมี booking ที่ยังไม่เสร็จสิ้นผูกอยู่, When Owner กด "ลบบริการ", Then ระบบไม่ลบจริงแต่ทำ soft-delete (`isActive = false`) และบริการหายจากหน้าจองใหม่ แต่ booking เดิมยังอ้างอิงข้อมูลได้ (อ้างอิง [Business Rules](business_rules.md) BR-006)

## FR-003 — Staff Invite & Service Assignment

Owner ต้องเชิญพนักงานเข้าธุรกิจ และกำหนดได้ว่าพนักงานคนไหนให้บริการอะไรได้บ้าง

**Acceptance Criteria:**
- Given Owner กรอกอีเมล/เบอร์โทรพนักงานใหม่, When กด "เชิญพนักงาน", Then ระบบส่งคำเชิญ และพนักงานเข้าร่วมธุรกิจได้ในบทบาท Staff หลังยืนยัน
- Given พนักงานยังไม่ถูกกำหนดว่าให้บริการใดได้, When ลูกค้าเลือกบริการในหน้าจอง, Then ระบบไม่แสดงพนักงานคนนั้นเป็นตัวเลือก

## FR-004 — Public Booking Page

ลูกค้าต้องจองนัดได้เองผ่านหน้าเว็บสาธารณะ โดยไม่ต้องสร้างบัญชีล่วงหน้า

**Acceptance Criteria:**
- Given ลูกค้าเปิดลิงก์จองของธุรกิจ, When เลือกบริการ → เลือกพนักงาน (หรือ "คนไหนก็ได้") → เลือกช่วงเวลาว่าง → กรอกชื่อและเบอร์โทร → กดยืนยัน, Then ระบบสร้าง booking สถานะ `confirmed` และส่งข้อความยืนยันไปยังเบอร์โทร/อีเมลที่กรอก
- Given ช่วงเวลาที่เลือกถูกจองไปแล้วโดยลูกค้าอื่นในระหว่างที่กำลังกรอกฟอร์ม, When กดยืนยัน, Then ระบบแจ้ง error "ช่วงเวลานี้ถูกจองแล้ว" และให้เลือกเวลาใหม่ (ไม่สร้าง booking ซ้ำ — อ้างอิง BR-001)

## FR-005 — Availability Engine

ระบบต้องคำนวณช่วงเวลาว่างของพนักงานแต่ละคน จากเวลาทำการของร้าน หัก booking ที่มีอยู่แล้ว และระยะเวลาของบริการที่เลือก

**Acceptance Criteria:**
- Given พนักงาน A มีนัดเวลา 10:00-10:30 อยู่แล้ว, When ลูกค้าเลือกบริการที่ใช้เวลา 30 นาทีและพนักงาน A, Then ระบบไม่แสดงช่วงเวลา 10:00-10:30 เป็นตัวเลือกว่าง
- Given ร้านปิดวันอาทิตย์, When ลูกค้าเลือกวันอาทิตย์, Then ระบบไม่แสดงช่วงเวลาว่างใดๆ ในวันนั้น

## FR-006 — Booking Management (Reschedule/Cancel)

ลูกค้า พนักงาน (เฉพาะนัดตัวเอง) และ Owner ต้องเลื่อนหรือยกเลิกนัดได้

**Acceptance Criteria:**
- Given booking อยู่ในสถานะ `confirmed` และยังไม่ถึง cutoff time, When ลูกค้ากดยกเลิกผ่านลิงก์จัดการนัด, Then สถานะเปลี่ยนเป็น `cancelled_by_customer` และพนักงาน+Owner ได้รับแจ้งเตือน
- Given เลยเวลา cutoff แล้ว, When ลูกค้ากดยกเลิก, Then ระบบยังอนุญาตให้ยกเลิกได้แต่บันทึกเป็น `late_cancellation` (อ้างอิง BR-002)

## FR-007 — Automated Reminder Notification

ระบบต้องส่งการแจ้งเตือนอัตโนมัติก่อนถึงเวลานัด

**Acceptance Criteria:**
- Given booking สถานะ `confirmed`, When เหลือเวลา 24 ชั่วโมงก่อนนัด, Then ระบบส่ง reminder ครั้งที่ 1 ทางอีเมล/SMS ตามช่องทางที่ลูกค้าให้ไว้
- Given ส่ง reminder ครั้งที่ 1 ไปแล้ว, When เหลือเวลา 1 ชั่วโมงก่อนนัด, Then ระบบส่ง reminder ครั้งที่ 2
- Given booking ถูกยกเลิกไปแล้วก่อนถึงเวลา reminder, When ถึงเวลาที่กำหนดส่ง reminder, Then ระบบไม่ส่ง reminder สำหรับ booking นั้น

## FR-008 — No-show Tracking

พนักงานหรือ Owner ต้องบันทึกได้ว่าลูกค้ามาตามนัดหรือไม่ หลังพ้นเวลานัด

**Acceptance Criteria:**
- Given ถึงเวลานัดแล้วผ่านไป 15 นาที (grace period) และยังไม่มีการ mark สถานะ, When ระบบตรวจสอบ background job, Then ระบบตั้งสถานะเป็น `no_show` โดยอัตโนมัติ (อ้างอิง BR-003) และ Owner เห็นในแดชบอร์ด
- Given พนักงานกด "ลูกค้ามาแล้ว" ก่อนหมด grace period, When กดยืนยัน, Then สถานะเปลี่ยนเป็น `completed` และไม่ trigger auto no-show

## FR-009 — Owner/Staff Dashboard

Owner ต้องเห็นภาพรวมนัดทั้งร้าน ส่วน Staff เห็นเฉพาะนัดของตัวเอง

**Acceptance Criteria:**
- Given login ด้วย role Staff, When เปิดแดชบอร์ด, Then เห็นเฉพาะ booking ที่ตัวเองถูก assign เท่านั้น
- Given login ด้วย role Owner, When เปิดแดชบอร์ด, Then เห็น booking ของพนักงานทุกคนในธุรกิจ พร้อมสรุปจำนวน no-show/ยกเลิกของ 7 วันล่าสุด

## FR-010 — Audit Log for Booking Changes

ทุกการเปลี่ยนแปลงสถานะ booking ต้องถูกบันทึกเป็น audit log แบบ append-only

**Acceptance Criteria:**
- Given booking ถูกสร้าง/เลื่อน/ยกเลิก/mark no-show, When action สำเร็จ, Then ระบบเขียน audit event พร้อม actor, timestamp, action, และค่าก่อน/หลัง
- Given audit log ถูกเขียนแล้ว, When ผู้ใช้ใดพยายามแก้ไข/ลบ record นั้นผ่าน API ปกติ, Then ระบบปฏิเสธ (ไม่มี endpoint สำหรับ update/delete audit log)
