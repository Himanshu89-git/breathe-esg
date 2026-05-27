# TRADEOFFS.md — Deliberate Omissions

Three things not built, and why.

---

## 1. Location-Based Scope 2 (Market-Based Only)

**What it is:** The GHG Protocol allows two methods for Scope 2 electricity emissions. Market-based uses the contractual instrument (supplier-specific factor, renewable energy certificate, PPA). Location-based uses the average grid emission factor for the geographic region.

**What was built:** Market-based only, using a single grid average factor per country (e.g., 0.233 kg CO2e/kWh for India per CEA 2023). This is the simpler and more commonly reported method.

**What was not built:** Location-based calculation requires knowing the specific grid region (not just country — India has five regional grids with different emission intensities), the billing period, and the corresponding year's grid factor. This requires a time-series database of regional grid emission factors and a geographic lookup from meter address to grid region.

**Why skipped:** This is a significant data infrastructure investment (sourcing, storing, and versioning regional grid factors for every geography the client operates in) that goes beyond what can be built in 4 days without client-specific configuration. It is also not necessary for initial CDP/GHG Protocol reporting — market-based alone is acceptable.

**What would be needed to add it:** A `GridEmissionFactor` model with (region, year, kg_co2e_per_kwh), a geographic hierarchy for meter addresses, and a second calculation pass on all utility records.

---

## 2. Automated Deduplication Across Batches

**What it is:** When the same data source is uploaded twice (e.g., a facilities manager re-exports January's utility data after a correction), the system would ideally detect overlapping records and flag or replace duplicates instead of creating two sets of records for the same billing period.

**What was built:** Batches are independent. Uploading the same file twice creates duplicate records. An analyst would need to reject the older batch's records manually.

**Why skipped:** Deduplication logic for financial/utility data is genuinely hard. The natural key for a utility record is (account_number, billing_period_start, billing_period_end, kWh). For SAP, it might be (posting_document_number, line_item). These natural keys vary by source and client. A generic deduplication rule that's wrong would silently drop valid records — worse than duplicates, which are at least visible.

**What would be needed to add it:** Source-type-specific natural keys defined per client (as configuration), a pre-ingest deduplication check, and a UI for analysts to review and resolve conflicts. Estimated: 2-3 additional days of careful work.

---

## 3. Scope 3 Beyond Business Travel (Category 6 Only)

**What it is:** The GHG Protocol Corporate Value Chain Standard defines 15 Scope 3 categories. This prototype covers Category 6 (Business Travel) only.

**The other 14 categories include:**
- Category 1: Purchased goods and services (the largest for most companies)
- Category 3: Fuel and energy-related activities
- Category 11: Use of sold products
- Category 15: Investments

**Why skipped:** Each category requires its own data model and emission factor logic. Category 1 alone (purchased goods) typically requires supplier-level spend data, industry-average emission factors (EEIO models), or supplier-specific product carbon footprints — a multi-month data collection exercise. The SAP procurement data in this prototype focuses on fuel/energy only; extending it to purchased goods would require a completely different category inference and factor lookup approach.

**What was not built:** Upstream transportation (Cat 4), employee commuting (Cat 7), upstream leased assets (Cat 8). These are commonly required for CDP and are the next priority after the three sources in this prototype.

**What would be needed:** A category-specific ingestion module for each Scope 3 category, with its own normalisation rules and emission factor table. The `EmissionRecord` model already has the `scope` and `category` fields to accommodate this — the data model is extensible.
