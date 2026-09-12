# Q42 benchmark review — approval pending

All 42 questions retain their original wording. Each proposed oracle is executed against the V3 database. Ambiguous business conclusions are proposed as diagnostic-only; no model predictions or scores exist.

Approval is required by README Phase 28 before full training. The attached CSV contains all old golds, new results and exact SQL. Numerical/company deltas are not certified because old gold is unstructured prose.

## Q01: Show all "Tier 1/2" suppliers in Georgia, list their EV Supply Chain Role and Product / Service.

Proposed primary eligibility: True. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company",
      "ev_supply_chain_role",
      "product_or_service"
    ],
    "rows": [
      [
        "F&P Georgia Manufacturing",
        "Battery Pack",
        "Lithium-ion battery recycler and raw materials provider"
      ],
      [
        "Fouts Brothers Fire Equipment",
        "General Automotive",
        "Automotive body parts and electronics Cylinder-head and specialty gaskets, housing modules and shielding systems for engines, transmissions, exhaust systems and auxiliary units"
      ],
      [
        "Hitachi Astemo",
        "General Automotive",
        "Car audio systems"
      ],
      [
        "Hitachi Astemo Americas Inc.",
        "Battery Cell",
        "Battery cells for electric mobility"
      ],
      [
        "Hollingsworth & Vose Co.",
        "Battery Pack",
        "Lithium-ion battery materials"
      ],
      [
        "Honda Development & Manufacturing",
        "Battery Cell",
        "Battery cells for electric mobility"
      ],
      [
        "Hwashin",
        "General Automotive",
        "Modules and storage systems"
      ],
      [
        "Hyundai & LG Energy Solution (LGES)",
        "General Automotive",
        "Storage batteries"
      ],
      [
        "Hyundai Industrial Co.",
        "General Automotive",
        "Automotive batteries"
      ],
      [
        "Hyundai MOBIS (Georgia)",
        "General Automotive",
        "Capacitors, electronic automotive components"
      ],
      [
        "Hyundai Motor Group",
        "Battery Pack",
        "Battery parts for electric vehicles"
      ],
      [
        "Hyundai Transys Georgia Powertrain",
        "Thermal Management",
        "Electrical heaters, control units, and actuators"
      ],
      [
        "Hyundai Transys Georgia Seating Systems",
        "General Automotive",
        "Automotive electronics, resonators, capacitors, resistors, electronics and electronic parts"
      ],
      [
        "IMMI",
        "Battery Pack",
        "Battery electrolyte"
      ],
      [
        "IMS Gear Georgia Inc.",
        "General Automotive",
        "Car audio systems"
      ],
      [
        "Inalfa Roof Systems Inc.",
        "General Automotive",
        "Automotive electronic safety systems"
      ],
      [
        "JAC Products Inc.",
        "General Automotive",
        "Switches, resistors and related products"
      ],
      [
        "Jefferson Southern Corp.",
        "General Automotive",
        "High current switches and resistors for automotive HVAC systems"
      ]
    ]
  }
}
```

## Q02: Which Georgia companies are classified under Battery Cell or Battery Pack roles, and what tier is each assigned?

Proposed primary eligibility: True. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company",
      "category",
      "ev_supply_chain_role"
    ],
    "rows": [
      [
        "F&P Georgia Manufacturing",
        "Tier 1/2",
        "Battery Pack"
      ],
      [
        "Hitachi Astemo Americas Inc.",
        "Tier 1/2",
        "Battery Cell"
      ],
      [
        "Hollingsworth & Vose Co.",
        "Tier 1/2",
        "Battery Pack"
      ],
      [
        "Honda Development & Manufacturing",
        "Tier 1/2",
        "Battery Cell"
      ],
      [
        "Hyundai Motor Group",
        "Tier 1/2",
        "Battery Pack"
      ],
      [
        "IMMI",
        "Tier 1/2",
        "Battery Pack"
      ]
    ]
  }
}
```

