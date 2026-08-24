# API Spec — BookNow

> ตัวอย่างเอกสารสมบูรณ์ (product สมมติ) — ใช้เป็นแม่แบบสำหรับโปรเจกต์อื่น

**Product Name:** BookNow
**API Style:** REST API
**Base Version:** `/v1`
**Document Type:** API Specification
**Primary Output:** Endpoints, Auth, Permission Matrix, Error Format, Examples

## Status

| Field | Value |
|---|---|
| Document Status | Approved |
| Owner | Tech Lead |
| Reviewer | Backend Team, QA |
| Last Updated | 2026-02-05 |
| Related | [Backend Architecture](../backend_architecture/backend_architecture.md), [Database Schema](../database/database_schema.md), [Permission Requirements](../../04_requirements/permission_requirements.md), [Business Rules](../../04_requirements/business_rules.md) |

---

## 0. Executive Summary

BookNow API เป็น REST API เดียวที่ให้บริการทั้ง Next.js public booking pages, Owner/Staff dashboard และในอนาคตอาจรองรับ partner integration แบ่งกลุ่ม endpoint ตาม actor เป็น 4 กลุ่มหลัก:

1. **Auth** — login ของ Owner/Staff (email+password/magic link)
2. **Owner-only management** — business/service/staff
3. **Public (ไม่ auth, rate-limited)** — availability + สร้าง booking สำหรับลูกค้า
4. **Token-based (customer)** — จัดการ booking ของตัวเองผ่าน signed token ในลิงก์
5. **Owner/Staff booking operations** — ดู list, mark complete/no-show, audit log

หลักที่ยึดทุก endpoint: **fail closed** — ตรวจสิทธิ์ไม่ผ่านหรือตรวจสอบไม่ได้ ให้ปฏิเสธเสมอ (ตรงตาม [Permission Requirements](../../04_requirements/permission_requirements.md) Core Principle)

---

## 1. Purpose

เอกสารนี้ใช้เพื่อ:

- กำหนด REST API contract ของ BookNow MVP ที่ `/v1`
- เป็น reference ให้ web (public + dashboard), backend และ QA ทำงานร่วมกัน
- ระบุ permission check ที่ต้องมีต่อ endpoint โดยอ้างอิงตรงกับ [Permission Requirements](../../04_requirements/permission_requirements.md)
- กำหนด error format และ response envelope มาตรฐาน

---

## 2. Base URL and Headers

### 2.1 Base URL

```text
Production: https://api.booknow.app/v1
Staging: https://staging-api.booknow.app/v1
Local: http://localhost:3000/v1
```

### 2.2 Headers

| Header | Required | Description |
|---|---:|---|
| `Authorization: Bearer <jwt>` | Owner/Staff endpoint | JWT access token |
| `X-Booking-Token: <token>` | Customer booking-management endpoint | signed token ผูกกับ booking เดียว (จากลิงก์ในอีเมล/SMS) |
| `Content-Type: application/json` | เมื่อมี body | request body type |
| `X-Correlation-Id` | Should | client-generated request trace id |
| `Accept-Language` | Should | `th`, `en` |

### 2.3 Standard Response Envelope

Success (single resource):

```json
{
  "data": {},
  "meta": { "requestId": "req_abc123", "version": "v1" }
}
```

Success (list):

```json
{
  "data": [],
  "pagination": { "nextCursor": "eyJjcmVhdGVkQXQ...", "hasMore": false, "limit": 20 },
  "meta": { "requestId": "req_abc123", "version": "v1" }
}
```

Error:

```json
{
  "error": {
    "code": "SLOT_ALREADY_BOOKED",
    "message": "ช่วงเวลานี้ถูกจองแล้ว กรุณาเลือกเวลาใหม่",
    "details": {}
  },
  "meta": { "requestId": "req_abc123", "version": "v1" }
}
```

---

## 3. Authentication

### 3.1 Owner/Staff Auth

| Method | Endpoint |
|---|---|
| Login (email+password) | `POST /auth/login` |
| Request magic link | `POST /auth/magic-link/request` |
| Verify magic link | `POST /auth/magic-link/verify` |
| Refresh access token | `POST /auth/refresh` |
| Logout (current device) | `POST /auth/logout` |
| Logout all devices | `POST /auth/logout-all` |

