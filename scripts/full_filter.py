import os
import sys
import glob
import polars as pl

COL_LIST_THTS = [ # Tick History Time & Sales
    "#RIC",
    "Date-Time",
    "GMT Offset",
    "Type",
    "Ex/Cntrb.ID",
    "Price",
    "Volume",
    "Buyer ID",
    "Bid Price",
    "Bid Size",
    "Seller ID",
    "Ask Price",
    "Ask Size",
    "Seq. No.",
    "Exch Time",
    "PE Ratio",
    "UpLim Price",
    "LoLim Price",
    "Tick Dir.",
    "Open",
    "High",
    "Low",
    "Acc. Volume",
    "Turnover",
    "Percentage Change",
    "Ask Market Maker Id",
    "Bid Market Maker Id",
    "Unique Trade Identification",
    "LULD Indicator",
    "Net Change",
    "Short Sale Restriction Indicator",
    "Trading Status",
]
LIMITS = (0,12+1) # we want to drop all fields after Ask Size
COL_LIST_THTS = COL_LIST_THTS[slice(*LIMITS)]

COL_LIST_ET = [ # Elektron Timeseries
    "Ask",
    "Bid",
    "High",
    "Implied Volatility",
    "Last",
    "Low",
    "Open",
    "Open Interest",
    "Reference Company",
    "RIC",
    "Trade Date",
    "Universal Ask Price",
    "Universal Bid Price",
    "Universal Close Price",
    "Volume",
]

COL_LIST_THIS = [ # Tick History Intraday Summaries
    "#RIC",
    "Date-Time",
    "GMT Offset",
    "Open",
    "High",
    "Low",
    "Last",
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
    "No. Asks"
]

COL_LIST_THMD = [
    "#RIC",
    "Date-Time",
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

CHUNK_SIZE = 500000 # num rows per dataframe chunk
TMP_DIR = "."

## if an argument is passed to the script use that as the filename to read; otherwise, use the string var
#read_file = f"{TMP_DIR}/tickhistoryintradaysummaries_0x096966108b2b1b2c_-vix_20230101000000000000000_20231231235959999999999.csv"
#if len(sys.argv)>1:
#    read_file = sys.argv[1]
#    #extraction_id = sys.argv[1][sys.argv[1].find("0x"):sys.argv[1].find("0x")+18]

if len(sys.argv) != 2:
    sys.exit(f'ERROR: requires filename pattern arg for glob, for example -> python {os.path.basename(__file__)} "./*" or python {os.path.basename(__file__)} /path/to/data.csv')

for read_file in glob.glob(sys.argv[1]):
    # set the filename for the modified file
    mod_file= f"{TMP_DIR}/{os.path.splitext(os.path.basename(read_file))[0]}_filtered.csv"

    # set column list
    report_type = os.path.basename(read_file).split("_")[0]
    if report_type == "tickhistorytimeandsales":
        col_list = COL_LIST_THTS
    elif report_type == "tickhistoryintradaysummaries":
        col_list = COL_LIST_THIS
    elif report_type == "tickhistorymarketdepth":
        col_list = COL_LIST_THMD
    elif report_type == "elektrontimeseries":
        col_list = COL_LIST_ET
    else:
        sys.exit("ERR: no column list found")

    # drop columns from large file using polars
    lf = pl.scan_csv(read_file,schema_overrides={"Volume": pl.Float64})
    removals = ["GMT Offset"]
    for c in removals:
        if c not in list(lf.collect_schema().keys()) and c in col_list:
            col_list.remove(c)
    #lf = lf.filter(~pl.all_horizontal(pl.col(*col_list[2:]).is_null())) #drop if null in certain cols
    lf.select(col_list).sink_csv(mod_file)

