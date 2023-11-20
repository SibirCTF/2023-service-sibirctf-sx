import logging
from pathlib import Path
import dataclasses
from typing import ClassVar
from enum import Enum

import requests

from exceptions import DataIsCorrupt


logger = logging.getLogger("SX.Checker")


class Gender(Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


@dataclasses.dataclass
class User:
    username: str
    fullname: str
    bio: str
    password: str | None = None
    gender: Gender | None = None
    avatar: str | None = None
    id: str | None = None


@dataclasses.dataclass
class Post:
    title: str
    content: str
    is_private: bool
    author: str
    created_at: str | None = None
    updated_at: str | None = None
    repost_on: str | None = None
    id: str | None = None


class SXClient:
    base_url: str
    port: ClassVar[int] = 3080
    timeout: ClassVar[int] = 3
    session: requests.Session
    current_user: User
    logger: logging.Logger

    def __init__(self, host: str, user: User) -> None:
        self.session = requests.session()
        self.base_url = f"http://{host}:{self.port}"
        body = {
            "grant_type": "password",
            "username": user.username,
            "password": user.password,
        }
        r = self.session.post(
            f"{self.base_url}/session", data=body, timeout=self.timeout
        )
        r.raise_for_status()
        self.session.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
        self.logger = logger.getChild(host)
        self.logger.info("%s is authorised", user.username)
        self.current_user = user

    @classmethod
    def register_user(cls, host: str, user: User) -> None:
        base_url = f"http://{host}:{cls.port}"
        body = {
            "username": user.username,
            "password": user.password,
            "fullname": user.fullname,
            "bio": user.bio,
        }
        r = requests.post(f"{base_url}/users", json=body, timeout=cls.timeout)

        class_logger = logger.getChild(host)

        # don't raise on existed user
        if r.status_code != 400 or r.json() != {
            "detail": f"User {user.username} already registered"
        }:
            user.id = r.json()["id"]
            r.raise_for_status()
            class_logger.info("%s is registered", user.username)
        else:
            class_logger.info("%s is already exists", user.username)

    def refresh_user_parameters(self, user: User) -> None:
        if user.id is not None:
            return
        username = user.username.replace("#", "%23")
        r = self.session.get(
            f"{self.base_url}/users/by_username/{username}", timeout=self.timeout
        )
        r.raise_for_status()
        user.id = r.json()["id"]
        user.avatar = r.json()["avatar"]

    def upload_avatar(self, avatar: Path) -> None:
        files = {"file": ("ava.png", open(avatar, "rb"), "image/png")}
        r = self.session.post(
            f"{self.base_url}/users/avatar", files=files, timeout=self.timeout
        )
        r.raise_for_status()
        self.current_user.avatar = r.json()["avatar"]
        self.logger.info(
            "%s uploaded his avatar (%s)",
            self.current_user.username,
            self.current_user.avatar,
        )

    def download_avatar(self, user: User) -> None:
        r = self.session.get(f"{self.base_url}{user.avatar}", timeout=self.timeout)
        r.raise_for_status()
        if b"PNG" not in r.content:
            raise DataIsCorrupt(f"Seems that it isn't a png file ({user.avatar})")
        self.logger.info("%s user's avatar is  %s checked", user.username, user.avatar)

    def subscribe_on(self, user: User) -> None:
        r = self.session.put(
            f"{self.base_url}/subscribes/{user.id}", timeout=self.timeout
        )
        r.raise_for_status()
        self.logger.info(
            "%s is subscribed on %s",
            self.current_user.username,
            user.username,
        )

    def public_post(
        self, title: str, content: str, is_private: bool, repost_on: str | None = None
    ) -> None:
        body = {
            "title": title,
            "content": content,
            "is_private": is_private,
            "repost_on": repost_on,
        }
        r = self.session.post(f"{self.base_url}/posts", json=body, timeout=self.timeout)
        r.raise_for_status()
        self.logger.info(
            "'%s' post was published by %s",
            title,
            self.current_user.username,
        )

    def get_feed(self) -> list[Post]:
        r = self.session.get(f"{self.base_url}/feed/others", timeout=self.timeout)
        r.raise_for_status()
        return [Post(**post) for post in r.json()]

    def get_my_posts(self) -> list[Post]:
        r = self.session.get(f"{self.base_url}/feed/my", timeout=self.timeout)
        r.raise_for_status()
        return [Post(**post) for post in r.json()]

    def get_post(self, id_: str) -> Post:
        r = self.session.get(f"{self.base_url}/posts/{id_}", timeout=self.timeout)
        r.raise_for_status()
        return Post(**r.json())

    def get_posts_from_profile(self, profile_id: str) -> list[Post]:
        r = self.session.get(
            f"{self.base_url}/posts/user/{profile_id}", timeout=self.timeout
        )
        r.raise_for_status()
        return [Post(**post) for post in r.json()]

    def get_followers(self) -> list[User]:
        r = self.session.get(
            f"{self.base_url}/subscribes/followers", timeout=self.timeout
        )
        r.raise_for_status()
        return [User(**user) for user in r.json()]
