"""
Polsterei-Preiskonfiguration
Basierend auf ALLE_PREISE_ÜBERSICHT.txt
"""

# Schaumstoff-Preise (€/m²/cm mit 40% Aufschlag bereits eingerechnet)
FOAM_TYPES = {
    # PU-Schäume
    'RG 2560': {'name': 'RG 2560 (anthrazit, leicht)', 'price': 3.00},
    'RG 3028': {'name': 'RG 3028 (rosa, Rücken)', 'price': 2.65},
    'RG 3543': {'name': 'RG 3543 (grün, Allround)', 'price': 3.35},
    'RG 3550': {'name': 'RG 3550 (weiß, leicht fest)', 'price': 3.00},
    'RG 4040': {'name': 'RG 4040 (lichtblau, mittlerer Sitz)', 'price': 4.10},
    'RG 4050': {'name': 'RG 4050 (hellblau, mittelfest)', 'price': 4.10},
    'RG 4060': {'name': 'RG 4060 (weiß, stabil)', 'price': 3.45},
    'RG 5063': {'name': 'RG 5063 (rot, sehr guter Sitz)', 'price': 4.65},
    'RG 5078': {'name': 'RG 5078 (orange, hart)', 'price': 4.30},
    'RG 6070': {'name': 'RG 6070 (anthrazit, hochelastisch)', 'price': 5.95},
    'RG 8080': {'name': 'RG 8080 (anthrazit, super)', 'price': 8.25},
    # Kaltschäume
    'GR 2515': {'name': 'GR 2515 (azur, weich Rücken)', 'price': 3.45},
    'GR 3028': {'name': 'GR 3028 (grün, elastisch Rücken)', 'price': 4.10},
    'GR 3530': {'name': 'GR 3530 (lila, elastisch Rücken)', 'price': 3.85},
    'GR 4036': {'name': 'GR 4036 (grau, weicher Sitz)', 'price': 4.50},
    'GR 5553': {'name': 'GR 5553 (hellblau, elastisch)', 'price': 5.35},
    'GR 5535': {'name': 'GR 5535 (silber, Top-Matratze)', 'price': 5.35},
    'GR 5560': {'name': 'GR 5560 (lila, schwer elastisch) ⭐ STANDARD', 'price': 5.35},
    'GR 5580': {'name': 'GR 5580 (rost/gelb, extrem stabil)', 'price': 6.50},
    'C 5740': {'name': 'C 5740 (marmoriert, B1)', 'price': 8.47},
    'C 5760': {'name': 'C 5760 (weiß, B1)', 'price': 8.47},
    # Verbundschaum
    'VB 140': {'name': 'VB 140 (bunt, Verbund)', 'price': 7.45},
}

# Standard Schaumplattengröße
FOAM_PLATE_WIDTH = 130  # cm
FOAM_PLATE_LENGTH = 205  # cm

# Nahttypen und Zusatzkosten (€/m)
SEAM_TYPES = {
    'Nur Schaum': {'zusatz': 0.00, 'zugabe': 0},
    'Normal': {'zusatz': 0.00, 'zugabe': 1, 'standard': True},
    'Keder': {'zusatz': 60.00, 'zugabe': 1},
    'Biese': {'zusatz': 30.00, 'zugabe': 3},
    'Kappnaht': {'zusatz': 10.00, 'zugabe': 1},
    'Doppelnaht': {'zusatz': 40.00, 'zugabe': 1},
}

# Materialpreise
MATERIALS = {
    'stoff': {'price': 100.00, 'unit': '€/m²', 'width': 140},  # Rollenbreite 140cm
    'antirutsch': {'price': 15.00, 'unit': '€/m', 'width': 146},
    'reissverschluss': {'price': 1.00, 'unit': '€/m'},
}

# Arbeitszeit und Stundensatz
LABOR_RATE = 65.00  # €/h

# Fertigungszeit-Berechnung (Kissen)
CUSHION_BASE_TIME = 1.4286  # Stunden
CUSHION_AREA_FACTOR = 0.00029762  # Stunden pro cm²

# Nahttyp-Faktoren für Fertigungszeit
SEAM_TIME_FACTORS = {
    'Normal': 0.0,
    'Keder': 0.0,
    'Biese': -0.2,  # schneller
    'Kappnaht': -0.5,  # schneller
    'Doppelnaht': 0.1,  # langsamer
}

# Nähzeiten pro Meter (in Minuten)
SEAM_TIME_PER_METER = {
    'Normale Naht': 3,  # Min
    'Keder-Naht': 6,
    'Biese': 4.5,
    'Kappnaht': 2.5,
    'Doppelnaht': 7,
    'Reißverschluss': 8,
}

