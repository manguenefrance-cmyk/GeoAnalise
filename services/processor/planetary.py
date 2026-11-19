"""Short-lived public dataset SAS tokens; never persist or log signed asset URLs."""

from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

_tokens = {}
HOST = "landsateuwest.blob.core.windows.net"


def sign_landsat_href(href):
    url = urlparse(href)
    if (
        url.scheme != "https"
        or url.hostname != HOST
        or url.port not in (None, 443)
        or url.username
        or url.password
        or not url.path.startswith("/landsat-c2/")
    ):
        raise ValueError("UNAPPROVED_LANDSAT_ASSET")
    token, expiry = _tokens.get(HOST, (None, 0))
    if expiry < datetime.now(timezone.utc).timestamp() + 120:
        try:
            response = httpx.get(
                "https://planetarycomputer.microsoft.com/api/sas/v1/token/landsateuwest/landsat-c2",
                timeout=httpx.Timeout(25, connect=10),
                follow_redirects=False,
            )
            response.raise_for_status()
            payload = response.json()
            token = payload["token"]
            expiry = datetime.fromisoformat(payload["msft:expiry"].replace("Z", "+00:00")).timestamp()
            if (
                not isinstance(token, str)
                or not token
                or expiry <= datetime.now(timezone.utc).timestamp() + 120
            ):
                raise ValueError("EXPIRED_TOKEN")
            _tokens[HOST] = token, expiry
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise ValueError("LANDSAT_SIGNING_UNAVAILABLE") from exc
    return url._replace(query=token, fragment="").geturl()
