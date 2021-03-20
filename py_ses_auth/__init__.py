"""
CLI API for for setting up AWS SES authentication on Cloudflare DNS.
"""

__version__ = "0.1.0.dev"

__all__ = [
    "create_byodkim_dns_record",
    "aws_ses_create_email_identity",
    "aws_set_mail_from_domain",
    "create_mail_from_dns_record",
    "create_inbound_mx_dns_record",
    " create_dmarc_dns_record",
]

from pathlib import Path
from string import Template
import json
import shlex
import subprocess
from .cloudflare_api import (
    Cloudflare_API,
    read_cloudflare_zone_id,
    read_dns_api_token,
)

json_temp_for_create = Template(
    "{\n"
    '    "EmailIdentity":"$domain",\n'
    '    "DkimSigningAttributes":{\n'
    '        "DomainSigningPrivateKey":"$private_key",\n'
    '        "DomainSigningSelector":"$selector"\n'
    "    }\n"
    "}"
)

json_temp_for_update = Template(
    "{\n"
    '    "SigningAttributes":{\n'
    '        "DomainSigningPrivateKey":"$private_key",\n'
    '        "DomainSigningSelector":"$selector"\n'
    "    },"
    '    "SigningAttributesOrigin":"EXTERNAL"\n'
    "}"
)


def _read_key_from_file(path: Path):
    with path.open("r") as f:
        l = f.readlines()
        return "".join(map(lambda s: s.strip(), l[1:-1]))


def _update_dns_record_info(path: Path, record: dict):
    if not path.exists():
        with path.open("w") as f:
            json.dump({"Cloudflare": []}, f, indent=4)

    with path.open("r+") as f:
        d = json.load(f)
        if not "Cloudflare" in d:
            d["Cloudflare"] = []
        d["Cloudflare"].append(record)
        f.seek(0)
        json.dump(d, f, indent=4)


def _create_dns_record(fn, path_src: Path, domain: str, token_name: str):
    def success_fn(response_json: dict):
        path_dns_record = path_src / "dns_record_info.json"
        _update_dns_record_info(path_dns_record, response_json["result"])
        print("update `dns_record_info.json`")

    token = read_dns_api_token(token_name)
    zone_id = read_cloudflare_zone_id(domain)
    if token and zone_id:
        if callable(fn):
            return fn(Cloudflare_API(token, zone_id), success_fn)


def create_byodkim_dns_record(path_src: Path, domain: str, token_name: str, selector: str):
    path_public_key = path_src / "public.key"
    assert path_public_key.exists(), "`{}` don't exist.".format(path_public_key.absolute())

    def success_fn(response_json: dict):
        path_dns_record = path_src / "dns_record_info.json"
        _update_dns_record_info(path_dns_record, response_json["result"])
        print("update `dns_record_info.json`")

    k = _read_key_from_file(path_public_key)
    print("read public key")

    name = "{selector}._domainkey.{domain}".format(selector=selector, domain=domain)
    value = "p={public_key}".format(public_key=k)

    token = read_dns_api_token(token_name)
    zone_id = read_cloudflare_zone_id(domain)

    if token and zone_id:
        dns_editor = Cloudflare_API(token, zone_id)
        payload = {"type": "TXT", "name": name, "content": value, "ttl": 1}

        return Cloudflare_API.response_post_processsing(
            dns_editor.create_dns_record(payload), success_fn
        )


def aws_ses_create_email_identity(
    path_src: Path, domain: str, region: str, selector=None, is_new=True
):
    path_private_key = path_src / "private.key"
    assert path_private_key.exists(), "`{}` don't exist.".format(
        path_private_key.absolute()
    )
    k = _read_key_from_file(path_private_key)
    if is_new:
        path_create_identity_json = path_src / "create-identity.json"
        if type(selector) is str:
            with path_create_identity_json.open("w") as f:
                out = json_temp_for_create.substitute(
                    domain=domain, private_key=k, selector=selector
                )
                f.write(out)
                print("dump 'create-identity.json'")
        assert (
            path_create_identity_json.exists()
        ), "Please use `--selector` to specify `DomainSigningSelector`."
        print("[AWS CLI]")
        cmd = (
            "aws sesv2 create-email-identity --cli-input-json file://{} --region {}".format(
                path_create_identity_json, region
            )
        )
        args = shlex.split(cmd)
        cp = subprocess.run(args)
    else:
        path_update_identity_json = path_src / "update-identity.json"
        if type(selector) is str:
            with path_update_identity_json.open("w") as f:
                out = json_temp_for_update.substitute(private_key=k, selector=selector)
                f.write(out)
                print("dump 'update-identity.json'")
        assert (
            path_update_identity_json.exists()
        ), "Please use `--selector` to specify `DomainSigningSelector`."
        print("[AWS CLI]")
        cmd = "aws sesv2 put-email-identity-dkim-signing-attributes --email-identity {} --cli-input-json file://{} --region {}".format(
            domain, path_update_identity_json, region
        )
        args = shlex.split(cmd)
        cp = subprocess.run(args)


