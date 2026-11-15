# Spec v2 (proposal): Earth Trail Detective

NASA Space Apps Challenge 2026 · Challenge "Be An Earth System Trend Detective!" · Team of two · Proposal of 14 November 2026; once approved it replaces *Spec_Natural_Experiment_Detective.pdf* (v1)

> Name of the app: **Earth Trail Detective**.

> This is the English translation of [`Spec_v2_Earth_Trail_Detective.md`](Spec_v2_Earth_Trail_Detective.md) (German original). Section numbers are identical in both versions.

---

## 0. What changes compared with v1

| Topic | v1 | v2 (this proposal) | Reason |
|---|---|---|---|
| Main case | IMO 2020: ship sulfur and clouds (event analysis) | **Pollutant trail**: exhaust gases and particles on the way air → cloud → precipitation/snow → glacier → soil → river/sea, two regions with opposite trends | The challenge stresses opposite trends of the same process, long series and hydrology; "more complex analyses are out of scope" |
| IMO 2020 | Must, main case | **Should**, short demo case B "Ships and clouds" as a two-region trend comparison; the event analysis becomes **Could** | Short series after 2020, small and disputed effect, MODIS orbit drift |
| Substances | Sulfate, clouds | Sulfur, soot, nitrogen, dust, smoke/organic carbon, microplastics (sea only), natural controls, CO as a transport marker | Original project idea; all backed by NASA variables |
| Users | one mode with detective questions | **Student mode** (guided form) and **Researcher mode** (expert form) | Interview decision |
| Data | cached only | Demos cached; Researcher mode optionally live (Giovanni API/OPeNDAP with the user's own Earthdata token) | Interview decision |
| Language | German | App, explanatory texts and pitch in **English**, spec in German | International jury |
| River straightening | optional case 2 | dropped; soil and river are steps of the trail | Focus |

---

## 1. Problem

There are thousands of Earth observation variables. For school students, university students and interested laypeople it is hard to see which of them show a change, and harder still to tell whether a trend is statistically sound. Existing tools each cover only one part:

- Giovanni produces time series, but does not test for significance and hardly explains the variables.
- Specialised tools such as the EPA Critical Loads Mapper (deposition), the NADP trend maps (precipitation chemistry) and the USGS river trend studies (WRTDS/EGRET) each cover only one sub-area.
- As far as our research shows, there is no tool that **follows one substance through several parts of the water cycle** and shows trend and significance for every step.

A learner who wants to ask today whether soot on Himalayan glaciers is increasing, and whether that can be measured at all, has to gather products, variable names, units and statistics on their own.

## 2. What the tool does

A web tool that selects variables from NASA missions and models through a form, shows them as a monthly time series for one or two regions, removes the seasonal cycle and computes the rate of change and its significance. Its special feature is the **trail view**: for one substance the tool shows side by side what happens in air, cloud, precipitation/snow, glacier, soil and river. Every step appears as a trend card, and where there is no data, an honest card says "Trail ends here".

Core capabilities:

- Variable catalog with short definition, unit, source, step in the trail and data kind (measured / model / estimate)
- Guided form (Student mode) and expert form (Researcher mode)
- Time series, anomalies, Sen's slope, Mann-Kendall with autocorrelation correction, OLS with confidence interval
- Two-region comparison for opposite trends
- Trail view per substance with trend cards and "Trail ends here" cards
- Plain-language result: What, Where, How strong, Significant? Plus the note "correlation is not causation"
- Prepared demos that run offline; export as CSV, PNG and method report

**Guiding idea:** The tool is the platform, the cases are presets (substance + variables + regions + explanatory text). Statistics and interface are the same for all cases.

## 3. Who it is for

| Mode | Users | Context |
|---|---|---|
| **Student mode** | Upper secondary school students, university students, interested laypeople with a science background (the challenge's target group) | Guided form with 3 to 4 questions, simple language, demos to watch |
| **Researcher mode** | Researchers and advanced students who want to check a hypothesis quickly | Free choice of variable, bounding box and period, options for the statistics, optional live retrieval with their own Earthdata token |

## 4. Who it is not for

- Not for publication-grade analyses. The tool is a screening and learning tool, not an assessment.
- Not for real-time air quality, health warnings or regulatory decisions.
- Not for the pollution of a single lake, well, field or glacier. The grid cells are 0.25° to 1° wide, i.e. about 25 to 100 km.
- Not for the chemistry in cloud droplets, glacier ice or soil as a measured value. No time series exist for these, and the tool does not claim them.
- Not for forecasts.

## 5. Mapping to the challenge

| Challenge requirement | Implementation |
|---|---|
| Identify variables (MODIS, OMI, AIRS, GPM, MERRA-2, GLDAS) | Curated catalog with all six: OMI (SO₂, NO₂, aerosol index), MODIS (clouds, snow albedo), AIRS (CO, CO₂), GPM IMERG (precipitation), MERRA-2 (aerosols, deposition, precipitation), GLDAS (snow, soil water, runoff) |
| Get data for a region | Region presets, bounding box in the expert form, cached demo data, optional live retrieval |
| Time series long enough for statistics | Monthly; MERRA-2 from 1980, OMI from 2004, GLDAS 2.1 from 2000. Warning below 10 years |
| Rate of change and significance (t-test, Mann-Kendall, confidence interval) | Sen's slope, Mann-Kendall (Hamed-Rao), OLS with 95 % confidence interval, plain-language result |
| "Same process, opposite trend in another region" | Two-region comparison as a **Must**; demo A1 eastern North America versus India |
| Where it changes | Two regions side by side (Must), spatial trend map (Could) |
| Simple definitions, data detectives, short sequence of questions, demos | Student mode with guided form, explanatory texts, three demos |
| Remove the seasonal cycle; linear trends are enough | Anomalies as a Must; only linear trends in the Must scope |
| "A non-significant trend is interesting too" | Label "No evidence" just as prominent; note "with more years it might become significant" |
| Resources tab (Hydrology Time Series, CUAHSI, KNMI, statistics guide) | Water side of the trail from the Hydrology Time Series datasets; validation against the KNMI Climate Explorer |
| AI (optional) | Not in the Must scope; free-text search as a Could (C8) |

## 6. Success criteria

1. A test person without prior knowledge gets from the start to a result card with trend and significance in Student mode in **under 3 minutes**.
2. **Demo A1** shows trends for sulfur (SO₂ or sulfate) in eastern North America and India with direction, rate of change per decade, p-value and confidence interval. Whether they are opposite is decided by the data; the tool shows it honestly.
3. The **trail view** shows at least 4 steps as trend cards for sulfur, soot and dust per region, and the remaining steps as "Trail ends here" cards with a reason.
4. The **validation case** (CO₂) and the synthetic tests meet all acceptance criteria of section 13.
5. Every card names product, version, variable, unit and data kind (measured / model / estimate).
6. All demos run without internet in under 5 seconds per analysis.
7. The repository is public, has an OSI licence and a README with data sources and limits.

## 7. User flow

**Student mode (guided form)**

1. *What do you want to follow?* Choice of substance with a picture and one sentence of explanation: Sulfur, Soot, Nitrogen, Dust, Smoke, Microplastics, Natural sources, CO.
2. *Where?* Demo region pairs or one region from a list: city, desert, rainforest, mountains/glacier, coast/river mouth, ocean.
3. *Which part of the water's journey?* Air, Cloud, Rain & snow, Glacier, Soil, River & sea, or "the whole trail".
4. *Which period?* The default is the longest available period.
5. **Result:** trail view or single card, plot, plain language, evidence label, export.

**Researcher mode (expert form)**

1. Any variable from the catalog or, if a token is available, by Giovanni data ID.
2. One or two bounding boxes, period, aggregation (monthly), climatology period.
3. Statistics options: Mann-Kendall variant, significance level, with or without anomalies, Benjamini-Hochberg for several cards.
4. Result as above, plus a method report with all parameters and retrieval URLs.

## 8. Functional requirements

### Must have

| ID | Requirement |
|---|---|
| M1 | Variable catalog (file `catalog/variables.yaml`): name, short English definition, unit, product, version, variable, substance, trail step, data kind, period, coverage |
| M2 | Guided form (Student mode) as in section 7 |
| M3 | Expert form (Researcher mode) with variable, bounding box(es) and period from the cache |
| M4 | Monthly area means with cos(latitude) weighting |
| M5 | Seasonal adjustment: anomalies against the monthly climatology |
| M6 | Trend: Sen's slope and OLS with 95 % confidence interval, given per year, per decade and in % of the mean |
| M7 | Significance: Mann-Kendall with Hamed-Rao correction, p-value, evidence label (section 9), note when the series is too short |
| M8 | Two-region comparison side by side, with plain language for opposite trends |
| M9 | Trail view: trend cards per step for one substance and one region; "Trail ends here" cards with reason and literature link |
| M10 | Demo A1 "Follow the trail": sulfur, soot and dust in eastern North America versus India, cached |
| M11 | Plain-language result (What, Where, How strong, Significant?), note "correlation is not causation", labelling of the data kind |
| M12 | Validation case CO₂ and synthetic tests (section 13) |

### Should have

| ID | Requirement |
|---|---|
| S1 | Demo A2 "Glaciers": Alps versus Himalaya with soot and dust deposition, MODIS snow albedo, snow and runoff |
| S2 | Smoke/organic carbon (MERRA-2 OC, OMI aerosol index) |
| S3 | Nitrogen: OMI tropospheric NO₂ |
| S4 | Demo B "Ships and clouds": shipping lane versus neighbouring patch of sea, SO₂/sulfate and MODIS droplet radius, as a two-region trend comparison |
| S5 | Live retrieval in Researcher mode through the Giovanni time series API or OPeNDAP with the user's Earthdata token |
| S6 | Export: CSV, PNG, method report (Markdown or PDF) |
| S7 | Derived quantity "concentration in precipitation (model estimate)" = wet deposition / precipitation |
| S8 | Optional comparison with open ground data (one NADP or CAPMoN series for precipitation, WQP or ECCC for river sulfate), off by default |
| S9 | Confidence band of the slope in the plot |

### Could have

| ID | Requirement |
|---|---|
| C1 | Microplastics in the sea (CYGNSS) off river mouths, e.g. Mississippi and Ganges |
| C2 | Natural controls: DMS (marine sulfur), sea salt, volcanic SO₂ |
| C3 | CO as a transport marker; arrow map from the MERRA-2 transport fluxes (`SUFLUXU/V`, `BCFLUXU/V`, `DUFLUXU/V`) |
| C4 | Event analysis (interrupted time series, difference-in-differences) for IMO 2020 |
| C5 | Spatial trend map (trend per grid cell) |
| C6 | Benjamini-Hochberg correction across all cards of a trail |
| C7 | Lagged correlation between neighbouring trail steps |
| C8 | AI free text ("soot on Himalayan glaciers") → catalog entries, only with the user's own key, keyword fallback |
| C9 | Docker image |

### Won't have (this time)

- Phosphorus and iron (no NASA variable)
- Measured values for pollutants in cloud droplets, glacier ice or soil; microplastics in clouds, glaciers or soil (no time series exist, only "Trail ends here" cards)
- Own database, Grafana, Java backend
- Forecasts, real-time or hourly data
- Health or regulatory assessments

## 9. Statistics specification

**Preprocessing**

- Monthly area means per variable and region, weighted with cos(latitude)
- Units are harmonised on loading, e.g. deposition from kg m⁻² s⁻¹ to mg m⁻² month⁻¹
- Anomalies: value minus the climatology of the calendar month; the climatology by default over the whole available period, selectable in Researcher mode
- Missing values are marked, not interpolated; warning above 10 % gaps

**Trend**

- Sen's slope (robust) and OLS with 95 % confidence interval (statsmodels)
- Mann-Kendall with Hamed-Rao correction as the default (pymannkendall); classic Mann-Kendall for comparison and a note when the two differ
- Significance level 5 %; always shown: p-value, slope per decade, confidence interval, change in % of the mean
- Length: warning below 10 years, recommendation from 15 years

**Evidence label**

| Label | Condition |
|---|---|
| **Strong** | Mann-Kendall (Hamed-Rao) p < 0.05, OLS confidence interval excludes 0, series ≥ 15 years |
| **Weak** | only one of the two criteria met, or series of 10 to 15 years |
| **No evidence** | not significant; shown just as prominently, with the sentence "a longer record might make it significant" |

**Two-region comparison and trail**

- Every region and every step is tested on its own. The plain-language text says "opposite trends" only if both directions are at least *Weak*.
- Trends in neighbouring trail steps are shown **side by side**, not linked causally.
- In Researcher mode optionally Benjamini-Hochberg across all cards of a trail (C6).

**Event analysis (Could, C4):** as in v1 section 6 (interrupted time series, difference-in-differences, minimum length 36 months before and after the event).

## 10. Variables, trail and data

### 10.1 The trail model

```text
Source (traffic, industry, ships, fire, desert, sea)
  → Air (column, surface, transport)
  → Cloud (formation, washout, ice nuclei)
  → Precipitation / snow (wet and dry deposition)
  → Glacier / snow cover (deposition, darkening, melt)
  → Soil (only water as the carrier: soil moisture by depth, seepage)
  → River / lake / sea (runoff, microplastics)
```

Every arrow is a hypothesis that the tool does not prove. It shows the trends of the individual steps so that the user becomes the detective.

**Dust and ice:** Mineral dust is the most important ice nucleus in clouds and therefore the substance most directly involved in ice formation. The tool follows dust itself (column, deposition, darkening of snow).

**Phosphorus and iron** are not followed (team decision of 14 November 2026): there is no NASA variable for them, only rough estimates from dust deposition.

### 10.2 Matrix substance × trail step

✅ measured time series · 🟡 model or estimate · ⚪ optional open ground data · ❌ no time series ("Trail ends here")

| Substance | Air | Cloud | Precipitation/snow | Glacier | Soil | River/lake/sea |
|---|---|---|---|---|---|---|
| Sulfur | ✅ OMI SO₂; 🟡 MERRA-2 sulfate | 🟡 sulfate formation in clouds, washout | 🟡 wet deposition; ⚪ NADP/CAPMoN | 🟡 deposition over glacier area | ❌ | ⚪ river sulfate (WQP/ECCC) |
| Soot | 🟡 MERRA-2 BC | 🟡 washout | 🟡 deposition | ✅ darkening (MODIS snow albedo) | ❌ | ❌ |
| Nitrogen | ✅ OMI NO₂ | ❌ | ⚪ nitrate NADP/CAPMoN | ❌ | ❌ | ⚪ river nitrate |
| Dust | 🟡 MERRA-2; ✅ OMI aerosol index | 🟡 ice nucleus, washout | 🟡 deposition | ✅ darkening | ❌ | ❌ |
| Smoke/OC | 🟡 MERRA-2 OC; ✅ OMI aerosol index | 🟡 washout | 🟡 deposition | ✅ darkening | ❌ | ❌ |
| Microplastics | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ CYGNSS, sea only, 37.4° S to 37.4° N, from 08/2018 |
| Natural controls | 🟡 DMS, sea salt, volcanic SO₂ | 🟡 | 🟡 | – | – | – |
| CO (transport) | ✅ MOPITT, AIRS | – | – | – | – | – |
| **Water** (carrier) | ✅ AIRS/MERRA-2 water vapour | ✅ MODIS/MERRA-2 cloud water | ✅ IMERG, MERRA-2 | 🟡 GLDAS snow, MERRA-2 glacier runoff | 🟡 GLDAS soil moisture by depth | 🟡 GLDAS runoff, NLDAS streamflow (USA only) |

### 10.3 Variable catalog (Must; names checked in the NASA catalog on 14 November 2026)

| Step | Substance | Product | Variable(s) | Unit (file) | Kind |
|---|---|---|---|---|---|
| Air | Sulfur | OMI `OMSO2e` (check version 003/004) | `ColumnAmountSO2` | DU | measured |
| Air | Sulfur | MERRA-2 `M2TMNXAER` | `SO4CMASS`, `SO4SMASS`, `SO2CMASS` | kg m⁻², kg m⁻³ | model |
| Cloud | Sulfur | MERRA-2 `M2TMNXADG` | `SUPSO4AQ` (sulfate formation in cloud water), `SUSV001`–`004` (convective washout) | kg m⁻² s⁻¹ | model |
| Precipitation | Sulfur | MERRA-2 `M2TMNXADG` | `SUWT001`–`004` (wet), `SUDP001`–`004` (dry) | kg m⁻² s⁻¹ | model |
| Air | Soot | MERRA-2 `M2TMNXAER` | `BCCMASS`, `BCSMASS` | kg m⁻² | model |
| Precipitation | Soot | MERRA-2 `M2TMNXADG` | `BCWT001`–`002`, `BCDP001`–`002` | kg m⁻² s⁻¹ | model |
| Air | Dust | MERRA-2 `M2TMNXAER` | `DUCMASS`, `DUSMASS` | kg m⁻² | model |
| Precipitation | Dust | MERRA-2 `M2TMNXADG` | `DUWT001`–`005`, `DUDP001`–`005` | kg m⁻² s⁻¹ | model |
| Glacier | Soot, dust, smoke | MODIS `MOD10A1.061` (AppEEARS) | `Snow_Albedo_Daily_Tile` | % | measured |
| Glacier | Water | MERRA-2 `M2TMNXGLC` | `RUNOFF`, `SNOMAS_GL` | kg m⁻² s⁻¹, kg m⁻² | model |
| Precipitation | Water | MERRA-2 `M2TMNXFLX`; GPM `GPM_3IMERGM` | `PRECTOTCORR`, `PRECSNO`; `precipitation` | kg m⁻² s⁻¹; mm h⁻¹ | model; measured |
| Snow | Water | GLDAS `GLDAS_NOAH025_M.2.1` | `SWE_inst`, `Snowf_tavg`, `Qsm_acc` | kg m⁻² | model |
| Soil | Water | GLDAS `GLDAS_NOAH025_M.2.1` | `SoilMoi0_10cm_inst` to `SoilMoi100_200cm_inst`, `Qs_acc`, `Qsb_acc` | kg m⁻² | model |
| Validation | CO₂ | OCO-2 L3 or AIRS (check product and record length) | CO₂ column / mixing ratio | ppm | measured/model |

Should and Could variables:

- **Nitrogen:** OMI `OMNO2d` `ColumnAmountNO2TropCloudScreened`
- **Smoke:** MERRA-2 `OCCMASS`, `OCWT001`–`002`, `OCDP001`–`002`; OMI `OMAERUVd` `UVAerosolIndex`
- **Ships (demo B):** MODIS `MOD08_M3`/`MYD08_M3` `Cloud_Effective_Radius_Liquid_Mean_Mean`, `Cloud_Water_Path_Liquid_Mean_Mean`, `Cloud_Optical_Thickness_Liquid_Mean_Mean`
- **Microplastics:** `CYGNSS_L3_MICROPLASTIC_V3.2` `mp_concentration` (#/km²), `num_mp_samples`
- **Natural controls:** MERRA-2 `DMSCMASS`, `SSCMASS`, `SO2EMVE`/`SO2EMVN` (volcanic)
- **Transport:** `SUFLUXU/V`, `BCFLUXU/V`, `DUFLUXU/V`; MOPITT `MOP03JM` (CO, from 2000); AIRS `AIRS3STM` `CO_VMR_A`
- **US rivers:** NLDAS `Streamflow` (USA only, up to about 53° N)

Further variable names, endpoints and authentication are in `research/hydrological_data_apis_and_variables.md` (in the wiki: *Datasets and Varsity*).

### 10.4 Common data format

One DataFrame with the columns `date` (first day of the month), `value`, `unit`, `variable`, `product`, `version`, `region`, `substance`, `step`, `kind` (`measured` | `model` | `estimate`), `source_url`.

### 10.5 Data sources and access

| Source | Access | Auth | Role |
|---|---|---|---|
| Giovanni / GES DISC (MERRA-2, OMI, AIRS, GLDAS, NLDAS, IMERG) | CSV export for the cache; live: `https://api.giovanni.earthdata.nasa.gov/timeseries` or OPeNDAP/Harmony | Earthdata token (free, per person) | Main source |
| Hydrology Time Series (GES DISC) | GLDAS, NLDAS, IMERG, MERRA-2, GRACE-DA, SMERGE | Earthdata | Water side of the trail |
| AppEEARS (MODIS snow albedo) | REST tasks, in advance for the demo regions | Earthdata | Glacier step |
| PO.DAAC (CYGNSS), LAADS (MOD08) | earthaccess | Earthdata | Should/Could |
| Optional, open: NADP, CAPMoN (open.canada.ca), Water Quality Portal, ECCC Long-term Water Quality | CSV/REST | none or free | comparison only, off by default |

Demo data loaded in advance is stored as Parquet under `data/`. There is no live retrieval during the presentation. The licences of all additional data are checked before use, as the Space Apps terms require.

## 11. Demo cases

The region boxes are proposals and are fixed before the data is fetched.

| Case | Purpose | Regions (proposal) | Substances | Priority |
|---|---|---|---|---|
| **A1 "Follow the trail: same process, opposite trends"** | Main demo; opposite trends | Eastern North America: Ohio Valley approx. 37–42° N, 88–80° W (source) and Québec/Adirondacks approx. 44–48° N, 78–70° W (downwind). India: Indo-Gangetic Plain approx. 22–30° N, 75–88° E | Sulfur, soot, dust | Must |
| **A2 "Glaciers"** | Glacier step with measurable darkening | Alps approx. 45.5–47.5° N, 6–13° E; central Himalaya approx. 27–30° N, 82–88° E | Soot, dust, smoke | Should |
| **B "Ships and clouds"** | Bridge to v1; ship sulfur | Shipping lane versus neighbouring patch of sea (take the boxes over from v1) | Sulfur, cloud droplet radius | Should |
| **V "Check a known trend"** | Validation (positive control) | Northern Hemisphere or global | CO₂ | Must |
| **Free choice** | Researcher and Student mode | any | all in the catalog | Must (from cache), Should (live) |

**Expectations are hypotheses, not targets.** The literature reports clearly falling sulfur values in air, precipitation and many rivers in eastern North America since the clean-air laws around 1990. For India it reports rising SO₂ values for large parts of the OMI period. The tool checks this with the data and shows every result, including "No evidence".

## 12. Key decisions

- **Main case:** IMO 2020 / pollutant trail / both. **Chosen: the trail as the main case, IMO 2020 as the short demo case B**, because the trail hits the challenge's focus points (opposite trends, hydrology, long series) directly.
- **Data access:** cache only / cache + live / live only. **Chosen: demos from the cache, Researcher mode optionally live**, so that the demo runs reliably in front of the jury.
- **Data sources:** NASA only / NASA + ground data. **Chosen: NASA as the main source, open ground data only optionally for comparison**, because of the challenge text, licence terms and effort.
- **Interface:** Streamlit / React + API. **Chosen: Streamlit with `st.form`**, because of a Python team and 1.5 days of time.
- **Modes:** one mode / Student + Researcher. **Chosen: two modes on the same core**, decided in the interview.
- **Language:** **app in English, spec in German**, because of the international jury.
- **AI:** Must / Could / not at all. **Chosen: Could (C8)**; not a core component and no dependency on paid keys.
- **Phosphorus and iron:** leave out / as an estimate. **Chosen: both are dropped**, because there is no direct NASA product and estimates from dust would be too rough.
- **Name:** **Earth Trail Detective** (English, like the app).
- **Licence:** **Apache-2.0** (OSI). Without a licence of our own, NASA distributes the code under Apache-2.0 anyway.

## 13. Build plan and verification

### 13.1 Build plan (in order)

| Step | Content | Who | Decision / requirement |
|---|---|---|---|
| 1 | Repository, licence, data format (10.4), `catalog/variables.yaml` with the Must variables | A | YAML instead of code, so that explanatory texts can be changed without programming |
| 2 | Statistics core: anomalies, Sen, OLS, Mann-Kendall (Hamed-Rao), evidence label, with tests on synthetic data | B | pymannkendall + statsmodels |
| 3 | Load the demo data for A1 (Giovanni CSV or earthaccess), area means, units, Parquet | A | Monthly data, longest period |
| 4 | Run validation case V; evaluate A1 only once it passes | B | Acceptance criteria 13.2 |
| 5 | Interface: guided form, result card, two-region comparison | B | `st.form`, Plotly |
| 6 | Trail view with trend cards and "Trail ends here" cards | A + B | Cards from the catalog field `step` |
| 7 | Expert form (Researcher mode) from the cache | B | — |
| 8 | Should items as time allows: A2, B, NO₂, smoke, export, live retrieval | A + B | A2 before B (glaciers are part of the core idea) |
| 9 | README, explanatory texts, pitch, video, submission | together | at least half a day |

**Schedule (from Saturday afternoon):** Sat afternoon steps 1–3 in parallel; Sat evening 4–5; Sun morning 6–7; Sun noon 8; Sun afternoon 9.

### 13.2 Verification

| Area | Procedure | Tools |
|---|---|---|
| Statistics core | Unit tests: (a) series with a known trend + noise → slope recovered; (b) pure noise → "not significant" in ~95 % of 1000 runs; (c) autocorrelated noise → Hamed-Rao prevents spurious significance; (d) seasonal adjustment narrows the confidence interval | pytest, numpy |
| Validation CO₂ | Trend significantly positive, label *Strong*, confidence interval overlaps the reference value (KNMI Climate Explorer or literature), Sen and OLS in the same direction | cached series, reference value noted |
| Data loader | Per variable: unit, period, share of missing values, plausibility range; spot check against the Giovanni plot of the same box | pytest + checklist |
| Area mean | Compare one box by hand against Giovanni "Area-Averaged Time Series" (deviation < 1 %) | Giovanni |
| Interface | Manual checklist: every form path ends in a card; a test person manages it in < 3 min; offline test with Wi-Fi switched off | Checklist |
| Honesty | Every card shows data kind, source and version; "Trail ends here" appears for all ❌ fields of matrix 10.2 | Checklist |

## 14. Non-functional requirements

- Demos run offline from the cache; analysis in under 5 seconds
- App texts in English, simple language, technical terms with a short definition
- Colour-blind-safe colours; trend direction also with an arrow and text, not only with colour
- Earthdata token only from an environment variable or `st.secrets`, never in the repository and never in the browser
- Public repository, Apache-2.0, README with installation, start, data sources, licences and limits; every source cited
- Statistics functions with tests

## 15. Risks and open questions

- **MERRA-2 emissions:** The anthropogenic emission inventories in MERRA-2 may have been updated only to a limited extent for recent years (to be checked, Randles et al. 2017). Sulfate and soot trends after about 2010 are therefore cross-checked with measured OMI SO₂ and the OMI aerosol index respectively, and labelled as model in the tool.
- **Model instead of measurement:** The cloud, deposition and glacier steps are mostly model values. Every card must say so clearly.
- **Grid resolution:** Glaciers and rivers are smaller than the grid cells; glacier values are area means over mountain boxes.
- **Microplastics (CYGNSS):** A research product, derived from sea-surface roughness, only between 37.4° S and 37.4° N, only from 2018. A short series, so often "No evidence".
- **Sensor drift and gaps:** Orbit drift of MODIS Terra/Aqua, the OMI row anomaly, the GLDAS 2.0/2.1 switch in 2000. Warnings in the tool.
- **Scope:** eight substance groups and three demos are a lot for 1.5 days. The Must list is deliberately narrow; Should items are started only after the Must items are finished.
- **Live retrieval:** The exact format of the Giovanni data IDs for the time series API has to be checked with a token.
- **Open:** fix the region boxes; look up the reference value for CO₂; check the submission format (video/slides) in the Participant Guide 2026.

## 16. Submission checklist (judging criteria)

The criteria are Impact, Creativity, Validity, Relevance and Presentation (check against the 2026 guide before submission).

- **Relevance:** all four challenge goals plus opposite trends (section 5)
- **Validity:** seasonal adjustment, autocorrelation correction, validation case, synthetic tests, labelling of model/measurement/estimate, honest "No evidence" and "Trail ends here" cards
- **Creativity:** following one substance through the water cycle; dust as an ice nucleus; two modes
- **Impact:** a learning tool for school and university students, a quick first look for researchers, without overpromising
- **Presentation:** demo A1 runs offline, a clear story ("Follow the trail"), public repository, video/slides
