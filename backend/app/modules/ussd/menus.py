"""
USSD Menu Definitions for KohwAI
"""

MAIN_MENU = """CON Welcome to KohwAI *123#
1. Zunde - Agriculture
2. Mvura - Water
3. Simba - Energy
4. Musika - Marketplace
0. Help / My Data
99. Change Language"""

_MENUS = {

    "help": """CON KohwAI Help
1. Call Agritex: 0800-AGRITEX
2. Request my data
3. Report a problem
0. Back""",

    "planting_guide": """END Planting Guide - Chipinge
Maize: Plant Nov 15 - Dec 10
Sorghum: Plant Oct 25 - Nov 20
Recommended: Maize SC403
Source: Agritex / SARCOF 2024""",

}


def get_menu(key: str) -> str:
    return _MENUS.get(
        key,
        "END Menu not found. Dial *123# to restart."
    )