def aws_set_mail_from_domain(
    domain: str, region: str, subdomain_name: str, on_mx_failure="USE_DEFAULT_VALUE"
):
    if not on_mx_failure in ("USE_DEFAULT_VALUE", "REJECT_MESSAGE"):
        on_mx_failure = "USE_DEFAULT_VALUE"
    print("[AWS CLI]")
    cmd = (
        "aws sesv2 put-email-identity-mail-from-attributes "
        "--email-identity {} --mail-from-domain {} --behavior-on-mx-failure {} --region {}"
    ).format(domain, "{}.{}".format(subdomain_name, domain), on_mx_failure, region)
    args = shlex.split(cmd)
    cp = subprocess.run(args)
    print("done.")


def create_mail_from_dns_record(
    path_src: Path, domain: str, region: str, token_name: str, subdomain_name: str
):
    def success_fn(response_json: dict):
        path_dns_record = path_src / "dns_record_info.json"
        _update_dns_record_info(path_dns_record, response_json["result"])
        print("update `dns_record_info.json`")

    token = read_dns_api_token(token_name)
    zone_id = read_cloudflare_zone_id(domain)

    if token and zone_id:
        dns_editor = Cloudflare_API(token, zone_id)
        name = "{}.{}".format(subdomain_name, domain)
        payloads = (
            {
                "type": "MX",
                "name": name,
                "content": "feedback-smtp.{}.amazonses.com".format(region),
                "ttl": 1,
                "priority": 10,
            },
            {
                "type": "TXT",
                "name": name,
                "content": '"v=spf1 include:amazonses.com ~all"',
                "ttl": 1,
            },
        )

        status = Cloudflare_API.response_post_processsing(
            dns_editor.create_dns_record(payloads[0]), success_fn
        )
        if not status:
            return status
        status = Cloudflare_API.response_post_processsing(
            dns_editor.create_dns_record(payloads[1]), success_fn
        )
        return status


def create_inbound_mx_dns_record(
    path_src: Path, domain: str, region: str, token_name: str, subdomain_name=None
):
    def procedure(dns_editor: Cloudflare_API, success_fn):
        if type(subdomain_name) is str:
            name = "{}.{}.".format(subdomain_name, domain)
        else:
            name = "{}.".format(domain)

        payload = {
            "type": "MX",
            "name": name,
            "content": "inbound-smtp.{}.amazonaws.com".format(region),
            "ttl": 1,
            "priority": 10,
        }

        return Cloudflare_API.response_post_processsing(
            dns_editor.create_dns_record(payload), success_fn
        )

    _create_dns_record(procedure, path_src, domain, token_name)


def create_dmarc_dns_record(
    path_src: Path, domain: str, token_name: str, local_part: str, subdomain_name=None
):
    def procedure(dns_editor: Cloudflare_API, success_fn):
        if type(subdomain_name) is str:
            email_domain = "{}.{}".format(subdomain_name, domain)
        else:
            email_domain = domain

        name = "_dmarc.{}".format(domain)
        value = '"v=DMARC1;p=quarantine;pct=25;rua=mailto:{}@{}"'.format(
            local_part, email_domain
        )

        print(value)

        payload = {
            "type": "TXT",
            "name": name,
            "content": value,
            "ttl": 1,
        }

        return Cloudflare_API.response_post_processsing(
            dns_editor.create_dns_record(payload), success_fn
        )

    _create_dns_record(procedure, path_src, domain, token_name)