```http
POST /v1/auth/login
Content-Type: application/json
```

```json
{
  "email": "owner@somsri-salon.com",
  "password": "••••••••"
}
```

Response:

```json
{
  "data": {
    "accessToken": "jwt_access_token",
    "refreshToken": "refresh_token",
    "user": {
      "id": "usr_01H...",
      "email": "owner@somsri-salon.com",
      "displayName": "สมศรี",
      "role": "owner",
      "businessId": "biz_01H..."
    }
  }
}
```

### 3.2 Customer Access (ไม่มี Login)

ลูกค้าไม่มีบัญชี — เข้าถึง booking ของตัวเองผ่านลิงก์ที่มี `X-Booking-Token` (ส่งทางอีเมล/SMS ตอนจองสำเร็จ) token นี้ผูกกับ `booking_id` เดียว หมดอายุ 30 วันหลัง booking เสร็จสิ้น/ถูกยกเลิก (PERM-003) ทุก endpoint ในกลุ่ม "Booking Management (Customer)" ตรวจสอบ token นี้แทนการ login

---

## 4. Endpoint Overview

| Group | Prefix | Auth | Actor |
|---|---|---|---|
| Auth | `/auth` | — | Owner, Staff |
| Business | `/businesses/me` | JWT | Owner |
| Services | `/services` | JWT | Owner |
| Staff | `/staff` | JWT | Owner |
| Public Availability | `/public/availability` | ไม่ auth (rate-limited) | Customer |
| Public Booking | `/public/bookings` | ไม่ auth (rate-limited) | Customer |
| Booking Management (Customer) | `/bookings/{bookingId}/manage` | `X-Booking-Token` | Customer |
| Bookings (Owner/Staff) | `/bookings` | JWT | Owner, Staff |
| Audit Logs | `/audit-logs` | JWT | Owner |

---

## 5. Permission Matrix ต่อ Endpoint

ตารางนี้ map endpoint แต่ละกลุ่มกับ [Permission Requirements](../../04_requirements/permission_requirements.md) เพื่อให้ backend ผูก guard ได้ตรง

| Endpoint | Method | ใครเรียกได้ | Permission Rule ที่ใช้ |
|---|---|---|---|
| `/businesses/me` | GET, PATCH | Owner เท่านั้น | PERM-001: ต้องเป็น Owner ของ business นั้น |
| `/services` | GET, POST, PATCH | Owner เท่านั้น | Staff ห้ามแก้ service ไม่ว่ามี flag ใดก็ตาม (Permission Requirements "Explicitly Not Allowed") |
| `/staff` | GET, POST, PATCH, DELETE | Owner เท่านั้น | PERM-005: เชิญ/ลบพนักงาน/เปลี่ยน flag ต้องสร้าง audit log; PERM-004: ลบพนักงานต้อง revoke session ทันที |
| `/public/availability` | GET | ทุกคน (rate-limited) | ไม่มี auth แต่ต้อง rate limit ป้องกัน scraping |
| `/public/bookings` | POST | ทุกคน (rate-limited) | ไม่มี auth — สร้าง booking ใหม่, ต้องผ่าน DB exclusion constraint (BR-001) |
| `/bookings/{bookingId}/manage` | GET, PATCH (reschedule), POST (cancel) | Customer ที่ถือ `X-Booking-Token` ตรงกับ booking นั้น | PERM-001, PERM-003: token ต้องผูกกับ booking นี้เท่านั้น |
| `/bookings` | GET | Owner เห็นทั้งหมด; Staff เห็นเฉพาะของตัวเอง เว้นแต่มี `view_all_bookings` | BR-004, PERM-002 |
| `/bookings/{bookingId}` | PATCH (reschedule/cancel) | Owner ทุก booking; Staff เฉพาะของตัวเองเว้นแต่มี `manage_all_bookings` | BR-004, PERM-002 |
| `/bookings/{bookingId}/complete` | POST | Owner ทุก booking; Staff เฉพาะของตัวเอง (มี/ไม่มี flag ก็ทำ mark ของนัดตัวเองได้) | Permission Matrix แถว "Mark completed / no-show" |
| `/bookings/{bookingId}/no-show` | POST | เหมือนกับ `/complete` — ปกติระบบ mark อัตโนมัติผ่าน background job (BR-003) endpoint นี้ใช้กรณี manual override | เหมือนด้านบน |
| `/audit-logs` | GET | Owner เท่านั้น | Permission Matrix: "ดู audit log" — Owner เท่านั้น ไม่มี flag ใดปลดล็อกให้ Staff |

