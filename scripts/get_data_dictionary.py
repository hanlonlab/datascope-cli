import requests
import json
import os


HOME_PATH = os.path.expanduser("~")
# TODO assert CRED_PATH is 644, same as .pgpass does
CRED_PATH = (
    HOME_PATH + "/.dspass"
)  # api credentials stored as string in format "selectapi:username:password"
TMP_DIR = "../../tmp"
DSS_AUTH_URL = (
    "https://selectapi.datascope.refinitiv.com/RestApi/v1/Authentication/RequestToken"
)
AUTH_HEADERS = {"Prefer": "respond-async", "Content-Type": "application/json"}
REPORT_TEMPLATE = "TickHistoryMarketDepth"


def get_data_dictionary(template_name: str):
    """Download data dictionary for report template as json and csv."""

    # set up creds for api auth
    with open(CRED_PATH, "r") as f:
        valid_creds = [line for line in f if line.startswith("selectapi")][0].split(":")
        auth_body = {
            "Credentials": {"Username": valid_creds[1], "Password": valid_creds[2]}
        }

    with requests.Session() as s:
        # authenicate to api, get token
        r = s.request(
            method="POST",
            url=DSS_AUTH_URL,
            data=json.dumps(auth_body),
            headers=AUTH_HEADERS,
        )
        token = json.loads(r.content)["value"]

        # pull available report fields
        get_headers = {"Prefer": "respond-async", "Authorization": "Token " + token}
        get_url = (
            "https://selectapi.datascope.refinitiv.com/RestApi/v1/Extractions/GetValidContentFieldTypes(ReportTemplateType=DataScope.Select.Api.Extractions.ReportTemplates.ReportTemplateTypes'"
            + template_name
            + "')"
        )
        r = s.request(method="GET", url=get_url, headers=get_headers)

        with open(
            TMP_DIR + "/" + str.lower(template_name) + "_data_dictionary.json", "w"
        ) as file:
            file.write(json.dumps(json.loads(r.content), indent=4))

        # compose report request body, pull all fields from field list
        with open(
            TMP_DIR + "/" + str.lower(template_name) + "_data_dictionary.csv", "w"
        ) as file:
            headers = ",".join(
                [
                    '"' + str(key) + '"'
                    for key in json.loads(r.content)["value"][0].keys()
                ]
            )
            file.write(headers + "\n")
            for item in json.loads(r.content)["value"]:
                record = ",".join(['"' + str(val) + '"' for val in item.values()])
                file.write(record + "\n")


if __name__ == "__main__":
    get_data_dictionary(template_name=REPORT_TEMPLATE)
