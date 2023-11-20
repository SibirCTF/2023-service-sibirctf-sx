#!/usr/bin/env python3
import logging
import argparse
from enum import IntEnum

import requests

from exceptions import FlagNotFoundException, DataIsCorrupt
from sx_client import SXClient
from utils import (
    generate_person,
    post_avatar,
    post_tweet,
    ping,
    check_that_flag_is_stored,
    check_that_user_in_followers,
    check_flag_in_feed,
    check_flag_in_users_posts,
    check_flag_by_post_id,
)


logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", level=logging.INFO
)
logger = logging.getLogger("SX Checker")

PUT_COMMAND = "put"
CHECK_COMMAND = "check"


class StatusCode(IntEnum):
    OK = 101
    CORRUPT = 102
    MUMBLE = 103
    DOWN = 104


def put(host: str, flag_id: str, flag: str) -> StatusCode:
    user1 = generate_person(flag_id, "1")
    user2 = generate_person(flag_id, "2")

    SXClient.register_user(host, user1)
    SXClient.register_user(host, user2)
    client1 = SXClient(host, user1)

    client1.refresh_user_parameters(user1)
    client1.refresh_user_parameters(user2)

    post_avatar(client1)
    client1.subscribe_on(user2)
    post_tweet(client1)
    post_tweet(client1, flag=flag)

    check_that_flag_is_stored(client1, flag)

    return StatusCode.OK


def check(host: str, flag_id: str, flag: str) -> StatusCode:
    user1 = generate_person(flag_id, "1")
    user2 = generate_person(flag_id, "2")

    client2 = SXClient(host, user2)

    client2.refresh_user_parameters(user1)
    client2.refresh_user_parameters(user2)

    client2.subscribe_on(user1)

    check_that_user_in_followers(client2, user1.username)
    client2.download_avatar(user1)
    post_id = check_flag_in_feed(client2, flag)
    check_flag_in_users_posts(client2, user1, flag)
    check_flag_by_post_id(client2, post_id, flag)

    return StatusCode.OK


def handler(host: str, command, flag_id: str, flag: str):
    local_logger.info("checker started")

    if not ping(host):
        local_logger.info("host is not answering")
        exit(StatusCode.DOWN)

    if command == PUT_COMMAND:
        status_code = put(host, flag_id, flag)
        local_logger.info("put command has ended with %d status code", status_code)
        exit(status_code)

    if command == CHECK_COMMAND:
        status_code = check(host, flag_id, flag)
        local_logger.info("check command has ended with %d status code", status_code)
        exit(status_code)

    # It's unreal to be there, but ...
    exit(StatusCode.MUMBLE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="SX checker")
    parser.add_argument("host")
    parser.add_argument("command", choices=(PUT_COMMAND, CHECK_COMMAND))
    parser.add_argument("flag_id")
    parser.add_argument("flag")
    args = parser.parse_args()

    local_logger = logger.getChild(args.host)

    try:
        handler(
            host=args.host,
            command=args.command,
            flag_id=args.flag_id,
            flag=args.flag,
        )

    except requests.exceptions.Timeout:
        local_logger.error("Timeout exception")
        exit(StatusCode.MUMBLE)

    except requests.exceptions.ConnectionError:
        local_logger.error("ConnectionError to host. Seems that it isn't work")
        exit(StatusCode.DOWN)

    except requests.exceptions.HTTPError as exc:
        local_logger.error("Service returned error status code %r", exc)
        exit(StatusCode.CORRUPT)

    except FlagNotFoundException as exc:
        local_logger.error("Flag is not found! %r", exc)
        exit(StatusCode.CORRUPT)

    except DataIsCorrupt as exc:
        local_logger.error(
            "Some required data that put before is not found now! %r", exc
        )
        exit(StatusCode.CORRUPT)

    except Exception as exc:
        local_logger.error("Everything is bad :c %r", exc, exc_info=True)
        exit(StatusCode.CORRUPT)