---

## 6. Business & Service & Staff Management (Owner-only)

### 6.1 Update Business Profile

```http
PATCH /v1/businesses/me
Authorization: Bearer <owner_token>
```

```json
{
  "name": "ร้านทำผมสมศรี",
  "cancellationCutoffMinutes": 120,
  "noShowGraceMinutes": 15
}
```

### 6.2 Create Service

```http
POST /v1/services
Authorization: Bearer <owner_token>
```

```json
{
  "name": "ตัดผมชาย",
  "durationMinutes": 30,
  "price": 150
}
```

Response:

```json
{
  "data": {
    "id": "svc_01H...",
    "name": "ตัดผมชาย",
    "durationMinutes": 30,
    "price": 150,
    "isActive": true
  }
}
```

### 6.3 Soft-delete Service

```http
DELETE /v1/services/{serviceId}
Authorization: Bearer <owner_token>
```

ระบบไม่ลบจริง — ตั้ง `isActive = false` เท่านั้น (BR-006) response คืน `204 No Content`

### 6.4 Invite Staff

```http
POST /v1/staff
Authorization: Bearer <owner_token>
```

```json
{
  "email": "chang@somsri-salon.com",
  "displayName": "ช่างเอ",
  "serviceIds": ["svc_01H...", "svc_02H..."]
}
```

### 6.5 Update Staff Permission Flags

```http
PATCH /v1/staff/{staffId}
Authorization: Bearer <owner_token>
```

```json
{
  "viewAllBookings": true,
  "manageAllBookings": false
}
```

การเรียกนี้ต้องสร้าง audit log ทันที (PERM-005)

---

## 7. Public Availability & Booking (ไม่ Auth, Rate-limited)

Rate limit แนะนำ: 30 requests/นาที ต่อ IP สำหรับ `/public/availability`, 10 requests/นาที ต่อ IP สำหรับ `/public/bookings` (ปรับตาม pilot จริง — ดู Open Questions)

### 7.1 Get Availability

```http
GET /v1/public/availability?businessSlug=somsri-salon&serviceId=svc_01H...&staffId=stf_01H...&date=2026-07-10
```

`staffId` เป็น optional — ไม่ส่งมาหมายถึง "คนไหนก็ได้" (ตาม FR-004) ระบบรวม slot ว่างของทุกคนที่ทำบริการนี้ได้

Response:

```json
{
  "data": {
    "date": "2026-07-10",
    "serviceId": "svc_01H...",
    "durationMinutes": 30,
    "slots": [
      { "startTime": "2026-07-10T02:00:00Z", "staffId": "stf_01H...", "staffName": "ช่างเอ" },
      { "startTime": "2026-07-10T02:30:00Z", "staffId": "stf_01H...", "staffName": "ช่างเอ" },
      { "startTime": "2026-07-10T03:00:00Z", "staffId": "stf_02H...", "staffName": "ช่างบี" }
    ]
  }
}
```

### 7.2 Create Booking (Most Important Endpoint)

```http
POST /v1/public/bookings
Content-Type: application/json
```

```json
{
  "businessSlug": "somsri-salon",
  "serviceId": "svc_01H...",
  "staffId": "stf_01H...",
  "startTime": "2026-07-10T02:00:00Z",
  "customer": {
    "name": "คุณมานี",
    "phone": "+66891234567",
    "email": "manee@example.com"
  }
}
```

Response — สำเร็จ (`201 Created`):

```json
{
  "data": {
    "id": "bkg_01H...",
    "status": "confirmed",
    "service": { "id": "svc_01H...", "name": "ตัดผมชาย", "durationMinutes": 30 },
    "staff": { "id": "stf_01H...", "name": "ช่างเอ" },
    "startTime": "2026-07-10T02:00:00Z",
    "endTime": "2026-07-10T02:30:00Z",
    "manageBookingUrl": "https://booknow.app/manage/bkg_01H...?token=eyJhbGciOi..."
  }
}
```

