"""
USSD Session Handler for KohwAI *123#
Menu depth: max 4 levels. Each screen max 160 chars.
Every non-root menu: 0=Back, 9=Main Menu.
"""

from fastapi.responses import PlainTextResponse

from app.modules.ussd.menus import MAIN_MENU, get_menu
from app.modules.ussd.rules_engine import RulesEngine

rules = RulesEngine()


class USSDHandler:

    async def handle(
        self,
        session_id: str,
        phone: str,
        text: str,
        service_code: str
    ) -> PlainTextResponse:

        # USSD gateway sends cumulative input separated by *
        parts = text.split("*") if text else []
        depth = len([p for p in parts if p])

        try:
            response = await self._route(phone, parts, depth)

        except Exception:
            response = (
                "END An error occurred. "
                "Please try again later. Dial *123#"
            )

        return PlainTextResponse(
            content=response,
            media_type="text/plain"
        )

    # -------------------------------------------------------------------------
    # ROUTER
    # -------------------------------------------------------------------------

    async def _route(
        self,
        phone: str,
        parts: list,
        depth: int
    ) -> str:

        if depth == 0:
            return MAIN_MENU

        top = parts[0]

        # ── Module 1: Zunde ────────────────────────────────────────────────
        if top == "1":
            return await self._zunde(phone, parts[1:])

        # ── Module 2: Mvura ────────────────────────────────────────────────
        elif top == "2":
            return await self._mvura(phone, parts[1:])

        # ── Module 3: Simba ────────────────────────────────────────────────
        elif top == "3":
            return await self._simba(phone, parts[1:])

        # ── Module 4: Musika ───────────────────────────────────────────────
        elif top == "4":
            return await self._musika(phone, parts[1:])

        # ── Help / DSAR ────────────────────────────────────────────────────
        elif top == "0":
            return get_menu("help")

        return "END Invalid option. Dial *123# to restart."

    # -------------------------------------------------------------------------
    # ZUNDE MODULE
    # -------------------------------------------------------------------------

    async def _zunde(self, phone: str, sub: list) -> str:

        if not sub:
            return """CON Zunde - Agriculture
1. Weather Forecast
2. Sick Crop
3. Sick Animal
4. Planting Guide
5. Report Sighting
0. Back  9. Main Menu"""

        sel = sub[0]

        if sel == "1":
            return await self._weather(phone, sub[1:])

        if sel == "2":
            return await self._crop_triage(phone, sub[1:])

        if sel == "3":
            return await self._livestock_triage(phone, sub[1:])

        if sel == "4":
            return get_menu("planting_guide")

        if sel == "9":
            return MAIN_MENU

        return "END Invalid option."

    # -------------------------------------------------------------------------
    # WEATHER
    # -------------------------------------------------------------------------

    async def _weather(self, phone: str, sub: list) -> str:

        # TODO:
        # Fetch from satellite/weather cache for farmer's district

        return """CON 7-Day Forecast - Chipinge
Mon: 28C, Light Rain
Tue: 31C, Sunny
Wed: 26C, Cloudy
Updated: 2h ago
0. Back  9. Main Menu"""

    # -------------------------------------------------------------------------
    # CROP TRIAGE
    # -------------------------------------------------------------------------

    async def _crop_triage(self, phone: str, sub: list) -> str:

        if not sub:
            return """CON Sick Crop - Symptoms
1. Yellow/brown leaves
2. Wilting/drooping
3. Holes in leaves
4. White powder/spots
5. Stunted growth
0. Back"""

        symptom = sub[0]

        if len(sub) < 2:
            return """CON Which crop?
1. Maize
2. Sorghum
3. Cassava
4. Groundnuts
5. Other
0. Back"""

        crop = sub[1]

        result = rules.diagnose_crop(
            symptom=symptom,
            crop=crop
        )

        return f"""END Likely: {result['disease1']} or {result['disease2']}
Action: {result['action']}
Agritex: 0800-AGRITEX (free)

NOTE:
This is a symptom guide,
not an AI diagnosis."""

    # -------------------------------------------------------------------------
    # LIVESTOCK TRIAGE
    # -------------------------------------------------------------------------

    async def _livestock_triage(self, phone: str, sub: list) -> str:

        if not sub:
            return """CON Sick Animal - Symptoms
1. Skin sores/lumps
2. Coughing/breathing
3. Limping/swelling
4. Loss of appetite
5. Sudden death
0. Back"""

        symptom = sub[0]

        if len(sub) < 2:
            return """CON Animal species?
1. Cattle
2. Goats
3. Sheep
4. Poultry
5. Other
0. Back"""

        animal = sub[1]

        result = rules.diagnose_livestock(
            symptom=symptom,
            animal=animal
        )

        return f"""END Likely: {result['disease']}
Action: {result['action']}
Vet Services: 0800-VET (free)

NOTE:
This is a symptom guide.
Consult an Agritex officer."""

    # -------------------------------------------------------------------------
    # MVURA MODULE
    # -------------------------------------------------------------------------

    async def _mvura(self, phone: str, sub: list) -> str:

        if not sub:
            return """CON Mvura - Water Security
1. Nearest Borehole
2. Report Borehole Status
3. Water Saving Tips
0. Back  9. Main Menu"""

        sel = sub[0]

        if sel == "1":

            # TODO:
            # Query PostGIS for nearest borehole
            # based on farmer's district

            return """END Nearest Working Borehole
Masvingo Village Well
5.2km - Status: Working
Last verified: 2 days ago"""

        if sel == "9":
            return MAIN_MENU

        return "END Coming soon."

    # -------------------------------------------------------------------------
    # SIMBA MODULE
    # -------------------------------------------------------------------------

    async def _simba(self, phone: str, sub: list) -> str:

        if not sub:
            return """CON Simba - Solar Energy
1. 48h Solar Forecast
2. Battery Calculator
3. Energy Saving Tips
0. Back  9. Main Menu"""

        if sub[0] == "1":
            return """END Solar Forecast - Tomorrow
Expected: 6.2 kWh/m2
Battery outlook: 78% by 6pm
Updated: 1h ago"""

        if sub[0] == "9":
            return MAIN_MENU

        return "END Coming soon."

    # -------------------------------------------------------------------------
    # MUSIKA MODULE
    # -------------------------------------------------------------------------

    async def _musika(self, phone: str, sub: list) -> str:

        if not sub:
            return """CON Musika - Marketplace
1. Browse Seeds/Produce
2. List My Produce
3. Insurance Status
0. Back  9. Main Menu"""

        if sub[0] == "3":
            return """END Insurance Status
Drought Index: 42/100
Status: Not triggered
Threshold: 70
Your payout: USD 15.00"""

        if sub[0] == "9":
            return MAIN_MENU

        return "END Coming soon."