# Schaum-Zuschnitt Arbeitszeit (Banken)
CUTTING_TIMES = {
    'Gerade': 2,  # Min
    'Schräg': 4,
    'Kontur': 8,
}

GLUING_TIMES = {
    'Kleben': 3,  # Min
    'Aushärten': 5,
}

# Kissen-Varianten
CUSHION_VARIANTS = {
    'Standard': 'Ober + Unterseite + 4 Seitenstreifen',
    'Oben+Seiten Stoff, unten Antirutsch': 'Oberseite + 4 Seiten Stoff, unten Antirutsch',
    'Ecken abgenäht + Antirutsch': 'Oberseite mit Ecken-Ausschnitt + Antirutsch',
    'Ecken abgenäht Stoff': 'Ober + Unterseite mit Ecken-Ausschnitt',
}


def calculate_cushion_time(area_cm2, seam_type='Normal'):
    """
    Berechnet Fertigungszeit für Kissen
    area_cm2: Fläche in cm²
    seam_type: Art der Naht

    Formel: Grundzeit + (Fläche × Faktor) + Nahttyp-Faktor
    """
    seam_factor = SEAM_TIME_FACTORS.get(seam_type, 0.0)
    time = CUSHION_BASE_TIME + (area_cm2 * CUSHION_AREA_FACTOR) + seam_factor
    return round(time, 2)


def calculate_foam_cost(foam_type, area_m2, thickness_cm):
    """
    Berechnet Schaumstoff-Kosten
    foam_type: Schaumstoff-Typ (z.B. 'GR 5560')
    area_m2: Fläche in m²
    thickness_cm: Dicke in cm
    """
    if foam_type not in FOAM_TYPES:
        return 0

    price_per_m2_cm = FOAM_TYPES[foam_type]['price']
    cost = area_m2 * thickness_cm * price_per_m2_cm
    return round(cost, 2)


def calculate_seam_cost(seam_type, perimeter_m):
    """
    Berechnet Naht-Zusatzkosten
    seam_type: Art der Naht
    perimeter_m: Umfang in Metern
    """
    if seam_type not in SEAM_TYPES:
        return 0

    zusatz = SEAM_TYPES[seam_type]['zusatz']
    cost = perimeter_m * zusatz
    return round(cost, 2)


def calculate_full_cushion_price(
    width_cm, height_cm, thickness_cm,
    foam_type='GR 5560', seam_type='Normal',
    fabric_price=100.0, has_antirutsch=False
):
    """
    Berechnet Gesamtpreis für ein Kissen

    Args:
        width_cm: Breite in cm
        height_cm: Höhe in cm
        thickness_cm: Dicke in cm
        foam_type: Schaumstoff-Typ
        seam_type: Nahttyp
        fabric_price: Stoff-Preis in €/m²
        has_antirutsch: Mit Antirutsch?

    Returns:
        dict mit Kosten-Übersicht
    """
    area_cm2 = width_cm * height_cm
    area_m2 = area_cm2 / 10000
    perimeter_cm = 2 * (width_cm + height_cm)
    perimeter_m = perimeter_cm / 100

    # Materialkosten
    foam_cost = calculate_foam_cost(foam_type, area_m2, thickness_cm)
    fabric_cost = area_m2 * fabric_price
    seam_cost = calculate_seam_cost(seam_type, perimeter_m)
    antirutsch_cost = (perimeter_m * MATERIALS['antirutsch']['price']) if has_antirutsch else 0
    zipper_cost = 0.60  # Durchschnittlich

    total_material = foam_cost + fabric_cost + seam_cost + antirutsch_cost + zipper_cost

    # Arbeitskosten
    fertig_time = calculate_cushion_time(area_cm2, seam_type)
    labor_cost = fertig_time * LABOR_RATE

    # Gesamtpreis
    total_cost = total_material + labor_cost

    return {
        'foam_cost': foam_cost,
        'fabric_cost': fabric_cost,
        'seam_cost': seam_cost,
        'antirutsch_cost': antirutsch_cost,
        'zipper_cost': zipper_cost,
        'total_material': total_material,
        'fertig_time': fertig_time,
        'labor_cost': labor_cost,
        'total_cost': total_cost,
        'breakdown': {
            'Schaumstoff': foam_cost,
            'Stoff': fabric_cost,
            'Nahttyp': seam_cost,
            'Antirutsch': antirutsch_cost,
            'Reißverschluss': zipper_cost,
            'Arbeitskosten': labor_cost,
        }
    }
