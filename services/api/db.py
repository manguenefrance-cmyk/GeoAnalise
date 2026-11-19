from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import TypeDecorator

from .config import settings


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class UUIDString(TypeDecorator):
    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(Uuid(as_uuid=False) if dialect.name == "postgresql" else String(36))


class UTCString(TypeDecorator):
    """ISO strings at the API boundary; native timestamptz in PostgreSQL."""

    impl = String(40)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(
            DateTime(timezone=True) if dialect.name == "postgresql" else String(40)
        )

    def process_bind_param(self, value, dialect):
        if value is not None and dialect.name == "postgresql":
            parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
        return value

    def process_result_value(self, value, dialect):
        return value.astimezone(timezone.utc).isoformat() if isinstance(value, datetime) else value


settings.data_dir.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": 30}
    if settings.database_url.startswith("sqlite")
    else {},
    pool_pre_ping=True,
)
Session = sessionmaker(engine, expire_on_commit=False)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_config(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(180))


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True)
    email: Mapped[str] = mapped_column(String(320), default="")
    display_name: Mapped[str] = mapped_column(String(180), default="")
    locale: Mapped[str] = mapped_column(String(2), default="en")
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    created_at: Mapped[str] = mapped_column(UTCString(), default=now)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "organization_id"),)
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    role: Mapped[str] = mapped_column(String(10), default="owner")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    description: Mapped[str] = mapped_column(String(2000), default="")
    status: Mapped[str] = mapped_column(String(10), default="active")
    created_at: Mapped[str] = mapped_column(UTCString(), default=now)
    updated_at: Mapped[str] = mapped_column(UTCString(), default=now)


class AOI(Base):
    __tablename__ = "aoi"
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    geometry: Mapped[dict] = mapped_column(JSON)
    area_km2: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(30), default="geojson")
    created_at: Mapped[str] = mapped_column(UTCString(), default=now)


class Scene(Base):
    __tablename__ = "scenes"
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    item: Mapped[dict] = mapped_column(JSON)
    sample: Mapped[bool] = mapped_column(Boolean, default=False)


class Analysis(Base):
    __tablename__ = "analyses"
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    aoi_id: Mapped[str] = mapped_column(ForeignKey("aoi.id"))
    scene_id: Mapped[str | None] = mapped_column(ForeignKey("scenes.id"), nullable=True)
    operation_kind: Mapped[str] = mapped_column(String(20))
    operation_id: Mapped[str] = mapped_column(String(50))
    params: Mapped[dict] = mapped_column(JSON, default=dict)
    input_analysis_ids: Mapped[list] = mapped_column(JSON, default=list)
    provenance: Mapped[dict] = mapped_column(JSON, default=dict)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(12), default="queued")
    created_at: Mapped[str] = mapped_column(UTCString(), default=now)


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("organization_id", "idempotency_key"),)
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), unique=True)
    idempotency_key: Mapped[str] = mapped_column(String(128))
    request_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(12), default="queued", index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(UTCString(), default=now)
    started_at: Mapped[str | None] = mapped_column(UTCString(), nullable=True)
    finished_at: Mapped[str | None] = mapped_column(UTCString(), nullable=True)


class Usage(Base):
    __tablename__ = "usage_events"
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"), unique=True)
    status: Mapped[str] = mapped_column(String(10), default="reserved")
    created_at: Mapped[str] = mapped_column(UTCString(), default=now)


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), index=True)
    analysis_id: Mapped[str] = mapped_column(ForeignKey("analyses.id"))
    artifact_type: Mapped[str] = mapped_column(String(10))
    storage_key: Mapped[str] = mapped_column(String(300))
    mime_type: Mapped[str] = mapped_column(String(100))
    bytes: Mapped[int] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(UTCString(), default=now)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(UUIDString(), primary_key=True, default=uid)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"))
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[str] = mapped_column(UTCString(), default=now)


def serialize(obj):
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def get_db():
    with Session() as session:
        yield session