## Q03: Map all Thermal Management suppliers in Georgia and show which Primary OEMs they are linked to.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company",
      "primary_oems"
    ],
    "rows": [
      [
        "Freudenberg-NOK",
        "Multiple OEMs"
      ],
      [
        "Hyundai Transys Georgia Powertrain",
        "Hyundai Kia Rivian"
      ],
      [
        "Novelis Inc.",
        "Multiple OEMs"
      ],
      [
        "Peerless-Winsmith Inc.",
        "Multiple OEMs"
      ]
    ]
  }
}
```

## Q04: List every Georgia company classified under Power Electronics or Charging Infrastructure, along with their Employment size.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company",
      "ev_supply_chain_role",
      "employment"
    ],
    "rows": [
      [
        "GSC Steel Stamping LLC",
        "Power Electronics",
        350
      ],
      [
        "Morgan Corp.",
        "Charging Infrastructure",
        320
      ],
      [
        "Yazaki North America",
        "Power electronics, sensors, and EV systems",
        230000
      ],
      [
        "ZF Gainesville LLC",
        "EV thermal management and power electronics",
        17500
      ]
    ]
  }
}
```

## Q05: Which companies are classified as Direct Manufacturer, and what EV Supply Chain Roles do they cover?

Proposed primary eligibility: True. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Use Classification Method = Direct Manufacturer; the old answer substituted Category = OEM.

```json
{
  "answer": {
    "columns": [
      "company",
      "ev_supply_chain_role"
    ],
    "rows": [
      [
        "Kia Georgia Inc.",
        "Vehicle Assembly"
      ],
      [
        "Minebea AccessSolutions USA Inc.",
        "General Automotive"
      ],
      [
        "Superior Essex Inc.",
        "Vehicle Assembly"
      ],
      [
        "Suzuki Manufacturing of America Corp.",
        "Vehicle Assembly"
      ],
      [
        "TCI Powder Coatings",
        "Vehicle Assembly"
      ],
      [
        "TDK Components USA Inc.",
        "Vehicle Assembly"
      ],
      [
        "TE Connectivity",
        "Vehicle Assembly"
      ],
      [
        "Teklas USA",
        "Vehicle Assembly"
      ],
      [
        "Textron Specialized Vehicles",
        "Vehicle Assembly"
      ],
      [
        "Thermal Ceramics Inc.",
        "Vehicle Assembly"
      ],
      [
        "Thomson Plastics Inc.",
        "Vehicle Assembly"
      ]
    ]
  }
}
```

## Q06: What locations does Novelis Inc. operate in, and what primary facility types are associated with each location?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Repeated rows do not prove distinct operational sites; preserve row attribution.

```json
{
  "answer": {
    "columns": [
      "row_id",
      "company",
      "location",
      "primary_facility_type"
    ],
    "rows": [
      [
        64,
        "Novelis Inc.",
        "Atlanta, Fulton County",
        "Manufacturing Plant"
      ],
      [
        128,
        "Novelis Inc.",
        "Atlanta, Fulton County",
        "Manufacturing Plant"
      ],
      [
        129,
        "Novelis Inc.",
        "Atlanta, Fulton County",
        "Manufacturing Plant"
      ]
    ]
  }
}
```

## Q07: In Gwinnett County, which company has the highest Employment and what is its EV Supply Chain Role?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic.

```json
{
  "answer": {
    "columns": [
      "company",
      "employment",
      "ev_supply_chain_role"
    ],
    "rows": [
      [
        "WIKA USA",
        250000,
        "HV and LV wiring harnesses for EVs and ICE vehicles"
      ]
    ]
  }
}
```

## Q08: Which county have the highest total Employment among Tier 1 suppliers only?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic.

```json
{
  "answer": {
    "columns": [
      "county"
    ],
    "rows": [
      [
        "Troup County"
      ]
    ]
  }
}
```

## Q09: Which county has the highest total employment across all companies, and what is the combined employment in that county?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic.

```json
{
  "answer": {
    "columns": [
      "county",
      "recorded_total"
    ],
    "rows": [
      [
        "Hall County",
        314452
      ]
    ]
  }
}
```

## Q10: Identify all Vehicle Assembly facilities in Georgia and list the corresponding Primary OEM associated with each facility.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Repeated rows do not prove distinct operational sites; preserve row attribution.

