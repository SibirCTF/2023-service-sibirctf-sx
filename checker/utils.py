import hashlib
import os
import random
import uuid
from pathlib import Path

import faker

from sx_client import User, Gender, SXClient, Post
from exceptions import DataIsCorrupt, FlagNotFoundException


fake = faker.Faker()

CHECKER_PATH = Path(os.path.abspath(__file__)).parent
AVATAR_PATH = CHECKER_PATH / "images"
PHRASES_PATH = CHECKER_PATH / "phrases"


def ping(host) -> bool:
    ping_timeout = 2
    response = os.system(f"timeout {ping_timeout}s ping -c 1 {host} > /dev/null 2>&1")
    return response == 0


def hash_uuid(string: str) -> str:
    return str(uuid.UUID(hashlib.sha1(string.encode("utf8")).hexdigest()[:32]))


def hash_int(string: str) -> int:
    return int(hashlib.sha1(string.encode("utf8")).hexdigest(), 16)


def gen_username(flag_id: str, suffix: str) -> str:
    return f"user#{str(hash_int('username1' + flag_id + suffix))[:16]}"


def generate_person(flag_id: str, suffix="1") -> User:
    gender = random.choice([Gender.MALE, Gender.FEMALE])
    username_1 = gen_username(flag_id, suffix)
    user = User(
        username=username_1,
        fullname=fake.name_male() if gender == Gender.MALE else fake.name_female(),
        bio="",
        password=hash_uuid("user" + username_1),
        gender=gender,
    )
    return user


def post_avatar(client: SXClient) -> None:
    avatar_dir = AVATAR_PATH / client.current_user.gender.value.lower()
    avatar_file = random.choice(
        list(file for file in avatar_dir.iterdir() if file.is_file())
    )
    client.upload_avatar(avatar_file)


def post_tweet(client: SXClient, flag: str | None = None) -> None:
    if flag is not None:
        text = f"Oh My God! They Killed Kenny! flag: {flag}"
        is_private = True
    else:
        file = PHRASES_PATH / f"{client.current_user.gender.value.lower()}.txt"
        with file.open() as f:
            text = random.choice(f.read().splitlines())
        is_private = False
    client.public_post(
        title=f"{text[:30]}...",
        content=text,
        is_private=is_private,
    )


def check_that_flag_is_stored(client: SXClient, flag: str) -> None:
    posts = client.get_my_posts()
    if len(posts) < 2:
        raise DataIsCorrupt(f"Checker put 2 posts, but got only {len(posts)}")
    if not is_flag_in_posts(posts, flag):
        raise FlagNotFoundException("Flag is not found in user1's posts")
    client.logger.info(
        "Checked that flag in %s individual posts", client.current_user.username
    )


def check_that_user_in_followers(client: SXClient, username: str):
    users = client.get_followers()
    users_usernames = [user.username for user in users]
    if username not in users_usernames:
        print(users_usernames)
        raise DataIsCorrupt(
            f"Seems that {username}"
            f" is not subscribed at {client.current_user.username}"
        )
    client.logger.info("Checked subscribe")


def check_flag_in_feed(client: SXClient, flag: str) -> str:
    posts = client.get_feed()
    if len(posts) < 2:
        raise DataIsCorrupt(f"Checker put 2 posts, but got only {len(posts)}")
    if not (private_post := is_flag_in_posts(posts, flag)):
        raise FlagNotFoundException("Flag is not found in user2's feed")
    client.logger.info("Checked that flag in feed")
    return private_post.id


def check_flag_in_users_posts(client: SXClient, user: User, flag: str):
    posts = client.get_posts_from_profile(user.id)
    if len(posts) < 2:
        raise DataIsCorrupt(f"Checker put 2 posts, but got only {len(posts)}")
    if not is_flag_in_posts(posts, flag):
        raise FlagNotFoundException("Flag is not found in user1's profile")
    client.logger.info("Checked that flag in user1's profile")


def check_flag_by_post_id(client: SXClient, post_id: str, flag: str):
    post = client.get_post(post_id)
    if flag not in post.content:
        raise FlagNotFoundException("Flag is not found in post profile")
    client.logger.info("Checked that flag is available by post id")


def is_flag_in_posts(posts: list[Post], flag: str) -> Post | None:
    for post in posts:
        if flag in post.content:
            return post
