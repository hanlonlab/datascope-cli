import os
import time
import json
import calendar
from datetime import datetime, timezone
import pytz

import sys
sys.path.append("..")
import datascope

# filesystem locations
HOME_DIR = os.environ.get("HOME")
DATASCOPE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INIT_CONFIG_PATH = f"{DATASCOPE_DIR}/config/datascope.conf"

SECS_PER_MIN = 60
RIC_LIMIT = 30000
MAX_DOWNLOAD_RETRIES = 3

REPORT_TYPE, REPORT_TYPE_FULL = ("elektron","elektron") # ("time","time_and_sales") ("intraday","intraday_summaries") ("market","market_depth") ("elektron","elektron")

MODE = "YEAR" # MONTH YEAR FULL
QUEUE_LIMIT = 24
MINS_TO_SLEEP = 3
START_DATE = "2010-01-01"
END_DATE = "2024-12-31"
SUMMARY_INTERVAL = "OneSecond" # OneSecond FiveSeconds OneMinute FiveMinutes TenMinutes FifteenMinutes OneHour
DATE_RANGE_TIME_ZONE = "UTC" # Local Exchange Time Zone || UTC
MESSAGE_TIME_STAMP_IN = "GmtUtc" # LocalExchangeTime GmtUtc 

START_YEAR = datetime.strptime(START_DATE, '%Y-%m-%d').date().year
START_MONTH = datetime.strptime(START_DATE, '%Y-%m-%d').date().month
END_YEAR = datetime.strptime(END_DATE, '%Y-%m-%d').date().year
END_MONTH = datetime.strptime(END_DATE, '%Y-%m-%d').date().month

INSTRUMENT_LIST = [
    {"Identifier": "0#SPX*.U","IdentifierType": "ChainRIC"},
    #{"Identifier": "0#AAPL*.U","IdentifierType": "ChainRIC"},
    # {"Identifier": "0#FB*.U","IdentifierType": "ChainRIC"},
    # {"Identifier": "0#GOOG*.U","IdentifierType": "ChainRIC"},
    # {"Identifier": ".SPX","IdentifierType": "Ric"},
    # {"Identifier": ".INX","IdentifierType": "Ric"},
    # {"Identifier": ".DJI","IdentifierType": "Ric"},
    # {"Identifier": ".NDX","IdentifierType": "Ric"},
    # {"Identifier": "SPY","IdentifierType": "Ric"},
    # {"Identifier": "QQQ","IdentifierType": "Ric"},
    # {"Identifier": "DIA","IdentifierType": "Ric"},
    # {"Identifier": "JPM","IdentifierType": "Ric"},
    # {"Identifier": "BAC","IdentifierType": "Ric"},
    # {"Identifier": "C","IdentifierType": "Ric"},
    # {"Identifier": "FB.O","IdentifierType": "Ric"},
    # {"Identifier": "META.O","IdentifierType": "Ric"},
    # {"Identifier": "GOOGL.O","IdentifierType": "Ric"},
    # {"Identifier": "GOOG.O","IdentifierType": "Ric"},
    # {"Identifier": "AMZN.O","IdentifierType": "Ric"},
    # {"Identifier": "NFLX.O","IdentifierType": "Ric"},
    # {"Identifier": "T","IdentifierType": "Ric"},
    # {"Identifier": "VZ","IdentifierType": "Ric"},
    # {"Identifier": "DIS","IdentifierType": "Ric"},
    # {"Identifier": "WBD.O","IdentifierType": "Ric"},
    # {"Identifier": "ABNB.O","IdentifierType": "Ric"},
    # {"Identifier": "CCL","IdentifierType": "Ric"},
    # {"Identifier": "CMG","IdentifierType": "Ric"},
    # {"Identifier": "F","IdentifierType": "Ric"},
    # {"Identifier": "GM","IdentifierType": "Ric"},
    # {"Identifier": "HD","IdentifierType": "Ric"},
    # {"Identifier": "HLT","IdentifierType": "Ric"},
    # {"Identifier": "MAR.O","IdentifierType": "Ric"},
    # {"Identifier": "NKE","IdentifierType": "Ric"},
    # {"Identifier": "RCL","IdentifierType": "Ric"},
    # {"Identifier": "SBUX.O","IdentifierType": "Ric"},
    # {"Identifier": "TSLA.O","IdentifierType": "Ric"},
    # {"Identifier": "YUM","IdentifierType": "Ric"},
    # {"Identifier": "KO","IdentifierType": "Ric"},
    # {"Identifier": "DG","IdentifierType": "Ric"},
    # {"Identifier": "PM","IdentifierType": "Ric"},
    # {"Identifier": "PG","IdentifierType": "Ric"},
    # {"Identifier": "WMT","IdentifierType": "Ric"},
    # {"Identifier": "XOM","IdentifierType": "Ric"},
    # {"Identifier": "GS","IdentifierType": "Ric"},
    # {"Identifier": "V","IdentifierType": "Ric"},
    # {"Identifier": "BRKa","IdentifierType": "Ric"},
    # {"Identifier": "BRKb","IdentifierType": "Ric"},
    # {"Identifier": "XLU","IdentifierType": "Ric"},
    # {"Identifier": "XTL","IdentifierType": "Ric"},
    # {"Identifier": "XLRE","IdentifierType": "Ric"},
    # {"Identifier": "XLF","IdentifierType": "Ric"},
    # {"Identifier": "XES","IdentifierType": "Ric"},
    # {"Identifier": "XHB","IdentifierType": "Ric"},
    # {"Identifier": "XLE","IdentifierType": "Ric"},
    # {"Identifier": "XLI","IdentifierType": "Ric"},
    # {"Identifier": "XLK","IdentifierType": "Ric"},
    # {"Identifier": "XLP","IdentifierType": "Ric"},
    # {"Identifier": "XLU","IdentifierType": "Ric"},
    # {"Identifier": "XLV","IdentifierType": "Ric"},
    # {"Identifier": "XLY","IdentifierType": "Ric"},
    # {"Identifier": "XLB","IdentifierType": "Ric"},
    # {"Identifier": "XLC","IdentifierType": "Ric"},
]

