#! /usr/bin/env python

import requests
import sys
import json
import os
import time
import click
import cmd
import difflib

requests.packages.urllib3.disable_warnings()

from requests.packages.urllib3.exceptions import InsecureRequestWarning


vmanage_host = os.environ.get("vmanage_host")
vmanage_port = os.environ.get("vmanage_port")
vmanage_username = os.environ.get("vmanage_username")
vmanage_password = os.environ.get("vmanage_password")

if vmanage_host is None or vmanage_port is None or vmanage_username is None or vmanage_password is None:
    print("For Windows Workstation, vManage details must be set via environment variables using below commands")
    print("set vmanage_host=198.18.1.10")
    print("set vmanage_port=8443")
    print("set vmanage_username=admin")
    print("set vmanage_password=admin")
    print("For MAC OSX Workstation, vManage details must be set via environment variables using below commands")
    print("export vmanage_host=198.18.1.10")
    print("export vmanage_port=8443")
    print("export vmanage_username=admin")
    print("export vmanage_password=admin")
    exit()


class Authentication:

    @staticmethod
    def get_jsessionid(vmanage_host, vmanage_port, username, password):
        api = "/j_security_check"
        base_url = "https://%s:%s"%(vmanage_host, vmanage_port)
        url = base_url + api
        payload = {'j_username' : username, 'j_password' : password}
        
        response = requests.post(url=url, data=payload, verify=False)
        try:
            cookies = response.headers["Set-Cookie"]
            jsessionid = cookies.split(";")
            return(jsessionid[0])
        except:
            if logger is not None:
                logger.error("No valid JSESSION ID returned\n")
            exit()
       
    @staticmethod
    def get_token(vmanage_host, vmanage_port, jsessionid):
        headers = {'Cookie': jsessionid}
        base_url = "https://%s:%s"%(vmanage_host, vmanage_port)
        api = "/dataservice/client/token"
        url = base_url + api      
        response = requests.get(url=url, headers=headers, verify=False)
        if response.status_code == 200:
            return(response.text)
        else:
            return None

Auth = Authentication()
jsessionid = Auth.get_jsessionid(vmanage_host,vmanage_port,vmanage_username,vmanage_password)
token = Auth.get_token(vmanage_host,vmanage_port,jsessionid)

if token is not None:
    header = {'Content-Type': "application/json",'Cookie': jsessionid, 'X-XSRF-TOKEN': token}
else:
    header = {'Content-Type': "application/json",'Cookie': jsessionid}

base_url = "https://%s:%s/dataservice"%(vmanage_host, vmanage_port)

@click.group()
def cli():
    """Command line tool for retrieving CLI diff in Audit logs.
    """
    pass

@click.command()
def auditlog_fields():
    """ Retrieve Audit log Query fields.                                  
        \nExample command: ./audit-logs.py auditlog_fields
    """

    try:
        api_url = "/auditlog/fields"

        url = base_url + api_url

        response = requests.get(url=url, headers=header, verify=False)

        if response.status_code == 200:
            items = response.json()
        else:
            click.echo("Failed to get list of Audit Log Query fields " + str(response.text))
            exit()

        tags = list()
        cli = cmd.Cmd()

        for item in items:
            tags.append(item['property'] + "(" + item['dataType'] + ")" )

        click.echo("")
        click.echo(cli.columnize(tags,displaywidth=120))

    except Exception as e:
        print('Exception line number: {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

@click.command()
def list_auditlogs():
    """ Retrieve CLI diff in Audit log.                                  
        \nExample command: ./audit-logs.py list_auditlogs
    """

    try:
        api_url = "/auditlog/severity"

        query = {
                    "query": {
                        "condition": "AND",
                        "rules": [
                        {
                            "value": [
                            "1"
                            ],
                            "field": "entry_time",
                            "type": "date",
                            "operator": "last_n_hours"
                        },
                        {
                            "value": [
                            "template"
                            ],
                            "field": "logmodule",
                            "type": "string",
                            "operator": "in"
                        }
                        ]
                     }
                  }

        url = base_url + api_url

        response = requests.get(url=url, headers=header, verify=False,  params={"query":json.dumps(query)})
        config_diff_ids = list()
        if response.status_code == 200:
            items = response.json()["data"]
            for item in items:
                if item.get("auditextras"):
                    config_diff_ids.append(item["auditextras"])
        else:
            click.echo("Failed to get list of Audit Logs" + str(response.text))
            exit()
        
        for item in config_diff_ids:

            temp = json.loads(item)
            api_url = "/device/history/config/diff/list?config_id1=%s&config_id2=%s"%(temp['config_id_0'],temp['config_id_1'])

            url = base_url + api_url
            response = requests.get(url=url, headers=header, verify=False)

            if response.status_code == 200:
                temp = response.json()
                config_old = temp[0]['config_1'].splitlines()
                config_new = temp[1]['config_2'].splitlines()
                for line in difflib.unified_diff(config_old, config_new):
                    click.echo(line)
            else:
                click.echo("Failed to get list of Audit Logs configuration diff details" + str(response.text))
                exit()

    except Exception as e:
        print('Exception line number: {}'.format(sys.exc_info()[-1].tb_lineno), type(e).__name__, e)

cli.add_command(auditlog_fields)
cli.add_command(list_auditlogs)


if __name__ == "__main__":
    cli()