Response — ชนกับ booking อื่น (`409 Conflict`, ตรงกับ FR-004 acceptance criteria และ [Backend Architecture](../backend_architecture/backend_architecture.md) หัวข้อ 5):

```json
{
  "error": {
    "code": "SLOT_ALREADY_BOOKED",
    "message": "ช่วงเวลานี้ถูกจองแล้ว กรุณาเลือกเวลาใหม่",
    "details": { "staffId": "stf_01H...", "startTime": "2026-07-10T02:00:00Z" }
  }
}
```

Backend ต้อง catch PostgreSQL exclusion constraint violation (`23P01`) ในธุรกรรมนี้และแปลงเป็น error ข้างต้น — ไม่ retry อัตโนมัติที่ server (ให้ client แจ้งลูกค้าเลือกเวลาใหม่)

---

## 8. Booking Management (Customer, Token-based)

### 8.1 Get Booking Detail

```http
GET /v1/bookings/{bookingId}/manage
X-Booking-Token: eyJhbGciOi...
```

Token ต้องตรวจสอบว่า `bookingId` ใน path ตรงกับ `booking_id` ที่ encode ไว้ใน token — ถ้าไม่ตรง ตอบ `403 TOKEN_MISMATCH` ไม่ใช่ `200` (ป้องกันการเดา booking ID อื่น)

### 8.2 Reschedule Booking

```http
PATCH /v1/bookings/{bookingId}/manage
X-Booking-Token: eyJhbGciOi...
```

```json
{
  "action": "reschedule",
  "newStartTime": "2026-07-11T03:00:00Z"
}
```

ผ่าน exclusion constraint เดียวกันกับการสร้าง booking — อาจได้ `409 SLOT_ALREADY_BOOKED` เช่นกัน

### 8.3 Cancel Booking

```http
POST /v1/bookings/{bookingId}/manage/cancel
X-Booking-Token: eyJhbGciOi...
```

```json
{ "reason": "ติดธุระ" }
```

Response ขึ้นกับเวลาปัจจุบันเทียบ cutoff (BR-002):

```json
{
  "data": {
    "id": "bkg_01H...",
    "status": "cancelled_by_customer",
    "wasLateCancellation": false
  }
}
```

ถ้ายกเลิกหลัง cutoff, `status` จะเป็น `late_cancellation` และ `wasLateCancellation: true` แต่ request ยัง**สำเร็จ** (ระบบยังอนุญาตให้ยกเลิกได้เสมอ ตาม BR-002 — ไม่มีการปฏิเสธ)

---

## 9. Booking Operations (Owner/Staff)

### 9.1 List Today's Bookings (Most Important Endpoint)

```http
GET /v1/bookings?date=2026-07-10&limit=20
Authorization: Bearer <staff_token>
```

Staff ที่ไม่มี `view_all_bookings` จะเห็นเฉพาะ booking ที่ `staffId` ตรงกับตัวเอง — backend ต้อง apply filter นี้ที่ query level (BR-004) ไม่ใช่กรองที่ response หลัง query มาแล้ว

Response:

```json
{
  "data": [
    {
      "id": "bkg_01H...",
      "status": "confirmed",
      "service": { "id": "svc_01H...", "name": "ตัดผมชาย" },
      "staff": { "id": "stf_01H...", "name": "ช่างเอ" },
      "customer": { "name": "คุณมานี", "phone": "+66891234567" },
      "startTime": "2026-07-10T02:00:00Z",
      "endTime": "2026-07-10T02:30:00Z"
    },
    {
      "id": "bkg_02H...",
      "status": "confirmed",
      "service": { "id": "svc_03H...", "name": "สีผม" },
      "staff": { "id": "stf_01H...", "name": "ช่างเอ" },
      "customer": { "name": "คุณสมชาย", "phone": "+66898887777" },
      "startTime": "2026-07-10T04:00:00Z",
      "endTime": "2026-07-10T05:30:00Z"
    }
  ],
  "pagination": { "nextCursor": null, "hasMore": false, "limit": 20 }
}
```

ถ้า login เป็น Owner (ไม่ส่ง filter เพิ่ม) response จะรวม booking ของพนักงานทุกคนในธุรกิจ (FR-009)

### 9.2 Mark Completed

```http
POST /v1/bookings/{bookingId}/complete
Authorization: Bearer <staff_token>
```