queue = {}

def log_msg(msg):
    now = datetime.now(timezone.utc).astimezone(pytz.timezone('America/New_York')).isoformat()
    print(f"{now}: {msg}")

def status_check_and_download(queue, extraction_id):
    e_resp_code, extr_info = datascope.get_extraction_state(extraction_id=extraction_id)

    if e_resp_code == 200:
        num_instruments = None
        not_found_note = None
        date_range = None

        # get num instruments after expansion to check against limit; if over limit, request needs to be split across smaller time intervals
        if (extr_info) and ("Notes" in extr_info):
            extr_notes = extr_info.get("Notes")
            for note in extr_notes:
                note = note.replace(r"\r\n", "\n")
                for line in str(note).split("\n"):
                    if line.startswith("Total instruments after instrument expansion = "):
                        num_instruments = int(line.split()[6])
                        limit_note = line
                    elif line.startswith("Timeseries Date Range: "): #elektron only start
                        date_range = (line.split()[3], line.split()[5])
                    elif line.startswith("Only 30000 constituents of CHAIN RIC"):
                        chain_ric = line.split()[6]
                    elif line.startswith("CHAIN RIC"):
                        chain_ric = line.split()[2]
                    elif line.startswith("WARNING: Chain details are not available within the queried date range"):  #elektron only end
                        not_found_note = line
                    elif line.startswith("Range Query from"): #intraday only start
                        date_range = (line.split()[3], line.split()[5])
                    elif line.endswith("will not be fully expanded because instrument limit of 30000 has been reached."): #intraday only end
                        chain_ric = line.split()[1]
        if not num_instruments:
            log_msg(f"error {extraction_id} number of instruments after expansion not found")
            if not_found_note:
                log_msg(f"{not_found_note}")
            del queue[extraction_id]
        elif num_instruments >= RIC_LIMIT:
            log_msg(f"limit failure {extraction_id} {chain_ric} {date_range} {limit_note}")
            del queue[extraction_id]
        elif num_instruments < RIC_LIMIT:
            retry_count = MAX_DOWNLOAD_RETRIES
            while True:
                try:
                    d_resp_code, download_path = datascope.download_extraction(extraction_id=extraction_id)
                    break
                except Exception as err:
                    log_msg(f"error on download {extraction_id} {err=}, {type(err)=}")
                    log_msg(f"retry download {extraction_id}, {retry_count} retries left")
                    retry_count -= 1
                    if retry_count <= 0:
                        log_msg(f"error: failure after {MAX_DOWNLOAD_RETRIES} retries, delete {extraction_id} from queue")
                        del queue[extraction_id]
                        break

            if d_resp_code == 200:
                log_msg(f"download {extraction_id} to {download_path}")
                del queue[extraction_id]
        else:
            log_msg(f"error {extraction_id} unknown")
    else:
        j_resp_code, resp = datascope.get_job_state(extraction_id=extraction_id)
        if j_resp_code==200 and ("StatusMessage" in resp) and resp["StatusMessage"] == "Extraction failed":
            log_msg(f"failure {extraction_id}, delete from queue")
            del queue[extraction_id]
        else:
            log_msg(f"timeout (probably) {extraction_id} {e_resp_code=}")


