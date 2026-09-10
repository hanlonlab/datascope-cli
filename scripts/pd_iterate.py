import pandas as pd

CHUNK_SIZE = 500000

# change the two paths below for your OS and filesystem
READ_FILE = "/path/to/data.csv" 
FILTERED_FILE = "/path/to/filtered_data.csv"

# iterate over a large CSV file in chunks
df_chunks = pd.read_csv(READ_FILE, dtype="str", chunksize=CHUNK_SIZE)
header_flag = True
for chunk in df_chunks:
    # print ten rows of dataframe chunk
    chunk.head(10)

    #do things to dataframe chunk here

    # append modified chunk to file on disk
    chunk.to_csv(
        FILTERED_FILE, sep=",", index=False, quotechar='"', mode="a", header=header_flag
    )
    header_flag = False
