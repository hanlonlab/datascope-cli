import polars as pl
import pandas as pd

OPRA_NONROOT_LEN = 10
ORD_UPPERCASE_ADJ_CALLS = 64
ORD_UPPERCASE_ADJ_PUTS = 76

def parse_underlying(opra_ric: str) -> str: 
    null_record = None
    if pd.isnull(opra_ric):
        return null_record 

    try:
        ric, exchange_code = tuple(opra_ric.split("."))
    except Exception as e:
        print(opra_ric, e)
        return null_record

    if exchange_code not in ["U"]:
        return null_record

    root_len = len(ric) - OPRA_NONROOT_LEN
    root = ric[:root_len]

    return root 

def parse_contract_type(opra_ric: str) -> str:
    null_record = None 
    if pd.isnull(opra_ric):
        return null_record 

    try:
        ric, exchange_code = tuple(opra_ric.split("."))
    except Exception as e:
        print(opra_ric, e)
        return null_record

    if exchange_code not in ["U"]:
        return null_record
    
    raw_expiry_month_put_or_call = ric[-10:-9]

    if ord(raw_expiry_month_put_or_call.upper()) <= (12 + ORD_UPPERCASE_ADJ_CALLS):
        contract_type = "call"
    else:
        contract_type = "put"

    return contract_type

def parse_expiry(opra_ric: str) -> str:
    null_record = None 
    if pd.isnull(opra_ric):
        return null_record 
    try:
        ric, exchange_code = tuple(opra_ric.split("."))
    except Exception as e:
        print(opra_ric, e)
        return null_record
    
    expiry_day = ric[-9:-7]
    raw_expiry_year = ric[-7:-5]
    if int(raw_expiry_year) <= 72:
        expiry_year = "20"+raw_expiry_year
    else:
        expiry_year = "19"+raw_expiry_year
    
    raw_expiry_month_put_or_call = ric[-10:-9]

    if ord(raw_expiry_month_put_or_call.upper()) <= (12 + ORD_UPPERCASE_ADJ_CALLS):
        expiry_month = str(ord(raw_expiry_month_put_or_call.upper()) - ORD_UPPERCASE_ADJ_CALLS).zfill(2)
    else:
        expiry_month = str(ord(raw_expiry_month_put_or_call.upper()) - ORD_UPPERCASE_ADJ_PUTS).zfill(2)

    expiry = f"{expiry_year}-{expiry_month}-{expiry_day}"

    return expiry

def parse_strike(opra_ric: str) -> float:
    null_record = None
    if pd.isnull(opra_ric):
        return null_record 
    try:
        ric, exchange_code = tuple(opra_ric.split("."))
    except Exception as e:
        print(opra_ric, e)
        return null_record
    
    raw_expiry_month_put_or_call = ric[-10:-9]
    strike_ge_1000 = raw_expiry_month_put_or_call.islower()
    if strike_ge_1000:
        strike = float(ric[-5:]) / 10
    else:
        strike = float(ric[-5:]) / 100

    return strike

target_in = "./test.csv"
target_out = "./test_filtered.csv"
target_batched_out = "./test_batched_filtered.csv"

header_flag = True
reader = pl.read_csv_batched(target_in, batch_size=10000)
batches = reader.next_batches(1)
while batches:
    df = (
        pl.concat(batches)
        .filter(pl.col("#RIC") != "SPY")
        .with_columns(
            trade_date = pl.col("Date-Time").str.to_datetime("%Y-%m-%dT%H:%M:%S%.9f%#z").dt.date(),
            root = pl.col("#RIC").map_elements(parse_underlying,return_dtype=pl.Utf8),
            expiry = pl.col("#RIC").map_elements(parse_expiry,return_dtype=pl.Utf8).str.to_date("%Y-%m-%d"),
            contract_type = pl.col("#RIC").map_elements(parse_contract_type,return_dtype=pl.Utf8),
            strike = pl.col("#RIC").map_elements(parse_strike,return_dtype=pl.Float64),
            )
        .filter(pl.col("contract_type") == "call")
        .filter((pl.col("strike") > 395.00) & (pl.col("strike") <= 405.00))
        .with_columns(
            dte = pl.business_day_count(pl.col("trade_date"),pl.col("expiry")),
            )
        .filter((pl.col("dte") >= 0) & (pl.col("dte") <= 3))
        #.filter(~pl.all_horizontal(pl.col("Open","High","Low","Last","Volume","No. Trades").is_null()))
        .select(["#RIC", "Date-Time", "root", "strike", "expiry", "contract_type", "dte", "Open", "High", "Low", "Last", "Volume", "No. Trades", ])
    )

    if header_flag:
        header_flag = False
        df.write_csv(target_batched_out, include_header=True)
    else:
        with open(target_batched_out,"a") as f:
            df.write_csv(f, include_header=False)

    batches = reader.next_batches(1) 
