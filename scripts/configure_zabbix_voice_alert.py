#!/usr/bin/env python3
import argparse
import json
import sys
import urllib.request


def rpc(url, token, method, params, req_id=1):
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": req_id,
    }
    if token is not None:
        payload["auth"] = token

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json-rpc"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if "error" in result:
        raise RuntimeError(f"RPC error {method}: {result['error']}")
    return result["result"]


def build_script_params(args):
    only_problem = "0" if args.with_recovery else "1"
    return [
        "{ALERT.SENDTO}",
        "{ALERT.SUBJECT}",
        "{ALERT.MESSAGE}",
        "{EVENT.VALUE}",
        args.ami_host,
        str(args.ami_port),
        args.ami_user,
        args.ami_secret,
        args.channel_template,
        args.context,
        "s",
        "1",
        args.callerid,
        str(args.timeout_ms),
        only_problem,
        args.voice,
        str(args.speed),
        str(args.max_chars),
        "{EVENT.ID}",
        str(args.dedupe_ttl),
        args.text_mode,
        str(args.repeat),
    ]


def ensure_media_type(api_url, token, args):
    name = args.media_type_name
    existing = rpc(
        api_url,
        token,
        "mediatype.get",
        {
            "output": ["mediatypeid", "name", "type"],
            "filter": {"name": [name]},
        },
    )

    params = {
        "name": name,
        "type": 1,
        "script_name": "zbxAsteriskCall.py",
        "script_params": build_script_params(args),
        "timeout": "30s",
    }

    if existing:
        mediatypeid = existing[0]["mediatypeid"]
        rpc(api_url, token, "mediatype.update", {"mediatypeid": mediatypeid, **params})
        return mediatypeid, "updated"

    created = rpc(api_url, token, "mediatype.create", params)
    return created["mediatypeids"][0], "created"


def ensure_action(api_url, token, args, mediatypeid):
    action_name = args.action_name
    existing = rpc(
        api_url,
        token,
        "action.get",
        {
            "output": ["actionid", "name"],
            "filter": {"name": [action_name]},
        },
    )

    # conditiontype=5 => trigger severity, operator=5 => >=
    # operationtype=0 => send message
    action_payload = {
        "name": action_name,
        "eventsource": 0,
        "status": 0,
        "esc_period": "5m",
        "filter": {
            "evaltype": 0,
            "conditions": [
                {
                    "conditiontype": 5,
                    "operator": 5,
                    "value": str(args.min_severity),
                }
            ],
        },
        "operations": [
            {
                "operationtype": 0,
                "opmessage": {
                    "default_msg": 1,
                    "mediatypeid": mediatypeid,
                },
                "opmessage_usr": [],
                "opmessage_grp": [{"usrgrpid": args.usergroup_id}],
            }
        ],
    }

    if existing:
        actionid = existing[0]["actionid"]
        rpc(api_url, token, "action.update", {"actionid": actionid, **action_payload})
        return actionid, "updated"

    created = rpc(api_url, token, "action.create", action_payload)
    return created["actionids"][0], "created"


def main():
    p = argparse.ArgumentParser(description="Configure Zabbix media type/action for Asterisk voice alerts")
    p.add_argument("--api-url", default="http://127.0.0.1/zabbix/api_jsonrpc.php")
    p.add_argument("--username", required=True)
    p.add_argument("--password", required=True)

    p.add_argument("--media-type-name", default="Asterisk Voice Call")
    p.add_argument("--action-name", default="Voice alerts: provider network incidents")
    p.add_argument("--usergroup-id", required=True, help="Zabbix user group ID for responsible team")
    p.add_argument("--min-severity", type=int, default=4, help="0..5 (default 4=High)")

    p.add_argument("--ami-host", required=True)
    p.add_argument("--ami-port", type=int, default=5038)
    p.add_argument("--ami-user", default="zabbix_call")
    p.add_argument("--ami-secret", required=True)
    p.add_argument("--channel-template", default="PJSIP/{number}@712031212")
    p.add_argument("--context", default="zabbix-alert-call")
    p.add_argument("--callerid", default="Zabbix Alert")
    p.add_argument("--timeout-ms", type=int, default=45000)
    p.add_argument("--with-recovery", action="store_true", help="Call on recovery too")
    p.add_argument("--voice", default="ru", choices=["ru", "uz"])
    p.add_argument("--speed", type=int, default=145)
    p.add_argument("--max-chars", type=int, default=420)
    p.add_argument("--dedupe-ttl", type=int, default=900)
    p.add_argument("--text-mode", default="summary", choices=["fast", "subject", "summary"])
    p.add_argument("--repeat", type=int, default=2)

    args = p.parse_args()

    token = rpc(args.api_url, None, "user.login", {"username": args.username, "password": args.password})
    mediatype_id, mediatype_mode = ensure_media_type(args.api_url, token, args)
    action_id, action_mode = ensure_action(args.api_url, token, args, mediatype_id)
    rpc(args.api_url, token, "user.logout", [])

    print(
        f"OK: media_type {mediatype_mode} id={mediatype_id}; "
        f"action {action_mode} id={action_id}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
