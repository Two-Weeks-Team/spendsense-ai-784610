import os
import uuid
from datetime import datetime, date
from typing import Optional, List, Any

from dotenv import load_dotenv
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Date,
    Boolean,
    Numeric,
    Float,
    JSON,
    ForeignKey,
    Index,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, Session
from pydantic import BaseModel, Field

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", os.getenv("POSTGRES_URL", "sqlite:///./app.db")
)

if DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgresql+asyncpg://", "postgresql+psycopg://", 1
    )
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+psycopg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

if "?ssl=" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("?ssl=", "?sslmode=")
if "&ssl=" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("&ssl=", "&sslmode=")

connect_args: dict = {}
if (
    "sqlite" not in DATABASE_URL
    and "localhost" not in DATABASE_URL
    and "sslmode" not in DATABASE_URL
    and "ssl" not in DATABASE_URL
):
    connect_args["sslmode"] = "require"

engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class User(Base):
    __tablename__ = "ss_users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_login = Column(DateTime(timezone=True), nullable=True)
    subscription_status = Column(String(50), nullable=False, server_default="free")
    auth_token = Column(String, nullable=True, index=True)
    reset_token = Column(String, nullable=True, index=True)

    transactions = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    reports = relationship(
        "WeeklyReport", back_populates="user", cascade="all, delete-orphan"
    )


class Transaction(Base):
    __tablename__ = "ss_transactions"
    __table_args__ = (
        Index("ix_ss_transactions_user_id", "user_id"),
        Index("ix_ss_transactions_date", "date"),
        Index("ix_ss_transactions_predicted_category", "predicted_category"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ss_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(String, nullable=False)
    predicted_category = Column(String(100), nullable=False)
    user_overridden_category = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    raw_csv_data = Column(String, nullable=False)
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="transactions")
    prediction = relationship(
        "Prediction",
        uselist=False,
        back_populates="transaction",
        cascade="all, delete-orphan",
    )


class ModelVersion(Base):
    __tablename__ = "ss_model_versions"
    __table_args__ = (Index("ix_ss_model_versions_active", "is_active"),)

    version = Column(String(50), primary_key=True)
    description = Column(String, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_active = Column(Boolean, nullable=False, default=False)


class Prediction(Base):
    __tablename__ = "ss_predictions"
    __table_args__ = (
        Index("ix_ss_predictions_transaction_id", "transaction_id"),
        Index("ix_ss_predictions_category", "category"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ss_transactions.id", ondelete="CASCADE"),
        nullable=False,
    )
    category = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(JSON, nullable=False)

    transaction = relationship("Transaction", back_populates="prediction")


class WeeklyReport(Base):
    __tablename__ = "ss_weekly_reports"
    __table_args__ = (
        Index("ix_ss_reports_user_id", "user_id"),
        Index("ix_ss_reports_start_end", "start_date", "end_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ss_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_spending = Column(Numeric(15, 2), nullable=False)
    category_breakdown = Column(JSONB, nullable=False)
    savings_recommendations = Column(JSONB, nullable=False)
    generated_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user = relationship("User", back_populates="reports")
    recommendations = relationship(
        "Recommendation", back_populates="report", cascade="all, delete-orphan"
    )


class Recommendation(Base):
    __tablename__ = "ss_recommendations"
    __table_args__ = (
        Index("ix_ss_recommendations_report_id", "report_id"),
        Index("ix_ss_recommendations_type", "recommendation_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("ss_weekly_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    recommendation_type = Column(String(50), nullable=False)
    description = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(JSON, nullable=False)
    user_accepted = Column(Boolean, nullable=True)

    report = relationship("WeeklyReport", back_populates="recommendations")


class TransactionCreate(BaseModel):
    date: date
    description: str
    amount: float
    raw_csv_data: str


class TransactionOut(BaseModel):
    id: uuid.UUID
    date: date
    description: str
    amount: float
    predicted_category: str = Field(..., description="Category from AI model")
    confidence_score: float
    user_overridden_category: Optional[str] = None

    model_config = {"from_attributes": True}


class CategorizeRequest(BaseModel):
    upload_id: str
    model_version: Optional[str] = None


class CategorizeResponse(BaseModel):
    transactions: List[TransactionOut]
    model_used: str


class SavingsPlanRequest(BaseModel):
    user_id: uuid.UUID
    timeframe_start: date
    timeframe_end: date


class SavingsPlanItem(BaseModel):
    description: str
    confidence: float
    estimated_monthly_savings: float


class SavingsPlanResponse(BaseModel):
    recommendations: List[SavingsPlanItem]
    model_used: str


class WeeklyReportResponse(BaseModel):
    start_date: date
    end_date: date
    total_spending: float
    category_breakdown: dict[str, float]
    savings_recommendations: List[dict]
    generated_at: datetime

    model_config = {"from_attributes": True}
