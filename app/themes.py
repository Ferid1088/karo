"""Design-Themes: altersgerechte Oberflaechen-Welten fuer den Kinderbereich.

Drei Ebenen, getrennt gehalten:

  * FAMILIES  — wiederverwendbare Gestaltungsfamilien. Ihre Farbtoken stehen
    in `static/themes.css` (ein Block je Familie, nicht je Theme).
  * CATALOG   — zehn Themes je Klassenstufe. Jedes Theme gehoert zu genau
    einer Familie und traegt Interessen-Tags — niemals eine Kategorie nach
    Geschlecht oder Personengruppe.
  * ui_pref   — die gespeicherte Wahl des Kindes (Tabelle in karo.db).

Das System ist reine Personalisierung: es veraendert weder Lernlogik noch
Katalog, Bewertung, Planung oder Modellaufrufe.

Alle Parameter kommen aus `config.themes` (zentral, siehe Config.themes) —
hier steht keine einzige Schwelle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from . import config, db

DEFAULT_THEME_ID = "default"


# ---------------------------------------------------------------------------
# Einstellungen — gelesen aus config.themes, mit denselben Defaults wie dort.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ThemeSettings:
    enabled: bool = True
    min_grade: int = 1
    max_grade: int = 13
    #: So viele Klassen darunter/darueber darf das Kind entdecken.
    grade_range_offset: int = 2
    themes_per_grade: int = 10
    desktop_columns: int = 2
    personalization_enabled: bool = True
    #: Wieviele vergangene Wahlen die Interessen-Sortierung praegt.
    history_size: int = 12


_THEME_SETTING_KEYS = set(ThemeSettings.__dataclass_fields__)


def settings() -> ThemeSettings:
    """Theme-Parameter aus config.themes; unbekannte Schluessel werden
    ignoriert, fehlende fallen auf die Defaults zurueck."""
    roh = getattr(config.load_safe(), "themes", None)
    if not isinstance(roh, dict):
        roh = {}
    werte = {}
    for key, wert in roh.items():
        if key not in _THEME_SETTING_KEYS:
            continue
        try:
            werte[key] = wert if isinstance(wert, bool) else type(
                getattr(ThemeSettings, key))(wert)
        except (TypeError, ValueError):
            continue
    return ThemeSettings(**werte)


# ---------------------------------------------------------------------------
# Reifemaessige Baender: gleiche Familie, anderes Erscheinungsbild.
# Die Stufen bestimmen Groesse der Ecken und Zurueckhaltung der Farben —
# die Umsetzung liegt komplett in themes.css.
# ---------------------------------------------------------------------------

def band_for_grade(grade: int) -> int:
    if grade <= 3:
        return 1    # verspielt
    if grade <= 6:
        return 2    # bunt
    if grade <= 10:
        return 3    # dynamisch
    return 4        # ruhig


# ---------------------------------------------------------------------------
# Interessen-Tags — kontrolliertes Vokabular. Kein Geschlecht, keine
# Personengruppe; nur Dinge, fuer die sich jemand interessieren kann.
# ---------------------------------------------------------------------------

TAGS = frozenset({
    "Abenteuer", "Anime", "Architektur", "Bauen", "Bücher", "Coding",
    "Cozy", "Design", "Fahrzeuge", "Fantasy", "Film", "Fitness",
    "Fotografie", "Gaming", "Kawaii", "Kreativ", "Kunst", "Manga", "Mode",
    "Musik", "Natur", "Racing", "Reisen", "Science", "Sport", "Technik",
    "Tiere", "Weltall",
})

#: Gestaltungsfamilien. Jede definiert in themes.css genau einen Token-Block;
#: hier steht nur die Vorschau-Farbe der Kachel, falls ein Theme keine eigene
#: angibt.
FAMILIES = {
    "dino":        {"accent": ("#2e7d32", "#66bb6a")},
    "rescue":      {"accent": ("#d63d1e", "#ff8a50")},
    "bau":         {"accent": ("#b07c00", "#f4c02e")},
    "space":       {"accent": ("#3350cc", "#7aa2f7")},
    "blocks":      {"accent": ("#1273b8", "#5ac8f5")},
    "fantasy":     {"accent": ("#7a3fd1", "#c084fc")},
    "cozy":        {"accent": ("#c27034", "#f2b27e")},
    "ocean":       {"accent": ("#0c8a99", "#4fd8e0")},
    "animals":     {"accent": ("#2f8a3d", "#7ccf8a")},
    "horses":      {"accent": ("#946f2f", "#d9b878")},
    "racing":      {"accent": ("#c2183f", "#ff5c72")},
    "roboter":     {"accent": ("#2c5d9e", "#6fa8dc")},
    "fussball":    {"accent": ("#0f8a42", "#4cd07f")},
    "fashion":     {"accent": ("#c22a7e", "#f472b6")},
    "kawaii":      {"accent": ("#d64295", "#f9a8d4")},
    "alien":       {"accent": ("#0ca07a", "#4ee3b5")},
    "musik":       {"accent": ("#5d3bd6", "#a78bfa")},
    "voxel":       {"accent": ("#5c9e26", "#a3d95c")},
    "creature":    {"accent": ("#b36a1c", "#f2a950")},
    "kreativ":     {"accent": ("#d0502a", "#ff8a66")},
    "gaming":      {"accent": ("#6d5ae0", "#22d3ee")},
    "anime":       {"accent": ("#c01e55", "#fb7185")},
    "manga":       {"accent": ("#e02442", "#f4f4f8")},
    "technik":     {"accent": ("#0892b8", "#22d3ee")},
    "engineering": {"accent": ("#c2510a", "#f59e0b")},
    "buecher":     {"accent": ("#8a6420", "#d4a94e")},
    "reisen":      {"accent": ("#0e86b8", "#5ec8f2")},
    "foto":        {"accent": ("#3f4a6b", "#8b96b8")},
    "architektur": {"accent": ("#4d5a68", "#9aa8b8")},
    "interior":    {"accent": ("#96684a", "#d9b48f")},
    "film":        {"accent": ("#e05575", "#8b5cf6")},
    "fitness":     {"accent": ("#3e9e14", "#86e04e")},
    "abenteuer":   {"accent": ("#0f8a68", "#3fd0a4")},
}


def _t(tid: str, name: str, family: str, icon: str, tags: tuple,
       accent: tuple | None = None) -> dict:
    """Rohe Katalogzeile — Klasse, Reifeband und Sichtbarkeit werden beim
    Aufbau des Katalogs ergaenzt."""
    return {"id": tid, "name": name, "family": family, "icon": icon,
            "tags": tags, "accent": accent or FAMILIES[family]["accent"]}


#: Zehn Themes je Klasse — jede Zeile: id, name, familie, icon, tags.
#: Die Auswahl deckt bewusst verschiedene Interessen ab (Technik, Sport,
#: Kreatives, Tiere, Musik, ...), ohne nach Personengruppen zu sortieren.
_RAW = {
    1: [
        _t("dino_abenteuer", "Dino Adventure", "dino", "🦕", ("Abenteuer", "Tiere")),
        _t("feuerwehr_rettung", "Feuerwehr & Rettung", "rescue", "🚒", ("Fahrzeuge", "Abenteuer")),
        _t("baustelle", "Baustelle", "bau", "🚧", ("Bauen", "Fahrzeuge")),
        _t("space_adventure", "Space Adventure", "space", "🚀", ("Weltall", "Abenteuer")),
        _t("building_blocks", "Building Blocks", "blocks", "🧱", ("Bauen", "Kreativ")),
        _t("unicorn_world", "Unicorn World", "fantasy", "🦄", ("Fantasy", "Kawaii")),
        _t("doll_world", "Doll World", "cozy", "🧸", ("Cozy", "Kreativ")),
        _t("fairy_kingdom", "Fairy Kingdom", "fantasy", "🧚", ("Fantasy", "Abenteuer")),
        _t("cute_pets", "Cute Pets", "animals", "🐶", ("Tiere", "Kawaii")),
        _t("mermaid_world", "Mermaid World", "ocean", "🧜", ("Fantasy", "Natur")),
    ],
    2: [
        _t("racing_cars", "Racing Cars", "racing", "🏎️", ("Racing", "Fahrzeuge")),
        _t("pirate_adventure", "Pirate Adventure", "abenteuer", "🏴‍☠️", ("Abenteuer", "Fantasy")),
        _t("dragons", "Dragons", "fantasy", "🐉", ("Fantasy", "Abenteuer")),
        _t("robot_lab", "Robot Lab", "roboter", "🤖", ("Technik", "Bauen")),
        _t("football", "Football", "fussball", "⚽", ("Sport",)),
        _t("fashion_dreamhouse", "Fashion Dreamhouse", "fashion", "👗", ("Mode", "Design")),
        _t("horse_farm", "Horse Farm", "horses", "🐴", ("Tiere", "Natur")),
        _t("kawaii_candy", "Kawaii Candy", "kawaii", "🍬", ("Kawaii", "Cozy")),
        _t("magic_school", "Magic School", "fantasy", "🪄", ("Fantasy", "Abenteuer")),
        _t("dance_music", "Dance & Music", "musik", "💃", ("Musik", "Kreativ")),
    ],
    3: [
        _t("voxel_builder", "Voxel Builder", "voxel", "⛏️", ("Gaming", "Bauen")),
        _t("creature_quest", "Creature Quest", "creature", "🐾", ("Tiere", "Gaming")),
        _t("kart_racing", "Kart Racing", "racing", "🏁", ("Racing", "Gaming")),
        _t("football_champions", "Football Champions", "fussball", "🏆", ("Sport",)),
        _t("dinosaur_expedition", "Dinosaur Expedition", "dino", "🦖", ("Abenteuer", "Tiere")),
        _t("cozy_island", "Cozy Island", "cozy", "🏝️", ("Cozy", "Kreativ")),
        _t("creative_avatar_world", "Creative Avatar World", "kreativ", "🧑‍🎨", ("Kreativ", "Gaming")),
        _t("fashion_studio", "Fashion Studio", "fashion", "👗", ("Mode", "Design")),
        _t("kawaii_friends", "Kawaii Friends", "kawaii", "🐱", ("Kawaii", "Cozy")),
        _t("horse_academy", "Horse Academy", "horses", "🐎", ("Tiere", "Sport")),
    ],
    4: [
        _t("space_mission", "Space Mission", "space", "🌕", ("Weltall", "Science")),
        _t("ninja_adventure", "Ninja Adventure", "abenteuer", "🥷", ("Abenteuer", "Sport")),
        _t("hero_academy", "Hero Academy", "abenteuer", "🦸", ("Abenteuer", "Fantasy")),
        _t("robot_coding_lab", "Robot & Coding Lab", "roboter", "🤖", ("Coding", "Technik")),
        _t("street_football", "Street Football", "fussball", "⚽", ("Sport",)),
        _t("cute_alien_world", "Cute Alien World", "alien", "👽", ("Weltall", "Kawaii")),
        _t("kawaii_cafe", "Kawaii Café", "kawaii", "🧋", ("Kawaii", "Cozy")),
        _t("diy_studio", "DIY Studio", "kreativ", "🛠️", ("Kreativ", "Design")),
        _t("dance_crew", "Dance Crew", "musik", "🕺", ("Musik", "Sport")),
        _t("animal_rescue", "Animal Rescue", "animals", "🐾", ("Tiere", "Natur")),
    ],
    5: [
        _t("voxel_craft", "Voxel Craft", "voxel", "⛏️", ("Gaming", "Bauen")),
        _t("creature_league", "Creature League", "creature", "🦊", ("Tiere", "Gaming")),
        _t("formula_racing", "Formula Racing", "racing", "🏎️", ("Racing", "Sport")),
        _t("football_league", "Football League", "fussball", "⚽", ("Sport",)),
        _t("galactic_adventure", "Galactic Adventure", "space", "🌌", ("Weltall", "Abenteuer")),
        _t("cute_alien_friends", "Cute Alien Friends", "alien", "👾", ("Weltall", "Kawaii")),
        _t("kawaii_world", "Kawaii World", "kawaii", "🌸", ("Kawaii", "Cozy")),
        _t("creator_world", "Creator World", "kreativ", "🌍", ("Kreativ", "Gaming")),
        _t("fashion_creator", "Fashion Creator", "fashion", "🧵", ("Mode", "Kreativ")),
        _t("home_designer", "Home Designer", "interior", "🏡", ("Design", "Kreativ")),
    ],
    6: [
        _t("gaming_arena", "Gaming Arena", "gaming", "🎮", ("Gaming", "Technik")),
        _t("formula_racing_6", "Formula Racing", "racing", "🏁", ("Racing", "Sport")),
        _t("football_stars", "Football Stars", "fussball", "⭐", ("Sport",)),
        _t("anime_action", "Anime Action", "anime", "⚔️", ("Anime", "Abenteuer")),
        _t("scifi_galaxy", "Sci-Fi Galaxy", "space", "🛸", ("Weltall", "Science")),
        _t("anime_kawaii", "Anime & Kawaii", "kawaii", "🌸", ("Anime", "Kawaii")),
        _t("music_stage", "Music Stage", "musik", "🎤", ("Musik", "Kreativ")),
        _t("street_fashion", "Street Fashion", "fashion", "🧢", ("Mode", "Design")),
        _t("cozy_gaming", "Cozy Gaming", "cozy", "🛋️", ("Gaming", "Cozy")),
        _t("room_makeover", "Room Makeover", "interior", "🪴", ("Design", "Kreativ")),
    ],
    7: [
        _t("competitive_gaming", "Competitive Gaming", "gaming", "🏆", ("Gaming", "Sport")),
        _t("football_gaming", "Football Gaming", "fussball", "🎮", ("Sport", "Gaming")),
        _t("racing_paddock", "Racing Paddock", "racing", "🏎️", ("Racing", "Technik")),
        _t("shonen_adventure", "Shonen Adventure", "anime", "⚔️", ("Anime", "Abenteuer")),
        _t("coding_lab", "Coding Lab", "technik", "💻", ("Coding", "Technik")),
        _t("manga_studio", "Manga Studio", "manga", "✒️", ("Manga", "Kreativ")),
        _t("music_kpop", "Music & K-Pop", "musik", "🎧", ("Musik",)),
        _t("fashion_7", "Fashion", "fashion", "👟", ("Mode", "Design")),
        _t("creative_studio", "Creative Studio", "kreativ", "🎨", ("Kreativ", "Design")),
        _t("photography_travel", "Photography & Travel", "reisen", "📸", ("Fotografie", "Reisen")),
    ],
    8: [
        _t("esports", "Esports", "gaming", "🏆", ("Gaming", "Sport")),
        _t("motorsport", "Motorsport", "racing", "🏎️", ("Racing", "Technik")),
        _t("cars_engineering", "Cars & Engineering", "engineering", "🔧", ("Technik", "Fahrzeuge")),
        _t("ai_robotics", "AI & Robotics", "roboter", "🤖", ("Technik", "Science")),
        _t("cyber_future", "Cyber Future", "technik", "🌐", ("Technik", "Science")),
        _t("anime_manga", "Anime & Manga", "anime", "📖", ("Anime", "Manga")),
        _t("music_festival", "Music Festival", "musik", "🎪", ("Musik",)),
        _t("creative_beauty", "Creative Beauty", "fashion", "💄", ("Kreativ", "Mode")),
        _t("fashion_editorial", "Fashion Editorial", "fashion", "📸", ("Mode", "Fotografie")),
        _t("fantasy_books", "Fantasy Books", "buecher", "🐉", ("Bücher", "Fantasy")),
    ],
    9: [
        _t("ai_technology", "AI & Technology", "technik", "🤖", ("Technik", "Science")),
        _t("gaming_setup", "Gaming Setup", "gaming", "🖥️", ("Gaming", "Technik")),
        _t("formula_racing_9", "Formula Racing", "racing", "🏁", ("Racing", "Technik")),
        _t("sneakers_streetwear", "Sneakers & Streetwear", "fashion", "👟", ("Mode", "Design")),
        _t("fitness", "Fitness", "fitness", "💪", ("Sport", "Fitness")),
        _t("fashion_creator_9", "Fashion Creator", "fashion", "🧵", ("Mode", "Kreativ")),
        _t("music_9", "Music", "musik", "🎵", ("Musik",)),
        _t("travel", "Travel", "reisen", "🌍", ("Reisen", "Natur")),
        _t("photography", "Photography", "foto", "📷", ("Fotografie", "Kreativ")),
        _t("books_fantasy", "Books & Fantasy", "buecher", "📚", ("Bücher", "Fantasy")),
    ],
    10: [
        _t("coding_ai", "Coding & AI", "technik", "💻", ("Coding", "Science")),
        _t("motorsport_engineering", "Motorsport Engineering", "engineering", "🏎️", ("Racing", "Technik")),
        _t("football_analytics", "Football Analytics", "fussball", "📊", ("Sport", "Technik")),
        _t("gaming_minimal", "Gaming Minimal", "gaming", "🎮", ("Gaming", "Design")),
        _t("cars_engineering_10", "Cars & Engineering", "engineering", "🚗", ("Technik", "Fahrzeuge")),
        _t("architecture_design", "Architecture & Design", "architektur", "📐", ("Architektur", "Design")),
        _t("fashion_10", "Fashion", "fashion", "👗", ("Mode", "Design")),
        _t("music_festival_10", "Music Festival", "musik", "🎶", ("Musik",)),
        _t("book_world", "Book World", "buecher", "📚", ("Bücher", "Fantasy")),
        _t("travel_cities", "Travel & Cities", "reisen", "🏙️", ("Reisen", "Fotografie")),
    ],
    11: [
        _t("startup_ai", "Startup & AI", "technik", "🚀", ("Technik", "Coding")),
        _t("racing_engineering", "Racing Engineering", "engineering", "🏁", ("Racing", "Technik")),
        _t("esports_11", "Esports", "gaming", "🎮", ("Gaming", "Sport")),
        _t("urban_streetwear", "Urban Streetwear", "fashion", "🧢", ("Mode", "Design")),
        _t("cinema", "Cinema", "film", "🎬", ("Film", "Kreativ")),
        _t("literature", "Literature", "buecher", "📖", ("Bücher",)),
        _t("fashion_editorial_11", "Fashion Editorial", "fashion", "📸", ("Mode", "Design")),
        _t("music_concert", "Music & Concert", "musik", "🎻", ("Musik",)),
        _t("world_travel", "World Travel", "reisen", "🌏", ("Reisen", "Fotografie")),
        _t("interior_design", "Interior Design", "interior", "🛋️", ("Design", "Architektur")),
    ],
    12: [
        _t("future_technology", "Future Technology", "technik", "🔭", ("Technik", "Science")),
        _t("motorsport_data", "Motorsport Data", "engineering", "📊", ("Racing", "Technik")),
        _t("urban_photography", "Urban Photography", "foto", "🏙️", ("Fotografie", "Reisen")),
        _t("minimal_gaming", "Minimal Gaming", "gaming", "🎮", ("Gaming", "Design")),
        _t("cosmos_science", "Cosmos & Science", "space", "🔭", ("Weltall", "Science")),
        _t("art_design", "Art & Design", "kreativ", "🎨", ("Kunst", "Design")),
        _t("fashion_magazine", "Fashion Magazine", "fashion", "📰", ("Mode", "Design")),
        _t("cafe_study", "Café & Study", "cozy", "☕", ("Cozy", "Bücher")),
        _t("travel_journal", "Travel Journal", "reisen", "✈️", ("Reisen", "Fotografie")),
        _t("wellness_fitness", "Wellness & Fitness", "fitness", "🧘", ("Sport", "Natur")),
    ],
    13: [
        _t("ai_startup", "AI & Startup", "technik", "💡", ("Technik", "Coding")),
        _t("data_motorsport", "Data & Motorsport", "engineering", "📈", ("Racing", "Technik")),
        _t("architecture", "Architecture", "architektur", "🏛️", ("Architektur", "Design")),
        _t("cinema_13", "Cinema", "film", "🎞️", ("Film", "Kreativ")),
        _t("premium_gaming", "Premium Gaming", "gaming", "🎮", ("Gaming", "Design")),
        _t("creative_studio_13", "Creative Studio", "kreativ", "🖌️", ("Kreativ", "Design")),
        _t("fashion_editorial_13", "Fashion Editorial", "fashion", "👠", ("Mode", "Design")),
        _t("city_travel", "City Travel", "reisen", "🌆", ("Reisen", "Fotografie")),
        _t("literature_13", "Literature", "buecher", "📚", ("Bücher",)),
        _t("coffee_study", "Coffee & Study", "cozy", "☕", ("Cozy", "Bücher")),
    ],
}


def _build() -> tuple[dict, dict]:
    """Baut den vollstaendigen Katalog aus den Rohzeilen.

    Rückgabe: (grade -> [theme, ...], id -> theme). Jedes Theme gehoert
    primaer zu genau einer Klasse; die ±2-Sichtbarkeit rechnet
    `grade_range`, sie steht nicht in den Daten.
    """
    pro_grade: dict[int, list[dict]] = {}
    pro_id: dict[str, dict] = {}
    for grade, roh in _RAW.items():
        eintraege = []
        for zeile in roh:
            tags = list(zeile["tags"])
            unbekannt = set(tags) - TAGS
            if unbekannt:  # pragma: no cover - schuetzt den Katalog beim Pflegen
                raise ValueError(
                    f"{zeile['id']}: unbekannte Interessen-Tags {sorted(unbekannt)}")
            if zeile["family"] not in FAMILIES:  # pragma: no cover
                raise ValueError(f"{zeile['id']}: unbekannte Familie")
            eintrag = {
                "id": zeile["id"],
                "name": zeile["name"],
                "family": zeile["family"],
                "grades": [grade],
                "recommended_grades": [grade],
                "interest_tags": tags,
                "maturity_level": band_for_grade(grade),
                "visual": {
                    "variant": f"{zeile['family']}_b{band_for_grade(grade)}",
                    "icon": zeile["icon"],
                    "accent": list(zeile["accent"]),
                },
            }
            if eintrag["id"] in pro_id:  # pragma: no cover
                raise ValueError(f"doppelte Theme-ID {eintrag['id']}")
            eintraege.append(eintrag)
            pro_id[eintrag["id"]] = eintrag
        pro_grade[grade] = eintraege
    return pro_grade, pro_id


CATALOG, _BY_ID = _build()


def theme(tid: str) -> dict | None:
    return _BY_ID.get(tid)


def grade_range(child_grade: int) -> tuple[int, int]:
    """Die Klassen, deren Designs das Kind entdecken darf: eigene Klasse
    plus `grade_range_offset` Stufen in beide Richtungen, an den Rändern
    eingekürzt. Komplett aus `config.themes` gerechnet."""
    s = settings()
    untere = max(s.min_grade, child_grade - s.grade_range_offset)
    obere = min(s.max_grade, child_grade + s.grade_range_offset)
    return untere, obere


def visible_grades(child_grade: int) -> list[int]:
    lo, hi = grade_range(child_grade)
    return list(range(lo, hi + 1))


def _learner_grade() -> int:
    s = settings()
    try:
        klasse = int(getattr(config.load_safe(), "learner_grade", s.min_grade))
    except (TypeError, ValueError):
        klasse = s.min_grade
    return max(s.min_grade, min(s.max_grade, klasse))


# ---------------------------------------------------------------------------
# Personalisierung (Phase 1): regelbasierte Sortierung.
# Wer oft Welten mit aehnlichen Tags waehlt, bekommt solche zuerst gezeigt.
# Es zaehlen ausschliesslich Interessen-Tags vergangener Wahlen.
# ---------------------------------------------------------------------------

def _pref(key: str, default: str = "") -> str:
    row = db.q1("SELECT value FROM ui_pref WHERE key=?", key)
    return row["value"] if row else default


def _set_pref(key: str, value: str) -> None:
    with db.tx() as c:
        c.execute(
            "INSERT INTO ui_pref (key, value, updated_at) VALUES (?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, "
            "updated_at=excluded.updated_at",
            (key, value, db.now()))


def selected_id() -> str:
    return _pref("theme_id", DEFAULT_THEME_ID) or DEFAULT_THEME_ID


def _recent_ids() -> list[str]:
    try:
        ids = json.loads(_pref("theme_picks", "[]"))
    except json.JSONDecodeError:
        return []
    return [i for i in ids if isinstance(i, str)][: settings().history_size]


def _tag_counts() -> dict:
    zaehler: dict[str, int] = {}
    for tid in _recent_ids():
        t = _BY_ID.get(tid)
        if not t:
            continue
        for tag in t["interest_tags"]:
            zaehler[tag] = zaehler.get(tag, 0) + 1
    return zaehler


def _sorted(themen: list[dict]) -> list[dict]:
    s = settings()
    if not s.personalization_enabled:
        return list(themen)
    counts = _tag_counts()
    if not counts:
        return list(themen)

    def score(t: dict) -> int:
        return sum(counts.get(tag, 0) for tag in t["interest_tags"])

    return sorted(themen, key=score, reverse=True)


def themes_for_grade(grade: int, personalize: bool = True) -> list[dict]:
    eintraege = CATALOG.get(grade, [])
    return _sorted(eintraege) if personalize else list(eintraege)


# ---------------------------------------------------------------------------
# Auswahl — validiert gegen Katalog und Klassenrahmen.
# ---------------------------------------------------------------------------

def auswaehlen(theme_id: str) -> dict:
    """Speichert die Wahl des Kindes. Wirft ValueError bei allem, was nicht
    im erlaubten Klassenrahmen liegt — auch bei unbekannten IDs."""
    s = settings()
    if not s.enabled:
        raise ValueError("Designs sind gerade nicht verfügbar.")
    theme_id = (theme_id or "").strip()
    if theme_id == DEFAULT_THEME_ID:
        _merken(DEFAULT_THEME_ID)
        return {"id": DEFAULT_THEME_ID, "family": "", "band": 0,
                "name": "Karo-Standard"}
    t = _BY_ID.get(theme_id)
    if t is None:
        raise ValueError("Dieses Design gibt es nicht.")
    lo, hi = grade_range(_learner_grade())
    if not lo <= t["grades"][0] <= hi:
        raise ValueError("Dieses Design passt nicht zu deiner Klasse.")
    _merken(theme_id)
    return {"id": t["id"], "family": t["family"], "band": t["maturity_level"],
            "name": t["name"], "tags": t["interest_tags"]}


def _merken(theme_id: str) -> None:
    _set_pref("theme_id", theme_id)
    if theme_id == DEFAULT_THEME_ID:
        return
    picks = [theme_id] + [i for i in _recent_ids() if i != theme_id]
    _set_pref("theme_picks", json.dumps(picks[: settings().history_size],
                                        ensure_ascii=False))


# ---------------------------------------------------------------------------
# Kontext fuer das Template — Kopf-Picker auf jeder Kinderseite.
# ---------------------------------------------------------------------------

def oberflaeche(cfg) -> dict:
    """Liefert die Template-Werte: aktives Theme am <html>-Element plus den
    Picker-Inhalt (aktuelle Klasse zuerst, Nachbarklassen als Chips)."""
    s = settings()
    leer = {"theme_id": DEFAULT_THEME_ID, "theme_family": "",
            "theme_band": "", "theme_picker": None}
    if not s.enabled:
        return leer
    grade = _learner_grade()
    lo, hi = grade_range(grade)
    aktuell = _BY_ID.get(selected_id())
    picker = {
        "grade": grade,
        "min_grade": lo,
        "max_grade": hi,
        "per_grade": s.themes_per_grade,
        "columns": s.desktop_columns,
        "selected": selected_id(),
        "themes": themes_for_grade(grade),
        "grades": list(range(lo, hi + 1)),
        # Katalog aller sichtbaren Klassen fuer den Wechsel im Popover —
        # nur die Felder, die die Kachel braucht.
        "catalog": {str(g): _kachel_liste(g) for g in range(lo, hi + 1)},
    }
    return {
        "theme_id": aktuell["id"] if aktuell else DEFAULT_THEME_ID,
        "theme_family": aktuell["family"] if aktuell else "",
        "theme_band": aktuell["maturity_level"] if aktuell else "",
        "theme_picker": picker,
    }


def _kachel_liste(grade: int) -> list[dict]:
    return [{
        "id": t["id"],
        "name": t["name"],
        "icon": t["visual"]["icon"],
        "tags": t["interest_tags"][:2],
        "family": t["family"],
        "band": t["maturity_level"],
        "accent": t["visual"]["accent"],
    } for t in themes_for_grade(grade)]
