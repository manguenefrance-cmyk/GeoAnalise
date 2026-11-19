# Sensor profiles in API v1

`POST /v1/satellite/search` accepts `sensor: "sentinel-2" | "landsat-8-9"`. Omitting it retains Sentinel-2. The server selects Copernicus for an omitted Sentinel provider, or Planetary Computer for Landsat. The web interface starts on the public Earth Search Sentinel collection. Mismatched sensor/provider requests are rejected.

`GET /v1/indices?sensor=landsat-8-9` returns 19 supported indices and their native OLI formulas, bands and 30 m resolution. Omitting the query returns the existing 21-index Sentinel catalog. Scene responses and output provenance include `sensor`.

The versioned calculation engine retains its existing **internal equation keys** for API transform parameters (`bands`, `numerator`, `denominator`). Use the catalog's `native_bands` mapping to label controls. Index execution uses the index ID and resolves its bands on the server. For Landsat:

| Internal parameter key | OLI source band |
| --- | --- |
| B01 | SR_B1, coastal |
| B02 | SR_B2, blue |
| B03 | SR_B3, green |
| B04 | SR_B4, red |
| B08 | SR_B5, NIR |
| B11 | SR_B6, SWIR1 |
| B12 | SR_B7, SWIR2 |

There is no mapping for the red-edge or water-vapour bands. Unsupported keys are rejected before quota reservation. A Landsat transform requesting `B05` does **not** mean OLI band 5: use the semantic key `B08` shown above. Output `sources` records the actual native band and unsigned asset URL, calibration and native resolution. Model formulas and PCA/composite band labels use native band names.

Landsat QA_PIXEL always excludes fill (bit 0). Cloud masking additionally excludes bits 1–5. QA_RADSAT excludes saturation only in selected reflectance bands and terrain occlusion (bit 11). QA uses nearest-neighbour resampling; zero and water flags remain valid. Disabling cloud masking does not enable fill/saturated pixels. Signed URLs are refreshed in memory and are not stored in scenes or provenance.

Temporal comparisons across sensors are rejected; this implementation does not claim spectral harmonization. Equal algebra is insufficient to establish interchangeable observations.
