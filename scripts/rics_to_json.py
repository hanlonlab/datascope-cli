import polars as pl

df = pl.read_csv("./rics_not_in_quota.csv")

df = df.with_columns(ric=pl.col("ric").str.replace(".OTC",".PK"))
df = df.with_columns(json_ric=('{"Identifier": "' + pl.col("ric") + '","IdentifierType": "Ric"}'))
df = df.filter(pl.col("ric").str.ends_with(".K") | ~pl.col("ric").str.contains(r"\."))

json_list = df.get_column("json_ric").to_list()

result = ",\n\t".join(json_list)
result = f"[\n{result}\n]"

print(result)
