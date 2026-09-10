import sys
import pandas as pd

CHUNK_SIZE = 500000
READ_FILE = "./tickhistorytimeandsales_0x095915ec437afd9f_nvda-oq_20250303000000000000000_20250303235959999999999.csv"
MOD_FILE = "./tickhistorytimeandsales_0x095915ec437afd9f_nvda-oq_20250303000000000000000_20250303235959999999999_filtered.csv"
COL_LIST = [
    "#RIC",
    "Domain",
    "Date-Time",
    #"GMT Offset",
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
]

# Drop columns from large file using pandas
df_chunks = pd.read_csv(READ_FILE, dtype="str", chunksize=CHUNK_SIZE)
header_flag = True
for chunk in df_chunks:
    chunk.to_csv(
        MOD_FILE, columns=COL_LIST, sep=",", index=False, quotechar='"', mode="a", header=header_flag
    )
    header_flag = False