def by_month(config):
    for ric in INSTRUMENT_LIST:
        for i in range(START_YEAR,END_YEAR+1):
            for j in range(START_MONTH,END_MONTH+1):
                query_start_date = f"{i}-{j:02}-01T00:00:00.000000000"
                query_end_date = f"{i}-{j:02}-{calendar.monthrange(i,j)[1]:02}T23:59:59.999999999"
                config[REPORT_TYPE_FULL]["report_settings"]["QueryStartDate"] = query_start_date
                config[REPORT_TYPE_FULL]["report_settings"]["QueryEndDate"] = query_end_date

                config[REPORT_TYPE_FULL]["instruments"] = [ric]
                if "SummaryInterval" in config[REPORT_TYPE_FULL]["report_settings"]: # intraday only
                    config[REPORT_TYPE_FULL]["report_settings"]["SummaryInterval"] = SUMMARY_INTERVAL
                elif "DateRangeTimeZone" in config[REPORT_TYPE_FULL]["report_settings"]:
                    config[REPORT_TYPE_FULL]["report_settings"]["DateRangeTimeZone"] = DATE_RANGE_TIME_ZONE
                elif "MessageTimeStampIn" in config[REPORT_TYPE_FULL]["report_settings"]:
                    config[REPORT_TYPE_FULL]["report_settings"]["MessageTimeStampIn"] = MESSAGE_TIME_STAMP_IN

                new_extraction = datascope.OnDemandExtraction(report_type=REPORT_TYPE,config=config)
                notes, error_info, extraction_id = new_extraction.create()
                if notes:
                    # log_msg(notes)
                    pass
                if error_info:
                    log_msg(error_info)
                log_msg(f"new extraction {extraction_id}")
                queue[extraction_id] = None

                while len(queue) >= QUEUE_LIMIT:
                    time.sleep(SECS_PER_MIN * MINS_TO_SLEEP)
                    for k in list(queue.keys()): 
                        status_check_and_download(queue=queue,extraction_id=k)

        while len(queue) > 0:
            time.sleep(SECS_PER_MIN * MINS_TO_SLEEP)
            for k in list(queue.keys()):
                status_check_and_download(queue=queue,extraction_id=k)

def by_year(config):
    for ric in INSTRUMENT_LIST:
        for i in range(START_YEAR,END_YEAR+1):
            query_start_date = f"{i}-01-01T00:00:00.000000000"
            query_end_date = f"{i}-12-31T23:59:59.999999999"
            config[REPORT_TYPE_FULL]["report_settings"]["QueryStartDate"] = query_start_date
            config[REPORT_TYPE_FULL]["report_settings"]["QueryEndDate"] = query_end_date

            config[REPORT_TYPE_FULL]["instruments"] = [ric]
            if "SummaryInterval" in config[REPORT_TYPE_FULL]["report_settings"]: # intraday only
                config[REPORT_TYPE_FULL]["report_settings"]["SummaryInterval"] = SUMMARY_INTERVAL

            new_extraction = datascope.OnDemandExtraction(report_type=REPORT_TYPE,config=config)
            notes, error_info, extraction_id = new_extraction.create()
            if notes:
                # log_msg(notes)
                pass
            if error_info:
                log_msg(error_info)
            log_msg(f"new extraction {extraction_id}")
            queue[extraction_id] = None

            while len(queue) >= QUEUE_LIMIT:
                time.sleep(SECS_PER_MIN * MINS_TO_SLEEP)
                for k in list(queue.keys()): 
                    status_check_and_download(queue=queue,extraction_id=k)

        while len(queue) > 0:
            time.sleep(SECS_PER_MIN * MINS_TO_SLEEP)
            for k in list(queue.keys()): 
                status_check_and_download(queue=queue,extraction_id=k)

def in_full(config):
    for ric in INSTRUMENT_LIST:
        query_start_date = f"{START_YEAR}-01-01T00:00:00.000000000"
        query_end_date = f"{END_YEAR}-12-31T23:59:59.999999999"
        config[REPORT_TYPE_FULL]["report_settings"]["QueryStartDate"] = query_start_date
        config[REPORT_TYPE_FULL]["report_settings"]["QueryEndDate"] = query_end_date

        config[REPORT_TYPE_FULL]["instruments"] = [ric]
        if "SummaryInterval" in config[REPORT_TYPE_FULL]["report_settings"]: # intraday only
            config[REPORT_TYPE_FULL]["report_settings"]["SummaryInterval"] = SUMMARY_INTERVAL

        new_extraction = datascope.OnDemandExtraction(report_type=REPORT_TYPE,config=config)
        notes, error_info, extraction_id = new_extraction.create()
        if notes:
            # log_msg(notes)
            pass
        if error_info:
            log_msg(error_info)
        log_msg(f"new extraction {extraction_id}")
        queue[extraction_id] = None

        while len(queue) >= QUEUE_LIMIT:
            time.sleep(SECS_PER_MIN * MINS_TO_SLEEP)
            for k in list(queue.keys()): 
                status_check_and_download(queue=queue,extraction_id=k)

    while len(queue) > 0:
        time.sleep(SECS_PER_MIN * MINS_TO_SLEEP)
        for k in list(queue.keys()): 
            status_check_and_download(queue=queue,extraction_id=k)

def init_conf(init_config_path):
    with open(init_config_path,"r") as f:
        conf = json.load(f)
    return conf

if __name__ == "__main__":
    conf = init_conf(init_config_path=INIT_CONFIG_PATH)

    if MODE == "YEAR":
        by_year(config=conf)
    elif MODE == "MONTH":
        by_month(config=conf)
    elif MODE == "FULL":
        in_full(config=conf)
    else:
        print("Choose a valid mode.\n")
