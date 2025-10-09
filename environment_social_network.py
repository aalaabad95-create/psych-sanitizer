"""منصة تواصل اجتماعي مبسطة لهيئة البيئة باستخدام Flask.

يوفر هذا الملف تطبيق Flask صغير يحاكي الوظائف الأساسية لمنصة تواصل
اجتماعي: تسجيل المستخدمين، نشر المحتوى، إنشاء فعاليات بيئية،
واستخراج تغذية إخبارية مخصصة اعتمادًا على الاهتمامات.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import hashlib
import secrets
import uuid

from flask import Flask, jsonify, request


def _utc_now() -> datetime:
    """إرجاع الوقت الحالي بتوقيت UTC."""

    return datetime.utcnow().replace(tzinfo=None)


@dataclass
class User:
    id: str
    name: str
    username: str
    email: str
    role: str
    password_hash: str
    interests: List[str] = field(default_factory=list)
    joined_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["joined_at"] = self.joined_at.isoformat() + "Z"
        payload.pop("password_hash", None)
        return payload


@dataclass
class Post:
    id: str
    author_id: str
    topic: str
    content: str
    created_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["created_at"] = self.created_at.isoformat() + "Z"
        return payload


@dataclass
class Event:
    id: str
    title: str
    description: str
    location: str
    start_time: datetime
    created_by: str
    created_at: datetime = field(default_factory=_utc_now)

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["start_time"] = self.start_time.isoformat() + "Z"
        payload["created_at"] = self.created_at.isoformat() + "Z"
        return payload


class SocialNetwork:
    """إدارة بسيطة للبيانات داخل الذاكرة."""

    def __init__(self) -> None:
        self._users: Dict[str, User] = {}
        self._posts: List[Post] = []
        self._events: List[Event] = []
        self._sessions: Dict[str, str] = {}

    # ---- المستخدمون -----------------------------------------------------
    @staticmethod
    def _hash_password(password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
        return f"{salt}${digest}"

    @staticmethod
    def _verify_password(password: str, hashed: str) -> bool:
        try:
            salt, digest = hashed.split("$")
        except ValueError:
            return False
        expected = hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()
        return secrets.compare_digest(expected, digest)

    def _is_unique_username(self, username: str) -> bool:
        return all(user.username.lower() != username.lower() for user in self._users.values())

    def _is_unique_email(self, email: str) -> bool:
        return all(user.email.lower() != email.lower() for user in self._users.values())

    def register_user(
        self,
        name: str,
        username: str,
        email: str,
        role: str,
        password: str,
        interests: List[str],
    ) -> User:
        if not self._is_unique_username(username):
            raise ValueError("username-taken")
        if not self._is_unique_email(email):
            raise ValueError("email-taken")
        user_id = uuid.uuid4().hex
        user = User(
            id=user_id,
            name=name.strip(),
            username=username.strip(),
            email=email.strip(),
            role=role.strip(),
            password_hash=self._hash_password(password),
            interests=interests,
        )
        self._users[user.id] = user
        return user

    def list_users(self) -> List[User]:
        return list(self._users.values())

    def get_user(self, user_id: str) -> User | None:
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        username_lower = username.lower()
        for user in self._users.values():
            if user.username.lower() == username_lower:
                return user
        return None

    def login(self, username: str, password: str) -> str:
        user = self.get_user_by_username(username)
        if not user or not self._verify_password(password, user.password_hash):
            raise ValueError("invalid-credentials")
        token = secrets.token_urlsafe(24)
        self._sessions[token] = user.id
        return token

    def logout(self, token: str) -> bool:
        return self._sessions.pop(token, None) is not None

    def user_id_from_token(self, token: str) -> Optional[str]:
        return self._sessions.get(token)

    # ---- المحتوى --------------------------------------------------------
    def add_post(self, author_id: str, topic: str, content: str) -> Post:
        if author_id not in self._users:
            raise ValueError("author-not-found")
        post = Post(id=uuid.uuid4().hex, author_id=author_id, topic=topic.strip(), content=content.strip())
        self._posts.append(post)
        return post

    def feed_for(self, user_id: str | None = None) -> List[Post]:
        if user_id and user_id in self._users:
            user_interests = {interest.lower() for interest in self._users[user_id].interests}
            if user_interests:
                posts = [
                    post
                    for post in self._posts
                    if post.topic.lower() in user_interests or post.topic.lower().startswith(tuple(user_interests))
                ]
            else:
                posts = list(self._posts)
        else:
            posts = list(self._posts)
        return sorted(posts, key=lambda p: p.created_at, reverse=True)

    # ---- الفعاليات ------------------------------------------------------
    def add_event(
        self,
        title: str,
        description: str,
        location: str,
        start_time: datetime,
        created_by: str,
    ) -> Event:
        if created_by not in self._users:
            raise ValueError("creator-not-found")
        event = Event(
            id=uuid.uuid4().hex,
            title=title.strip(),
            description=description.strip(),
            location=location.strip(),
            start_time=start_time,
            created_by=created_by,
        )
        self._events.append(event)
        return event

    def list_events(self) -> List[Event]:
        return sorted(self._events, key=lambda e: e.start_time)


def _parse_interests(raw: object) -> List[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        return [part.strip() for part in raw.split(",") if part.strip()]
    raise TypeError("interests must be a list or comma-separated string")


def _parse_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", ""))
    except ValueError as exc:
        raise ValueError("invalid-datetime") from exc


def create_app() -> Flask:
    app = Flask(__name__)
    network = SocialNetwork()

    @app.post("/users")
    def register_user():
        payload = request.get_json(force=True)
        name = payload.get("name", "").strip()
        username = payload.get("username", "").strip()
        email = payload.get("email", "").strip()
        role = payload.get("role", "").strip()
        password = payload.get("password", "")
        try:
            interests = _parse_interests(payload.get("interests"))
        except TypeError:
            return jsonify({"error": "invalid-interests"}), 400
        if not all([name, username, email, role, password]):
            return jsonify({"error": "missing-required-fields"}), 400
        try:
            user = network.register_user(
                name=name,
                username=username,
                email=email,
                role=role,
                password=password,
                interests=interests,
            )
        except ValueError as exc:
            message = str(exc)
            status = 409 if message in {"username-taken", "email-taken"} else 400
            return jsonify({"error": message}), status
        return jsonify(user.to_dict()), 201

    @app.get("/users")
    def list_users():
        return jsonify([user.to_dict() for user in network.list_users()])

    @app.post("/posts")
    def create_post():
        payload = request.get_json(force=True)
        author_id = payload.get("author_id")
        topic = payload.get("topic", "").strip()
        content = payload.get("content", "").strip()
        if not author_id or not topic or not content:
            return jsonify({"error": "author-topic-content-required"}), 400
        try:
            post = network.add_post(author_id=author_id, topic=topic, content=content)
        except ValueError:
            return jsonify({"error": "author-not-found"}), 404
        return jsonify(post.to_dict()), 201

    @app.get("/feed")
    def get_feed():
        user_id = request.args.get("user_id")
        token = request.args.get("token")
        if token and not user_id:
            user_id = network.user_id_from_token(token)
        posts = network.feed_for(user_id=user_id)
        return jsonify([post.to_dict() for post in posts])

    @app.post("/events")
    def create_event():
        payload = request.get_json(force=True)
        required = ("title", "description", "location", "start_time", "created_by")
        if not all(payload.get(key) for key in required):
            return jsonify({"error": "missing-required-fields"}), 400
        try:
            start_time = _parse_datetime(payload["start_time"])
            event = network.add_event(
                title=payload["title"],
                description=payload["description"],
                location=payload["location"],
                start_time=start_time,
                created_by=payload["created_by"],
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400 if str(exc) == "invalid-datetime" else 404
        return jsonify(event.to_dict()), 201

    @app.get("/events")
    def list_events():
        return jsonify([event.to_dict() for event in network.list_events()])

    @app.post("/auth/login")
    def login():
        payload = request.get_json(force=True)
        username = payload.get("username", "").strip()
        password = payload.get("password", "")
        if not username or not password:
            return jsonify({"error": "missing-credentials"}), 400
        try:
            token = network.login(username=username, password=password)
        except ValueError:
            return jsonify({"error": "invalid-credentials"}), 401
        return jsonify({"token": token}), 200

    @app.post("/auth/logout")
    def logout():
        payload = request.get_json(force=True)
        token = payload.get("token")
        if not token:
            return jsonify({"error": "token-required"}), 400
        if not network.logout(token):
            return jsonify({"error": "invalid-token"}), 404
        return jsonify({"status": "logged-out"}), 200

    @app.get("/")
    def home():
        return jsonify(
            {
                "message": "منصة هيئة البيئة للتواصل الاجتماعي (نسخة تجريبية)",
                "endpoints": [
                    "GET /users",
                    "POST /users",
                    "POST /posts",
                    "GET /feed",
                    "POST /events",
                    "GET /events",
                    "POST /auth/login",
                    "POST /auth/logout",
                ],
            }
        )

    return app


if __name__ == "__main__":
    create_app().run(host="0.0.0.0", port=5001, debug=True)
