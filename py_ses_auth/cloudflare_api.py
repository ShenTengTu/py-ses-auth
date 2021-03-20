from pathlib import Path
import json
import requests

_path_cwd = Path.cwd()
_path_api_token_json = _path_cwd / "CLOUDFLARE_API_TOKEN.json"
_path_cloudflare_zone_json = _path_cwd / "CLOUDFLARE_ZONE.json"


def read_dns_api_token(token_name: str) -> str:
    with _path_api_token_json.open("r") as f:
        token_dict: dict = json.load(f)
        return token_dict.get(token_name, None)


def read_cloudflare_zone_id(domain: str):
    with _path_cloudflare_zone_json.open("r") as f:
        zone_dict: dict = json.load(f)
        return zone_dict.get(domain, None)


class Cloudflare_API:
    endpoint = "https://api.cloudflare.com/client/v4/"

    @classmethod
    def response_post_processsing(cls, response: requests.Response, success_fn):
        status_code = response.status_code
        if not status_code in (200, 400):
            print("[Response] HTTP  status  : {} {}".format(status_code, response.reason))
            return False

        response_json: dict = response.json()
        success = response_json.get("success", None)

        print("[Cloudflare API]")
        if success is True:
            if callable(success_fn):
                success_fn(response_json)
                return True
        elif success is False:
            for entry in response_json["errors"]:
                print(
                    "API Response Error: [code:{}] {}".format(
                        entry["code"], entry["message"]
                    )
                )
                if "error_chain" in entry:
                    for item in entry["error_chain"]:
                        print(
                            "        ----> [code:{}] {}".format(
                                item["code"], item["message"]
                            )
                        )
        else:
            print("Unexepected response:", response_json)
        return False

    def __init__(self, token: str, zone_identifier: str):
        self.token = token
        self.zone_identifier = zone_identifier

    def create_dns_record(self, payload: dict) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer {}".format(self.token),
        }
        url = "{}zones/{}/dns_records".format(self.endpoint, self.zone_identifier)
        print(
            "Add DNS Record: {} | {} | {}".format(
                payload["type"], payload["name"], payload["content"]
            )
        )
        return requests.post(url, headers=headers, json=payload)
