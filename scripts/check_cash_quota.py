import os
import polars as pl

# directory and file locations
HOME_DIR = os.environ.get("HOME")
TMP_DIR = f"{HOME_DIR}/code/hfsl/hfsl-data/tmp"
CASH_QUOTA_PATH = f"{TMP_DIR}/cash_quota_usage_details_20250305.csv"
CHECK_PATH = f"{TMP_DIR}/darsh_rics.csv"

OUTPUT_PATH = f"{TMP_DIR}/darsh_rics_check.csv"
INQUOTA_PATH = f"{TMP_DIR}/darsh_rics_inquota.csv"

# read CSVs to dataframes
quota = pl.read_csv(CASH_QUOTA_PATH)
rics = pl.read_csv(CHECK_PATH)

# add boolean columns based on presence in quota with: any exchange code; exact exchange code
result = rics.with_columns(
    in_quota_anyexch=pl.col("ric").str.split(by=".").list.first().is_in(quota["AuthorizedValue"].str.split(by=".").list.first().replace("", None).drop_nulls()),
    in_quota=pl.col("ric").is_in(quota["AuthorizedValue"]),
)

# write output files with: full list of RICs to check; list of RICs in quota with any exchange code
in_quota_any = pl.col("in_quota_anyexch") | pl.col("in_quota")
result.sort("in_quota", "in_quota_anyexch", "symbol", descending=[True, True, False]).write_csv(OUTPUT_PATH)
result.filter(in_quota_any).sort("in_quota", "in_quota_anyexch", "symbol", descending=[True, True, False]).write_csv(INQUOTA_PATH)

# print counts of RICs in quota, both exact and any
print(result.group_by("in_quota").len())
print(result.group_by("in_quota_anyexch").len())

# get list of RICs in quota with any exchange code
rics = result.filter(in_quota_any).select("ric").sort("ric", descending=False).to_series().to_list()

# format instrument list
rics_json = ",\n\t".join([f'{{"Identifier": "{inst}","IdentifierType": "Ric"}}' for inst in rics])
print(f"[\n\t{rics_json}\n]")

# mani = pl.read_csv(f"{TMP_DIR}/manifest_0x095181d81ebaeea3.csv")
# mres = result.filter(in_quota_any).with_columns(
#     in_mani=pl.col("ric").is_in(mani["#RIC"]),
# ).filter(~pl.col("in_mani"))
# print(mres)