```json
{
  "answer": {
    "columns": [
      "row_id",
      "company",
      "primary_oems"
    ],
    "rows": [
      [
        95,
        "Kia Georgia Inc.",
        "Club Car LLC"
      ],
      [
        171,
        "Superior Essex Inc.",
        "Hyundai Motor Group"
      ],
      [
        172,
        "Suzuki Manufacturing of America Corp.",
        "Rivian Automotive"
      ],
      [
        173,
        "TCI Powder Coatings",
        "Kia Georgia Inc."
      ],
      [
        174,
        "TDK Components USA Inc.",
        "Mercedes-Benz USA LLC"
      ],
      [
        175,
        "TE Connectivity",
        "Blue Bird Corp."
      ],
      [
        176,
        "Teklas USA",
        "Yamaha Motor Manufacturing Corp."
      ],
      [
        177,
        "Textron Specialized Vehicles",
        "Textron Specialized Vehicles"
      ],
      [
        178,
        "Thermal Ceramics Inc.",
        "SK Battery America"
      ],
      [
        179,
        "Thomson Plastics Inc.",
        "Archer Aviation Inc."
      ]
    ]
  }
}
```

## Q11: Identify the primary products and services associated with Sewon America Inc. across its different operational sites in Georgia.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Repeated rows do not prove distinct operational sites; preserve row attribution.

```json
{
  "answer": {
    "columns": [
      "row_id",
      "company",
      "location",
      "product_or_service"
    ],
    "rows": [
      [
        148,
        "Sewon America Inc.",
        "LaGrange, Troup County",
        "Automotive aftermarket parts"
      ],
      [
        151,
        "Sewon America Inc.",
        "LaGrange, Troup County",
        "Motor vehicle engines and parts"
      ],
      [
        161,
        "Sewon America Inc.",
        "LaGrange, Troup County",
        "Fire truck bodies"
      ]
    ]
  }
}
```

## Q12: List all Tier 2/3 companies in Georgia with primary involvement in the electric vehicle or battery supply chain and specify their respective roles.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company",
      "ev_supply_chain_role"
    ],
    "rows": [
      [
        "Duckyang",
        "General Automotive"
      ],
      [
        "Enchem America Inc.",
        "General Automotive"
      ],
      [
        "GSC Steel Stamping LLC",
        "Power Electronics"
      ]
    ]
  }
}
```

## Q13: Show the full supplier network linked to Rivian Automotive in Georgia, broken down by tier and EV Supply Chain Role.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "category",
      "ev_supply_chain_role",
      "primary_oems"
    ],
    "rows": [
      [
        "Duckyang",
        "Tier 2/3",
        "General Automotive",
        "Hyundai Kia Rivian"
      ],
      [
        "Enchem America Inc.",
        "Tier 2/3",
        "General Automotive",
        "Hyundai Kia Rivian"
      ],
      [
        "GSC Steel Stamping LLC",
        "Tier 2/3",
        "Power Electronics",
        "Hyundai Kia Rivian"
      ],
      [
        "Hyundai Transys Georgia Powertrain",
        "Tier 1/2",
        "Thermal Management",
        "Hyundai Kia Rivian"
      ],
      [
        "Racemark International LLC",
        "Tier 1",
        "General Automotive",
        "Hyundai Kia Rivian"
      ],
      [
        "Suzuki Manufacturing of America Corp.",
        "OEM",
        "Vehicle Assembly",
        "Rivian Automotive"
      ]
    ]
  }
}
```

## Q14: Identify all Georgia companies with an EV Supply Chain Role related to wiring harnesses and show their Primary OEMs.

Proposed primary eligibility: True. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company",
      "primary_oems"
    ],
    "rows": [
      [
        "WIKA USA",
        "Not specified"
      ],
      [
        "Woodbridge Foam Corp.",
        "Not specified"
      ]
    ]
  }
}
```

## Q15: Identify Georgia Tier 2/3 companies in the Electronic and Electrical Equipment industry group that could be upgraded to supply EV power electronics.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "product_or_service"
    ],
    "rows": []
  }
}
```

