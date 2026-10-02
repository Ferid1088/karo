"""The learning owl is decorative; destination names and other mascots stay intact."""
from pathlib import Path

import re

from .test_app import einrichten, kind_modus_aktivieren


def test_learning_pages_use_their_own_mascot(client, fake_llm, app_env):
    einrichten(client, fake_llm)
    app_env.config.update(klassenarbeit_kind=True)
    kind_modus_aktivieren(client)
    for path in ('/lernen', '/lernen/neu', '/lernen/material'):
        response = client.get(path)
        assert response.status_code == 200
        page = response.text
        nav = re.search(r'<a class="learning-entry" href="/lernen".*?</a>', page).group()
        assert '<span>Lernen</span>' in nav
        assert 'src="/static/karo-owl-book.png" alt="" aria-hidden="true"' in nav
        assert re.search(r'class="plans-entry"[^>]*>.*?karo-fox-wave.png', page)
        assert re.search(r'class="welten-entry zweite-gruppe"[^>]*>.*?welt-biene.svg', page)
        main = re.search(r'<main\b.*?</main>', page, re.S).group()
        assert 'src="/static/karo-owl-book.png"' in main
        assert 'karo-fox' not in main
        subnav = re.search(r'<nav class="sub-nav".*?</nav>', page, re.S).group()
        # "Meine Themen" ist ersetzt durch die drei Fächer.
        assert [m for m in re.findall(r'href="(/lernen/[a-z]+)"', subnav)] == [
            '/lernen/deutsch', '/lernen/mathematik', '/lernen/englisch']
        assert 'href="/klassenarbeit' not in subnav
        # Die Klassenarbeit ist ein eigener Hauptreiter rechts neben Lernen.
        mainnav = re.search(r'<nav class="simple-nav".*?</nav>', page, re.S).group()
        exam_tab = re.search(r'<a class="exam-entry".*?</a>', mainnav).group()
        assert 'href="/klassenarbeit"' in exam_tab
        assert 'src="/static/pruefung-duo.jpg"' in exam_tab
        assert '<span>Klassenarbeit</span>' in exam_tab
        assert mainnav.index('href="/lernen"') < mainnav.index('href="/klassenarbeit"') < mainnav.index('href="/lernstand"')
    # Unter dem Reiter Klassenarbeit steht der Prüfungskalender.
    page = client.get('/klassenarbeit').text
    mainnav = re.search(r'<nav class="simple-nav".*?</nav>', page, re.S).group()
    assert re.search(r'class="exam-entry" href="/klassenarbeit" aria-current=page', mainnav)
    subnav = re.search(r'<nav class="sub-nav".*?</nav>', page, re.S).group()
    assert 'aria-label="Klassenarbeit"' in subnav
    assert 'class="kalender-tab" href="/klassenarbeit/kalender"' in subnav
    assert 'class="exam-nav-banner"' in subnav
    # Kein zweites "Klassenarbeit" unter dem gleichnamigen Reiter.
    assert 'pruefung-tab' not in subnav and 'href="/klassenarbeit"' not in subnav
    assert 'href="/lernen"' not in subnav


def test_learning_mascot_asset_exists():
    from PIL import Image
    asset = Path(__file__).parents[1] / 'app/static/karo-owl-book.png'
    with Image.open(asset) as image:
        assert image.format == 'PNG'
        assert 'A' in image.getbands()
        assert image.getchannel('A').getextrema()[0] == 0


def test_heute_hat_ein_eigenes_tier(client, fake_llm, app_env):
    """"Heute" gehoert dem Igel. Fuchs, Eule und Biene sind anderswo zu Hause
    — zwei Bereiche mit demselben Tier waeren nicht auseinanderzuhalten."""
    einrichten(client, fake_llm)
    kind_modus_aktivieren(client)
    seite = client.get('/')
    assert seite.status_code == 200

    reiter = re.search(r'<a class="heute-entry" href="/".*?</a>', seite.text).group()
    assert 'src="/static/karo-igel.svg"' in reiter
    assert '<span>Heute</span>' in reiter

    inhalt = re.search(r'<main\b.*?</main>', seite.text, re.S).group()
    assert 'karo-igel' in inhalt
    assert 'karo-fox' not in inhalt
    assert 'karo-owl' not in inhalt

    for datei in ('karo-igel.svg', 'karo-igel-jubel.svg'):
        quelle = (Path(__file__).parents[1] / 'app/static' / datei).read_text(encoding='utf-8')
        assert quelle.lstrip().startswith('<svg')
        # Zwei SVG auf einer Seite duerfen sich nicht dieselbe Verlaufs-Kennung
        # teilen; sonst faerbt das zweite das erste um.
        assert 'id="igel-jubel-stachel"' in quelle or 'id="igel-stachel"' in quelle
    assert 'id="igel-stachel"' not in (Path(__file__).parents[1] /
                                       'app/static/karo-igel-jubel.svg').read_text(encoding='utf-8')
