## LSEG Tick History

LSEG (formerly Refinitiv, Thomson Reuters) Tick History is a historical market data service, offering global intraday time and sales, quotes and market depth content dating back to January 1996. More info can be found on the [Tick History factsheet](https://www.lseg.com/content/dam/data-analytics/en_us/documents/fact-sheets/final_re2664707_ent_tick_history_factsheet_a4_v4_web.pdf).

From our LSEG Tick History subscriptions, we can pull:

- **Tick History Time & Sales:** individual trades and quotes (or more precisely, quote changes)
- **Tick History Intraday Summaries:** open/high/low/close/volume for an interval from 1s, 5s, 1m, 5m, 10m, 15m, 1h
- **Elektron Timeseries:** open/high/low/close/volume on a daily basis
- **Tick History Market Depth:** best 10 bids and best 10 asks, for NYSE-listed securities only (the other three only have the best bid/ask)

Stevens users can access [sample files and data dictionaries on OneDrive](https://stevens0.sharepoint.com/:f:/s/HanlonLab/Enb_ej_gpepAoXisg3JxCpEB5sJl38XA7AnsPXLxxldj6g?e=IGXCpS). Timestamps are [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601).

TH Times & Sales data files can be very large, TB/year for actively traded symbols, so students generally request no more than a few days of Time & Sales data. TH Market Depth data can also be quite large for actively traded symbols. We have access to a variety of other data products through Tick History (index constituents, corporate actions, etc) but the four above are used most often by researchers and students.

When we request data for a symbol from Tick History, we request it using an instrument code called a RIC. RICs can be looked up using [LSEG's RIC Search](https://developers.lseg.com/en/tools-catalog/ric-search). Students and faculty don't need to look up RICs to request data: ticker symbols and descriptive names are sufficient.

Options data is available only by chain or by individual contract. Chain data for actively traded symbols can be very large, even for summary data and particularly across longer date ranges. Contract RICs encode strike, expiry and contract type; see [the docs on OneDrive](https://stevens0.sharepoint.com/:f:/s/HanlonLab/ErceCf3dt0dJgz7J7JPTSLQBd4XLK1bhVSLZRRdlzX-iHw?e=7qTy8E) for more info.

Futures data is often pulled using a continuation (RIC root + continuation suffix + expiring contract position), which tracks the next expiring contract based on some condition:

| suffix | description | example |
| --- | --- | --- |
| c | General continuation of each record in the futures chain. Tracks the monthly contract and rolls over upon contract expiry. | Cc1 |
| cm | Tracks quarterly months only and rolls over upon contract expiration. | FVcm1 |
| cm1t | Tracks only the lead month and rolls over on the last day of the month before contract expiration. | TYcm1t |
| v | Tracks the contract month with the highest volume and rolls over on volume change. | LCOv1 |
| cv | Continuation based on volume. Rolls over to the contract with the highest volume when the existing contract expires. | NQcv1 |
| coi | Tracks the contract month with the highest open interest and rolls over on open interest change. | STXXcoi1 |

## Using the CLI

The `datascope.py` CLI simplifies Tick History data downloads from the DataScope API. Accessing data from the API is generally a two-step process:
- A user submits a request to start a data extraction, to which the server responds with an extraction ID. The extraction ID can be used to check the extraction's status and to download data files when the extraction is complete.
- Extractions can take seconds or hours to run. After the extraction is complete, a user can download it by extraction ID.

The `datascope.py` CLI has the following options:
- `new <extraction-type>`: create a new data extraction job
- `download <extraction-id>`: download a completed extraction
- `status <extraction-id>`: check the status of an extraction
- `cancel <extraction-id>`: cancel an active extraction
- `active`: get a list of all active extractions
- `query`: start a query loop against the SQLite database tracking requests

When running `python datascope.py new <extraction-type>`, the CLI will read extraction parameters from the JSON configuration file `/config/datascope.conf`; to edit parameters like date ranges or RICs, users should edit the config file directly. The `<extraction-type>` can be one of: `time`, `intraday`, `market`, or `elektron`. When downloaded, data files will be placed in the `/tmp` directory.

To install dependencies, use [uv](https://docs.astral.sh/uv/getting-started/) to create and activate a virtual environment, then run `uv sync` from the project's root.

(A group of ad hoc utility scripts are also provided for reference in `/scripts`, but they are not dependencies of the datascope CLI. The scripts may require modification to run successfully.)

Run `python datascope.py --help` for more info.