## Q16: Find Georgia-based companies that manufacture copper foil or electrodeposited materials suitable for EV battery current collectors.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "product_or_service"
    ],
    "rows": [
      [
        "Duckyang",
        "High-quality electrodeposited (ED) copper foil for electric vehicles"
      ]
    ]
  }
}
```

## Q17: Which Georgia Tier 1/2 companies produce engineered plastics, polymers, or composite materials applicable to EV structural or thermal components?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability. Process/service membership is included; keyword matching is an explicit candidate definition, not validated engineering suitability.

```json
{
  "answer": {
    "columns": [
      "company",
      "product_or_service"
    ],
    "rows": [
      [
        "Fouts Brothers Fire Equipment",
        "Automotive body parts and electronics Cylinder-head and specialty gaskets, housing modules and shielding systems for engines, transmissions, exhaust systems and auxiliary units"
      ]
    ]
  }
}
```

## Q18: Identify Georgia companies producing DC-to-DC converters, capacitors, or power electronics components and what tier is each assigned?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "category"
    ],
    "rows": [
      [
        "GSC Steel Stamping LLC",
        "Tier 2/3"
      ],
      [
        "Hyundai MOBIS (Georgia)",
        "Tier 1/2"
      ],
      [
        "Hyundai Transys Georgia Seating Systems",
        "Tier 1/2"
      ],
      [
        "Yazaki North America",
        "OEM (Footprint)"
      ],
      [
        "ZF Gainesville LLC",
        "OEM Supply Chain"
      ]
    ]
  }
}
```

## Q19: Which Georgia companies provide powder coating-related products or services, and what tier are they classified under?

Proposed primary eligibility: True. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Process/service membership is included; keyword matching is an explicit candidate definition, not validated engineering suitability.

```json
{
  "answer": {
    "columns": [
      "company",
      "category"
    ],
    "rows": [
      [
        "Archer Aviation Inc.",
        "Tier 2/3"
      ],
      [
        "Continental Tire the Americas LLC",
        "Tier 2/3"
      ],
      [
        "DAS Corp.",
        "Tier 2/3"
      ],
      [
        "FOX Factory",
        "Tier 2/3"
      ],
      [
        "FREYR Battery",
        "Tier 2/3"
      ],
      [
        "TCI Powder Coatings",
        "OEM"
      ]
    ]
  }
}
```

## Q20: Which Georgia companies are classified under Battery Cell/Battery Pack roles or battery-related products and are Tier 1/2, making them ready for direct OEM engagement and show which Primary OEMs they are linked to.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "primary_oems"
    ],
    "rows": [
      [
        "F&P Georgia Manufacturing",
        "Hyundai Kia"
      ],
      [
        "Hitachi Astemo Americas Inc.",
        "Hyundai Kia"
      ],
      [
        "Hollingsworth & Vose Co.",
        "Hyundai Kia"
      ],
      [
        "Honda Development & Manufacturing",
        "Hyundai Kia"
      ],
      [
        "Hyundai Motor Group",
        "Hyundai Kia"
      ],
      [
        "IMMI",
        "Hyundai Kia"
      ]
    ]
  }
}
```

## Q21: Find Tier 2/3 Georgia-based suppliers with employment over 300 that are classified as General Automotive but produce components transferable to EV platforms.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "employment",
      "product_or_service"
    ],
    "rows": [
      [
        "ACM Georgia LLC",
        400,
        "Automotive floor mats made of purchased wire"
      ],
      [
        "AVS",
        310,
        "Tires for light trucks, SUVs and commercial vehicles"
      ],
      [
        "Arising Industries Inc.",
        582,
        "Automotive and aircraft tires"
      ],
      [
        "Dinex Emissions Inc.",
        500,
        "Aluminum sheet for automotive bodies"
      ],
      [
        "Dongwon Autopart Technology Georgia LLC",
        315,
        "Aluminum extrusions"
      ],
      [
        "FOX Factory",
        345,
        "Chrome plated automotive parts"
      ],
      [
        "Flambeau Inc.",
        700,
        "Door locks, ignition locks, side mirrors and door handles"
      ],
      [
        "Grudem",
        807,
        "Sensors for mobile hydraulic applications"
      ]
    ]
  }
}
```

## Q22: Identify Georgia Tier 2/3 companies in the Chemicals and Allied Products industry group and list their products.

