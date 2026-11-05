"""USSD copy that is plain text (no data). Every screen must be <= 160 characters; this is
enforced by tests (tests/test_ussd_screens.py) for every reachable screen."""

MAX_LEN = 160

MAIN_MENU = """CON KohwAI
1. Farming (Zunde)
2. Water (Mvura)
3. Solar (Simba)
4. Market (Musika)
5. My account
0. Help"""

ZUNDE_MENU = """CON Farming
1. Recent weather
2. Sick crop
3. Sick animal
4. Planting guide
5. Report pest
0. Back 9. Menu"""

MVURA_MENU = """CON Water
1. Boreholes near me
2. Report borehole
3. Water tips
0. Back 9. Menu"""

SIMBA_MENU = """CON Solar
1. Recent sunshine
2. Battery calculator
3. Energy tips
0. Back 9. Menu"""

MUSIKA_MENU = """CON Market
1. Browse
2. Sell produce
3. My insurance
0. Back 9. Menu"""

WATER_TIPS = """END Water tips
Water crops early or late in the day. Mulch to cut evaporation. Boil drinking water 1 min if unsure it is clean."""

ENERGY_TIPS = """END Energy tips
Charge phones in daylight. Switch off unused lights. Keep panels clean and shade-free."""

NOT_REGISTERED = "END Please register first: dial again, choose 5 (My account)."
INVALID = "END Invalid choice. Dial again to restart."
UNAVAILABLE = "END KohwAI USSD is temporarily unavailable. Please try later."
