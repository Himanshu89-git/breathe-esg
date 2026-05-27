# SOURCES.md — Real-World Format Research

For each source: what was researched, what was learned, what the sample data looks like and why, and what would break in a real deployment.

---

## Source 1: SAP (Fuel & Procurement)

### What was researched

SAP exports can take several forms. I looked at:

- **IDoc (Intermediate Document):** SAP's standard EDI format. Hierarchical, fixed-width segments (E1MBGMKPF for goods movement headers, E1MBGMPOSITION for line items). Used for system-to-system integration. Documentation: SAP Help Portal, IDoc type MBGMCR.
- **Flat file via ABAP report:** Transaction MB51 (Material Document List) or SE16N (table browser on MSEG — Material Document Segment) exports semicolon or tab-delimited files. This is what sustainability leads actually download.
- **OData (via SAP Gateway):** REST+JSON. Available on S/4HANA via `/sap/opu/odata/sap/API_MATERIAL_DOCUMENT_SRV`. Requires Gateway configuration.
- **BAPI:** BAPI_MATERIAL_GETLIST, BAPI_GOODSMVT_GETDETAIL. Requires ABAP programming or RFC connection.

**Key learnings:**
- Real SAP exports use German field names in German-language systems (WERKS = Plant, KOSTL = Cost Center, MENGE = Quantity, MEINS = Unit of Measure, BUDAT = Posting Date)
- Units are SAP internal codes: L (litre), KG, TO (metric ton), M3, GAL, LB
- Dates are in DD.MM.YYYY format in German systems, YYYYMMDD in some ABAP report variants
- Movement Type 261 = goods issue to cost center (most common for fuel consumption)
- Plant codes (WERKS) are 4-character codes meaningless without the plant master lookup table

### Sample data rationale

`sap_fuel_export.csv` uses:
- Semicolon delimiter (most common in non-English SAP systems)
- German column headers (WERKS, KOSTL, MENGE, MEINS, BUDAT, MAKTX)
- DD.MM.YYYY dates (German system format)
- SAP unit codes (L, KG, M3)
- Realistic Indian plant codes (PLANT-DEL, PLANT-BOM)
- Movement Type 261 throughout
- One deliberately suspicious row: 120,000 litres diesel in a single transaction

### What would break in production

1. **Plant master not included:** WERKS codes are meaningless without the T001W table. Real deployments need a plant-to-address/country mapping.
2. **Material master not included:** MATNR is a free-form code. Material descriptions (MAKTX) are not standardized — "Diesel HSD Grade A" and "HSD Diesel" are the same thing but won't match our keyword list.
3. **Split valuations and batch management:** High-volume fuel usage may be split across multiple line items with different valuations. Our parser sums by category, which is correct but hides the split.
4. **Character encoding:** Old SAP systems export in SAP1 or ISO-8859-1. We handle UTF-8 and latin-1 but SAP1 has non-standard characters for some European languages.
5. **Large files:** MB51 exports for a full year across all plants can be 100k+ rows. Our parser loads into pandas in-memory — would need chunked processing for files >50MB.

---

## Source 2: Utility Data (Electricity)

### What was researched

Utility data access in India:
- **TATA Power, MSEDCL, BESCOM, BSES:** All offer online customer portals with bill history download as CSV or PDF
- **Indian DISCOM portals:** Typically export: account number, meter number, billing period, units consumed (kWh), demand (kVA or kW), tariff category, amount billed
- **Green Button:** US standard for smart meter data export (XML or CSV). Not widely available in India.
- **ESPI API (Energy Service Provider Interface):** Extension of Green Button for API access. Available from some US utilities (PG&E, ComEd). Not relevant for India.
- **EnergyCAP, Urjanet:** Third-party platforms that aggregate utility bill data from multiple utilities. Enterprise clients sometimes use these — they export in normalized CSV.

**Key learnings:**
- Indian commercial tariffs are complex: LT (Low Tension), HT (High Tension), time-of-day variants
- Billing periods do NOT align with calendar months — they follow meter reading schedules
- Large facilities (data centers, factories) may have multiple meters on one account
- Demand charges (kW) are billed separately from consumption (kWh) — both on the same bill
- Some bills show renewable % if the supplier offers green tariffs
- PDF bills are the norm for smaller accounts; larger accounts get portal CSV access

### Sample data rationale

