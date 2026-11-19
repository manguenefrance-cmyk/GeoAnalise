# PRODUCT AND UI SPECIFICATION — PRD v1.0

## Vision and users
ARCAMBE GeoAnalytics: professional self-service web GIS for satellite processing and environmental mapping. Global reach, initial market Mozambique and Southern Africa. Personas: student, GIS consultant, environmental consultant, university researcher. The platform is a tool, not a source of automatically certified environmental conclusions.

## Core entities and user journeys
1. Visitor visits English-first landing page and switches to Portuguese via persistent language selector. Clear CTA starts account signup.
2. User signs in via verified Firebase email authentication, receives private personal organization; optionally updates profile or deletes account.
3. Dashboard shows projects, successful/failed/running jobs, usage and recently exported products.
4. Project owner creates/renames/archives/deletes project; deletion with confirmation and retention policy.
5. Workspace displays MapLibre base map, AOI polygon drawing/editing, area and bounds; import GeoJSON/ZIP shapefile with .prj, validation and safe extraction. Store AOI in PostGIS EPSG:4326. Correct displayed area geodesically.
6. Satellite Explorer selects AOI, UTC date range, max scene cloud cover, Sentinel-2 L2A collection; returns dated scene cards, cloud metadata, footprint, provider, pixel/asset availability; clearly label scene-level cloud percentage. No scenes -> suggest adjusting filters.
7. Analysis Wizard selects scene, index category (vegetation, water, built environment, fire, soil, general transformation), index, formula, band list, target native resolution, cloud masking and output. Warn about limitations. Enqueue job after computing estimated credits. Support source-aware NDWI alias and NDSI ambiguity disambiguation.
8. Job detail: queued/running/completed/failed/cancelled and progress only if trustworthy, retry button, deterministic error codes.
9. Results: raster tile overlay with palette/range/opacity, legends, histograms, valid-pixel stats min/max/mean/std and masked fraction, inspect pixel; provenance panel contains dataset, acquisition, algorithm, source, masks and CRS. No fake results.
10. Transformations: band ratio; date2-date1 temporal difference of aligned analysis rasters; PCA on selected co-registered bands with scree chart and output components; RGB true/false color visualization.
11. Exports: cloud-optimized GeoTIFF, provenance JSON, map PNG/PDF, private signed download URLs; listing, retention, re-download, failed-export error handling.
12. Settings: locale EN/PT, user profile, usage and security settings; billing labelled 'Coming later' until actually integrated.

## Screen catalog (routes and functional acceptance)
- LP-01 `/`: product identity, screenshots marked illustrative, CTAs, use cases, features, docs links, legal links, locale toggle.
- AUTH-01 `/auth/login`, `/auth/register`, `/auth/forgot-password`, `/auth/verify`: validated forms, password reset, Firebase error handling, no exposed secrets.
- DASH-01 `/app/dashboard`: metrics from real API, recent jobs, usage, project shortcuts; empty/loading/error states.
- PRJ-01 `/app/projects`, `/app/projects/new`, `/app/projects/[id]/settings`: create/list/update/delete; confirmation for destructive actions.
- MAP-01 `/app/projects/[id]/workspace`: top nav (product, project, locale, account), left tools (layers, AOI, satellite, indices, transformations, exports), map, right context inspector, bottom job status. Draw polygon and import; keyboard and screen-reader accessible controls.
- SAT-01 workspace Imagery tab: search filters, scene results, date, coverage and metadata; hover/zoom footprint; provider access error states.
- IDX-01 workspace Index tab: category filter, searchable registry, formula+band description, selectable scene, parameter controls, execute action with quota warning.
- JOB-01 `/app/jobs/[id]`: state timeline, errors, timings, retry/cancel, provenance.
- RES-01 workspace Results tab: map overlay opacity + legend + histogram + stats; never colorize NoData as 0.
- EXP-01 `/app/exports`: export formats, status, expiration and secure download.
- SET-01 `/app/settings`: profile, locale, quota, account deletion request.

## UX and design
Editorial professional visual identity: white/light surface, deep navy headers, teal/green geospatial accents, restrained cards; clean cartographic legend and source labels. Consistent ARCAMBE branding, not the generic QGIS interface. Responsive 360px upward with MapLibre controls keyboard/focus support. On narrow viewports, use bottom sheets/tabs instead of permanent sidebars. Chart accessibility: text equivalents of quantitative values and high contrast. Default en, pt translation fallbacks flagged in CI. All calculations have method/help tooltips. Show explicit scale/resolution, missing data, cloud %, and scientific caveats.

## Plans and quotas
Initial Free/Beta only; 100 km² maximum AOI, max 12-month scene search, 5 daily jobs, 1 concurrent job, 1 scene per index analysis, configurable limits at backend, fair use. Domain model for future Student, Professional, Business and Enterprise; no real checkout until payment onboarding and accounting reviewed. Admin can override limits via config without code changes.

## KPIs
Activation = first successful index and visualized result; trial-to-paid when available; cost per completed job; 95%+ task success (for accessible source scenes); correctness of pixels and metadata; monthly return rate; latency and cloud bill.

## Scope boundaries
Explicitly not in this release: EnviroMonitor, RiskMapper, field data sampling integration, LST (Sentinel-2 lacks thermal bands), surface water turbidity in NTU (requires calibrated models), predictive risk models, native mobile apps, automatic validated land-cover maps, unlimited mass processing, automatic payment capture. Provide informative disabled/coming-later roadmap only where useful.
