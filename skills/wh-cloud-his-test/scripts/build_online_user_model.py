#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys


DEFAULT_TOKEN = "codex-cloud-his-dev-token"
DEFAULT_USER_ID = "codex-dev-user"
DEFAULT_USER_CODE = "codex"
DEFAULT_USER_NAME = "Codex Dev"
DEFAULT_APP_ID = "HIS-PC"
DEFAULT_LOGIN_SOFT_ID = "10001"
DEFAULT_LOGIN_OFFICE_CODE = "DEV"
DEFAULT_LOGIN_OFFICE_NAME = "开发联调科室"
DEFAULT_TTL_SECONDS = 604800
ONLINE_USER_TYPE = "com.whxx.base.domain.bo.OnlineUserModel"


def build_payload(args):
    payload = {
        "@type": ONLINE_USER_TYPE,
        "token": args.token,
        "loginSuccess": 1,
        "hospitalId": args.hospital_id,
        "hospitalName": args.hospital_name,
        "userId": args.user_id,
        "userCode": args.user_code,
        "userName": args.user_name,
        "appId": args.app_id,
        "loginSoftId": args.login_soft_id,
        "loginOfficeCode": args.login_office_code,
        "loginOfficeName": args.login_office_name,
    }
    if args.login_office_id:
        payload["loginOfficeId"] = args.login_office_id
    if args.login_ward_code:
        payload["loginWardCode"] = args.login_ward_code
    if args.login_ward_name:
        payload["loginWardName"] = args.login_ward_name
    if args.job_title:
        payload["jobTitle"] = args.job_title
    if args.job_title_name:
        payload["jobTitleName"] = args.job_title_name
    return payload


def apply_to_redis(args, payload_json):
    key = f"TOKEN:SYS:{args.token}"
    cmd = [
        "redis-cli",
        "-h",
        args.redis_host,
        "-p",
        str(args.redis_port),
    ]
    if args.redis_password:
        cmd.extend(["-a", args.redis_password])
    if args.redis_db is not None:
        cmd.extend(["-n", str(args.redis_db)])
    cmd.extend(["SETEX", key, str(args.ttl_seconds), payload_json])
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        sys.exit(result.returncode)
    print("Redis 写入结果:")
    print(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description="构建 cloud_his OnlineUserModel 测试 token")
    parser.add_argument("--token", default=DEFAULT_TOKEN)
    parser.add_argument("--hospital-id", required=True)
    parser.add_argument("--hospital-name", required=True)
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    parser.add_argument("--user-code", default=DEFAULT_USER_CODE)
    parser.add_argument("--user-name", default=DEFAULT_USER_NAME)
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--login-soft-id", default=DEFAULT_LOGIN_SOFT_ID)
    parser.add_argument("--login-office-id")
    parser.add_argument("--login-office-code", default=DEFAULT_LOGIN_OFFICE_CODE)
    parser.add_argument("--login-office-name", default=DEFAULT_LOGIN_OFFICE_NAME)
    parser.add_argument("--login-ward-code")
    parser.add_argument("--login-ward-name")
    parser.add_argument("--job-title")
    parser.add_argument("--job-title-name")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6379)
    parser.add_argument("--redis-db", type=int, default=0)
    parser.add_argument("--redis-password")
    parser.add_argument("--ttl-seconds", type=int, default=DEFAULT_TTL_SECONDS)
    args = parser.parse_args()

    payload = build_payload(args)
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    redis_key = f"TOKEN:SYS:{args.token}"

    print("Redis Key:")
    print(redis_key)
    print()
    print("Header:")
    print(f"token: {args.token}")
    print()
    print("Payload:")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print()
    print("Single-line Payload:")
    print(payload_json)

    if args.apply:
        print()
        apply_to_redis(args, payload_json)


if __name__ == "__main__":
    main()
