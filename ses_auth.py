#!/usr/bin/env python
from pathlib import Path
from py_ses_auth import (
    __version__,
    create_byodkim_dns_record,
    aws_ses_create_email_identity,
    aws_set_mail_from_domain,
    create_mail_from_dns_record,
    create_inbound_mx_dns_record,
    create_dmarc_dns_record,
)
from py_ses_auth.cli import CLI, arg_meta

path_cwd = Path.cwd()

# ===== CLI =====

_dest = "cmd"
_ses_auth = CLI(
    __version__,
    dict(
        prog="ses_auth",
        description="CLI for setting up AWS SES email authentication on Cloudflare DNS.",
        epilog="Base on AWS CLI & Cloudflare API.",
    ),
    dict(
        title="Sub commands",
        description="DKIM, SPF, 'Mail From' domain, DMARC",
        dest=_dest,
    ),
)

_ses_auth.register_argument_group(
    "Common arguments",
    list_of_arg_conf=[
        arg_meta("domain", help="Which domain name you want to authenticate."),
        arg_meta("--region", help="Which AWS region you use."),
        arg_meta(
            "--token_name",
            help="Which name of Cloudflare API token  listed in `CLOUDFLARE_API_TOKEN.json` you would use.",
        ),
        arg_meta(
            "--aws_only",
            help="Skip the creation of DNS records and only configure AWS SES .",
            action="store_true",
        ),
    ],
)


@_ses_auth.arg_group("Common arguments")
@_ses_auth.sub_command_arg(
    "--selector",
    help="Unique name used in DNS TXT record name to identify the public key.",
)
@_ses_auth.sub_command_arg(
    "--exist",
    help="Updating an existing domain identity to use BYODKIM",
    action="store_true",
)
@_ses_auth.sub_command(
    help="Setting up Bring Your Own DKIM (BYODKIM).",
    description="Configuring DKIM authentication by using your own public-private key pair.",
)
def byodkim(ns):
    domain = ns.domain
    path_src: Path = path_cwd / domain
    assert path_src.exists(), "`{}` don't exist.".format(path_src)

    token_name = ns.token_name
    selector = ns.selector
    if not ns.aws_only:
        assert (
            type(token_name) is str
        ), "Please use `--token_name` to specify the token name which is in `CLOUDFLARE_API_TOKEN.json`."
        assert (
            type(selector) is str
        ), "Please use `--selector` to specify `DomainSigningSelector`."
        success = create_byodkim_dns_record(path_src, domain, token_name, selector)
        if not success:
            return

    region = ns.region
    assert type(region) is str, "Please use `--region` to specify the AWS region."
    aws_ses_create_email_identity(
        path_src, domain, ns.region, selector, is_new=(not ns.exist)
    )


@_ses_auth.arg_group("Common arguments")
@_ses_auth.sub_command_arg(
    "subdomain",
    help="The name of 'Mail From' subdomain you would use. Not need the domain name as suffix.",
)
@_ses_auth.sub_command_arg(
    "--reject",
    help="Reject message if MX record is not set up correctly. Default behavior is to use a subdomain of `amazonses.com`.",
    action="store_const",
    const="REJECT_MESSAGE",
    default="USE_DEFAULT_VALUE",
)
@_ses_auth.sub_command(
    help="Setting up 'Mail From' domain.",
    description="Configuring custom 'Mail From' domain of AWS SES.",
)
def mail_from_domain(ns):
    domain = ns.domain
    path_src: Path = path_cwd / domain
    assert path_src.exists(), "`{}` don't exist.".format(path_src)

    region = ns.region
    assert type(region) is str, "Please use `--region` to specify the AWS region."
    subdomain = ns.subdomain
    aws_set_mail_from_domain(domain, region, subdomain, ns.reject)
    if not ns.aws_only:
        token_name = ns.token_name
        assert (
            type(token_name) is str
        ), "Please use `--token_name` to specify the token name which is in `CLOUDFLARE_API_TOKEN.json`."
        create_mail_from_dns_record(path_src, domain, region, token_name, subdomain)


@_ses_auth.arg_group("Common arguments")
@_ses_auth.sub_command_arg(
    "--subdomain",
    help="The subdomain name you would use. Not need the domain name as suffix.",
)
@_ses_auth.sub_command(
    help="Creating MX record of the endpoint that receive email in Amazon SES.",
    description="Creating MX record refering to the endpoint that receives email for the AWS region.",
)
def inbound_smtp(ns):
    domain = ns.domain
    path_src: Path = path_cwd / domain
    assert path_src.exists(), "`{}` don't exist.".format(path_src)

    region = ns.region
    assert type(region) is str, "Please use `--region` to specify the AWS region."
    token_name = ns.token_name
    assert (
        type(token_name) is str
    ), "Please use `--token_name` to specify the token name which is in `CLOUDFLARE_API_TOKEN.json`."

    create_inbound_mx_dns_record(path_src, domain, region, token_name, ns.subdomain)


@_ses_auth.arg_group("Common arguments")
@_ses_auth.sub_command_arg(
    "local_part",
    help="The Local-part of email you would use.",
)
@_ses_auth.sub_command_arg(
    "--subdomain",
    help="The subdomain name of eamil you would use. Not need the domain name as suffix.",
)
@_ses_auth.sub_command(
    help="Creating TX record of DMARC policy.",
    description="Creating TX record to set up DMARC.",
)
def dmarc(ns):
    domain = ns.domain
    path_src: Path = path_cwd / domain
    assert path_src.exists(), "`{}` don't exist.".format(path_src)

    token_name = ns.token_name
    assert (
        type(token_name) is str
    ), "Please use `--token_name` to specify the token name which is in `CLOUDFLARE_API_TOKEN.json`."

    create_dmarc_dns_record(path_src, domain, token_name, ns.local_part, ns.subdomain)


def main():
    try:
        _ses_auth.handle_args()
    except AssertionError as err:
        print(err.args[0])


if __name__ == "__main__":
    main()
