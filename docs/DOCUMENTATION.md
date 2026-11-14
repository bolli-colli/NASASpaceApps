# Earth Trail Detective – Technical Documentation

Contents

1. [Architecture](#1-architecture)
2. [Libraries](#2-libraries)
3. [Concepts](#3-concepts)
4. [How the data is accessed in practice](#4-how-the-data-is-accessed-in-practice)
5. [Developer setup in the shell (Windows, Linux, macOS)](#5-developer-setup-in-the-shell-windows-linux-macos)
6. [How to extend the app](#6-how-to-extend-the-app)
7. [Tests and verification](#7-tests-and-verification)
8. [Deviations from the spec and open items](#8-deviations-from-the-spec-and-open-items)

---

## 1. Architecture

The code follows a **layered architecture**. Dependencies point inwards only:

```
presentation  ──►  application  ──►  domain  ◄──  infrastructure
(Streamlit)        (use cases,       (entities,    (YAML, Parquet,
                    ports)            statistics)   CSV, Earthdata)
```

| Layer | Folder | Responsibility | May import |
|-------|--------|----------------|------------|
| Domain | `domain/` | Entities, value objects, statistics, units. Pure functions, no files, no network, no UI. | nothing of ours |
| Application | `application/` | Use cases (analyse a series, build a trail, compare regions, write texts and reports) and the **ports** – interfaces to the outside world. | domain |
| Infrastructure | `infrastructure/` | Adapters that implement the ports: YAML catalog, Parquet cache, CSV reader, Earthdata gateway. | application, domain |
| Presentation | `presentation/` | Streamlit forms, cards, charts, downloads. | application, domain |

`bootstrap.py` is the **composition root**: the only module that knows the concrete
classes and wires them together. `config.py` reads all environment variables.

### Module map

```
domain/
  enums.py            Step, DataKind, EvidenceLabel, TrendDirection, GapStatus, ...
  models.py           BoundingBox, Period, Region, Substance, VariableSpec, TrailGap, DemoCase
  series.py           MonthlySeries + SeriesMeta = the common data format (spec 10.4)
  units.py            unit conversion registry
  results.py          TrendResult, TrendCard, TrailEndCard, UnavailableCard, Trail, Comparison
  errors.py           exception types
  statistics/
    anomalies.py      monthly climatology, anomalies
    trend.py          Sen's slope, OLS with confidence interval and band
    mann_kendall.py   Mann-Kendall variants (registry)
    evidence.py       evidence label rules
    multiple_testing.py  Benjamini-Hochberg
    area_mean.py      cos(latitude)-weighted mean
application/
  ports.py            Catalog, SeriesSource, SeriesStore, LiveDataGateway (Protocols)
  options.py          AnalysisOptions, AnalysisRequest
  ingest.py           raw values -> MonthlySeries (monthly mean + unit harmonisation)
  sources.py          DerivedSeriesSource (sum / ratio), LiveSeriesSource
  trend_analysis.py   TrendAnalyzer – the statistics pipeline
  trail.py            TrailBuilder – cards for a substance or for free variables
  comparison.py       two-region comparison, reference check (validation case)
  narrative.py        plain-language result
  methods_report.py   Markdown methods report
  formatting.py       shared wording and number formats
infrastructure/
  yaml_catalog.py     reads and validates catalog/*.yaml
  parquet_repository.py  offline cache
  csv_import.py       Giovanni / plain CSV reader
  grid_reduction.py   one gridded file -> area mean of a box
  earthaccess_gateway.py  NASA Earthdata access
presentation/
  main.py             page layout and control flow
  student_form.py, researcher_form.py, form_widgets.py
  result_view.py, charts.py, exports.py, theme.py
```

### SOLID in this code base

- **Single responsibility** – one reason to change per module: `evidence.py` only knows
  the label rules, `charts.py` only draws, `yaml_catalog.py` only reads YAML.
- **Open/closed** – new behaviour is added by registration, not by editing logic:
  a Mann-Kendall variant (`mann_kendall._TESTS`), a unit conversion
  (`units._CONVERSIONS`), a derivation (`sources._OPERATIONS`), a variable or demo (YAML).
- **Liskov substitution** – every `SeriesSource` is interchangeable: the Parquet cache,
  the live source and the derived-series decorator are used by `TrailBuilder` in exactly
  the same way. Tests use an in-memory fake.
- **Interface segregation** – small ports: reading a series (`SeriesSource`) is separate
  from storing one (`SeriesStore`) and from fetching grids (`LiveDataGateway`).
- **Dependency inversion** – use cases depend on the Protocols in `application/ports.py`;
  infrastructure implements them; `bootstrap.py` injects them.

### DRY – one place per fact

| Fact | Single place |
|------|--------------|
| Column names of the data format | `domain/series.py` (derived from the `SeriesMeta` fields) |
| Monthly aggregation + unit harmonisation | `application/ingest.py::build_series` (used by CSV import, live gateway) |
| Evidence thresholds (10 / 15 years, criteria) | `domain/statistics/evidence.py` |
| Wording of labels, number formats | `application/formatting.py` |
| Colours and symbols | `presentation/theme.py` |
| Product descriptions in the catalog | YAML anchors in `catalog/variables.yaml` |
| Year-range input | `presentation/form_widgets.py::period_picker` |
| Object wiring | `bootstrap.py` |

### Request flow

```
form / demo button ──► AnalysisRequest
        │
        ▼
TrailBuilder.run(request)
   for each region, for each step of the trail:
      catalog.variables_for(substance, step)
        ├─ variables found ─► SeriesSource.load ─► TrendAnalyzer.analyze ─► TrendCard
        │                         └─ nothing cached / too short ─► UnavailableCard
        └─ no variable ─► catalog.gap(...) ─► TrailEndCard ("Trail ends here")
        ▼
result_view.render_results ─► cards side by side, comparison text, exports
```

---

## 2. Libraries

### Runtime

| Library | Used for | Where |
|---------|----------|-------|
| **Streamlit** | Web interface in pure Python. `st.form` collects all inputs and sends them with one button; `st.session_state` keeps the last result across reruns; `st.cache_resource` builds the object graph once; `st.secrets` holds the token. | `presentation/` |
| **Plotly** | Interactive charts: series, OLS line, confidence band, Sen line. The toolbar's camera button exports PNG in the browser. | `presentation/charts.py` |
| **pandas** | Time series with a monthly `DatetimeIndex`; grouping by calendar month; Parquet and CSV I/O. | everywhere |
| **NumPy** | Array maths, weights, random numbers in tests. | domain, tests |
| **SciPy** | `scipy.stats.theilslopes` – Sen's slope (Theil-Sen estimator). | `statistics/trend.py` |
| **statsmodels** | `OLS` with `conf_int` and prediction band; `multipletests(method="fdr_bh")` for Benjamini-Hochberg. | `statistics/trend.py`, `multiple_testing.py` |
| **pymannkendall** | Mann-Kendall tests: classic, Hamed-Rao, Yue-Wang, pre-whitening. | `statistics/mann_kendall.py` |
| **PyYAML** | Reads the catalog. `safe_load` supports anchors (`&name`, `*name`) and merge keys (`<<:`), used to describe each product once. | `infrastructure/yaml_catalog.py` |
| **PyArrow** | Parquet engine behind `DataFrame.to_parquet` / `pd.read_parquet`. | `infrastructure/parquet_repository.py` |

### Optional – extra `live`

| Library | Used for |
|---------|----------|
| **earthaccess** | NASA's library for Earthdata: login with a token, search granules in the Common Metadata Repository (CMR), open files over HTTPS. |
| **xarray** | Opens a netCDF-4/HDF5 file as labelled arrays (`lat`, `lon`), so a box can be selected by coordinates. |
| **h5netcdf** | The xarray engine that can read netCDF-4/HDF5 from a remote file object. |

These are imported lazily inside `earthaccess_gateway.py`; the app runs offline without them.

### Development – extra `dev`

| Library | Used for |
|---------|----------|
| **pytest** | Test runner. |
| **ruff** | Linter and formatter (config in `pyproject.toml`). |
| `streamlit.testing.v1.AppTest` | Runs the app headless in tests and clicks through the forms. |

---

## 3. Concepts

### 3.1 The trail model

```
Source → Air → Cloud → Rain & snow → Glacier → Soil → River & sea
```

Every arrow is a **hypothesis**. The tool shows the trend of each step next to the
others; it never links them causally. The matrix *substance × step* of the spec decides
what each cell is:

- a **variable** in `catalog/variables.yaml` → trend card,
- a **gap** in `catalog/trail.yaml` → "Trail ends here" card with reason and reference,
- `not_applicable` → the step is skipped.

The catalog refuses to load if a cell is neither – no card can silently disappear.

### 3.2 Common data format

A table with the columns
`date, value, unit, variable, product, version, region, substance, step, kind, source_url`.
In memory this is a `MonthlySeries`: values on a gap-free monthly index (missing months
are `NaN`) plus one `SeriesMeta`. Missing values are marked, **never interpolated**.

### 3.3 Area mean with cos(latitude) weights

Grid cells get narrower towards the poles. A fair regional mean therefore weights each
cell with the cosine of its latitude: `mean = Σ(wᵢ·xᵢ) / Σ(wᵢ)`, `wᵢ = cos(latᵢ)`,
ignoring cells without data. Implemented in `statistics/area_mean.py`.

### 3.4 Unit harmonisation

Raw units are converted once, when data is loaded (`ingest.build_series`):

| From | To | Rule |
|------|----|------|
| kg m⁻² | mg m⁻² | × 10⁶ |
| kg m⁻³ | µg m⁻³ | × 10⁹ |
| kg m⁻² s⁻¹ | mg m⁻² month⁻¹ | × 10⁶ × seconds in the month |
| kg m⁻² s⁻¹ | mm month⁻¹ | × seconds in the month (1 kg m⁻² water = 1 mm) |
| mm h⁻¹ | mm month⁻¹ | × hours in the month |
| kg m⁻² (3h)⁻¹ | mm month⁻¹ | × 8 × days in the month (GLDAS `*_acc`) |
| mol mol⁻¹ | ppm | × 10⁶ |

### 3.5 Removing the seasonal cycle

Most variables swing with the seasons. The **climatology** is the mean of each calendar
month (all Januaries, all Februaries, …); the **anomaly** is the value minus the
climatology of its month. Trends are computed on anomalies by default. The climatology
period is the whole record unless the researcher chooses otherwise.

### 3.6 Trend

- **Sen's slope** – the median of the slopes between all pairs of points. Robust against
  outliers. Reported per year, per decade and in % of the mean per decade.
- **OLS** – ordinary least squares line with its 95 % confidence interval (level follows
  the chosen significance level). The band in the chart is the confidence band of the line.

Both use the real time axis in decimal years, so gaps do not distort the slope.

### 3.7 Significance

The **Mann-Kendall test** asks whether values tend to rise or fall over time, without
assuming a straight line or a normal distribution. Monthly environmental data is
**autocorrelated** (a month resembles the previous one), which makes the classic test
report trends too often. The **Hamed-Rao correction** adjusts the test's variance for
that. It is the default; Yue-Wang and pre-whitening are selectable.

**Safeguard added in this implementation:** the corrected p-value is never allowed to be
smaller than the classic one. In simulations the plain Hamed-Rao test of `pymannkendall`
reported a trend in about 10 % of pure-noise series instead of the nominal 5 %, because a
randomly negative autocorrelation estimate *shrinks* the variance. With the safeguard the
rate is 5 %. For autocorrelated noise (AR(1) = 0.7, 20 years) false alarms drop from about
35 % (classic) to about 18 % – the correction reduces spurious significance, it does not
remove it completely.

### 3.8 Evidence label

| Label | Condition |
|-------|-----------|
| **Strong evidence** | Mann-Kendall p < α **and** OLS interval excludes 0 **and** record ≥ 15 years |
| **Weak evidence** | only one criterion, or both on a record shorter than 15 years |
| **No evidence** | neither criterion – shown just as prominently, with "A longer record might make it significant." |

Warnings: record below 10 years, 10–15 years, more than 10 % missing months, classic and
corrected test disagree, and the product caveats from the catalog.

### 3.9 Two-region comparison

Each region is tested on its own. The text says **"Opposite trends"** only if both trends
are at least *Weak* and point in different directions; otherwise "Same direction" or
"No clear comparison".

### 3.10 Benjamini-Hochberg

Testing many cards at once produces chance hits. The optional correction (researcher
mode) adjusts the p-values across all cards of one region; the labels then use the
adjusted values.

### 3.11 Derived quantities

A catalog entry can be computed from others (`derivation: {operation, inputs}`):

- `ratio` – *sulfur concentration in precipitation* = wet deposition ÷ precipitation
  (kind `estimate`),
- `sum` – *sulfur deposited on the glacier region* = wet + dry deposition.

`DerivedSeriesSource` computes them on the fly for cached and live data alike.

### 3.12 Accessibility and honesty rules

- Okabe-Ito colours; direction is always arrow **and** word; evidence is symbol **and** text.
- Every card names product, version, variable, unit, data kind and source.
- Artificial development data triggers a red banner.

---

## 4. How the data is accessed in practice

### 4.1 Overview

```
                     ┌─ scripts/build_cache.py ── EarthaccessGateway ─┐
NASA Earthdata ──────┤                                                ├──► data/*.parquet ──► app
 (token needed)      └─ Giovanni / AppEEARS CSV ── scripts/import_csv.py ┘      (offline)

Researcher mode, "Live": EarthaccessGateway ──► app   (no file is written)
```

During a presentation nothing is fetched: demos read `data/` only.

### 4.2 Authentication

1. Free account: <https://urs.earthdata.nasa.gov/users/new>.
2. Profile → *Generate Token*.
3. Provide it as environment variable `EARTHDATA_TOKEN`, or in `.streamlit/secrets.toml`
   (copied to the environment on start-up by `presentation/main.py`).

The token is read on the server only. It is never typed into the browser, never logged
and never committed (`.gitignore` covers `.streamlit/secrets.toml` and `.env`).

### 4.3 Scripted access with earthaccess

What `EarthaccessGateway.fetch` does, reduced to its essence:

```python
import earthaccess, xarray as xr

earthaccess.login(strategy="environment")  # uses EARTHDATA_TOKEN

granules = earthaccess.search_data(  # one granule = one monthly file
    short_name="M2TMNXAER",
    version="5.12.4",
    temporal=("2000-01-01", "2024-12-31"),
)
for granule, handle in zip(granules, earthaccess.open(granules)):  # HTTPS, no download
    with xr.open_dataset(handle, engine="h5netcdf") as dataset:
        value = area_mean(dataset, ("SO4CMASS",), region.bbox)  # cos(lat) weighted
```

- Short name, version and optional HDF5 group come from the `access` block of the
  catalog entry.
- Variables of the same product share their files: each file is opened once for all
  variables and regions.
- Lists such as `[SUWT001, …, SUWT004]` are summed (species or size bins).
- The month of a file is taken from its CMR metadata.
- `build_series` then converts the unit and builds the `MonthlySeries`.

Works for regular lat/lon netCDF-4/HDF5 grids: **MERRA-2, GLDAS, GPM IMERG, OCO-2 GEOS**.

```bash
pip install -e ".[live]"
export EARTHDATA_TOKEN="..."
python scripts/build_cache.py --demo A1 --start 2000-01 --end 2024-12
```

### 4.4 Manual export + import

**OMI, MODIS, AIRS and CYGNSS** files are HDF-EOS/HDF4 swaths or tiles without simple
lat/lon coordinates. For them, NASA's own tools do the area averaging:

- **Giovanni** (<https://giovanni.gsfc.nasa.gov/giovanni/>): plot type
  *Time Series, Area-Averaged* → choose variable, box, period → download CSV.
- **AppEEARS** (<https://appeears.earthdatacloud.nasa.gov/>): *area request* for
  MOD10A1 `Snow_Albedo_Daily_Tile` → statistics CSV.

```bash
python scripts/import_csv.py --variable no2_column_omi --region indo_gangetic_plain file.csv
python scripts/import_csv.py --variable snow_albedo_modis --region alps stats.csv \
    --date-column Date --value-column Mean
```

The reader (`infrastructure/csv_import.py`) skips metadata lines, finds the table by its
date column, turns fill values into gaps and averages daily values to months.
Options: `--date-column`, `--value-column`, `--fill-value`, `--unit`, `--source-url`.

> The Giovanni **time-series API** (`api.giovanni.earthdata.nasa.gov/timeseries`) returns
> series for a single point only, not area averages, so it is not used.

### 4.5 The cache

`data/<variable id>__<region id>.parquet`, common data format. Read by
`ParquetSeriesRepository`. Inspect a file:

```bash
python -c "import pandas as pd; print(pd.read_parquet('data/so2_column_omi__ohio_valley.parquet'))"
```

### 4.6 Checks after loading (spec 13.2)

For every new file compare with the Giovanni plot of the same box: unit, period, share of
missing values, plausible range. For one box compare the area mean with Giovanni's
*Area-Averaged Time Series* (difference below 1 %).

### 4.7 Environment variables

| Variable | Meaning | Default |
|----------|---------|---------|
| `EARTHDATA_TOKEN` | Earthdata Login token for live access and `build_cache.py` | – |
| `ETD_DATA_DIR` | folder of the data cache | `data/` |
| `ETD_CATALOG_DIR` | folder of the YAML catalog | `catalog/` |

---

## 5. Developer setup in the shell (Windows, Linux, macOS)

All commands are for **bash**. Linux and macOS have it built in (macOS Terminal uses zsh,
where the same commands work). On Windows use **Git Bash** (part of Git for Windows) or
WSL; PowerShell equivalents are listed at the end.

### 5.1 Install the prerequisites

| | Python 3.11+ | Git |
|---|---|---|
| **Linux (Debian/Ubuntu)** | `sudo apt update && sudo apt install python3 python3-venv python3-pip` | `sudo apt install git` |
| **Linux (Fedora)** | `sudo dnf install python3 python3-pip` | `sudo dnf install git` |
| **macOS** | `brew install python@3.12` ([Homebrew](https://brew.sh)) or the installer from python.org | `xcode-select --install` or `brew install git` |
| **Windows** | installer from <https://www.python.org/downloads/> – tick **"Add python.exe to PATH"** | <https://git-scm.com/download/win> (includes Git Bash) |

Check: `python3 --version` (Windows: `python --version`) must print 3.11 or higher.

### 5.2 Clone and create the environment

```bash
git clone https://github.com/bolli-colli/NASASpaceApps.git
cd NASASpaceApps

python3 -m venv .venv                 # Windows (Git Bash): python -m venv .venv
```

### 5.3 Activate the environment

| Shell | Command |
|-------|---------|
| Linux / macOS (bash, zsh) | `source .venv/bin/activate` |
| Windows, Git Bash | `source .venv/Scripts/activate` |
| Windows, PowerShell | `.venv\Scripts\Activate.ps1` |
| Windows, cmd | `.venv\Scripts\activate.bat` |

The prompt then starts with `(.venv)`. Leave with `deactivate`. Activate again in every
new terminal.

### 5.4 Install

```bash
python -m pip install --upgrade pip
pip install -e ".[dev,live]"          # quotes are required in zsh and PowerShell
```

### 5.5 Daily commands

```bash
pytest                                  # run all tests
pytest tests/test_statistics.py -k noise   # run selected tests
ruff check . && ruff format .           # lint and format

python scripts/make_synthetic_cache.py  # artificial data for UI work
ETD_DATA_DIR=data/synthetic streamlit run app.py
```

Setting variables:

```bash
export EARTHDATA_TOKEN="..."            # for the whole terminal session
ETD_DATA_DIR=data/synthetic streamlit run app.py    # for one command only
```

To keep a variable permanently, add the `export` line to `~/.bashrc` (Linux, Git Bash)
or `~/.zshrc` (macOS).

### 5.6 PowerShell equivalents

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev,live]"
$env:EARTHDATA_TOKEN = "..."
$env:ETD_DATA_DIR = "data/synthetic"; streamlit run app.py
Remove-Item Env:ETD_DATA_DIR            # unset again
```

### 5.7 Troubleshooting

| Problem | Fix |
|---------|-----|
| `python3: command not found` (Windows) | use `python`; reinstall Python with "Add to PATH" if that fails too |
| PowerShell: "running scripts is disabled" | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or use Git Bash |
| `ModuleNotFoundError: earth_trail_detective` | environment not activated, or `pip install -e .` not run |
| `zsh: no matches found: .[dev]` | put the argument in quotes: `pip install -e ".[dev]"` |
| `error: externally-managed-environment` (Linux) | you are installing outside the virtual environment – activate it first |
| Port 8501 in use | `streamlit run app.py --server.port 8502` |
| Every card says "Not in the offline cache" | fill `data/` (README section 4) or use the synthetic cache |
| Live mode is greyed out | `EARTHDATA_TOKEN` is not set in the terminal that started the app |

---

## 6. How to extend the app

| Goal | What to do |
|------|------------|
| New variable | add an entry to `catalog/variables.yaml`; if its unit is new, one line in `units._CONVERSIONS` |
| Edit an explanation | change the text in the YAML files – no code |
| New region | add it to `catalog/regions.yaml`, then fetch or import its data |
| New demo | add it to `catalog/demos.yaml` |
| Variable for an empty matrix cell | add the variable and delete the matching gap in `catalog/trail.yaml` |
| New Mann-Kendall variant | one enum value + one entry in `mann_kendall._TESTS` (+ label in `researcher_form.py`) |
| New derived quantity | new operation in `sources._OPERATIONS`, then a `derivation` entry |
| New data source | a class implementing `SeriesSource` or `LiveDataGateway`, wired in `bootstrap.py` |

---

## 7. Tests and verification

| File | Covers |
|------|--------|
| `tests/test_statistics.py` | the synthetic acceptance tests of spec 13.2: (a) known trend recovered, (b) pure noise ≈ 95 % not significant in 1000 runs, (c) Hamed-Rao reduces false alarms in autocorrelated noise, (d) deseasonalising narrows the interval; evidence table, gaps, short records, Benjamini-Hochberg, area mean |
| `tests/test_data.py` | data format round trip, unit conversions (every catalog variable convertible), Parquet cache, CSV import, grid reduction |
| `tests/test_application.py` | catalog contains the Must variables; every matrix cell is a variable or documented gap; ≥ 4 trend steps for sulfur, soot and dust; derived values; comparison rule; reference check; texts and report |
| `tests/test_app.py` | the Streamlit app end to end: demo, student form, researcher form, validation demo |

Not covered by automated tests, because they need real NASA data or a person:
the CO₂ validation on real data, the comparison of an area mean with Giovanni (< 1 %),
the 3-minute user test and the offline test with Wi-Fi switched off.

---

## 8. Deviations from the spec and open items

| Topic | Status |
|-------|--------|
| Demo data | The repository ships **no** NASA data; `data/` must be filled once with a token (section 4). |
| Live access | Implemented with earthaccess over HTTPS for MERRA-2, GLDAS, IMERG and OCO-2 GEOS. Not via the Giovanni time-series API (single points only). Written against the library documentation; **not yet run against the NASA servers**, because that needs a token. |
| Giovanni data ID in the researcher form | Not implemented, for the same reason (point series only; ID format unverified). |
| Custom bounding boxes | Only with live access; the cache holds area means of fixed regions. |
| PNG export | Via the Plotly toolbar of each chart, not a separate button. |
| Hamed-Rao | With the conservative safeguard described in 3.7. |
| Records below 10 years | Capped at *Weak* plus warning (the spec leaves this case open). |
| Demo B "Ships and clouds" | Variables are in the catalog; the region boxes come from spec v1 and are missing – see the commented block in `catalog/demos.yaml`. |
| Validation case CO₂ | Uses OCO-2 GEOS L3 (from 2015). With under 15 years it cannot reach *Strong*; product and reference value are open items of the spec. The reference range in `catalog/demos.yaml` is a placeholder marked `confirmed: false`. |
| Catalog additions | Cloud-washout variables (`BCSV`, `DUSV`, `OCSV`, `SSSV`, `SSWT`) fill matrix cells marked "model" but are not in table 10.3 – verify the names. |
| Student regions | Boxes marked `PROPOSAL` in `catalog/regions.yaml` are suggestions. |
| Not implemented | S8 ground-data comparison; C1 data access for CYGNSS (catalog entry only), C3 arrow map, C4 event analysis, C5 trend map, C7 lagged correlation, C8 AI search, C9 Docker; water vapour and cloud water for the *water* row; MOPITT CO; NLDAS streamflow. |
