import sys
import pandas as pd


READ_FILE = "../../tmp/tickhistoryintradaysummaries_0x08968b72701903d1_0spy-u_plus_by_ric_20230601000000000_20230630235959999.csv"
MOD_FILE = "../../tmp/intraday_0x08968b72701903d1_0spy-u_plus_by_ric_20230601000000000_20230630235959999.csv"

INITIAL_COL_LIST = [
    "#RIC",
    "Last",
    "Date-Time",
]
WRITE_COL_LIST = [
    "#RIC",
    "Root",
    "Strike",
    "Expiry",
    "Type",
    "Date",
    "Last",
]

CHUNK_SIZE = 500000

OPRA_NONROOT_LEN = 10
ORD_UPPERCASE_ADJ_CALLS = 64
ORD_UPPERCASE_ADJ_PUTS = 76


# return root,strike,expiry,type - eg. MSFT,157.70,2020-01-17,call
def parse_opra_ric(opra_ric: str) -> tuple[str, float, str, str]:
    # skip null values - but, why are any of these null?
    if pd.isnull(opra_ric):
        return (None,None,None,None)

    try:
        ric, exchange_code = tuple(opra_ric.split("."))
    except Exception:
        print(opra_ric)
        return(None,None,None,None)

    if exchange_code not in ["U"]:
        return (None,None,None,None)

    root_len = len(ric) - OPRA_NONROOT_LEN
    root = ric[:root_len]

    expiry_day = ric[-9:-7]
    raw_expiry_year = ric[-7:-5]
    if int(raw_expiry_year) <= 72:
        expiry_year = "20"+raw_expiry_year
    else:
        expiry_year = "19"+raw_expiry_year
    
    raw_expiry_month_put_or_call = ric[-10:-9]
    strike_ge_1000 = raw_expiry_month_put_or_call.islower()

    if ord(raw_expiry_month_put_or_call.upper()) <= (12 + ORD_UPPERCASE_ADJ_CALLS):
        contract_type = "call"
        expiry_month = str(ord(raw_expiry_month_put_or_call.upper()) - ORD_UPPERCASE_ADJ_CALLS).zfill(2)
    else:
        contract_type = "put"
        expiry_month = str(ord(raw_expiry_month_put_or_call.upper()) - ORD_UPPERCASE_ADJ_PUTS).zfill(2)

    expiry = f"{expiry_year}-{expiry_month}-{expiry_day}"

    if strike_ge_1000:
        strike = float(ric[-5:]) / 10
    else:
        strike = float(ric[-5:]) / 100

    return (root, strike, expiry, contract_type)


if __name__=="__main__":

    if len(sys.argv) > 1:
        READ_FILE = sys.argv[1]
        EXTRACTION_ID = sys.argv[1][sys.argv[1].find("0x") : sys.argv[1].find("0x") + 18]
        EXTRACTION_PARAM_STRING = sys.argv[1][sys.argv[1].find("0x") : len(sys.argv[1])]
        MOD_FILE = "../../tmp/intraday_" + EXTRACTION_ID + EXTRACTION_PARAM_STRING

    # Stream over data file
    df_chunks = pd.read_csv(READ_FILE, dtype="str", chunksize=CHUNK_SIZE)
    header_flag = True
    last_write_df = pd.DataFrame()
    for chunk in df_chunks:
        # Remove the columns we don't need
        chunk = chunk[INITIAL_COL_LIST]

        # Add date column, convert timezones
        chunk["Date-Time"] = pd.to_datetime(chunk["Date-Time"], utc=True)
        chunk["Date"] = (
            chunk["Date-Time"]
            .dt.tz_convert("America/Chicago")
            .dt.date.astype("datetime64[ns]")
        )
        chunk["Date-Time"] = chunk["Date-Time"].dt.tz_convert("America/Chicago")

        # Get unique RICs and Dates for chunk
        chunk_rics = pd.unique(chunk["#RIC"])
        chunk_dates = pd.unique(chunk["Date"])

        # Iterate over RICs and Dates, writing latest Last value to CSV file
        for ric in chunk_rics:
            for date in chunk_dates:
                subchunk = chunk[
                    (chunk["#RIC"] == ric)
                    & (chunk["Date"] == date)
                    & (chunk["Last"].notnull())
                ]

                if (
                    subchunk.empty
                    and (not last_write_df.empty)
                    and (ric == last_write_df["#RIC"].iloc[-1])
                    and (date == last_write_df["Date"].iloc[-1])
                ):
                    last_write_df[["Root", "Strike", "Expiry", "Type"]] = last_write_df.apply(
                        lambda row: pd.Series(parse_opra_ric(row["#RIC"])), axis=1
                    )
                    last_write_df = last_write_df[WRITE_COL_LIST]
                    last_write_df.to_csv(
                        MOD_FILE,
                        sep=",",
                        index=False,
                        quotechar='"',
                        mode="a",
                        header=header_flag,
                    )
                    last_write_df = pd.DataFrame()
                    header_flag = False
                elif subchunk.empty:
                    subchunk = chunk[(chunk["#RIC"] == ric) & (chunk["Date"] == date)]
                    subchunk = subchunk[
                        subchunk["Date-Time"] == subchunk["Date-Time"].max()
                    ]
                    subchunk[["Root", "Strike", "Expiry", "Type"]] = subchunk.apply(
                        lambda row: pd.Series(parse_opra_ric(row["#RIC"])), axis=1
                    )
                    subchunk = subchunk[WRITE_COL_LIST]
                    subchunk.to_csv(
                        MOD_FILE,
                        sep=",",
                        index=False,
                        quotechar='"',
                        mode="a",
                        header=header_flag,
                    )
                    header_flag = False
                else:
                    subchunk = subchunk[
                        subchunk["Date-Time"] == subchunk["Date-Time"].max()
                    ]
                    subchunk[["Root", "Strike", "Expiry", "Type"]] = subchunk.apply(
                        lambda row: pd.Series(parse_opra_ric(row["#RIC"])), axis=1
                    )
                    subchunk = subchunk[WRITE_COL_LIST]
                    subchunk.to_csv(
                        MOD_FILE,
                        sep=",",
                        index=False,
                        quotechar='"',
                        mode="a",
                        header=header_flag,
                    )
                    header_flag = False

        last_write_df = subchunk
