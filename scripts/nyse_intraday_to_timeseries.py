import sys
import pandas as pd
import pandas_market_calendars as mcal

CHUNK_SIZE = 500000
READ_FILE = "../../tmp/tickhistoryintradaysummaries_0x087815b52678c435_axp_plus_20211201093000000_20211231160000000.csv"
MOD_FILE = "../../tmp/intraday_0x087815b52678c435.csv"
COL_LIST = [
    "#RIC",
    "Date-Time",
    "Last",
]

if len(sys.argv)>1:
    READ_FILE = sys.argv[1]
    EXTRACTION_ID = sys.argv[1][sys.argv[1].find("0x"):sys.argv[1].find("0x")+18]
    EXTRACTION_PARAM_STRING = sys.argv[1][sys.argv[1].find("0x"):len(sys.argv[1])]
    MOD_FILE = "../../tmp/intraday_timeseries_" + EXTRACTION_ID + EXTRACTION_PARAM_STRING

# Get NYSE calendar
nyse = mcal.get_calendar("NYSE")
nyse_schedule = nyse.schedule(start_date="2005-01-01", end_date="2021-12-31")

# Stream over data file
df_chunks = pd.read_csv(READ_FILE, dtype="str", chunksize=CHUNK_SIZE)
header_flag = True
last_split = {}
last_ts_row = pd.Series(dtype=object)
for chunk in df_chunks:
    # Remove the columns we don't need
    chunk = chunk[COL_LIST]

    # Add date column for calendar testing
    chunk["Date-Time"] = pd.to_datetime(chunk["Date-Time"], utc=True)
    chunk["Date"] = (
        chunk["Date-Time"]
        .dt.tz_convert("America/New_York")
        .dt.date.astype("datetime64[ns]")
    )

    # Get Date-Time min and max before cleaning
    min = str(chunk["Date-Time"].min())
    max = str(chunk["Date-Time"].max())
    total_rows = len(chunk)

    # Get numbers of records that will be removed because market was closed all day
    market_closed_count = len(
        chunk[
            ~pd.to_datetime(chunk["Date"]).isin(
                nyse_schedule.index.strftime("%Y-%m-%d").tolist()
            )
        ]
    )

    # Remove record if market was closed all day
    chunk = chunk[
        pd.to_datetime(chunk["Date"]).isin(
            nyse_schedule.index.strftime("%Y-%m-%d").tolist()
        )
    ]

    # Add market open and market close timestamps
    chunk = pd.merge(chunk, nyse_schedule, left_on="Date", right_index=True, how="left")

    # Get number of records removed that were outside market hours on a day market was open
    outside_hours_count = len(
        chunk[~chunk["Date-Time"].between(chunk["market_open"], chunk["market_close"])]
    )

    # Remove record if outside market open or close on a day market was open
    chunk = chunk[
        chunk["Date-Time"].between(chunk["market_open"], chunk["market_close"])
    ]

    # If dataframe is empty, skip to next loop iteration
    if chunk.empty:
        # Print data cleaning stats
        print(
            min,
            "to",
            max + "",
            "\n",
            total_rows,
            "total rows |",
            market_closed_count,
            "market closure rows |",
            outside_hours_count,
            "rows outside market hours |",
        )
        continue

    # Initialize/reset vars to count na values observed and filled
    na_count = chunk["Last"].isna().sum().sum()
    xcfill_count = 0

    # Forward fill last price values by RIC
    chunk_rics = chunk["#RIC"].unique()
    chunk_split = dict.fromkeys(chunk_rics, 0)
    for ric in chunk_split.keys():
        # Filter by RIC
        chunk_split[ric] = chunk.loc[chunk["#RIC"] == ric].copy()

        # If first row missing last price value, fill with previous chunk's final row
        if pd.isna(chunk_split[ric]["Last"].iloc[0]):
            if ric in last_split:
                chunk_split[ric]["Last"].iat[0] = last_split[ric]
                xcfill_count += 1

        # Forward fill last price
        chunk_split[ric]["Last"] = chunk_split[ric]["Last"].fillna(method="ffill")

        # Keep final row for next chunk
        last_split[ric] = chunk_split[ric]["Last"].iloc[-1]

    # Concatenate RIC dataframes
    chunk = pd.concat(chunk_split.values())

    # Get final na value count, calculate ffilled na values
    post_na_count = chunk.isna().sum().sum()
    ffill_na_count = na_count - xcfill_count - post_na_count

    # Print data cleaning stats
    print(
        min,
        "to",
        max,
        "\n",
        total_rows,
        "total rows |",
        market_closed_count,
        "weekend/holiday rows |",
        outside_hours_count,
        "rows outside market hours |",
        round(
            na_count * 100 / (total_rows - market_closed_count - outside_hours_count)
        ),
        "% na |",
        na_count,
        "na vals |",
        xcfill_count,
        "xcfill na vals |",
        ffill_na_count,
        "ffill na vals |",
    )

    # Remove the columns we don't need anymore
    chunk = chunk[COL_LIST]

    # Convert timezone before writing
    chunk["Date-Time"] = chunk["Date-Time"].dt.tz_convert("America/New_York")

    # Pivot dataframe to time series
    chunk = chunk.pivot(index="Date-Time", columns="#RIC", values="Last")

    # If the first pivoted row has na values, fill using last pivoted row of previous chunk
    if not last_ts_row.empty and chunk.iloc[0].isna().any():
        chunk.iloc[0].fillna(last_ts_row, inplace=True)

    # If last pivoted row has na values, remove and keep for next chunk
    if chunk.iloc[-1].isna().any():
        last_ts_row = chunk.iloc[-1]
        chunk = chunk.iloc[:-1]

    # Write chunk to csv
    chunk.to_csv(MOD_FILE, sep=",", index=True, quotechar='"', mode="a", header=header_flag)
    header_flag = False