Proposed primary eligibility: True. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company",
      "product_or_service"
    ],
    "rows": [
      [
        "Archer Aviation Inc.",
        "Powder coatings for automotive and other industries"
      ],
      [
        "Arising Industries Inc.",
        "Rubber powders for tires"
      ]
    ]
  }
}
```

## Q23: Which EV Supply Chain Roles in Georgia are served by only a single company, creating a single-point-of-failure risk for the state's EV ecosystem?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "ev_supply_chain_role",
      "recorded_companies"
    ],
    "rows": [
      [
        "Advanced electrical architecture for EVs",
        1
      ],
      [
        "Body and chassis components for EV and ICE OEMs",
        1
      ],
      [
        "Charging Infrastructure",
        1
      ],
      [
        "EV and ICE component manufacturing",
        1
      ],
      [
        "EV and ICE powertrain and HVAC components",
        1
      ],
      [
        "EV body, powertrain, and thermal components",
        1
      ],
      [
        "EV electrical distribution and interior systems",
        1
      ],
      [
        "EV sensors, braking, and control systems",
        1
      ],
      [
        "EV thermal management and power electronics",
        1
      ],
      [
        "EV thermal systems and electronics",
        1
      ],
      [
        "EV wiring harnesses and power distribution",
        1
      ],
      [
        "HV and LV wiring harnesses for EVs and ICE vehicles",
        1
      ],
      [
        "High‑voltage EV connectors and electronics",
        1
      ],
      [
        "Interior and exterior plastic parts",
        1
      ],
      [
        "Interior trim and textile components",
        1
      ],
      [
        "Machined components supporting EV and ICE vehicles",
        1
      ],
      [
        "OEM corporate and engineering footprint (electrification)",
        1
      ],
      [
        "OEM corporate footprint and supplier integration",
        1
      ],
      [
        "OEM corporate footprint influencing EV strategy",
        1
      ],
      [
        "OEM parent group footprint (EV + HD electrification)",
        1
      ],
      [
        "OEM parent group footprint (electric truck strategy)",
        1
      ],
      [
        "Plastic components for EV and ICE vehicles",
        1
      ],
      [
        "Power Electronics",
        1
      ],
      [
        "Power electronics, sensors, and EV systems",
        1
      ],
      [
        "Stamped and welded assemblies for OEMs",
        1
      ],
      [
        "Stamped metal components for OEMs",
        1
      ],
      [
        "Tier 1 automotive components",
        1
      ],
      [
        "Vehicle safety systems OEM (EV + ICE)",
        1
      ]
    ]
  }
}
```

## Q24: Which Georgia Battery Cell or Battery Pack suppliers are sole-sourced by a specific OEM, indicating high dependency risk?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability. The workbook lacks verified sole-source or Hyundai Metaplant-specific supplier links; no numerical or named-supplier conclusion is supported.

```json
"Insufficient evidence in the supplied dataset."
```

## Q25: For Hyundai Metaplant, how many of its Georgia-based EV component suppliers have fewer than 200 employees, flagging potential capacity fragility?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability. The workbook lacks verified sole-source or Hyundai Metaplant-specific supplier links; no numerical or named-supplier conclusion is supported.

```json
"Insufficient evidence in the supplied dataset."
```

## Q26: Identify Georgia Tier 2/3 suppliers that are EV Relevant and classified as General Automotive.

Proposed primary eligibility: True. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company"
    ],
    "rows": [
      [
        "Duckyang"
      ],
      [
        "Enchem America Inc."
      ]
    ]
  }
}
```

## Q27: Identify all Georgia-based Tier 1/2 automotive suppliers that maintain a diversified customer base (serving 'Multiple OEMs').

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company"
    ],
    "rows": [
      [
        "Fouts Brothers Fire Equipment"
      ],
      [
        "Hitachi Astemo"
      ],
      [
        "Hwashin"
      ],
      [
        "Hyundai & LG Energy Solution (LGES)"
      ],
      [
        "Hyundai Industrial Co."
      ],
      [
        "Hyundai MOBIS (Georgia)"
      ],
      [
        "Hyundai Transys Georgia Seating Systems"
      ],
      [
        "IMS Gear Georgia Inc."
      ],
      [
        "Inalfa Roof Systems Inc."
      ],
      [
        "JAC Products Inc."
      ],
      [
        "Jefferson Southern Corp."
      ]
    ]
  }
}
```

