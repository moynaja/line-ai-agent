# Screen Spec — Owner Dashboard

> ตัวอย่างเอกสารสมบูรณ์ (product สมมติ) — ใช้เป็นแม่แบบสำหรับโปรเจกต์อื่น
> ใช้โครงสร้างเดียวกับ [screen_spec_template.md](../../../05_design/04_screen_specs/screen_spec_template.md) ของ repo หลัก

## Status

| Field | Value |
|---|---|
| Document Status | Approved |
| Owner | UX/UI Designer |
| Reviewer | Product Owner, Tech Lead |
| Last Updated | 2026-01-22 |
| Related | [Staff Schedule Flow](../01_user_flows/staff_schedule_flow.md), [Web IA](../02_information_architecture/web_ia.md), [FR-009](../../04_requirements/functional_requirements.md), [BR-003/BR-004](../../04_requirements/business_rules.md), [Permission Matrix](../../04_requirements/permission_requirements.md#permission-matrix) |

---

## Screen Name

แดชบอร์ด Owner (Owner Dashboard — Today Overview) — route `/dashboard`

## Purpose

ให้ Business Owner เห็นภาพรวมนัดวันนี้ของ**ทุกพนักงาน**ในร้านภายในหน้าเดียว พร้อมสรุป no-show และการยกเลิกของ 7 วันล่าสุด เพื่อให้ตัดสินใจเชิงธุรกิจได้ทันที (เช่น ช่วงเวลาไหนคนแน่น ควรจ้างพนักงานเพิ่มไหม พนักงานคนไหน no-show บ่อยจนต้องตรวจสอบ)

## Primary Users

- **Business Owner** — ผู้ใช้หลัก เห็นและจัดการนัดของทุกพนักงานได้เต็มสิทธิ์
- **Staff ที่ได้รับสิทธิ์ `view_all_bookings`** — เห็นหน้าเดียวกันนี้แบบ read-only (ดูสรุปได้ แต่จัดการนัดของคนอื่นไม่ได้ เว้นแต่มี `manage_all_bookings` เพิ่ม)

## Layout Sketch (Reference)

```
┌─────────────────────────────┐
│ ร้านสวยดี ตัดผม-เล็บ         │
│ วันนี้ อังคาร 12 ก.พ. 2026    │
├─────────────────────────────┤
│ นัดวันนี้ 8   เสร็จแล้ว 3     │
│ กำลังจะถึง 4   no-show 1     │
├─────────────────────────────┤
│ ตารางวันนี้ (ทุกพนักงาน)      │
│ 09:00 คุณนุช  - สมชาย - ตัดผม│
│        [เสร็จแล้ว]           │
│ 10:00 คุณเอ   - สมหญิง- เล็บ │
│        [มาแล้ว] [no-show]    │
│ 11:00 คุณนุช  - ว่าง          │
├─────────────────────────────┤
│ สรุป 7 วันล่าสุด              │
│ No-show rate      6%         │
│ ยกเลิกปกติ         9%         │
│ ยกเลิกล่าช้า        3%        │
│ [ดูรายละเอียด]                │
├─────────────────────────────┤
│ Dashboard│Bookings│Services  │
│ Staff│Settings│Reports│Audit │
└─────────────────────────────┘
```

## Data Shown

- สรุปตัวเลขด่วนของวันนี้: จำนวนนัดทั้งหมด, เสร็จแล้ว (`completed`), กำลังจะถึง (`confirmed` ในอนาคตของวันนี้), no-show วันนี้
- ตารางนัดวันนี้ของทุกพนักงาน เรียงตามเวลา แสดง: เวลา, ชื่อพนักงาน, ชื่อลูกค้า, บริการ, สถานะปัจจุบัน
- สรุป 7 วันล่าสุด: no-show rate, cancellation rate (แยก `cancelled_by_customer` ปกติ กับ `late_cancellation`), เทียบเป็น % ของนัดทั้งหมดในช่วง
- จำนวนนัดต่อพนักงาน (เพื่อดูว่าใครแน่น/ใครว่าง)

## Main Actions

1. ดูรายละเอียดนัดใดนัดหนึ่ง (คลิกแถว)
2. Mark นัดเป็น "มาแล้ว" (`completed`) หรือ "no-show" (`no_show`) ได้ทุกนัดในร้าน (ไม่จำกัดเฉพาะที่ตัวเองรับผิดชอบ เพราะเป็น Owner)
3. กรองตารางตามพนักงาน
4. คลิก "ดูรายละเอียด" ที่สรุป 7 วัน เพื่อไปหน้ารายงานฉบับเต็ม
5. นำทางไปเมนูอื่น (บริการ, พนักงาน, ตั้งค่าธุรกิจ, Audit Log) จาก navigation หลัก

## Empty State

| สถานการณ์ | สิ่งที่แสดง |
|---|---|
| ยังไม่มีนัดใดๆ เลยวันนี้ | ข้อความเชิงบวก "วันนี้ยังไม่มีนัดเข้ามา" พร้อมปุ่มคัดลอกลิงก์จองนัดสาธารณะ/QR code เพื่อกระตุ้นให้แจกลิงก์เพิ่ม |
| ธุรกิจยังไม่มีพนักงานคนไหนรับนัดได้ (setup ยังไม่เสร็จ) | banner แนะนำให้ไปหน้า "พนักงาน" เพื่อเชิญพนักงานคนแรกก่อน |

## Error State

| สถานการณ์ | สิ่งที่แสดง |
|---|---|
| โหลดข้อมูลแดชบอร์ดไม่สำเร็จ (network/server error) | แสดงข้อความ "โหลดข้อมูลไม่สำเร็จ" พร้อมปุ่ม "โหลดใหม่" ไม่ล้างข้อมูลเก่าที่ยังแสดงอยู่ทันที (แสดง stale data พร้อม label เวลาที่อัปเดตล่าสุด) |
| Staff ที่ไม่มีสิทธิ์ `view_all_bookings` พยายามเข้าหน้านี้ตรงผ่าน URL | แสดงหน้า "ไม่มีสิทธิ์เข้าถึง" และนำทางกลับไปแดชบอร์ดของตัวเอง (ตรวจสิทธิ์ที่ระดับ API ก่อนส่งข้อมูลกลับมา ไม่ใช่ซ่อนแค่ฝั่ง UI) |
| กด mark สถานะนัดที่ background job เพิ่ง auto no-show ไปพร้อมกัน | แสดงข้อความแจ้งว่าสถานะถูกอัปเดตโดยระบบไปแล้ว และ refresh แถวนั้นให้ตรงกับสถานะจริง (ดู [Staff Schedule Flow §4](../01_user_flows/staff_schedule_flow.md#4-edge-case-staff-mark-พร้อมกับ-auto-no-show-job)) |

## Permission / Privacy Notes

- Owner เห็นและจัดการนัดของพนักงานทุกคนในธุรกิจของตัวเองได้เต็มสิทธิ์ (อ้างอิง [Permission Matrix](../../04_requirements/permission_requirements.md#permission-matrix))
- Staff ที่มี `view_all_bookings` เห็นหน้านี้แบบ read-only เท่านั้น — ปุ่ม "มาแล้ว/no-show" สำหรับนัดของพนักงานคนอื่นต้องซ่อนไปเลยถ้าไม่มี `manage_all_bookings` เพิ่ม (PERM-002)
- ไม่แสดง Audit Log ในหน้านี้ (อยู่แยกเมนู เข้าถึงได้ Owner เท่านั้น)
- ข้อมูลลูกค้า (ชื่อ/เบอร์โทร) ที่แสดงในตารางเป็นข้อมูลภายในธุรกิจเดียวกันเท่านั้น ห้าม export หรือแสดงข้ามธุรกิจ

## Acceptance Criteria

- Given login ด้วย role Owner, When เปิดแดชบอร์ด, Then เห็น booking ของพนักงานทุกคนในธุรกิจ พร้อมสรุปจำนวน no-show/ยกเลิกของ 7 วันล่าสุด (อ้างอิง FR-009)
- Given login ด้วย role Staff ที่ไม่มี `view_all_bookings`, When พยายามเปิด route นี้, Then ระบบปฏิเสธที่ระดับ API และนำทางกลับไปแดชบอร์ดของตัวเอง (อ้างอิง BR-004, PERM-001)
- Given booking ผ่านเวลานัดไปแล้วเกิน 15 นาทีโดยไม่มีการ mark สถานะ, When Owner เปิดแดชบอร์ด, Then เห็นสถานะเป็น `no_show` ที่ระบบตั้งอัตโนมัติ พร้อมมี indicator ว่าเป็นการตั้งค่าอัตโนมัติ ไม่ใช่ที่ Owner หรือ Staff กดเอง (อ้างอิง BR-003)
- Given มี late_cancellation เกิดขึ้นในสัปดาห์นี้, When ดูสรุป 7 วันล่าสุด, Then ตัวเลข late_cancellation ต้องแยกออกจากการยกเลิกปกติ ไม่รวมเป็นตัวเดียวกัน
