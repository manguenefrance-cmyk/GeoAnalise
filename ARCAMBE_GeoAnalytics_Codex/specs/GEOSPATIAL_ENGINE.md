# SCIENTIFIC PROCESSING SPECIFICATION — v1.0

## Source distinction
The user's 258-page Canada Centre for Remote Sensing *Fundamentals of Remote Sensing* (chapter 4.6, printed pp. 158–160) explicitly mentions NDVI and describes band ratios, image subtraction and principal component analysis. It does not list EVI/SAVI/NDWI/NDBI or the other modern index formulas. The full registry in `contracts/spectral_indices.yaml` is an **additional requirement** based on standard remote-sensing methods and must be implemented and tested, not incorrectly attributed to the book.

## Satellite data adapter
- STAC provider: configurable endpoint default `https://stac.dataspace.copernicus.eu/v1`; collection `sentinel-2-l2a`; metadata STAC search by intersects AOI and datetime; cloud cover filter where available.
- Probe actual collection / asset key naming from provider; do NOT assume uniform `B04` property key across all STAC backends. Provide a band resolver using `eo:bands`, `raster:bands`, asset names, links and explicit verified provider adapters. Fail loudly if band ambiguous. Many raw products require signed access; integrate OAuth/token capability as provider requires, never invent public asset URLs.
- Provide separate raster readers for native SAFE/DN and for provider reflectance assets: read `scale` and `offset` in raster metadata or `raster:bands`, if present; for SAFE, use `rho=(DN+BOA_ADD_OFFSET)/QUANTIFICATION_VALUE` from official metadata. **Do not apply both**. Record pipeline in provenance. Mask DN=0 NoData before scaling. Never assume all scenes have identical processing baseline.
- SCL classes: default mask 0,1,3,8,9,10,11; optional mask 2 and 7 by explicit policy, not hidden. Cloud/shadow dilation configurable in metres; record all settings. Ensure mask resampling nearest; analytic spectral band resampling bilinear or nearest chosen and reported. Preserve mask/NoData separate from numerical zero.
- Windowed COG reads, GDAL /vsicurl or authenticated alternative; bounds clipped to AOI and scenes; fail when unsupported external access. Limit concurrent reads, bytes and memory. Search timeout, retry with jitter for 429/5xx, respect provider rate limits.
- Data type: `float32`; guard zero/near-zero denominators (`abs(denom) < 1e-6` configurable) and invalid domain (square roots) with NoData + warning. Do **not** globally clamp spectral index outputs to [-1,1]. Preserve genuine negative reflectance and >1 values resulting from atmospheric correction if source valid; quality warnings.

## Spatial grid and statistics
- AOI GeoJSON WGS84; validate polygon rings, self intersections, bounds, max 100 km² true geodesic area. Reject empty/no coverage. Handle anti-meridian and UTM zone crossing with suitable target projected CRS or explicit unsupported reason.
- Default output resolution = coarsest native resolution of required bands. B02/B03/B04/B08 = 10m; B05/B06/B07/B8A/B11/B12 = 20m; B01/B09/B10 = 60m (B10 not in L2A reflectance; disallow it). For indexes mixing 10m and 20m, native result 20m. NIR choice B08 or B8A must be explicit; never silently substitute.
- One standard target aligned raster grid per analysis; record CRS, transform, width, height, resolution, interpolation and bounds; clip exact AOI. Valid-pixel stats use masks and exclude nodata. Export rasters with same grid and metadata.
- Output COG Float32 tiled with internal overviews, nodata/mask, compression suitable for float; preserve CRS. Generate histograms and min/max/mean/median/std/percentiles count and valid fraction.

