import os
import sys
import pandas as pd
import polars as pl

TMP_DIR = "."

# if an argument is passed to the script use that as the filename to read; otherwise, use the string var
read_file = f"{TMP_DIR}/tickhistoryintradaysummaries_0x096966108b2b1b2c_-vix_20230101000000000000000_20231231235959999999999.csv"
if len(sys.argv)>1:
    read_file = sys.argv[1]
    #extraction_id = sys.argv[1][sys.argv[1].find("0x"):sys.argv[1].find("0x")+18]

stats_file = f"{TMP_DIR}/{os.path.splitext(os.path.basename(read_file))[0]}_stats.csv"

# drop columns from large file using polars
lf = pl.scan_csv(read_file)
cols = lf.collect_schema().names()

nonnull = lf.select(pl.count(cols)).collect()
n_unique = lf.select(pl.n_unique(cols)).collect()
describe = lf.describe()

pl.concat([nonnull,n_unique]).write_csv(stats_file)
print(stats_file)

