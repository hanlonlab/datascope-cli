#!/usr/bin/env python3
import argparse
import os
import sys
import json
import sqlite3
import requests
import re
from datetime import datetime, timezone

# filesystem locations
HOME_DIR = os.environ.get("HOME")
DATASCOPE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = f"{DATASCOPE_DIR}/config/datascope.conf" #possible future replacement: f"{os.environ.get("HOME")}/.config/datascope/datascope.conf"
CRED_PATH = f"{HOME_DIR}/.dspass" #possible future replacement: f"{os.environ.get("HOME")}/.config/datascope/dspass"
DB_INIT_PATH = f"{DATASCOPE_DIR}/sql/datascope_db_init.sql"
DB_PATH = f"{DATASCOPE_DIR}/db/datascope_db"
TMP_DIR = f"{DATASCOPE_DIR}/tmp"
os.makedirs(TMP_DIR, exist_ok=True)

# api urls, headers, static settings
AUTH_URL = "https://selectapi.datascope.lseg.com/RestApi/v1/Authentication/RequestToken"
AUTH_HEADERS = {"Prefer": "respond-async", "Content-Type": "application/json"}
GET_FIELDS_URL_F = "https://selectapi.datascope.lseg.com/RestApi/v1/Extractions/GetValidContentFieldTypes(ReportTemplateType=DataScope.Select.Api.Extractions.ReportTemplates.ReportTemplateTypes'{template_name}')" #.format(template_name=foo)
GET_ACTIVE_JOBS_URL = "https://selectapi.datascope.lseg.com/RestApi/v1/Jobs/JobGetActive"
GET_JOB_STATE_URL_F = "https://selectapi.datascope.lseg.com/RestApi/v1/Jobs/Jobs('{extraction_id}')" #.format(extraction_id=foo)
GET_EXTRACTION_STATE_URL_F = "https://selectapi.datascope.lseg.com/RestApi/v1/Extractions/ExtractRawResult(ExtractionId='{extraction_id}')" #.format(extraction_id=foo)
CANCEL_EXTRACTION_URL_F = "https://selectapi.datascope.lseg.com/RestApi/v1/Extractions/ExtractRawResult(ExtractionId='{extraction_id}')" #.format(extraction_id=foo)
DOWNLOAD_EXTRACTION_URL_F = "https://selectapi.datascope.lseg.com/RestApi/v1/Extractions/RawExtractionResults('{extraction_id}')/$value" #.format(extraction_id=foo)
GET_HEADERS_F = '{{"Prefer": "respond-async", "Authorization": "Token {token}"}}' #.format(token=foo)
POST_EXTRACTION_URL = "https://selectapi.datascope.lseg.com/RestApi/v1/Extractions/ExtractRaw"
POST_HEADERS_F = '{{"Prefer": "respond-async", "Content-Type": "application/json; odata=minimalmetadata", "Authorization": "Token {token}"}}' #.format(token=foo)
DL_CHUNK_SIZE = 8192
REQ_TIMEOUT_S = (30,3) # (connect,read)

# columns for table extraction in sqlite database
DB_EXTRACTION_COLS = ("extraction_id", "extraction_timestamp", "report_type", "instruments", "report_settings", "export_filename")

# mapping to abbreviate summary interval parameter for filenames
SUMMARY_INTERVAL_MAPPING = {"OneSecond": "1s", "FiveSeconds": "5s", "OneMinute": "1m", "FiveMinutes": "5m", "TenMinutes": "10m", "FifteenMinutes": "15m", "OneHour": "1h"}