## Index registry contract
- All 21 named indices listed in YAML are MUST HAVE for this handoff, including original three. Formula strings are documentation and trusted registry configuration, NOT evaluated using general `eval`, Python `exec` or unsafe interpreter; define a whitelisted AST or function registry mapped by stable ID.
- Spectral arguments are calibrated reflectances, not raw DN or scaled integers. Coefficients apply to reflectance unit [0,1] convention (but measured values may exceed nominal range).
- NDSI always identified as snow index `NDSI_SNOW`, not ambiguous soil/salinity; avoid generic `NDWI` ambiguity: `NDWI_MCF` = McFeeters Green-NIR; `NDMI` = Gao NIR-SWIR vegetation moisture. `NDRE_B05` uses red-edge B05 and NIR B8A at 20m.
- When formula numerator and denominator source data are invalid, mask output and preserve. For formulas with a sqrt (MSAVI2), handle small negative due to rounding by tolerance; meaningful negative radicand is invalid (mask+warning).
- Include uncertainty and limitations in UI: indices are proxies, do not automatically equate to water-quality, urban classification, vegetation species, chlorophyll concentration or burn severity class.

## Image transforms from the manual (MUST)
- BAND_RATIO: allowed numerator/denominator from available calibrated reflectance bands; `rho(A) / rho(B)`, no forced index bound. Show explicit selected bands. Example NIR/RED B08/B04.
- TEMPORAL_DIFFERENCE: pixel-wise raster B minus raster A, either same named index or same calibrated band, same band semantics, resample onto aligned common grid at coarsest resolution; temporal metadata mandatory. No automatic thematic classification.
- PCA: user selects 3–10 calibrated bands with spatial co-registration; valid-pixel intersection; optional centering (required), configurable standardization (z-score); fit deterministic eigen-decomposition/SVD with stable sign convention, float64 numerics for model fitting, image output Float32; return PC rasters, eigenvectors, means, standard deviations and explained variance. Sample deterministically for fit if >cap while applying model tiled to full raster; record sample count/seed. Validate against sklearn reference in tests, but runtime may use numpy.
- RGB/FCC COMPOSITES: true-color B04/B03/B02 and false-color B08/B04/B03, optional B11/B08/B04 at coarsest 20m. Visual-only contrast stretch (e.g. 2–98 percentile), never change underlying reflectance product.

## Multi-date and preprocessing acceptance
- Same AOI, same named formula version, same reflectance units, grid and NoData handling. Reprojection should be deliberate and logged.
- Cloud fraction per AOI (postmask) separate from scene metadata cloud cover. If valid fraction < configurable threshold, show prominent warning; user may choose to proceed subject to policy.
- Raster download is never a blank rendered PNG labelled GeoTIFF. Test open/read via rasterio and QGIS compatibility.

## Calibration tests
1. Unit tests of every formula with `tests/reference_vectors.json` and independent Python reference expressions; masks/zeros/negative reflectance.
2. Real 10m and 20m raster fixtures that verify alignment, interpolation, nodata, boundary clipping and output resolution.
3. SAFE baseline pre-04 offset-free and baseline >=04 with offsets; normalized reflectance provider; compare and demonstrate absence of double scaling.
4. Compare NDVI/NDWI/NDBI and one advanced index to independently computed QGIS/GDAL outputs over same grid/mask, tolerance <=1e-5 for pure algebra.
5. PCA test explained variance sum~1 and eigenvectors, spectral ratios not clamped.
6. Antimeridian, invalid geometry, cross-zone AOI; explicit correct behavior or appropriate errors.

## Sources
- Canada Centre for Remote Sensing, *Fundamentals of Remote Sensing*, chapter 4.6 pp. 158–160 (user PDF).
- Sentinel-2 Processing Baseline / BOA offsets: https://sentiwiki.copernicus.eu/web/s2-products
- Official STAC: https://documentation.dataspace.copernicus.eu/APIs/STAC.html
- Sentinel-2 Level-2A and band information: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html
- External spectral index examples: https://hls.gsfc.nasa.gov/data-products/ and https://www.nature.com/articles/s41598-025-34720-x
