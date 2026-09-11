"""Throwaway: confirm whether GET /wissen actually works. Not part of the
suite — delete after checking."""
from .test_app import einrichten


def test_wissen_page_loads(client, fake_llm, fake_cli):
    einrichten(client, fake_llm)
    r = client.get('/wissen')
    print("STATUS", r.status_code)
    print(r.text[:2000])