class OnDemandExtraction:
    def __init__(self, report_type: str, config: str = CONFIG_PATH, extraction_id: str = None, pull_all_fields = False, ):
        self.report_type = report_type
        if isinstance(config, dict):
            dconf = config
        else:
            with open(config) as file:
                dconf = json.load(file)

        self.canon_name = dconf["metadata"][report_type]["canon_name"]
        self.template_name = dconf["metadata"][report_type]["template_name"]
        self.report_name = dconf["metadata"][report_type]["report_name"]

        self.fields_wo_permissions = dconf["metadata"][report_type]["fields_wo_permission"]
        self.default_fields = dconf["metadata"][report_type]["default_fields"]

        self.instruments = dconf[self.canon_name]["instruments"]
        self.report_settings = dconf[self.canon_name]["report_settings"]

        self.report_fields = []
        self.pull_all_fields = pull_all_fields
        self.extraction_id = None
        self.extraction_timestamp = None
        self.export_filename = None

        self.token = None

        if extraction_id and os.path.isfile(DB_PATH):
            self._db_read()

        if not os.path.isfile(DB_PATH):
            with open(DB_INIT_PATH, "r") as file:
                db_init_sql = file.read()
            con = sqlite3.connect(DB_PATH)
            cur = con.cursor()
            cur.execute(db_init_sql)
            con.commit()
            con.close()

    def _populate_fields(self, ):
        with requests.Session() as s:
            r = s.get(url=GET_FIELDS_URL_F.format(template_name=self.template_name), headers=json.loads(GET_HEADERS_F.format(token=self.token)))
            for item in r.json()["value"]:
                if self.pull_all_fields and item["Name"] not in self.fields_wo_permissions:
                    self.report_fields.append(item["Name"])
                elif item["Name"] in self.default_fields and item["Name"] not in self.fields_wo_permissions:
                    self.report_fields.append(item["Name"])

    def _set_filename(self, ):
        max_inst_in_filename = 3
        inst_summary = "_".join([re.sub("[.]", "-", re.sub("[#*]", "", inst["Identifier"])).lower() for inst in self.instruments[:max_inst_in_filename]])
        query_start = re.sub("[-:.TZ]", "", self.report_settings["QueryStartDate"])
        query_end = re.sub("[-:.TZ]", "", self.report_settings["QueryEndDate"])
        
        if len(self.instruments) > max_inst_in_filename:
            addl_flag = "_addl"
        else:
            addl_flag = ""
        
        if self.canon_name == "intraday_summaries":
            summary_interval = f"_{SUMMARY_INTERVAL_MAPPING[self.report_settings["SummaryInterval"]]}"
        else:
            summary_interval = ""
        
        self.export_filename = f"{self.report_name.lower()}{summary_interval}_{self.extraction_id}_{inst_summary}{addl_flag}_{query_start}_{query_end}.csv"
    
    def _db_write(self, ):
        column_names = ", ".join(DB_EXTRACTION_COLS)
        column_parameters = ", :".join(DB_EXTRACTION_COLS)
        insert_statement = f"INSERT INTO extraction ({column_names}) VALUES (:{column_parameters})"
        attr_to_write = {k: str(v) for k,v in vars(self).items() if k in DB_EXTRACTION_COLS}
        
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        cur.execute(insert_statement, attr_to_write)
        con.commit()
        con.close()

    def _db_read(self, ): #not yet used
        column_names = ", ".join(DB_EXTRACTION_COLS)
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        query_string = f"SELECT {column_names} FROM extraction WHERE extraction_id = :extraction_id ORDER BY extraction_timestamp DESC LIMIT 1;"
        rows = cur.execute(query_string, {"extraction_id": self.extraction_id}).fetchone()
        record_cols = [description[0] for description in cur.description]
        record = dict(zip(record_cols,rows[0]))
        con.close()
        for k,v in record.items():
            setattr(self, k, v)


    def create(self, ) -> tuple[str, str, str]:
        self.token = auth_token()
        self._populate_fields()
        
        request_body = {
            "ExtractionRequest": {
                "@odata.type": f"#DataScope.Select.Api.Extractions.ExtractionRequests.{self.report_name}ExtractionRequest",
                "ContentFieldNames": self.report_fields,
                "IdentifierList": {
                    "@odata.type": "#DataScope.Select.Api.Extractions.ExtractionRequests.InstrumentIdentifierList",
                    "InstrumentIdentifiers": self.instruments,
                    "ValidationOptions": {"AllowHistoricalInstruments": True},
                    "UseUserPreferencesForValidationOptions": False,
                },
                "Condition": self.report_settings,
            }
        }

        with requests.Session() as s: 
            r = s.post(url=POST_EXTRACTION_URL, headers=json.loads(POST_HEADERS_F.format(token=self.token)), json=request_body)

        try:
            r.raise_for_status()
            
            notes = None
            error_info = None

            if r.content:
                resp_info = r.json()
                if "Notes" in resp_info:
                    notes = resp_info["Notes"][0]
                if "error" in resp_info:
                    error_info = resp_info["error"]
            
            if r.content and self.canon_name == "elektron" and ("JobId" in resp_info):
                self.extraction_id = resp_info["JobId"]
            elif r.content and ("JobId" in resp_info): #likely an error validating the request
                self.extraction_id = resp_info["JobId"]
            else:
                self.extraction_id = str(r.headers["Location"].split("'")[1])
            
            self.extraction_timestamp = datetime.now(timezone.utc).isoformat()
        except requests.HTTPError as err:
            print(f"Request fails with status code {err.response.status_code=}")
            print(f"Error {err=}")
            if r.content:
                print(f"Server returned error message: {r.json()}")
            sys.exit(1)
        except requests.JSONDecodeError as err:
            print(f"Response can't be decoded as JSON, {err=}")
            sys.exit(1)
        except KeyError as err:
            print(f"Failed to extract JobId from response content or headers, {err=}")
            sys.exit(1)
        except Exception as err:
            print(f"Unexpected {err=}, {type(err)=}")
            sys.exit(1)
        
        self._set_filename()
        self._db_write()

        return (notes, error_info, self.extraction_id)

