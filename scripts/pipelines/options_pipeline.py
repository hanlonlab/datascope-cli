import re
import os
import sys
import glob
import polars as pl
# import holidays

def clean_col_name(col_name: str) -> str:
    col_name = re.sub(r'(?<=^L[0-9])-','_',col_name)
    col_name = re.sub(r'(?<=^L[0-9][0-9])-','_',col_name)
    col_name = re.sub(r'[#.-]','',col_name)
    col_name = re.sub(r'[/ ]','_',col_name)
    return col_name.lower()

MONTH_MAPPING = {
   "A": 1,
   "B": 2,
   "C": 3,
   "D": 4,
   "E": 5,
   "F": 6,
   "G": 7,
   "H": 8,
   "I": 9,
   "J": 10,
   "K": 11,
   "L": 12,
   "M": 1,
   "N": 2,
   "O": 3,
   "P": 4,
   "Q": 5,
   "R": 6,
   "S": 7,
   "T": 8,
   "U": 9,
   "V": 10,
   "W": 11,
   "X": 12
}

COL_LIST_THTS = [ # Tick History Time & Sales (options chain field, checked 0#AAPL*.U 0#SPY*.U)
    "#RIC",
    "Date-Time",
    "GMT Offset",
    "Type",
    "Ex/Cntrb.ID",
    "Price",
    "Volume",
    "Market VWAP",
    "Buyer ID",
    "Bid Price",
    "Bid Size",
    "Seller ID",
    "Ask Price",
    "Ask Size",
    "Qualifiers",
    "Seq. No.",
    "Exch Time",
    "UpLim Price",
    "LoLim Price",
    "Bid Imp. Vol",
    "Ask Imp. Vol",
    "Date",
    "Tick Dir.",
    "Open",
    "High",
    "Low",
    "Acc. Volume",
    "Turnover",
    "Mid Price",
    "Percentage Change",
    "Original Price",
    "Original Volume",
    "Delta",
    "Ask Market Maker Id",
    "Bid Market Maker Id",
    "Gamma",
    "Theta",
    "Unique Trade Identification",
    "LULD Indicator",
    "Net Change",
    "Original Unique Trade Identification",
    "Short Sale Restriction Indicator",
    "Trading Status",
    "Rho",
    "Vega",
]

COL_LIST_ET = [ # Elektron Timeseries (options chain fields, checked 0#AAPL*.U 0#SPY*.U)
    "Ask",
    "Bid",
    "Block Volume",
    "High",
    "Implied Volatility",
    "Instrument ID",
    "Last",
    "Low",
    "Net Asset Value",
    "Open",
    "Open Interest",
    "Reference Company",
    "RIC",
    "Trade Date",
    "Universal Ask Price",
    "Universal Bid Price",
    "Universal Close Price",
    "Volume",
    "VWAP",
]

COL_LIST_THIS = [ # Tick History Intraday Summaries (options chain fields, checked 0#AAPL*.U 0#SPY*.U)
    "#RIC",
    "Date-Time",
    "GMT Offset",
    "Open",
    "High",
    "Low",
    "Last",
    "Volume",
    "No. Trades",
    "Open Bid",
    "High Bid",
    "Low Bid",
    "Close Bid",
    "No. Bids",
    "Open Ask",
    "High Ask",
    "Low Ask",
    "Close Ask",
    "No. Asks",
    "Open Yld",
    "High Yld",
    "Low Yld",
    "Close Yld",
    "No. Ylds",
    "Open Bid Size",
    "High Bid Size",
    "Low Bid Size",
    "Close Bid Size",
    "Open Ask Size",
    "High Ask Size",
    "Low Ask Size",
    "Close Ask Size",
    "Open Mid Price",
    "High Mid Price",
    "Low Mid Price",
    "Close Mid Price",
]
SCHEMA_OVERRIDES_THIS = {
    "#RIC": pl.Utf8,
    "Date-Time": pl.Utf8,
    "GMT Offset": pl.Utf8,
    "Open": pl.Float64,
    "High": pl.Float64,
    "Low": pl.Float64,
    "Last": pl.Float64,
    "Volume": pl.Int64,
    "No. Trades": pl.Int64,
    "Open Bid": pl.Float64,
    "High Bid": pl.Float64,
    "Low Bid": pl.Float64,
    "Close Bid": pl.Float64,
    "No. Bids": pl.Int64,
    "Open Ask": pl.Float64,
    "High Ask": pl.Float64,
    "Low Ask": pl.Float64,
    "Close Ask": pl.Float64,
    "No. Asks": pl.Int64,
    "Open Yld": pl.Float64,
    "High Yld": pl.Float64,
    "Low Yld": pl.Float64,
    "Close Yld": pl.Float64,
    "No. Ylds": pl.Int64,
    "Open Bid Size": pl.Int64,
    "High Bid Size": pl.Int64,
    "Low Bid Size": pl.Int64,
    "Close Bid Size": pl.Int64,
    "Open Ask Size": pl.Int64,
    "High Ask Size": pl.Int64,
    "Low Ask Size": pl.Int64,
    "Close Ask Size": pl.Int64,
    "Open Mid Price": pl.Float64,
    "High Mid Price": pl.Float64,
    "Low Mid Price": pl.Float64,
    "Close Mid Price": pl.Float64,
}

