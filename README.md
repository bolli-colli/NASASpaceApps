# Earth Trail Detective

Follow a pollutant through the water cycle – air → cloud → rain & snow → glacier → soil →
river & sea – and test every step for a trend.

Built for the NASA Space Apps Challenge 2026, challenge *"Be An Earth System Trend
Detective!"*. The specification is in [`specs/`](specs/) (English translation and German original); the technical
documentation is in [`docs/DOCUMENTATION.md`](docs/DOCUMENTATION.md).

**What it does**

- Shows NASA variables as monthly time series for one or two regions.
- Removes the seasonal cycle and computes the rate of change (Sen's slope, OLS with
  confidence interval) and its significance (Mann-Kendall with Hamed-Rao correction).
- Puts the steps of one substance next to each other (the *trail view*). Where no data
  exists, an honest card says **"Trail ends here"** and why.
- Labels every result as *Strong evidence*, *Weak evidence* or *No evidence* and always
  names the data kind (measured / model / estimate), product, version and source.
- Two modes on the same core: **Student** (guided form) and **Researcher** (expert form).

**What it is not:** no publication-grade assessment, no real-time air quality, no health
or regulatory advice, no forecast, and no statement about a single lake, field or glacier
(grid cells are 25–100 km wide).

---

## 1. Requirements

| What | Version | Check with |
|------|---------|------------|
| Python | 3.11 or newer | `python --version` (macOS/Linux often `python3 --version`) |
| Git | any recent | `git --version` |
| Internet | only for the installation and for fetching NASA data | |