def auth_token() -> str:
    with open(CRED_PATH, "r") as f:
        creds = [line for line in f if line.startswith("selectapi")][0].split(":")
        auth_body = {"Credentials": {"Username": creds[1], "Password": creds[2]}}

    with requests.Session() as s: 
        try:
            r = s.post(url=AUTH_URL, data=json.dumps(auth_body), headers=AUTH_HEADERS) 
            token = r.json()["value"]
        except KeyError as err:
            print(f"Authentication failure {err=}, {type(err)=}:\n{r.content}")
            sys.exit(1)

    return token

def get_active_extractions() -> dict:
    token = auth_token()
    with requests.Session() as s:
        r = s.get(url=GET_ACTIVE_JOBS_URL, headers=json.loads(GET_HEADERS_F.format(token=token)))
    
    if (r.content):
        resp = r.json()
    else:
        resp = None
    
    return resp

def get_job_state(extraction_id: str) -> dict:
    token = auth_token()
    with requests.Session() as s:
        try:
            r = s.get(url=GET_JOB_STATE_URL_F.format(extraction_id=extraction_id), headers=json.loads(GET_HEADERS_F.format(token=token)), timeout=REQ_TIMEOUT_S)
        except requests.exceptions.Timeout as err:
            return (408, f"{err=}")
    
    if (r.content):
        resp = r.json()
    else:
        resp = None
    
    return (r.status_code, resp)

def get_extraction_state(extraction_id: str) -> dict:
    token = auth_token()
    with requests.Session() as s:
        try:
            r = s.get(url=GET_EXTRACTION_STATE_URL_F.format(extraction_id=extraction_id), headers=json.loads(GET_HEADERS_F.format(token=token)), timeout=REQ_TIMEOUT_S)
        except requests.exceptions.Timeout as err:
            return (408, f"{err=}")
    
    if (r.content):
        resp = r.json()
    else:
        resp = None

    return (r.status_code, resp)

def download_extraction(extraction_id: str) -> tuple[int, str]:
    token = auth_token()
    if not os.path.isfile(DB_PATH):
        export_filename = f"export_{extraction_id}.csv" 
    else:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        query_string = "SELECT export_filename FROM extraction WHERE extraction_id = :extraction_id ORDER BY extraction_timestamp DESC LIMIT 1;"
        rows = cur.execute(query_string, {"extraction_id": extraction_id}).fetchone()
        if not rows:
            export_filename = f"export_{extraction_id}.csv" 
        else:
            export_filename = rows[0]
        con.close()
    
    with requests.Session() as s:
        r = s.get(url=DOWNLOAD_EXTRACTION_URL_F.format(extraction_id=extraction_id), headers=json.loads(GET_HEADERS_F.format(token=token)), stream=True)
    try:
        with open(f"{TMP_DIR}/{export_filename}", "wb") as file:
            for chunk in r.iter_content(chunk_size=DL_CHUNK_SIZE):
                file.write(chunk)
    except Exception as err:
        print(f"Extraction download for {extraction_id} failed with unexpected error {err=}, {type(err)=}.")
        raise err

    return (r.status_code, f"{TMP_DIR}/{export_filename}")

