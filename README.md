# SES_Auth: Domain authentication in AWS SES  on Cloudflare DNS
SES_Auth is a simple CLI for setting up AWS SES domain authentication on Cloudflare DNS:
- BYODKIM
- Custom 'Mail From' domain (SPF)
- DMARC

Before running the CLI, you have to install Python module  `requests` and AWS CLI.

The full related directory structure  is as below:
```
├── CLOUDFLARE_API_TOKEN.json
├── CLOUDFLARE_ZONE.json
├── config_mail_from.py
├── py_ses_auth
├── README.md
├── ses_auth.py
└── example.com
    ├── create-identity.json
    ├── dns_record_info.json
    ├── private.key
    ├── public.key
    └── update-identity.json
```

Using Cloudflare API needs the token and the zone identifier,  You have to separately write them into `CLOUDFLARE_API_TOKEN.json` and `CLOUDFLARE_ZONE.json`. 

The format of `CLOUDFLARE_API_TOKEN.json` is:
```json
{
    "Token name": "Token value"
}
```

The format of `CLOUDFLARE_ZONE.json`is:
```json
{
    "example.com": "Zone identifier"
}
```

The CLI would read `CLOUDFLARE_API_TOKEN.json` and `CLOUDFLARE_ZONE.json` to find out the token and zone identifier.

 Successful response result of DNS records createing  through Cloudflare API would be stored in `dns_record_info.json`.

## BYODKIM
All related files put into the directory named as domain name, the directory structure as below:
```
./example.com
├── create-identity.json
├── dns_record_info.json
├── private.key
├── public.key
└── update-identity.json
```

BYODKIM authentication needs the key pair `private.key` and `public.key` , execute the follow command to create them in the directory named as domain name.
```
openssl genrsa -f4 -out private.key 1024
openssl rsa -in private.key -outform PEM -pubout -out public.key
```

The CLI would read `public.key` to create TXT record on Cloudflare DNS, then read `private.key`to dump `create-identity.json` and `update-identity.json` for creating email domain Identity in AWS SES.

The example of setting up BYODKIM authentication with the command `byodkim` is :
```
./ses_auth.py byodkim example.com --region us-east-1 --token_name token_edit_dns --selector aws-dkim
```

If you want to configure an existing domain to use BYODKIM, use `--exist` flag:
```
./ses_auth.py byodkim example.com --region us-east-1 --token_name token_edit_dns --selector aws-dkim --exist
```

If you want to skip DNS record creating, use `--aws_only` flag, so that you can omit `--token_name` :
```
./ses_auth.py byodkim example.com --region us-east-1  --selector aws-dkim --aws_only
```

if you have created the domain identity in an AWS region and want to create the same domain identity  for another region, use `--aws_only` flag without `--token_name` and `--selector`:
```
./ses_auth.py byodkim example.com --region us-west-2 --aws_only
```
The CLI would create the identity in the other region by existing `create-identity.json`(or `update-identity.json` if the command contains `--exist` flag).

To check the DKIM status for a domain that uses BYODKIM on AWS SES:
```
aws sesv2 get-email-identity --email-identity example.com --region <region>
```

If DKIM status is success, another TXT record and CNAME record that need to  write in the  DNS would show in the details of the AWS SES domain page.

## Custom MAIL FROM domain
The CLI would use the command  `put-email-identity-mail-from-attributes` of AWS CLI to set up "MAIL FROM" domain, then creates MX record and TXT record (SPF) on Cloudflare DNS by Cloudflare API.

The example of setting up MAIL FROM domain with the command `mail_from_domain` is :
```
./ses_auth.py mail_from_domain subdomain example.com --region us-west-2 --token_name token_edit_dns
```

As default, if MX record is not set up correctly, Amazon SES will use a subdomain of `amazonses.com`. If you want to automatically reject emails that you attempt to send from, use `--reject` flag:
```
./ses_auth.py mail_from_domain subdomain example.com --region us-west-2 --token_name token_edit_dns --reject
```

If you want to skip DNS record creating, use `--aws_only` flag, so that you can omit `--token_name` :
```
./ses_auth.py mail_from_domain subdomain example.com --region us-west-2  --reject
```

You must use different subdomain name for each AWS region, or verification will fail.

To check the MAIL FROM domain status for a domain that uses BYODKIM on AWS SES:
```
aws sesv2 get-email-identity --email-identity example.com --region <region>
```

## Inbound SMTP endpoint
To have Amazon SES manage your incoming email (like DMARC reports),  you  need to create an MX record of the endpoint that receive email.

The example of creating the MX record with the command `inbound_smtp` is :
```
./ses_auth.py inbound_smtp example.com --region us-west-2 --token_name token_edit_dns
```

The content of the MX record would be:
```
Type: MX
Name: example.com.
Value: 10 inbound-smtp.us-west-2.amazonaws.com
```

You can use `--subdomain` argument to specify a subdomain name:
```
./ses_auth.py inbound_smtp example.com --region us-west-2 --token_name token_edit_dns --subdomain income
```

The content of the MX record would be:
```
Type: MX
Name: income.example.com.
Value: 10 inbound-smtp.us-west-2.amazonaws.com
```

After creating the MX record successfully, you need to giving permissions & ceating receipt rules for Amazon SES email receiving. See the detail infomation as below:
- [Creating receipt rules](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/receiving-email-receipt-rules.html)
- [Giving permission](https://docs.aws.amazon.com/ses/latest/DeveloperGuide/receiving-email-permissions.html)

## Complying with DMARC
To set up DMARC, you have to modify the DNS settings for your domain. The DNS settings for your domain should include a TXT record that specifies the domain's DMARC settings. 

The CLI would create a TXT record as below:
```
Type: TXT
Name: _dmarc.example.com
Value: "v=DMARC1;p=quarantine;pct=25;rua=mailto:dmarcreports@example.com"
```
For complete specifications of the DMARC system, see [RFC 7489](https://tools.ietf.org/html/rfc7489) on the IETF website.

The example of setting up DMARC with the command `dmarc` is :
```
./ses_auth.py dmarc dmarcreports example.com --token_name token_edit_dns
```

You can use `--subdomain` argument to specify a subdomain name of email:
```
./ses_auth.py dmarc dmarcreports example.com --token_name token_edit_dns --subdomain reports
```

The CLI would create a TXT record as below:
```
Type: TXT
Name: _dmarc.example.com
Value: "v=DMARC1;p=quarantine;pct=25;rua=mailto:dmarcreports@reports.example.com"
```

You can determine your domain's DMARC alignment for SPF or DKIM by typing the following command:
```
nslookup -type=TXT _dmarc.example.com
```

Alternatively, you can use a web-based DMARC lookup tool, such as the [DMARC Inspector](https://dmarcian.com/dmarc-inspector/) from the dmarcian website or the [DMARC Check](https://stopemailfraud.proofpoint.com/dmarc/) tool from the Proofpoint website, to determine your domain's policy alignment for DKIM.


