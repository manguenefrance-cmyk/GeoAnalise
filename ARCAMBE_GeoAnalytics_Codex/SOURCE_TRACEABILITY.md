# REFERENCE DOCUMENT TRACEABILITY / SCIENTIFIC HONESTY

## User-supplied reference
*Fundamentals of Remote Sensing*, Canada Centre for Remote Sensing / Natural Resources Canada, 258-page PDF attached to the conversation as `document.pdf`.
- Printed pp. 158–160, §4.6 **Image Transformations**: multi-band arithmetic, temporal subtraction, spectral/band ratios, **NDVI** explicitly named, principal components analysis (PCA). All mandatory platform operations.
- Printed pp. 149–153: geometric/radiometric preprocessing concepts.
- Printed pp. 161–164: image classification and integration conceptual background — NOT a mandate to automatically classify scenes in MVP.
- Printed pp. 174–240: broad application areas (agriculture, forestry, geology, hydrology, land cover, coastal and ocean studies), not an enumeration of mathematical vegetation/water indices.
**Do not state that the book enumerates every modern formula in this package.** It does not. NDVI is the explicitly named spectral index in the transformations chapter. The modern 21-index catalog is an ARCAMBE-expanded scientific/product requirement.

## Technical supporting sources
- Sentinel-2 BOA offsets (processing baseline >=04.00): https://sentiwiki.copernicus.eu/web/s2-products
- Sentinel-2 STAC collection: https://documentation.dataspace.copernicus.eu/APIs/STAC.html
- Sentinel-2 Level-2A bands & units: https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html
- NASA HLS vegetation/water/burn spectral index overview: https://hls.gsfc.nasa.gov/data-products/
- 2025 paper index formulations (e.g. MNDWI, EVI, MSAVI2, NDRE): https://www.nature.com/articles/s41598-025-34720-x
- FAO index discussion: https://www.fao.org/fileadmin/user_upload/GSP/GSAS21/day1/PS1_02_Sahbeni.pdf

## Index formula naming caveats
- NDWI is ambiguous. Platform ID `NDWI_MCF` means Green/NIR water index. `NDMI` means NIR/SWIR moisture index. Do not call both simply 'NDWI'.
- `NDSI_SNOW` has the same algebra as `MNDWI` but different interpretation; avoid misleading users.
- `CI_GREEN`, `CI_RE` are proxies for pigment/chlorophyll-related spectral response; they are NOT laboratory chlorophyll measurement.
- `NBR`, `NBR2` are indices, not validated burned-area maps without appropriate pre/post and local calibration.
- `SIPI` becomes unstable when NIR-Red~0: mask denominator.
- Formula choices are specified explicitly and versioned for reproducibility. External literature may use alternative band variants; never silently change an implementation.

## Terms and permissions
Do not upload, republish, or embed the user-provided book PDF into public app assets/repository. Link to legitimate publication or use short original summaries. Source formulas are mathematical descriptions; implement from the documented equations and verify the chosen variants.
