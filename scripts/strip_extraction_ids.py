import glob
import sys
import os
import re

if len(sys.argv) != 2:
    sys.exit(f'ERROR: requires filename pattern arg for glob, for example -> python {os.path.basename(__file__)} "./*"')

extraction_id_pattern = "_0x[0-9a-f]{16}"
files = glob.glob(sys.argv[1])
for file in files:
    file_clean = re.sub(extraction_id_pattern,'',file)
    if file != file_clean:
        #print(file,file_clean)
        os.rename(file,file_clean)