`utility_electricity_export.csv` uses realistic Indian utility data:
- Multiple meters at different facilities with different tariff types (LT-Commercial, HT-Industrial)
- Realistic kWh consumption ranges (9,500 to 620,000 kWh/month)
- One zero-consumption row (meter issue / vacant facility — suspicious)
- One very high consumption row (data center — also suspicious to flag for review)
- One row spanning two months (Chennai office — period Jan 1 to Feb 28, 59 days, triggers warning)
- Multiple real Indian utilities (TATA Power, MSEDCL, BESCOM, BSES Rajdhani, TANGEDCO)

### What would break in production

1. **PDF bills:** Many Indian utilities still issue only PDF bills for some account types. These require OCR, which is unreliable without a utility-specific parser.
2. **Demand data:** We store demand_kw but don't use it for emissions (kWh is the correct basis). Some carbon accounting methodologies use demand for transmission loss calculations.
3. **Time-of-use meters:** Interval data (15-minute reads) for ToU tariffs is not handled — we only handle monthly totals.
4. **Renewable energy certificates:** If the client has purchased RECs or has a PPA, the market-based Scope 2 calculation needs to use the contractual factor (potentially zero), not the grid factor. This is not in scope.
5. **Multi-currency:** Indian utilities bill in INR; international facilities bill in local currency. We store amount as-is with no FX conversion.

---

## Source 3: Corporate Travel (Concur/Navan)

### What was researched

- **SAP Concur Travel:** Concur exports via Reports > Travel > Trip Report. Standard columns include: Employee Name, Travel Date, Trip Type (Air/Hotel/Car/Rail), Origin, Destination, Amount, Currency, Cabin Class, Vendor. Distance not always included.
- **Navan (TripActions):** Very similar CSV format. Available from Reports section. Includes booking date, travel date, segment type, route codes.
- **Concur API:** OAuth 2.0. Endpoints: `/travel/v2/trips`, `/expense/v4/reports`. Enterprise-only; requires IT admin to register app.
- **IATA airport codes:** Standard 3-letter codes used by all travel platforms. Great-circle distance must be computed from coordinates when not provided.
- **Emission factors:** DEFRA 2023 GHG Conversion Factors for Company Reporting (Table 6.1 for air, Table 4 for ground transport, Table 14.4 for hotels). ICAO Carbon Offset Calculator methodology also consulted.

**Key learnings:**
- Concur exports one row per booking segment (outbound and return are separate rows)
- Hotel records don't have origin/destination — just check-in city and number of nights
- Car rental records have a pickup location but distance is often absent
- Business class multiplier is approximately 2x economy per DEFRA (seat-area method)
- Radiative Forcing Index (RFI): DEFRA 2023 bakes in an RFI of ~2x for aviation (accounts for non-CO2 warming effects of contrails and NOx at altitude)
- Short-haul vs long-haul threshold: DEFRA uses 3,700 km

### Sample data rationale

`travel_concur_export.csv` includes:
- All four travel categories: Air, Hotel, Car Rental, Taxi, Rail
- Mix of domestic (DEL-BOM, BLR-MAA) and international (BOM-LHR, DEL-JFK) flights
- Business class rows (Amit Kumar — realistic for exec travel to New York)
- One suspicious row: DEL-JFK at 12,000 km appears twice (outbound + return), realistic
- Hotel nights attached to travel: separate rows for same traveler on same dates
- Indian airlines (IndiGo, SpiceJet, Air India) and international (British Airways)
- One rail segment (Delhi-Mumbai — realistic, Rajdhani Express)
- IATA codes: DEL, BOM, BLR, MAA, LHR, CDG, JFK — all in our lookup table

### What would break in production

1. **IATA codes not in lookup table:** We only have ~25 airports. A flight to a secondary airport (e.g., Coimbatore COK, Patna PAT) would fail distance calculation, and kg CO2e would be null.
2. **Missing distance for ground transport:** Car rental and taxi records rarely include distance in Concur exports. Without distance, kg CO2e cannot be calculated. We warn but cannot fill this gap without additional data.
3. **Hotel emission factor quality:** 31.2 kg CO2e/room-night is a very coarse global average. A luxury hotel in Singapore vs a budget hotel in Nagpur have very different footprints. The HCMI (Hotel Carbon Measurement Initiative) provides property-level factors but requires the hotel's cooperation.
4. **Multi-platform deduplication:** Large enterprises often use multiple travel agencies. The same trip may appear in Concur (for airfare booked via corporate portal) and on an expense report (for a locally booked taxi). Deduplication across platforms is not handled.
5. **Personal vehicle mileage:** Employee mileage claims (driving personal car for business) are typically on expense reports, not travel booking systems. These are a meaningful Scope 3 source but are not in the Concur travel export.
