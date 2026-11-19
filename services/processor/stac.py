import time
from functools import lru_cache

import httpx

from services.api.config import settings


class ProviderError(ValueError):
    pass


@lru_cache(maxsize=64)
def search_cached(geometry_json, start, end, cloud, limit, cache_epoch, provider="copernicus"):
    import json

    providers = {
        "copernicus": (settings.stac_url, settings.stac_collection),
        "earthsearch_c1": ("https://earth-search.aws.element84.com/v1", "sentinel-2-c1-l2a"),
        "planetary_computer": ("https://planetarycomputer.microsoft.com/api/stac/v1", "landsat-c2-l2"),
    }
    if provider not in providers:
        raise ProviderError("INVALID_PROVIDER")
    endpoint, collection = providers[provider]
    body = {
        "collections": [collection],
        "intersects": json.loads(geometry_json),
        "datetime": f"{start}T00:00:00Z/{end}T23:59:59Z",
        "limit": min(limit * 2, 100),
    }
    if provider == "planetary_computer":
        body["query"] = {"platform": {"in": ["landsat-8", "landsat-9"]}}
    try:
        with httpx.Client(timeout=httpx.Timeout(25, connect=10), follow_redirects=False) as client:
            for attempt in range(3):
                response = client.post(endpoint.rstrip("/") + "/search", json=body)
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(min(float(response.headers.get("retry-after", 2**attempt)), 5))
                    continue
                response.raise_for_status()
                payload = response.json()
                features = payload.get("features", [])
                # Scene-level metadata filtering; AOI cloud fraction is computed after pixel masking.
                features = [
                    f for f in features if float(f.get("properties", {}).get("eo:cloud_cover", 100)) <= cloud
                ]
                if provider == "planetary_computer":
                    features = [
                        f
                        for f in features
                        if f.get("properties", {}).get("platform") in ("landsat-8", "landsat-9")
                    ]
                return features[:limit], bool(
                    payload.get("links") and any(link.get("rel") == "next" for link in payload["links"])
                )
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError("STAC_PROVIDER_UNAVAILABLE") from exc
    raise ProviderError("STAC_PROVIDER_UNAVAILABLE")