# values for parsing (root,strike,expiry,contract_type) from RIC
OPRA_NONROOT_LEN = 10
OPRA_NONROOT_YEAR_POS = OPRA_NONROOT_LEN - 3
OPRA_NONROOT_YEAR_LEN = 2
AFTER_2000_CUTOFF = 72 # (19)72
OPRA_NONROOT_MONTH_POS = OPRA_NONROOT_LEN
OPRA_NONROOT_MONTH_LEN = 1
OPRA_NONROOT_DAY_POS = OPRA_NONROOT_LEN - 1
OPRA_NONROOT_DAY_LEN = 2
OPRA_NONROOT_STRIKE_POS = OPRA_NONROOT_LEN - 5
OPRA_NONROOT_STRIKE_LEN = 5

TMP_DIR = "/Users/warble/code/hfsl/hfsl-data/tmp"
OPTIONS_DIR = f"{TMP_DIR}/options"
MAX_PARTITION_ROWS = 32_768_000 # maximum number of rows per *{part}.parquet file within a given partition directory
# nyse_holidays = holidays.NYSE()

# get glob pattern for files to combine
if len(sys.argv) != 2:
    sys.exit(f'ERROR: requires filename pattern arg for glob, for example -> python {os.path.basename(__file__)} "./*"')

# iterate over per-month CSVs; scan and sink to partitioned parquet files
for file_path in glob.glob(sys.argv[1]):

    filename_noext = os.path.splitext(os.path.basename(file_path))[0]
    report_type = filename_noext.split("_")[0]
    if report_type == "tickhistorytimeandsales":
        file_root = filename_noext.split("_")[1][1:-2]
        col_list = COL_LIST_THTS
    elif report_type == "tickhistoryintradaysummaries":
        file_root = filename_noext.split("_")[2][1:-2]
        file_interval = filename_noext.split("_")[1]
        col_list = COL_LIST_THIS
        schema_overrides = SCHEMA_OVERRIDES_THIS
    elif report_type == "elektrontimeseries":
        file_root = filename_noext.split("_")[1][1:-2]
        col_list = COL_LIST_ET
    else:
        sys.exit("ERR: no column list found")

    file_start = filename_noext.split("_")[-2]
    file_year, file_month, file_day = file_start[:4], str(int(file_start[4:6])), str(int(file_start[6:8])) # extract year month day of file's start date; str(int()) to drop leading zeros
    
    lf = pl.scan_csv(file_path,infer_schema=True,schema_overrides=schema_overrides)
    if "GMT Offset" not in list(lf.collect_schema().keys()):
        if "GMT Offset" in col_list:
            col_list.remove("GMT Offset")
    clean_col_list = [clean_col_name(name) for name in col_list]
    rename_map = {k: v for k, v in zip(col_list, clean_col_list)}

    lf = (
        lf.select(col_list)
        .rename(rename_map)
        .filter(pl.col("ric") != file_root.upper())
        .with_columns(
            pl.col("datetime").str.to_datetime("%Y-%m-%dT%H:%M:%S%.9f%#z",time_unit='ns',).dt.convert_time_zone("America/New_York"), # TODO maybe add a time_unit='s' column as well to support Spark from_unixtime() conversions without arithmetic? or at least change column name
            # # --START-- code in this block fails on large files (300+ GB) by exceeding available RAM (256 GB); everything in this block has been converted to Spark
            # root = pl.col("ric").str.head(pl.col("ric").str.split(".").list.first().str.len_chars().sub(OPRA_NONROOT_LEN)).str.to_lowercase().alias("root"),
            # contract_type = (
            #     pl.when(pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_MONTH_POS).str.head(OPRA_NONROOT_MONTH_LEN).str.to_uppercase().is_between(pl.lit("A"),pl.lit("L")))
            #     .then(pl.lit("c")) # if the letter encoding the month is between A-L or a-l, then it's a call
            #     .otherwise(pl.lit("p")) # otherwise it's a put (and the letter is between M-X or m-x)
            # ).alias("contract_type"),
            # expiration_date = (
            #     pl.format("{}-{}-{}",(
            #         pl.when(pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_YEAR_POS).str.head(OPRA_NONROOT_YEAR_LEN).str.to_integer() <= AFTER_2000_CUTOFF)
            #         .then(pl.format("20{}",pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_YEAR_POS).str.head(OPRA_NONROOT_YEAR_LEN)))
            #         .otherwise(pl.format("19{}",pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_YEAR_POS).str.head(OPRA_NONROOT_YEAR_LEN)))
            #         ),
            #         pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_MONTH_POS).str.head(OPRA_NONROOT_MONTH_LEN).str.to_uppercase().replace_strict(MONTH_MAPPING),
            #         pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_DAY_POS).str.head(OPRA_NONROOT_DAY_LEN)
            #     )
            # ).str.to_date("%Y-%m-%d").alias("expiration_date"),
            # strike = (
            #     pl.when(pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_MONTH_POS).str.head(OPRA_NONROOT_MONTH_LEN).is_between(pl.lit("a"),pl.lit("x")))
            #     .then(pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_STRIKE_POS).str.to_decimal().truediv(10)) # if the letter encoding the expiration month is lowercase, then the strike is >= 1000 and 12345 encodes 1234.50
            #     .otherwise(pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_STRIKE_POS).str.to_decimal().truediv(100)) # otherwise the strike is < 1000 and 12345 encodes strike 123.45
            # ).cast(pl.Float32).alias("strike"),
            # days_to_expiration_trading_only = pl.business_day_count(
            #     start=pl.col("datetime").str.to_datetime("%Y-%m-%dT%H:%M:%S%.9f%#z",time_unit='ns',).dt.convert_time_zone("America/New_York").dt.date(),
            #     end=pl.format("{}-{}-{}",(
            #             pl.when(pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_YEAR_POS).str.head(OPRA_NONROOT_YEAR_LEN).str.to_integer() <= AFTER_2000_CUTOFF)
            #             .then(pl.format("20{}",pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_YEAR_POS).str.head(OPRA_NONROOT_YEAR_LEN)))
            #             .otherwise(pl.format("19{}",pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_YEAR_POS).str.head(OPRA_NONROOT_YEAR_LEN)))
            #             ),
            #             pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_MONTH_POS).str.head(OPRA_NONROOT_MONTH_LEN).str.to_uppercase().replace_strict(MONTH_MAPPING),
            #             pl.col("ric").str.split(".").list.first().str.tail(OPRA_NONROOT_DAY_POS).str.head(OPRA_NONROOT_DAY_LEN)
            #         ).str.to_date("%Y-%m-%d"),
            #     holidays=nyse_holidays
            # ).alias("days_to_expiration_trading_only"),
            # # --END-- 
        )
    )

    if report_type == "tickhistoryintradaysummaries":
        parquet_hive_dir = f"{OPTIONS_DIR}/report_type={report_type}/summary_interval={file_interval}/symbol={file_root}/year={file_year}/month={file_month}" # TODO change year month to trade_year trade_month; adds clarity when Hive dirs are read as cols in Spark dataframe
    else:
        parquet_hive_dir = f"{OPTIONS_DIR}/report_type={report_type}/symbol={file_root}/year={file_year}/month={file_month}"
    
    # print(lf.head(100).collect())
    partition = pl.PartitionMaxSize(
        parquet_hive_dir,
        max_size=MAX_PARTITION_ROWS
    )
    lf.sink_parquet(partition, mkdir=True, compression="zstd", compression_level=3) # Compression level can be changed to max of 22; these parquet files with be read by PySpark, not by Trino/BigQuery/Athena/etc
