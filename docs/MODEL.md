# MODEL.md — Breathe ESG Data Model

## Core Philosophy

The data model has one job: make every emission number **traceable back to its source, unambiguously**. Every row in `EmissionRecord` knows where it came from, when it was ingested, who touched it, and whether it has been reviewed. Nothing gets lost, mutated silently, or orphaned.

---

## Entity Overview

```
Tenant
  └── User (analyst, admin, auditor)
  └── IngestionBatch (one per upload session)
        └── EmissionRecord (one per activity event)
              └── EmissionFactor (lookup — kg CO2e per unit)
```

---

## Multi-Tenancy

**Model:** `Tenant`

Every data-bearing model carries a `tenant` FK. There are no shared records between tenants. All querysets in API views filter by `request.user.tenant` as the first operation — this is enforced at the viewset level, not the model level, which means a misconfigured view could leak data. In production, row-level security in PostgreSQL would be the correct enforcement mechanism.

Each `User` belongs to exactly one `Tenant`. Users with `role=admin` can see all data for their tenant; `role=auditor` gets read-only access to approved records only (not implemented in prototype but the role field is there).

---

## IngestionBatch — Provenance Tracking

Every upload creates an `IngestionBatch`. The batch records:

| Field | Purpose |
|---|---|
| `source_type` | Which of the three ingestion paths (sap / utility / travel) |
| `file_name` | Original filename as uploaded |
| `file_path` | Stored file (for re-processing or audit) |
| `uploaded_by` | FK to User — who triggered this ingest |
| `status` | pending → processing → done / failed |
| `row_count` | How many records were created |
| `error_count` | How many rows failed parsing |
| `error_log` | JSON array of row-level parse errors with raw data snapshot |
| `reporting_period_start/end` | Inferred from the records' `activity_date` range |
| `processed_at` | Timestamp of completion |

This means: if a batch fails, we know exactly which rows failed and why, without losing the raw input.

---

## EmissionRecord — Source of Truth

One row = one activity event (one fuel transaction, one billing period, one travel booking).

### Scope 1/2/3 Categorisation

| Scope | Categories |
|---|---|
| 1 (Direct) | diesel, petrol, lpg, natural_gas, coal — from SAP |
| 2 (Indirect electricity) | electricity — from utility |
| 3 (Value chain) | flight, hotel, car_rental, taxi, rail — from travel |

Scope is **inferred at parse time** from the activity category, not entered manually. The inference logic lives in the parser layer so it can be audited and updated independently.

### Unit Normalisation

Raw units from SAP (litres, gallons, M3, kg, tons) are normalised at parse time into a **canonical unit set**:

| Canonical | Covers |
|---|---|
| litre | L, LT, GAL (×3.785), M3 (×1000) |
| kg | KG, G (×0.001), T (×1000), TO, LB (×0.454) |
| kWh | KWH, MWH (×1000), GJ (×277.8), MMBTU (×293.1) |
| passenger-km | for travel |
| room-night | for hotels |
| km | for car/taxi |

Both `quantity` (normalised) and `quantity_original` + `unit_original` are stored. The original is frozen — never recalculated. This lets analysts verify the conversion.

### Emission Calculation

`kg_co2e = quantity × emission_factor.kg_co2e_per_unit`

Emission factors are stored in a separate `EmissionFactor` table (not hard-coded). The FK from `EmissionRecord` to `EmissionFactor` means you can see exactly which factor version was used at the time of ingest. If DEFRA releases updated factors, old records retain their original factor reference — the analyst can trigger a recalculation if needed.

Travel emissions are partially pre-computed in the parser (flight distance × DEFRA factor, hotel room-nights × factor) because the inputs (airport codes, distance) don't fit neatly into the `quantity × factor` pattern.

### Source-of-Truth Tracking

`raw_data` (JSONField) stores the original row as parsed — a snapshot of every field from the source file at ingest time. This field is **never mutated** after creation.

`edit_history` (JSONField, list) records any analyst edits:
```json
[{"field": "quantity", "old": 15000, "new": 14850, "by": "analyst@acme.com", "at": "2024-01-15T10:30:00Z"}]
```

`is_edited` (boolean) flags records that have been manually corrected.

### Review Workflow

```
pending → approved   (analyst signs off)
pending → flagged    (analyst wants discussion)
pending → rejected   (analyst rejects as erroneous)
flagged → approved   (after discussion)
flagged → rejected
```

Approved records are considered locked for audit purposes. In a full implementation, approved records would be write-protected at the DB level.

### Suspicious Record Flagging

Heuristic flags set at parse time:
- SAP: quantity > 100,000 litres fuel in a single transaction
- Utility: zero kWh consumption; kWh > 500,000 in one billing period
- Travel: flight distance > 18,000 km; single trip > 10,000 kg CO2e

`is_suspicious` and `suspicion_reason` are stored on the record. Analysts see these prominently in the dashboard.

---

## EmissionFactor

Separate table rather than hard-coded constants because:
1. Factors are updated annually (DEFRA, EPA, IEA)
2. Regional variants (India grid vs UK grid electricity)
3. Auditors need to verify which factor version was applied

Key fields: `source_type`, `activity`, `unit`, `region`, `kg_co2e_per_unit`, `valid_from`, `valid_to`, `source_reference`.

Currently seeded with DEFRA 2023 values. CEA India 2023 grid emission factor for electricity (0.23314 kg CO2e/kWh).

---

## Indexes

```sql
INDEX (tenant, scope, status)    -- dashboard filter: show me all pending Scope 2
INDEX (tenant, source_type)      -- filter by ingestion source
INDEX (batch)                    -- drill into a specific upload
INDEX (activity_date)            -- time-range queries for reporting periods
```

---

## What This Model Does Not Handle (by design)

See TRADEOFFS.md for the full list. In brief:
- **Location-based vs market-based Scope 2** — we store market-based (grid average). Renewable energy certificates / PPAs would require a separate contract table.
- **Scope 3 categories beyond travel** — GHG Protocol has 15 Scope 3 categories. We cover Category 6 (Business Travel) only.
- **Version-controlled emission factors** — the FK captures which factor was used, but there is no migration tool to recalculate all records when factors are updated.
- **Currency conversion** — billed amounts are stored as-is; no FX normalisation.
