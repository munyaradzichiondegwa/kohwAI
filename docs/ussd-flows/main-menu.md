# USSD Flow Map

```
*123# → MAIN MENU
├── 1. Zunde - Agriculture
│   ├── 1. Weather Forecast
│   ├── 2. Sick Crop → symptom → crop → [DIAGNOSIS + DISCLAIMER]
│   ├── 3. Sick Animal → symptom → animal → [DIAGNOSIS + DISCLAIMER]
│   ├── 4. Planting Guide
│   └── 5. Report Sighting
├── 2. Mvura - Water
│   ├── 1. Nearest Borehole
│   ├── 2. Report Borehole Status
│   └── 3. Water Saving Tips
├── 3. Simba - Solar Energy
│   ├── 1. 48h Solar Forecast
│   └── 2. Battery Calculator
├── 4. Musika - Marketplace
│   ├── 1. Browse Seeds/Produce
│   ├── 2. List My Produce
│   └── 3. Insurance Status
└── 0. Help / My Data
```

Rules:
- Max 4 menu levels from root
- Every screen ≤160 chars
- Every non-root screen has 0. Back + 9. Main Menu
- All disease output includes USSD disclaimer (not AI diagnosis)