## Q28: Identify Georgia companies in the Thermal Management or Power Electronics role with fewer than 200 employees - their small scale may limit surge production capacity.

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "employment",
      "ev_supply_chain_role"
    ],
    "rows": [
      [
        "Freudenberg-NOK",
        160,
        "Thermal Management"
      ],
      [
        "Hyundai Transys Georgia Powertrain",
        130,
        "Thermal Management"
      ],
      [
        "Peerless-Winsmith Inc.",
        160,
        "Thermal Management"
      ]
    ]
  }
}
```

## Q29: Identify any EV-relevant Georgia companies classified as OEM Footprint or OEM Supply Chain?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Canonical category is OEM (Footprint); Yes and Indirect are included in this proposed interpretation.

```json
{
  "answer": {
    "columns": [
      "company",
      "category"
    ],
    "rows": [
      [
        "TI Fluid Systems",
        "OEM (Footprint)"
      ],
      [
        "TN Americas Holding Inc.",
        "OEM (Footprint)"
      ],
      [
        "Tie Down Engineering",
        "OEM (Footprint)"
      ],
      [
        "Toyota Industries Group (TACG-TICA)",
        "OEM (Footprint)"
      ],
      [
        "Trenton Pressing",
        "OEM (Footprint)"
      ],
      [
        "Trenton Pressing Inc.",
        "OEM Supply Chain"
      ],
      [
        "Valeo",
        "OEM Supply Chain"
      ],
      [
        "Vanguard National Trailer Corp.",
        "OEM Supply Chain"
      ],
      [
        "Vernay",
        "OEM Supply Chain"
      ],
      [
        "Vista Metals Corp.",
        "OEM Supply Chain"
      ],
      [
        "Voestalpine Automotive Body Parts Inc.",
        "OEM Supply Chain"
      ],
      [
        "Volvo Cars USA",
        "OEM Supply Chain"
      ],
      [
        "Volvo Group North America",
        "OEM Supply Chain"
      ],
      [
        "WIKA USA",
        "OEM Supply Chain"
      ],
      [
        "Wabash National Corp.",
        "OEM Supply Chain"
      ],
      [
        "Wheelabrator Group Inc.",
        "OEM Supply Chain"
      ],
      [
        "Woodbridge Foam Corp.",
        "OEM Supply Chain"
      ],
      [
        "Woory Industrial Co.",
        "OEM Supply Chain"
      ],
      [
        "YKK USA Inc.",
        "OEM (Footprint)"
      ],
      [
        "Yachiyo Manufacturing of America LLC",
        "OEM Supply Chain"
      ],
      [
        "Yamaha Motor Manufacturing Corp.",
        "OEM Supply Chain"
      ],
      [
        "Yazaki North America",
        "OEM (Footprint)"
      ],
      [
        "ZF Gainesville LLC",
        "OEM Supply Chain"
      ],
      [
        "ZF Gainesville LLC",
        "OEM (Footprint)"
      ]
    ]
  }
}
```

## Q30: Top 10 Georgia companies based on employment size that supply both General Automotive and EV-specific components, indicating transition readiness?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "employment"
    ],
    "rows": [
      [
        "JTEKT North America Corp.",
        860
      ],
      [
        "Kautex Inc.",
        800
      ],
      [
        "Lark United Manufacturing Inc.",
        700
      ],
      [
        "Fouts Brothers Fire Equipment",
        630
      ],
      [
        "Arising Industries Inc.",
        582
      ],
      [
        "Dinex Emissions Inc.",
        500
      ],
      [
        "Lund International Inc.",
        500
      ],
      [
        "Mack Trucks",
        500
      ],
      [
        "Mando America Corp.",
        460
      ],
      [
        "ACM Georgia LLC",
        400
      ]
    ]
  }
}
```

