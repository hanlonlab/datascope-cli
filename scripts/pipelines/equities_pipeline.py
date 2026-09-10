import re
import os
import sys
import glob
import polars as pl
    
def clean_col_name(col_name: str) -> str:
    col_name = re.sub(r'(?<=^L[0-9])-','_',col_name)
    col_name = re.sub(r'(?<=^L[0-9][0-9])-','_',col_name)
    col_name = re.sub(r'[#.-]','',col_name)
    col_name = re.sub(r'[/ ]','_',col_name)
    return col_name.lower()

COL_LIST_THTS = [ # Tick History Time & Sales (equity fields, checked AAPL.O SPY)
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
    "Ask Market Maker Id",
    "Bid Market Maker Id",
    "Unique Trade Identification",
    "LULD Indicator",
    "Net Change",
    "Short Sale Restriction Indicator",
]

COL_LIST_ET = [ # Elektron Timeseries (equity fields, checked AAPL.O SPY)
    "Ask",
    "Bid",
    "Block Volume",
    "High",
    "Last",
    "Low",
    "Number of Price Moves",
    "Open", 
    "RIC",
    "Trade Date",
    "Turnover",
    "Universal Ask Price",
    "Universal Bid Price",
    "Universal Close Price",
    "Volume",
    "VWAP",
    "VWAP Volume",
]

COL_LIST_THIS = [ # Tick History Intraday Summaries (equity fields, checked AAPL.O SPY)
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

COL_LIST_THMD = [ # Tick History Market Depth (equity fields, checked SPY JPM)
    "#RIC",
    "Date-Time",
    "GMT Offset",
    "L1-BidPrice",
    "L1-BidSize",
    "L1-AskPrice",
    "L1-AskSize",
    "L2-BidPrice",
    "L2-BidSize",
    "L2-AskPrice",
    "L2-AskSize",
    "L3-BidPrice",
    "L3-BidSize",
    "L3-AskPrice",
    "L3-AskSize",
    "L4-BidPrice",
    "L4-BidSize",
    "L4-AskPrice",
    "L4-AskSize",
    "L5-BidPrice",
    "L5-BidSize",
    "L5-AskPrice",
    "L5-AskSize",
    "L6-BidPrice",
    "L6-BidSize",
    "L6-AskPrice",
    "L6-AskSize",
    "L7-BidPrice",
    "L7-BidSize",
    "L7-AskPrice",
    "L7-AskSize",
    "L8-BidPrice",
    "L8-BidSize",
    "L8-AskPrice",
    "L8-AskSize",
    "L9-BidPrice",
    "L9-BidSize",
    "L9-AskPrice",
    "L9-AskSize",
    "L10-BidPrice",
    "L10-BidSize",
    "L10-AskPrice",
    "L10-AskSize",
]

TMP_DIR = "/Users/warble/code/hfsl/hfsl-data/tmp"
EQUITIES_DIR = f"{TMP_DIR}/equities"
MAX_PARTITION_ROWS = 32_768_000 # maximum number of rows per *{part}.parquet file within a given partition directory

# get glob pattern for files to combine
if len(sys.argv) != 2:
    sys.exit(f'ERROR: requires filename pattern arg for glob, for example -> python {os.path.basename(__file__)} "./*"')

# iterate over per-month CSVs; scan and sink to partitioned parquet files
for file_path in glob.glob(sys.argv[1]):

    filename_noext = os.path.splitext(os.path.basename(file_path))[0]
    report_type = filename_noext.split("_")[0]
    if report_type == "tickhistorytimeandsales":
        file_symbol = filename_noext.split("_")[1].split("-")[0]
        col_list = COL_LIST_THTS
    elif report_type == "tickhistoryintradaysummaries":
        file_symbol = filename_noext.split("_")[2].split("-")[0]
        file_interval = filename_noext.split("_")[1]
        col_list = COL_LIST_THIS
        schema_overrides = SCHEMA_OVERRIDES_THIS
    elif report_type == "elektrontimeseries":
        file_symbol = filename_noext.split("_")[1].split("-")[0]
        col_list = COL_LIST_ET
    else:
        sys.exit("ERR: no column list found")

    lf = pl.scan_csv(file_path,infer_schema=True,schema_overrides=schema_overrides)
    if "GMT Offset" not in list(lf.collect_schema().keys()):
        if "GMT Offset" in col_list:
            col_list.remove("GMT Offset")
    clean_col_list = [clean_col_name(name) for name in col_list]
    rename_map = {k: v for k, v in zip(col_list, clean_col_list)}

    lf = (
        lf.select(col_list)
        .rename(rename_map)
        .with_columns(
            pl.col("datetime").str.to_datetime("%Y-%m-%dT%H:%M:%S%.9f%#z",time_unit='ns',).dt.convert_time_zone("America/New_York"), # TODO maybe add a time_unit='s' column as well to support Spark from_unixtime() conversions without arithmetic? or at least change column name
        )
    )

    if report_type == "tickhistoryintradaysummaries":
        parquet_hive_dir = f"{EQUITIES_DIR}/report_type={report_type}/summary_interval={file_interval}/symbol={file_symbol}"
    else:
        parquet_hive_dir = f"{EQUITIES_DIR}/report_type={report_type}/symbol={file_symbol}"
    
    # print(lf.head(100).collect())
    partition = pl.PartitionMaxSize(
        parquet_hive_dir,
        max_size=MAX_PARTITION_ROWS
    )
    lf.sink_parquet(partition, mkdir=True, compression="zstd", compression_level=3)