Staff ทำได้เฉพาะนัดของตัวเอง เว้นแต่มี `manage_all_bookings` — ถ้าไม่มีสิทธิ์ ตอบ `403 ROLE_FORBIDDEN`

### 9.3 Mark No-show (Manual Override)

```http
POST /v1/bookings/{bookingId}/no-show
Authorization: Bearer <staff_token>
```

ใช้เมื่อ Staff ต้องการ mark ก่อนที่ background job auto no-show จะรัน (ปกติระบบ mark อัตโนมัติหลัง grace period ตาม BR-003 — endpoint นี้เป็น manual path เสริม)

---

## 10. Audit Log (Owner-only)

```http
GET /v1/audit-logs?bookingId=bkg_01H...&limit=20
Authorization: Bearer <owner_token>
```

```json
{
  "data": [
    {
      "id": "aud_01H...",
      "action": "booking.cancelled",
      "actorType": "customer",
      "actorId": null,
      "bookingId": "bkg_01H...",
      "beforeState": { "status": "confirmed" },
      "afterState": { "status": "cancelled_by_customer" },
      "createdAt": "2026-07-09T10:15:00Z"
    }
  ],
  "pagination": { "nextCursor": null, "hasMore": false, "limit": 20 }
}
```

ไม่มี `PATCH`/`DELETE` endpoint สำหรับ resource นี้เลยตามหลักการ BR-007 — เป็น read-only เสมอ

---

## 11. Error Format & Codes

### 11.1 Standard Error Response

```json
{
  "error": {
    "code": "ROLE_FORBIDDEN",
    "message": "คุณไม่มีสิทธิ์ทำรายการนี้",
    "details": {}
  },
  "meta": { "requestId": "req_abc123", "version": "v1" }
}
```

### 11.2 Error Codes

| HTTP | Code | Meaning | เมื่อไหร่ |
|---:|---|---|---|
| 400 | `VALIDATION_ERROR` | input ไม่ถูกต้อง | body/query ผิด schema |
| 401 | `AUTH_REQUIRED` | ยังไม่ login | Owner/Staff endpoint ไม่มี/หมด token |
| 401 | `TOKEN_EXPIRED` | access token หมดอายุ | client ต้อง refresh |
| 401 | `BOOKING_TOKEN_INVALID` | `X-Booking-Token` ไม่ถูกต้อง/หมดอายุ (PERM-003) | customer endpoint |
| 403 | `ROLE_FORBIDDEN` | role ไม่มีสิทธิ์ทำ action | เช่น Staff พยายามแก้ service |
| 403 | `TOKEN_MISMATCH` | token ผูกกับ booking อื่น | customer ใช้ token ของ booking ตนเองไปเรียก booking อื่น |
| 404 | `BOOKING_NOT_FOUND` | ไม่พบหรือไม่มีสิทธิ์เห็น | ใช้แทน 403 เพื่อไม่เปิดเผยว่า booking มีอยู่จริง เมื่อ Staff query booking นอกสิทธิ์ |
| 409 | `SLOT_ALREADY_BOOKED` | ช่วงเวลาที่เลือกถูกจองไปแล้ว | exclusion constraint violation (BR-001) |
| 422 | `CUTOFF_ALREADY_PASSED_INFO` | informational — ยกเลิกได้แต่เลย cutoff แล้ว | ไม่ block request แค่แจ้ง client แสดง UI ต่างออกไป (ไม่ใช่ error จริง มักไม่ถูกใช้เพราะ endpoint ยัง 200 พร้อม `wasLateCancellation`) |
| 429 | `RATE_LIMITED` | request ถี่เกินไป | `/public/*` endpoints |
| 503 | `NOTIFICATION_PROVIDER_UNAVAILABLE` | ส่ง confirmation/reminder ไม่ได้ ณ ขณะนั้น | booking ยังสร้างสำเร็จ แต่ notification จะ retry ผ่าน background job |

### 11.3 Privacy-safe Error Rule

ถ้า Staff query booking ที่ไม่มีสิทธิ์เห็น (ไม่ใช่ของตัวเองและไม่มี `view_all_bookings`) ให้ตอบ `404 BOOKING_NOT_FOUND` แทน `403` เพื่อไม่เปิดเผยว่า booking นั้นมีอยู่จริง (สอดคล้องแนวทาง fail-closed)

