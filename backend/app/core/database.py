"""
Database connection – SQLAlchemy async engine + session factory
"""
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, JSON, ForeignKey, Text, Uuid
import uuid
from datetime import datetime, timezone

# ─────────────────────────────────────────────
# DATABASE URL (read from env, fallback to local dev)
# ─────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./neurorelief.db"
)

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ─────────────────────────────────────────────
# Dependency: get DB session (FastAPI DI)
# ─────────────────────────────────────────────
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ─────────────────────────────────────────────
# SQLAlchemy ORM Models (mirror schema.sql)
# ─────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


class Signal(Base):
    __tablename__ = "signals"

    id                    = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    issue_type            = Column(String(100), nullable=False)
    center_lat            = Column(Float, nullable=False)
    center_lon            = Column(Float, nullable=False)
    report_count          = Column(Integer, default=1)
    base_severity         = Column(Float, default=1.0)
    urgency_score         = Column(Float, default=0.0)
    priority_score        = Column(Float, default=0.0)
    status                = Column(String(50), default="open")
    first_seen            = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_updated          = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    assigned_volunteer_id = Column(Uuid(as_uuid=True), ForeignKey("volunteers.id"), nullable=True)


class Report(Base):
    __tablename__ = "reports"

    id            = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    location_lat  = Column(Float, nullable=False)
    location_lon  = Column(Float, nullable=False)
    issue_type    = Column(String(100), nullable=False)
    description   = Column(Text, nullable=False)
    severity      = Column(Integer, default=1)
    timestamp     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    signal_id     = Column(Uuid(as_uuid=True), ForeignKey("signals.id"), nullable=True)
    reporter_name = Column(String(100), nullable=True)
    created_at    = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Volunteer(Base):
    __tablename__ = "volunteers"

    id           = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name         = Column(String(150), nullable=False)
    email        = Column(String(200), unique=True, nullable=True)
    skills       = Column(JSON, default=list)
    languages    = Column(JSON, default=list)
    location_lat = Column(Float, nullable=False)
    location_lon = Column(Float, nullable=False)
    trust_score  = Column(Float, default=0.5)
    is_available = Column(Boolean, default=True)
    created_at   = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class Assignment(Base):
    __tablename__ = "assignments"

    id             = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signal_id      = Column(Uuid(as_uuid=True), ForeignKey("signals.id"), nullable=False)
    volunteer_id   = Column(Uuid(as_uuid=True), ForeignKey("volunteers.id"), nullable=False)
    match_score    = Column(Float, default=0.0)
    skill_score    = Column(Float, default=0.0)
    distance_score = Column(Float, default=0.0)
    language_score = Column(Float, default=0.0)
    trust_score    = Column(Float, default=0.0)
    status         = Column(String(50), default="suggested")
    created_at     = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


async def test_sql_connection() -> bool:
    """Test if the SQL database is reachable and responsive."""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        import logging
        logging.getLogger("neurorelief.database").error(f"SQL connection test failed: {e}")
        return False


async def init_db():
    """Create all tables (dev helper – use Alembic in production)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
