import polars as pl
import json

status_output_msg = "err.txt"
conf_path = "/path/to/hfsl-data/datascope/config/datascope.conf"
report_type = "time_and_sales"

with open(status_output_msg, "r") as f:
    lines = f.readlines()

# get RICs included in status output, whether or not they expanded
included_rics = []
for line in lines:
    if line.lstrip().startswith("Total instruments after instrument expansion"):
        print(line.lstrip())
    if line.lstrip().startswith("Historical Instrument <RIC,") or line.lstrip().startswith("Instrument <RIC,"):
        included_rics.append(line.split(",")[1].split(">")[0])

# get RICs that did not expand or are inactive
errors = [line.rstrip() for line in lines if line.rstrip().endswith("expanded to 0 RICS.") or line.rstrip().endswith("Inactive,0")]
print(f"{len(errors)} rics not expanded or inactive:")
for err in errors:
    print(err.lstrip())
print()

# get input list of RICs, filter for what wasn't included in status output ("discrepancies")
with open(conf_path, "r") as f:
    dsconf = json.load(f)
input_list = [inst["Identifier"] for inst in dsconf[report_type]["instruments"]]
discrepancies = [ric for ric in input_list if ric not in included_rics ]
print(f"{len(discrepancies)} rics in input list not included:")
for disc in discrepancies:
    print(disc)
print()

# combine discrepancies and errors; print full info for all
for err in errors:
    discrepancies.append(err.split(",")[1].split(">")[0])
print(f"summary of {len(discrepancies)} errors and rics that weren't included:")
df = pl.read_csv("./darsh_rics.csv")
df = df.filter(pl.col("ric").str.replace(".OTC",".PK").is_in(input_list))
df = df.filter(pl.col("ric").str.replace(".OTC",".PK").is_in(discrepancies))
disc_rics = df.get_column("ric").to_list()
disc_names = df.get_column("name").to_list()
for i in range(len(disc_rics)):
    print(disc_rics[i],disc_names[i])

# write all not included RICs as datascope-config-suitable JSON
disc_rics.sort()
with open(f"{report_type}_missing_rics.json", "w") as f:
    f.write("[\n")
    for idx, ric in enumerate(disc_rics):
        f.write('\t{"Identifier": "' + ric + '","IdentifierType": "Ric"}')
        if idx == len(disc_rics)-1:
            f.write("\n]\n")
        else:
            f.write(",\n")