def cancel_extraction(extraction_id: str) -> int:
    token = auth_token()
    with requests.Session() as s:
        r = s.request(method="DELETE", url=CANCEL_EXTRACTION_URL_F.format(extraction_id=extraction_id), headers=json.loads(GET_HEADERS_F.format(token=token)))

    return r.status_code

def query():
    if not os.path.isfile(DB_PATH):
        print("Database does not exist.")
        sys.exit(1)
    
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    
    while True:
        query_string = input("Query to run against extraction database ('q' to quit)?\n# ")
        try:
            if query_string in ("exit", "quit", "q"):
                break
            else:
                results = cur.execute(query_string)
                print(tuple([col_info[0] for col_info in cur.description]))
                for row in results:
                    print(row)
                print("\n")
        except Exception as err:
            print(f"Unexpected error {err=}, {type(err)=}; likely an invalid query.")

    con.commit()
    con.close()
    print("\nGoodbye.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(
        description="The way you want to use the API for extractions.",
        dest="action",
        required=True,
        help="",
        )

    # new
    parser_new = subparsers.add_parser("new")
    parser_new.add_argument(
        "report_type",
        choices=["time", "intraday", "market", "elektron"],
        type=str,
        help="The type of report for which to start a new extraction."
        )
    parser_new.add_argument("--all-fields", action="store_true", help="Pull all available fields.")

    # download
    parser_download = subparsers.add_parser("download")
    parser_download.add_argument(
        "extraction_id",
        type=str,
        help="The extraction id to download."
        )

    # status
    parser_status = subparsers.add_parser("status")
    parser_status.add_argument(
        "extraction_id",
        type=str,
        help="The extraction id of which to print the status."
        )

    # cancel
    parser_cancel = subparsers.add_parser("cancel")
    parser_cancel.add_argument(
        "extraction_id",
        type=str,
        help="The extraction id to cancel."
        )

    # active
    parser_active = subparsers.add_parser("active")

    # query
    parser_query = subparsers.add_parser("query")

    args = parser.parse_args()
    try:
        if args.action == "new":
            new_extraction = OnDemandExtraction(report_type=args.report_type, pull_all_fields=args.all_fields)
            notes, error_info, extraction_id = new_extraction.create()
            if notes:
                print(notes)
            if error_info:
                print(error_info)
            print(extraction_id)
        elif args.action == "download":
            status_code, download_path = download_extraction(extraction_id=args.extraction_id)
            print(status_code)
            print(download_path)
        elif args.action == "status":
            job_resp_code, job_info = get_job_state(extraction_id=args.extraction_id)
            print(f"{job_resp_code=}")
            print(json.dumps(job_info, indent=4))
            extr_resp_code, extr_info = get_extraction_state(extraction_id=args.extraction_id)
            print(f"\n{extr_resp_code=}")
            if (extr_info) and ("Notes" in extr_info):
                extr_notes = extr_info.get("Notes")
                for note in extr_notes:
                    note = note.replace(r"\r\n", "\n")
                    print(f"{note}")
            elif (extr_info):
                print(extr_info)
        elif args.action == "cancel":
            resp_code = cancel_extraction(extraction_id=args.extraction_id)
            print(f"{resp_code=}")
        elif args.action == "active":
            active_info = get_active_extractions()
            print(json.dumps(active_info, indent=4))
        elif args.action == "query":
            query() 
        else:
            parser.print_help()
    except FileNotFoundError as err:
        print(f"{err=}, {err.filename=}")
        sys.exit(1)
    except requests.exceptions.ChunkedEncodingError as err:
        print(f"Unexpected {err=}, {type(err)=}")
        sys.exit(1)
    except Exception as err:
        print(f"Unexpected {err=}, {type(err)=}")
        sys.exit(1)