---

## 12. Pagination

List endpoints ทั้งหมด (`/bookings`, `/audit-logs`) ใช้ cursor pagination:

```http
GET /v1/bookings?limit=20&cursor=eyJjcmVhdGVkQXQ...
```

`limit` default 20, สูงสุด 100

---

## 13. Versioning

- URL versioning: `/v1`, `/v2` ในอนาคต
- Backward compatible: เพิ่ม optional field, เพิ่ม endpoint ใหม่, เพิ่ม enum value ที่ client มี fallback
- Breaking change: ลบ field, เปลี่ยน type, เปลี่ยน required field, เปลี่ยน permission behavior, เปลี่ยน error code semantics — ต้องขึ้น `/v2`

---

## 14. Security Considerations

- ทุก Owner/Staff endpoint ตรวจ JWT ก่อนเข้า business logic เสมอ
- ทุก customer endpoint ตรวจ `X-Booking-Token` และ match `bookingId` ก่อนเสมอ — ไม่มี path ที่ skip การตรวจนี้
- `/public/*` endpoints ต้อง rate-limit ด้วย IP (และพิจารณาผูกกับ `businessSlug` เพิ่มถ้า scraping เจาะจงร้านเดียว)
- ไม่ log request body เต็มของ endpoint ที่มีข้อมูลลูกค้า (เบอร์โทร/อีเมล) ใน application log ทั่วไป — ใช้ audit log แทนสำหรับ mutation สำคัญ

---

## 15. Testing Considerations

| Area | Test |
|---|---|
| Auth | login, refresh, logout, logout-all |
| Public booking | create booking success, concurrent booking → 409, rate limit |
| Customer token | reschedule/cancel with valid token, token mismatch → 403, expired token → 401 |
| Staff visibility | Staff เห็นเฉพาะของตัวเอง, มี `view_all_bookings` แล้วเห็นทั้งหมด |
| Cancellation cutoff | ยกเลิกก่อน cutoff → `cancelled_by_customer`, หลัง cutoff → `late_cancellation` |
| Audit log | ไม่มี endpoint update/delete, Owner เท่านั้นที่เข้าถึงได้ |

---

## 16. Product and API Decisions

| Decision | Choice | Reasoning |
|---|---|---|
| API style | REST | เข้าใจง่าย เหมาะกับ web client เดียวใน MVP |
| Versioning | URL `/v1` | ชัดเจน รองรับ breaking change ในอนาคต |
| Owner/Staff auth | JWT access+refresh | มาตรฐาน รองรับ mobile app ใน Phase 2 ได้โดยไม่เปลี่ยน pattern |
| Customer auth | Signed single-purpose token | ไม่ต้องมีบัญชีลูกค้าตาม MVP scope |
| Pagination | Cursor-based | รองรับ list ที่โตเร็ว เช่น audit log |
| Error สำหรับ booking นอกสิทธิ์ | 404 ไม่ใช่ 403 | privacy-safe ตามหลัก fail-closed |

---

## 17. Open Questions

- Rate limit ที่เหมาะสมสำหรับ `/public/bookings` ควรผูกกับ phone number ที่กรอกด้วยไหม (กัน spam booking ชื่อปลอม — ดู PRD Open Questions เรื่อง OTP)
- ควรมี idempotency key จาก client สำหรับ `POST /public/bookings` เพื่อป้องกัน double-submit จาก double-click หรือพอจะพึ่ง exclusion constraint (ที่กันแค่ "ชนกับคนอื่น" ไม่กัน "ตัวเองกดซ้ำ 2 ครั้งในเวลาเดียวกันสำเร็จทั้งคู่เป็นบริการต่างกัน") — ควรเพิ่ม client-generated idempotency key ในรอบถัดไป
- ต้อง generate OpenAPI YAML จาก markdown นี้ตั้งแต่ MVP หรือรอ endpoint stable ก่อน

---

## 18. Linked Docs

- [Backend Architecture](../backend_architecture/backend_architecture.md)
- [Database Schema](../database/database_schema.md)
- [Web Architecture](../web/web_architecture.md)
- [Permission Requirements](../../04_requirements/permission_requirements.md)
- [Business Rules](../../04_requirements/business_rules.md)
- [Functional Requirements](../../04_requirements/functional_requirements.md)
