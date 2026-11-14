# Offline data cache

One Parquet file per variable and region: `<variable id>__<region id>.parquet`.

Every file follows the common data format (spec 10.4) with the columns

`date, value, unit, variable, product, version, region, substance, step, kind, source_url`

- `date` is the first day of the month; months without data hold an empty value.
- `kind` is `measured`, `model` or `estimate`.

How to fill this folder is described in the main [README](../README.md#4-filling-the-data-cache).

`synthetic/` (ignored by git) holds artificial development data created by
`scripts/make_synthetic_cache.py`. It must never be copied into this folder.
