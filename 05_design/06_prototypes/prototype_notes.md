# Prototype Notes — BookNow

> ตัวอย่างเอกสารสมบูรณ์ (product สมมติ) — ใช้เป็นแม่แบบสำหรับโปรเจกต์อื่น

## Status

| Field | Value |
|---|---|
| Document Status | Approved |
| Owner | UX/UI Designer |
| Reviewer | Product Owner |
| Last Updated | 2026-01-22 |
| Related | [Design Brief](../00_design_brief/design_brief.md), [Booking Flow](../01_user_flows/booking_flow.md), [Cancellation Flow](../01_user_flows/cancellation_flow.md) |

---

## 1. สถานะปัจจุบัน

Starter kit นี้**ไม่ได้แนบ prototype ที่คลิกได้จริง** (ไม่มีไฟล์ Figma/HTML แนบมาด้วย) เอกสารนี้อธิบายแค่ **ขอบเขตที่ prototype ขั้นต่ำของ BookNow ควรครอบคลุม** ก่อนเริ่มพัฒนาจริง เพื่อให้ทีมที่ copy starter kit นี้ไปใช้รู้ว่าต้องทำ prototype แบบไหนถึงจะพอสำหรับ user testing รอบแรก

ตาม [PRD — Roadmap](../../03_product/prd/prd.md#6-roadmap-ภาพรวม) งาน Phase 0 (Discovery) ต้องมี clickable prototype ก่อนเข้า Phase 1 (MVP Launch) — เอกสารนี้คือ scope ของ prototype นั้น

## 2. เป้าหมายของ Prototype

- ทดสอบว่าลูกค้าจองนัดจบได้เองโดยไม่ต้องมีคนอธิบาย (self-service จริง)
- ทดสอบว่า Owner เข้าใจภาพรวมร้านจากแดชบอร์ดได้เร็วพอ (ไม่ต้องมีคนสอนใช้)
- หา friction point ก่อนลงทุนเขียนโค้ดจริง โดยเฉพาะจุดที่มี business rule ซับซ้อน เช่น cutoff time และ availability

## 3. หน้าจอที่ Prototype ขั้นต่ำต้องมี

| #   | หน้าจอ                                                        | สิ่งที่ต้องทดสอบได้                                                           | อ้างอิง                                                                                                                                     |
| --- | ------------------------------------------------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | หน้าจองนัดสาธารณะ (เลือกบริการ → พนักงาน → เวลา → กรอกข้อมูล) | ผู้ทดสอบจองนัดจบได้เองภายในไม่กี่นาที ไม่งง ว่าต้องกดอะไรต่อ                  | [Booking Flow](../01_user_flows/booking_flow.md), [Screen Spec: Public Booking Page](../04_screen_specs/screen_spec_public_booking_page.md) |
| 2   | หน้ายืนยันสำเร็จ + ตัวอย่างข้อความ SMS/อีเมลยืนยัน            | ผู้ทดสอบเข้าใจว่านัดสำเร็จแล้ว และรู้ว่าจะจัดการนัดยังไงถ้าต้องเปลี่ยนแผน     | [Booking Flow](../01_user_flows/booking_flow.md)                                                                                            |
| 3   | หน้าจัดการนัด (เลื่อน/ยกเลิก) รวม branch cutoff time          | ผู้ทดสอบเข้าใจความแตกต่างของยกเลิกก่อน/หลัง cutoff โดยไม่ต้องอ่านคำอธิบายยาว  | [Cancellation Flow](../01_user_flows/cancellation_flow.md)                                                                                  |
| 4   | แดชบอร์ด Owner (นัดวันนี้ทุกพนักงาน + สรุป 7 วัน)             | ผู้ทดสอบ (สมมติเป็นเจ้าของร้าน) บอกได้ภายใน 5 วินาทีว่าวันนี้มีอะไรต้องจัดการ | [Screen Spec: Owner Dashboard](../04_screen_specs/screen_spec_owner_dashboard.md)                                                           |
| 5   | แดชบอร์ด Staff (ตารางวันนี้ของตัวเอง + mark เสร็จ/no-show)    | ผู้ทดสอบ (สมมติเป็นพนักงาน) mark สถานะนัดได้ในไม่กี่แตะระหว่างทำงานจริง       | [Staff Schedule Flow](../01_user_flows/staff_schedule_flow.md)                                                                              |


Prototype ไม่จำเป็นต้องมี state จริง (mock ข้อมูลได้) แต่ **ต้องครอบคลุม edge case หลักอย่างน้อย 1 เคส** ต่อหน้าจอที่มี business rule ซับซ้อน — ที่สำคัญที่สุดคือ:

- หน้า 1: edge case ช่วงเวลาถูกจองไปแล้วตอนกดยืนยัน (double booking)
- หน้า 3: edge case ยกเลิกหลัง cutoff time (ต้องเห็น label `late_cancellation` ชัดเจน)

## 4. รูปแบบ Prototype ที่แนะนำ

- **Fidelity:** เริ่มจาก low-fidelity (wireframe คลิกได้) พอสำหรับทดสอบ flow และคำที่ใช้ ยังไม่ต้องขึ้น branding เต็ม
- **เครื่องมือ:** Figma prototype หรือ HTML/CSS คลิกได้แบบง่าย (ไม่ต้องต่อ backend จริง — ใช้ mock data)
- **การทดสอบ:** อย่างน้อย 5 คนต่อกลุ่มผู้ใช้ (Customer, Owner, Staff) ตาม [PRD — Roadmap Phase 0](../../03_product/prd/prd.md#6-roadmap-ภาพรวม) ที่ระบุให้สัมภาษณ์เจ้าของธุรกิจบริการ 10-15 ราย

## 5. หมายเหตุสำหรับทีมที่ Reuse Starter Kit นี้

**ไฟล์นี้เป็นแค่ placeholder เชิงเนื้อหา ไม่ใช่ prototype จริง** เมื่อทีมของคุณทำ prototype จริงแล้ว (Figma, HTML คลิกได้ หรืออื่นๆ) ให้แทนที่เนื้อหาในไฟล์นี้ด้วย:

1. ลิงก์ไปยัง prototype จริง (เช่น Figma share link)
2. วันที่ทดสอบล่าสุดและจำนวนผู้ทดสอบ
3. สรุป finding สำคัญที่ทำให้ปรับ flow/screen spec เอกสารอื่นในโฟลเดอร์ `05_design/`

ไม่ควรปล่อยให้เอกสารนี้อ้างอิง "หน้าจอที่ควรมี" ต่อไปเรื่อยๆ หลังจากมี prototype จริงแล้ว เพราะจะกลายเป็นข้อมูลซ้ำที่ไม่มีใคร maintain
