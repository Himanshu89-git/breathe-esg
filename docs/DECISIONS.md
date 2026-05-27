# DECISIONS.md — Ambiguity Resolution Log

Every non-obvious choice made during this build, and what I'd ask the PM if I could.

---

## SAP Export Format: Flat File (not IDoc, not OData)

**Chose:** Semicolon/tab-delimited flat file export from ABAP report (transaction SE16N / MB51 style)

**Why not IDoc:** IDoc is the right long-term choice for system-to-system integration, but it requires an SAP Basis admin to configure a partner profile and port definition. The flat file is what sustainability leads actually email to analysts today.

**Why not OData:** SAP's OData services (via SAP Fiori / Gateway) require whitelisting on the client's SAP system and IT involvement. Overkill for a prototype that needs to work with a new enterprise client in 4 days.

**What I chose to handle:** Plant-level fuel and procurement movements (SAP MM Movement Type 261 — goods issue). Material master is not ingested — we infer fuel category from material number and description text matching.

**What I ignored:** Cost object accounting (internal orders, WBS elements), split valuations, batch management, purchasing documents. These exist in SAP but are not needed for emissions calculation.

**German headers:** SAP exports field names in the system language. Added a bilingual column map (WERKS/PLANT, MENGE/QUANTITY, etc.). This covers ~90% of real deployments.

**What I'd ask the PM:** Does the client use SAP S/4HANA or ECC? S/4HANA has a native sustainability module (SAP Sustainability Footprint Management) — if they're on S/4 we should explore that API instead of raw file exports.

---

## Utility Data: CSV Portal Export (not PDF, not API)

**Chose:** CSV export from utility customer portal

**Why not PDF:** PDF bill parsing breaks with every template change. Indian utilities (TATA Power, BESCOM, MSEDCL) all have slightly different PDF layouts; some are scanned images. OCR is fragile and would require significant validation effort.

**Why not Green Button API / utility API:** Green Button is primarily a US standard; Indian utilities do not expose it. Some large utilities have informal APIs but they require separate vendor agreements.

**CSV wins because:** Every major utility portal (including Indian state DISCOMs' online portals) offers a CSV download. Facilities teams already do this monthly. It's the lowest-friction path.

**Billing period vs calendar month:** Utility bills don't align with month ends. A bill may run Jan 15–Feb 14. We store both `period_start` and `period_end` and use `period_end` as the `activity_date` (standard practice for accrual-based reporting). We warn if a billing period exceeds 35 days (may indicate combined billing).

**What I'd ask the PM:** Are any facilities on time-of-use or real-time tariffs? If so, we need interval data (15-min or hourly reads), not just monthly totals. That's a significant scope expansion.

---

## Travel Data: CSV Export (not Concur/Navan API)

**Chose:** CSV export from corporate travel platform (Concur or Navan format)

**Why not Concur API:** Concur's SAP Concur API requires OAuth 2.0 with a registered app. Enterprise clients typically need IT and procurement approval to enable third-party API access. A CSV export from the Reports section is available to any travel admin.

**Why not Navan API:** Same reason. Navan (TripActions) has an API but it requires an enterprise plan and IT setup.

**Flight distance calculation:** Concur exports sometimes include distance, sometimes only airport codes. When codes are present but distance is absent, we compute great-circle distance from a hardcoded lookup table of ~30 major airports. This covers the most common routes for an Indian enterprise client. Routes involving smaller airports fall back to null distance with a warning.

**Emission factors:** DEFRA 2023 values per passenger-km, split by short-haul (<3700 km) and long-haul (≥3700 km). Radiative Forcing Index (RFI) of approximately 2x is baked into the DEFRA short-haul factor. Business class uses a 2x multiplier; first class 3x.

**Hotel emissions:** DEFRA 2023 global average of 31.2 kg CO2e per room-night. This is very rough — hotel emissions vary hugely by property, country, and star rating. We flag this as a known limitation.

**What I'd ask the PM:** Does the client track employee-level travel budgets? If so, we could attribute emissions to business units for internal reporting. Also: does the travel policy cover personal car mileage claims? Those are common Scope 3 sources not covered by the Concur export.

---

## Scope Assignment

Scope is inferred at parse time from category, not entered manually. Rationale: manual entry is error-prone and inconsistent across analysts. The inference rules are documented in each parser and can be overridden by an analyst via the review workflow (reject + re-upload with corrected data).

**Edge cases resolved:**
- Natural gas from SAP → Scope 1 (direct combustion, on-site boiler)
- Electricity from SAP → Scope 2 (if material description contains STROM/ELECTRICITY)
- Purchased steam → Scope 2

---

## Authentication

JWT (via djangorestframework-simplejwt). 8-hour access tokens, 7-day refresh tokens. Simple, stateless, works with React SPA without session cookies. Not SSO/SAML — that would be required in production for an enterprise client.

---

## File Storage

Files stored via Django's `FileField` / `MEDIA_ROOT`. For local/SQLite development this means the `media/` directory. On Render with PostgreSQL, this means the ephemeral filesystem — files would be lost on dyno restart. Production fix: switch to S3/GCS using `django-storages`. This is a known limitation documented in TRADEOFFS.md.

---

## What I'd Ask the PM (consolidated)

1. Is this client on SAP S/4HANA or ECC? Affects integration path significantly.
2. Are there time-of-use electricity meters? Interval data changes the utility ingestion entirely.
3. Do they need location-based Scope 2 (requires regional grid factors) or is market-based sufficient?
4. What is the audit standard? GHG Protocol Corporate Standard? ISO 14064? CDP? This affects which Scope 3 categories are mandatory.
5. Is the travel data from one platform or multiple (Concur + Amex GBT + manual)? Multiple sources means deduplication logic is needed.
6. What's the reporting year boundary? April–March (India financial year) vs January–December?
