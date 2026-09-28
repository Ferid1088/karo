"""The learning owl is decorative; destination names and other mascots stay intact."""
from pathlib import Path

import re

from .test_app import einrichten, kind_modus_aktivieren


def test_learning_pages_use_their_own_mascot(client, fake_llm, fake_cli, app_env):
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
        assert 'class="learning-entry" href="/lernen"' in subnav
        exam_tab = re.search(r'<a class="pruefung-tab".*?</a>', subnav).group()
        assert 'href="/klassenarbeit"' in exam_tab
        assert 'src="/static/pruefung-duo.jpg"' in exam_tab
        assert 'Klassenarbeit</a>' in exam_tab


def test_learning_mascot_asset_exists():
    from PIL import Image
    asset = Path(__file__).parents[1] / 'app/static/karo-owl-book.png'
    with Image.open(asset) as image:
        assert image.format == 'PNG'
        assert 'A' in image.getbands()
        assert image.getchannel('A').getextrema()[0] == 0
