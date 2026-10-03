"""HTTP-Grundgerüst der Anbieter-Adapter.

Nur Adapter rufen das auf; die Fehler-Einordnung ist einheitlich:
401/403 → dauerhafter Zugangsfehler, 429 → Ratenbegrenzung,
5xx/Zeitüberschreitung → vorübergehend. Nie Header oder Bodies loggen.
"""

from __future__ import annotations

from .base import AIAuthError, AIConnectionError, AIError


def api_request(provider: str, method: str, base_url: str, path: str, *,
                headers: dict | None = None, payload: dict | None = None,
                timeout: float = 60.0) -> dict:
    import httpx

    try:
        with httpx.Client(base_url=base_url.rstrip("/"),
                          headers=headers or {}, timeout=timeout) as client:
            r = client.request(method, path, json=payload)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise AIConnectionError(
            f"{provider} API {method} {path}: {exc.__class__.__name__}",
            retryable=True) from exc
    if r.status_code < 400:
        try:
            return r.json()
        except ValueError as exc:
            raise AIError(f"{provider} API {method} {path}: ungültige Antwort",
                          retryable=False) from exc
    if r.status_code in (401, 403):
        raise AIAuthError(
            f"{provider} API {method} {path}: {r.status_code} — der "
            "Zugangsschlüssel wird abgelehnt.")
    if r.status_code == 429:
        try:
            ra = float(r.headers.get("retry-after", ""))
        except ValueError:
            ra = None
        raise AIConnectionError(
            f"{provider} API {method} {path}: 429 Rate-Limit",
            rate_limited=True, retryable=True, retry_after=ra)
    if r.status_code >= 500:
        raise AIConnectionError(
            f"{provider} API {method} {path}: {r.status_code} Serverfehler",
            retryable=True)
    raise AIError(f"{provider} API {method} {path}: {r.status_code}",
                  retryable=False)