## Q31: Which Georgia Tier 2/3 suppliers currently produce lightweight aluminum or composite materials and are ev relevant or indirectly ev relevant?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "product_or_service",
      "ev_battery_relevant"
    ],
    "rows": [
      [
        "Bridgestone Bandag",
        "Composite materials and specialty polymers for automotive components",
        "Indirect"
      ],
      [
        "Dinex Emissions Inc.",
        "Aluminum sheet for automotive bodies",
        "Indirect"
      ],
      [
        "Down 2 Earth Trailers",
        "Standard and custom aluminum-lithium products for automotive customers",
        "Indirect"
      ],
      [
        "Eaton Corp.",
        "Aluminum products for various markets including automotive market",
        "Indirect"
      ],
      [
        "Ecoplastic America Corporation",
        "Aluminum sheet for automotive bodies",
        "Indirect"
      ],
      [
        "Erdrich USA Inc.",
        "Aluminum sheet for automotive bodies",
        "Indirect"
      ],
      [
        "Global Powertrain Systems LLC",
        "Motor vehicle brake systems and parts Fabricates metal products, including coated coils, metal wall and roof systems and aluminum recreational vehicle doors",
        "Indirect"
      ]
    ]
  }
}
```

## Q32: Identify Georgia companies whose product descriptions include 'high-voltage', 'DC-to-DC', 'inverter', or 'motor controller' — these signal EV powertrain electronics growth.

Proposed primary eligibility: True. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company",
      "product_or_service"
    ],
    "rows": [
      [
        "GSC Steel Stamping LLC",
        "Deep grove ball bearings Toyota Industries Electric Systems North 255 DC-to-DC converters Jackson America, Inc.*"
      ]
    ]
  }
}
```

## Q33: Which Georgia automotive companies employ over 1,000 workers but are currently categorized as only "Indirectly Relevant" to the EV sector, indicating a massive workforce pool ready for a strategic pivot?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "employment"
    ],
    "rows": [
      [
        "TCI Powder Coatings",
        3000
      ],
      [
        "Teklas USA",
        1800
      ],
      [
        "Textron Specialized Vehicles",
        1100
      ]
    ]
  }
}
```

## Q34: Which four Georgia companies have the largest employment in EV thermal management, and how many employees does each have?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic.

```json
{
  "answer": {
    "columns": [
      "company",
      "employment"
    ],
    "rows": [
      [
        "ZF Gainesville LLC",
        170000
      ],
      [
        "ZF Gainesville LLC",
        106100
      ],
      [
        "ZF Gainesville LLC",
        17500
      ],
      [
        "Novelis Inc.",
        200
      ]
    ]
  }
}
```

## Q35: Which companies are involved in thermal-related products or services, and what roles and facility types are they associated with?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Process/service membership is included; keyword matching is an explicit candidate definition, not validated engineering suitability.

```json
{
  "answer": {
    "columns": [
      "company",
      "ev_supply_chain_role",
      "primary_facility_type"
    ],
    "rows": [
      [
        "Aspen Aerogels",
        "Materials",
        "Manufacturing Plant"
      ],
      [
        "Freudenberg-NOK",
        "Thermal Management",
        "Manufacturing Plant"
      ],
      [
        "Hyundai Transys Georgia Powertrain",
        "Thermal Management",
        "Manufacturing Plant"
      ],
      [
        "Magna International",
        "General Automotive",
        "Manufacturing Plant"
      ],
      [
        "Novelis Inc.",
        "Thermal Management",
        "Manufacturing Plant"
      ],
      [
        "Peerless-Winsmith Inc.",
        "Thermal Management",
        "Manufacturing Plant"
      ],
      [
        "Thermal Ceramics Inc.",
        "Vehicle Assembly",
        "Manufacturing Plant"
      ],
      [
        "ZF Gainesville LLC",
        "EV body, powertrain, and thermal components",
        "Manufacturing"
      ],
      [
        "ZF Gainesville LLC",
        "EV thermal management and power electronics",
        "Manufacturing"
      ],
      [
        "ZF Gainesville LLC",
        "EV thermal systems and electronics",
        "Engineering / Operations"
      ]
    ]
  }
}
```

## Q36: Which Tier 1/2 Georgia companies listed under General Automotive?

Proposed primary eligibility: True. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production.

```json
{
  "answer": {
    "columns": [
      "company"
    ],
    "rows": [
      [
        "Fouts Brothers Fire Equipment"
      ],
      [
        "Hitachi Astemo"
      ],
      [
        "Hwashin"
      ],
      [
        "Hyundai & LG Energy Solution (LGES)"
      ],
      [
        "Hyundai Industrial Co."
      ],
      [
        "Hyundai MOBIS (Georgia)"
      ],
      [
        "Hyundai Transys Georgia Seating Systems"
      ],
      [
        "IMS Gear Georgia Inc."
      ],
      [
        "Inalfa Roof Systems Inc."
      ],
      [
        "JAC Products Inc."
      ],
      [
        "Jefferson Southern Corp."
      ]
    ]
  }
}
```

## Q37: How is demand for thermal management solutions reflected in the number and employment size of Georgia Thermal Management suppliers?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Employment scope/date and conflicting duplicate observations prevent a defensible company-level or county workforce/capacity total; SQL output is only a record-level diagnostic. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "count": {
    "columns": [
      "n"
    ],
    "rows": [
      [
        5
      ]
    ]
  },
  "employment": {
    "columns": [
      "row_id",
      "company",
      "employment"
    ],
    "rows": [
      [
        60,
        "Freudenberg-NOK",
        160
      ],
      [
        84,
        "Hyundai Transys Georgia Powertrain",
        130
      ],
      [
        129,
        "Novelis Inc.",
        200
      ],
      [
        139,
        "Peerless-Winsmith Inc.",
        160
      ],
      [
        203,
        "ZF Gainesville LLC",
        170000
      ],
      [
        204,
        "ZF Gainesville LLC",
        17500
      ],
      [
        205,
        "ZF Gainesville LLC",
        106100
      ]
    ]
  }
}
```

