"""Curated, deterministic content for "Meine Welt".

No model call and no live web search happens here. Public editorial content is
kept outside the private world database so personal data and product content do
not mix.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

AGE_BANDS = ("8-9", "10-11", "12-13", "14-15")


@dataclass(frozen=True)
class Discovery:
    id: str
    category: str
    title: str
    teaser: str
    simple: tuple[str, ...]
    advanced: tuple[str, ...]
    think: str
    source_label: str
    source_url: str

    def paragraphs(self, age_band: str) -> tuple[str, ...]:
        return self.simple if age_band in ("8-9", "10-11") else self.advanced


@dataclass(frozen=True)
class Reflection:
    id: str
    category: str
    question: str


DISCOVERIES = (
    Discovery(
        "body-hiccup", "Körper & Gehirn", "Warum haben wir Schluckauf?",
        "Ein kleiner Reflex, bei dem dein Zwerchfell plötzlich zuckt.",
        (
            "Unter deinen Lungen liegt ein großer Atemmuskel: das Zwerchfell. Beim Schluckauf zieht er sich plötzlich und ungewollt zusammen.",
            "Kurz danach schließt sich die Öffnung zwischen den Stimmbändern. Dabei entsteht das typische „Hicks“. Häufig verschwindet Schluckauf nach kurzer Zeit von selbst.",
        ),
        (
            "Das Zwerchfell ist der wichtigste Atemmuskel. Beim Schluckauf kommt es zu einer unwillkürlichen, schnellen Kontraktion dieses Muskels.",
            "Fast gleichzeitig schließt sich die Stimmritze. Der Luftstrom wird abrupt unterbrochen – dadurch entsteht das typische Geräusch. Meist ist Schluckauf harmlos und endet von selbst.",
        ),
        "Warum kann sehr schnelles Essen oder Trinken Schluckauf begünstigen?",
        "MedlinePlus – Hiccups", "https://medlineplus.gov/hiccups.html",
    ),
    Discovery(
        "nature-blue-sky", "Natur", "Warum ist der Himmel blau?",
        "Sonnenlicht besteht aus vielen Farben – die Luft verteilt sie unterschiedlich.",
        (
            "Sonnenlicht sieht weiß aus, enthält aber viele Farben. Wenn es durch die Luft reist, wird blaues Licht besonders stark in viele Richtungen verteilt.",
            "Darum erreicht uns tagsüber aus vielen Richtungen blaues Licht und der Himmel wirkt blau. Bei Sonnenuntergang nimmt das Licht einen längeren Weg durch die Luft.",
        ),
        (
            "Moleküle in der Atmosphäre streuen kurzwelliges sichtbares Licht stärker als langwelliges. Dieser Effekt heißt Rayleigh-Streuung.",
            "Blau wird deshalb stärker über den Himmel verteilt. Bei tief stehender Sonne ist der Weg durch die Atmosphäre länger; mehr Blau wird aus der direkten Sichtlinie gestreut, sodass Rot und Orange stärker hervortreten.",
        ),
        "Warum sieht ein Sonnenuntergang oft orange oder rot aus?",
        "NASA Space Place – Blue Sky", "https://spaceplace.nasa.gov/blue-sky/en/",
    ),
    Discovery(
        "nature-autumn-leaves", "Natur", "Warum werden Blätter im Herbst bunt?",
        "Wenn das Grün verschwindet, werden andere Farben im Blatt sichtbar.",
        (
            "Im Sommer macht Chlorophyll viele Blätter grün. Es hilft Pflanzen dabei, Licht für ihr Wachstum zu nutzen.",
            "Wenn die Tage kürzer werden, baut der Baum Chlorophyll ab. Dann werden gelbe und orange Farbstoffe sichtbar, die vorher vom Grün überdeckt waren.",
        ),
        (
            "Chlorophyll absorbiert Licht für die Photosynthese und dominiert im Sommer die Blattfarbe. Im Herbst wird es bei kürzeren Tagen und sinkenden Temperaturen schrittweise abgebaut.",
            "Dadurch treten andere Pigmente hervor, besonders Carotinoide. Bei manchen Arten entstehen zusätzlich rote Anthocyane. Welche Farbe erscheint, hängt deshalb auch von Pflanzenart und Bedingungen ab.",
        ),
        "Warum werden nicht alle Baumarten im Herbst gleichfarbig?",
        "US Forest Service – Fall Colors", "https://www.fs.usda.gov/visit/fall-colors/science-of-fall-colors",
    ),
    Discovery(
        "space-twinkling-stars", "Weltall", "Warum funkeln Sterne?",
        "Das Sternenlicht muss durch unsere unruhige Atmosphäre.",
        (
            "Sterne senden ihr Licht sehr weit durch den Weltraum. Kurz bevor es unsere Augen erreicht, muss es durch die Luftschichten der Erde.",
            "Diese Luft bewegt sich und hat unterschiedlich warme Bereiche. Dadurch wird das Licht ständig ein kleines bisschen abgelenkt. Für uns sieht es so aus, als würde der Stern funkeln.",
        ),
        (
            "Von der Erde aus erscheinen Sterne fast punktförmig. Turbulenzen und Temperaturunterschiede in der Atmosphäre verändern den Brechungsindex entlang des Lichtwegs.",
            "Das Sternenbild wird dadurch in sehr kurzer Zeit leicht verschoben und heller oder dunkler. Planeten wirken meist ruhiger, weil ihre sichtbare Scheibe größer ist und sich viele dieser Schwankungen teilweise ausmitteln.",
        ),
        "Warum funkeln Planeten meistens weniger stark als Sterne?",
        "NASA – Why do stars twinkle?", "https://science.nasa.gov/universe/stars/",
    ),
    Discovery(
        "animals-bee-dance", "Tiere", "Wie zeigen Bienen den Weg zu Futter?",
        "Honigbienen können anderen Bienen Richtung und Entfernung mitteilen.",
        (
            "Eine Honigbiene, die eine gute Futterstelle gefunden hat, kann im Stock einen besonderen Tanz aufführen.",
            "Bei diesem sogenannten Schwänzeltanz verraten Richtung und Dauer der Bewegung anderen Bienen ungefähr, wo sich das Futter befindet.",
        ),
        (
            "Beim Schwänzeltanz codiert die Biene Informationen über eine Futterquelle. Der Winkel des Schwänzellaufs steht in Beziehung zur Richtung relativ zur Sonne.",
            "Die Dauer des Schwänzellaufs liefert Information über die Entfernung. Andere Arbeiterinnen können diese Signale nutzen und anschließend selbst zur Futterquelle fliegen.",
        ),
        "Welche Informationen muss eine Biene kennen, damit die Richtung auch Stunden später noch stimmt?",
        "Nobel Prize – Karl von Frisch", "https://www.nobelprize.org/prizes/medicine/1973/frisch/facts/",
    ),
    Discovery(
        "body-fingerprints", "Körper & Gehirn", "Warum sind Fingerabdrücke verschieden?",
        "Die feinen Hautleisten entstehen schon vor der Geburt.",
        (
            "Auf deinen Fingerspitzen verlaufen winzige Hautleisten. Ihr Muster entsteht, während ein Baby noch im Bauch wächst.",
            "Gene spielen dabei eine Rolle, aber auch viele kleine Bedingungen während der Entwicklung. Deshalb haben sogar eineiige Zwillinge nicht genau dieselben Fingerabdrücke.",
        ),
        (
            "Reibungsleisten an Fingern und Handflächen entwickeln sich vor der Geburt. Genetische Faktoren beeinflussen die Grundform, gleichzeitig wirken lokale Wachstumsbedingungen auf die feinen Details.",
            "Deshalb sind die resultierenden Muster hochgradig individuell. Auch eineiige Zwillinge teilen zwar sehr ähnliche Gene, aber nicht dieselben feinen Leistenmerkmale.",
        ),
        "Warum sehen die Fingerabdrücke eineiiger Zwillinge ähnlich aus, sind aber nicht identisch?",
        "NIH / MedlinePlus Genetics", "https://medlineplus.gov/genetics/",
    ),
    Discovery(
        "tech-gps", "Technik", "Woher weiß dein Handy, wo du bist?",
        "GPS-Satelliten senden Zeitinformationen – dein Gerät berechnet daraus Entfernungen.",
        (
            "Viele Satelliten senden ständig Signale mit sehr genauer Zeit. Dein Handy kann messen, wie lange mehrere dieser Signale bis zu ihm gebraucht haben.",
            "Aus den unterschiedlichen Entfernungen kann es seine Position berechnen. Dafür braucht es Signale von mehreren Satelliten.",
        ),
        (
            "GPS-Satelliten senden präzise Zeit- und Bahndaten. Ein Empfänger vergleicht die Ankunftszeiten mehrerer Signale und leitet daraus Laufzeiten und damit sogenannte Pseudodistanzen ab.",
            "Mit Signalen von mindestens vier Satelliten kann der Empfänger neben seiner dreidimensionalen Position auch die Abweichung seiner eigenen Uhr bestimmen.",
        ),
        "Warum reicht für eine genaue GPS-Position nicht nur ein einziger Satellit?",
        "GPS.gov – How GPS Works", "https://www.gps.gov/systems/gps/",
    ),
)

REFLECTIONS = (
    Reflection("r-better-year", "Zurückschauen", "Was kannst du heute besser als vor einem Jahr?"),
    Reflection("r-proud-week", "Ich", "Worauf warst du diese Woche ein bisschen stolz?"),
    Reflection("r-helped", "Andere", "Wann hat dir jemand zuletzt geholfen – und wie hat sich das angefühlt?"),
    Reflection("r-school-room", "Vorstellen", "Wenn deine Schule einen neuen Raum bekommen dürfte: Wofür wäre er?"),
    Reflection("r-sound-happy", "Ich", "Welches Geräusch macht dich sofort ein bisschen glücklicher?"),
    Reflection("r-courage", "Mut", "Was hast du einmal gemacht, obwohl du vorher unsicher warst?"),
    Reflection("r-keep-month", "Zurückschauen", "Welchen Moment aus diesem Monat möchtest du nicht vergessen?"),
    Reflection("r-friend", "Freundschaft", "Was macht für dich einen guten Freund oder eine gute Freundin aus?"),
    Reflection("r-change", "Entscheiden", "Welche kleine Sache würdest du an deinem Alltag ändern, wenn du könntest?"),
    Reflection("r-learn", "Ich", "Welche Sache würdest du gern können, ohne sie erst üben zu müssen?"),
    Reflection("r-kind", "Andere", "Was war eine kleine freundliche Sache, die du heute gesehen hast?"),
    Reflection("r-future", "Zukunft", "Worauf freust du dich in den nächsten vier Wochen?"),
)

WEEKDAY_CATEGORIES = {
    0: "Körper & Gehirn",
    1: "Natur",
    2: "Technik",
    3: "Körper & Gehirn",
    4: "Weltall",
    5: "Tiere",
    6: "Natur",
}


def daily_discovery(age_band: str, on_date: date) -> Discovery:
    if age_band not in AGE_BANDS:
        age_band = "10-11"
    category = WEEKDAY_CATEGORIES[on_date.weekday()]
    candidates = [item for item in DISCOVERIES if item.category == category] or list(DISCOVERIES)
    return candidates[on_date.toordinal() % len(candidates)]


def daily_reflection(age_band: str, on_date: date) -> Reflection:
    # Age band is part of the public API so future editorial sets can vary by age.
    if age_band not in AGE_BANDS:
        age_band = "10-11"
    return REFLECTIONS[on_date.toordinal() % len(REFLECTIONS)]


def by_id(article_id: str) -> Discovery | None:
    return next((item for item in DISCOVERIES if item.id == article_id), None)