Windows users: install [Git for Windows](https://git-scm.com/download/win); it includes
**Git Bash**, in which all commands below work. PowerShell variants are given where they differ.

## 2. Installation

```bash
# 1. Get the code
git clone https://github.com/bolli-colli/NASASpaceApps.git
cd NASASpaceApps

# 2. Create a virtual environment (an isolated Python just for this project)
python3 -m venv .venv            # Windows: python -m venv .venv

# 3. Activate it (repeat in every new terminal)
source .venv/bin/activate        # Linux / macOS
source .venv/Scripts/activate    # Windows, Git Bash
# .venv\Scripts\Activate.ps1     # Windows, PowerShell

# 4. Install the app with its test tools
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

`pip install -e .` installs the package in *editable* mode: changes to the code are active
immediately. The extras are optional add-ons:

| Extra | Installs | Needed for |
|-------|----------|------------|
| `.[dev]` | pytest, ruff | running the tests and the code style check |
| `.[live]` | earthaccess, harmony-py, xarray, h5netcdf, h5py | fetching data from NASA Earthdata |

Install both with `pip install -e ".[dev,live]"`.

## 3. Start the app

```bash
streamlit run app.py
```

The browser opens at <http://localhost:8501>. Stop the app with `Ctrl+C`.

The app reads its data from the offline cache in [`data/`](data/). **A fresh clone contains
no data yet** – every card then says "Not in the offline cache". You have two options:

### Option A – try the app with artificial data (2 minutes, no account)

```bash
python scripts/make_synthetic_cache.py

# Linux / macOS / Git Bash
ETD_DATA_DIR=data/synthetic streamlit run app.py
# PowerShell
$env:ETD_DATA_DIR="data/synthetic"; streamlit run app.py
```

These numbers are **random** and say nothing about the real world. The app shows a red
warning banner whenever such data is on screen. Use this only to develop and test the
interface – never in a presentation.

### Option B – fill the cache with real NASA data

See the next section.

## 4. Filling the data cache

All NASA data needs a free **Earthdata Login**.

1. Create an account at <https://urs.earthdata.nasa.gov/users/new>.
2. In your profile choose *Generate Token* and copy the token.
3. Approve the GES DISC archive once, otherwise downloads fail with an authorisation
   error even with a valid token: profile → *Applications* → *Authorized Apps* →
   *Approve More Applications* → **NASA GESDISC DATA ARCHIVE**.
4. Giovanni and AppEEARS (section 4b) need the same account: click *Login* on their
   pages before you plot or download.
5. Put the token into a `.env` file – never write it into the code and never commit it
   (`.env` is ignored by git):

   ```bash
   cp .env.example .env          # PowerShell: Copy-Item .env.example .env
   # then open .env and fill in: EARTHDATA_TOKEN=paste-your-token-here
   ```

   The app and all scripts read `.env` on start. Alternatives: an environment variable
   (`export EARTHDATA_TOKEN="..."`, PowerShell `$env:EARTHDATA_TOKEN="..."`), which wins
   over `.env`, or `.streamlit/secrets.toml` (copy `.streamlit/secrets.toml.example`),
   which is used only if neither of the other two is set.

### 4a. Scripted: MERRA-2, GLDAS, IMERG, OMI and OCO-2 GEOS

```bash
pip install -e ".[live]"
python scripts/build_cache.py                                           # everything
python scripts/build_cache.py --demo A1 --start 2020-01 --end 2020-12   # a quick trial
```

The script fetches every product of the chosen demos, averages each region with
cos(latitude) weights and writes one Parquet file per variable and region to `data/`.
Options: `--demo` (A1, A2, V; repeatable; default all), `--start` / `--end` (`YYYY-MM`;
default: the full record of each product), `--refresh` (reload what is already cached).

Two NASA services are used, chosen per product in the catalog (`access.provider`):

- **Harmony** for MERRA-2, GLDAS, IMERG and the daily OMI products (SO₂, NO₂, aerosol
  index): NASA's servers cut the region box out of every file, the script downloads the
  small results and averages them. One job per region and year.
- **earthaccess** for OCO-2 GEOS, which Harmony does not serve: one whole file per month
  is read over the network (about a minute per file).

A full run takes a few hours, mostly for the daily OMI files – **start with the quick
trial** to see that your token and approvals work. Every product is saved as soon as it is
complete and cached series are skipped, so an interrupted run can simply be started again.

### 4b. By hand: MODIS, AIRS, CYGNSS (and OMI as a fallback)

These products have no scripted access, so they are exported once by hand. The same way
works for OMI if the Harmony route fails:

1. Open [Giovanni](https://giovanni.gsfc.nasa.gov/giovanni/), choose the plot
   *Time Series, Area-Averaged*, the variable, the bounding box of the region
   (see [`catalog/regions.yaml`](catalog/regions.yaml)) and the period.
2. Download the result as CSV into `data/raw/` (ignored by git).
3. Import it:

   ```bash
   python scripts/import_csv.py --variable so2_column_omi --region ohio_valley data/raw/download.csv
   ```

For MODIS snow albedo use an [AppEEARS](https://appeears.earthdatacloud.nasa.gov/) area
request and import its statistics file:

```bash
python scripts/import_csv.py --variable snow_albedo_modis --region alps stats.csv \
    --date-column Date --value-column Mean
```

The script prints unit, period, share of missing months and value range – compare them
with the Giovanni plot of the same box before you trust the file.

Variable ids are listed in [`catalog/variables.yaml`](catalog/variables.yaml), region ids
in [`catalog/regions.yaml`](catalog/regions.yaml).

## 5. Using the app

- **Prepared demos** (sidebar): pick a demo, a substance and the regions, press *Run demo*.
- **Student mode**: answer four questions – what, where, which part of the journey, which
  period – and press *Follow the trail*.
- **Researcher mode**: choose any catalog variables, one or two regions, the period, the
  climatology period and the statistics options. With an Earthdata token, data can also
  be fetched live, including custom bounding boxes.
- **Export**: CSV and methods report via the buttons below the results; PNG via the
  camera button in the toolbar of each chart.

## 6. Tests and code style

```bash
pytest              # all tests (about one minute)
ruff check .        # code style and common mistakes
ruff format .       # automatic formatting
```

## 7. Project layout

```
app.py                      start script for Streamlit
catalog/                    variables, substances, regions, trail gaps, demos (YAML)
data/                       offline cache (Parquet), one file per variable and region
docs/DOCUMENTATION.md       libraries, concepts, data access, developer setup
scripts/                    build_cache.py, import_csv.py, make_synthetic_cache.py
specs/                      specification (English translation, German original)
src/earth_trail_detective/
    domain/                 entities, statistics, units – pure logic, no I/O
    application/            use cases and ports (interfaces)
    infrastructure/         YAML, Parquet, CSV and NASA Earthdata adapters
    presentation/           Streamlit user interface
tests/                      pytest suite
```

## 8. Data sources

| Source | Products used | Access |
|--------|---------------|--------|
| [NASA GES DISC](https://disc.gsfc.nasa.gov/) | MERRA-2 (M2TMNXAER, M2TMNXADG, M2TMNXFLX, M2TMNXGLC), GLDAS Noah 2.1, GPM IMERG, OMI (OMSO2e, OMNO2d, OMAERUVd), AIRS, OCO-2 GEOS | Earthdata Login |
| [NSIDC](https://nsidc.org/data/mod10a1/versions/61) via AppEEARS | MODIS MOD10A1 snow albedo | Earthdata Login |
| [LAADS DAAC](https://ladsweb.modaps.eosdis.nasa.gov/) | MODIS MOD08_M3 cloud properties | Earthdata Login |
| [PO.DAAC](https://podaac.jpl.nasa.gov/dataset/CYGNSS_L3_MICROPLASTIC_V3.2) | CYGNSS microplastics | Earthdata Login |

Each variable cites its product page in `catalog/variables.yaml` and on its card. NASA
data is free and open; please cite the data sets as requested on their product pages.
Key reference for the aerosol model: Randles et al. (2017), *The MERRA-2 Aerosol
Reanalysis*, <https://doi.org/10.1175/JCLI-D-16-0609.1>.

## 9. Limits

- **Model, not measurement:** most cloud, deposition and glacier steps come from the
  MERRA-2 and GLDAS models. Every card says so.
- **Emission inventories** in MERRA-2 may be outdated for recent years; cross-check with
  measured OMI data.
- **Resolution:** glaciers and rivers are smaller than the grid cells.
- **Sensor drift and gaps:** MODIS orbit drift, OMI row anomaly, GLDAS version change.
- **Statistics:** trends are linear and tested per step and region. Steps shown side by
  side are not causally linked. *Correlation is not causation.*
- **Short records** (below 10 years) give unreliable tests; the app warns.

## 10. Licence

[Apache License 2.0](LICENSE).