## Q38: Which Georgia companies are involved in battery recycling or second-life battery processing, reflecting the emerging circular economy trend?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "product_or_service"
    ],
    "rows": [
      [
        "EVCO Plastics",
        "Recycler of copper, precious metals, and non-ferrous materials"
      ],
      [
        "Enplas USA Inc.",
        "Recycler of lithium ion batteries"
      ],
      [
        "F&P Georgia Manufacturing",
        "Lithium-ion battery recycler and raw materials provider"
      ]
    ]
  }
}
```

## Q39: Which Georgia supplier appears to play an innovation-stage role through research, development, or prototyping activity?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability. Process/service membership is included; keyword matching is an explicit candidate definition, not validated engineering suitability.

```json
{
  "answer": {
    "columns": [
      "company",
      "product_or_service",
      "primary_facility_type"
    ],
    "rows": [
      [
        "Racemark International LLC",
        "Manufacturing and R&D engine parts for EV",
        "R&D"
      ]
    ]
  }
}
```

## Q40: Which Georgia suppliers currently serving traditional OEMs are also linked to EV-native OEMs, showing dual-platform supply capability?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "primary_oems"
    ],
    "rows": [
      [
        "Duckyang",
        "Hyundai Kia Rivian"
      ],
      [
        "Enchem America Inc.",
        "Hyundai Kia Rivian"
      ],
      [
        "GSC Steel Stamping LLC",
        "Hyundai Kia Rivian"
      ],
      [
        "Hyundai Transys Georgia Powertrain",
        "Hyundai Kia Rivian"
      ],
      [
        "Racemark International LLC",
        "Hyundai Kia Rivian"
      ]
    ]
  }
}
```

## Q41: For an international battery materials company seeking a Georgia location, which areas have existing chemical manufacturing infrastructure?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "location"
    ],
    "rows": [
      [
        "Archer Aviation Inc.",
        "Covington, Morgan County"
      ],
      [
        "Arising Industries Inc.",
        "Norcross, Gwinnett County"
      ]
    ]
  }
}
```

## Q42: Which Georgia areas have R&D facility types in the automotive sector, suggesting innovation infrastructure suitable for EV technology development centers?

Proposed primary eligibility: False. Approval: pending.

Source records are not independent verification of current operations or Georgia-only production. Recorded categories or keyword matches do not prove qualification, sole sourcing, readiness, demand, capacity, supplier completeness or vulnerability.

```json
{
  "answer": {
    "columns": [
      "company",
      "location",
      "primary_facility_type"
    ],
    "rows": [
      [
        "Racemark International LLC",
        "Gray, Jones County",
        "R&D"
      ]
    ]
  }
}
```
