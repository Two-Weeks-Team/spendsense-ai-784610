import uuid
from datetime import datetime, date
from typing import Optional, List, Any

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
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# ---------------------------------------------------------------------
# User model (simplified – authentication omitted for brevity)
# ---------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    subscription_status = Column(String(50), nullable=False, server_default="free")
    auth_token = Column(String, nullable=True, index=True)
    reset_token = Column(String, nullable=True, index=True)

    transactions: List["Transaction"] = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    reports: List["WeeklyReport"] = relationship("WeeklyReport", back_populates="user", cascade="all, delete-orphan")

# ---------------------------------------------------------------------
# Transaction model – raw CSV rows and AI predictions
# ---------------------------------------------------------------------
class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_id", "user_id"),
        Index("ix_transactions_date", "date"),
        Index("ix_transactions_predicted_category", "predicted_category"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    description = Column(String, nullable=False)
    predicted_category = Column(String(100), nullable=False)
    user_overridden_category = Column(String(100), nullable=True)
    model_version = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    raw_csv_data = Column(String, nullable=False)  # encrypted before storage (handled in service layer)
    processed = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="transactions")
    prediction = relationship("Prediction", uselist=False, back_populates="transaction", cascade="all, delete-orphan")

# ---------------------------------------------------------------------
# ModelVersions – tracks which model was used for a given inference batch
# ---------------------------------------------------------------------
class ModelVersion(Base):
    __tablename__ = "model_versions"
    __table_args__ = (Index("ix_model_versions_active", "is_active"),)

    version = Column(String(50), primary_key=True)
    description = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)

# ---------------------------------------------------------------------
# Prediction – separates raw AI output from the transaction table
# ---------------------------------------------------------------------
class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (
        Index("ix_predictions_transaction_id", "transaction_id"),
        Index("ix_predictions_category", "category"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(JSON, nullable=False)  # JSON‑blob with model rationale

    transaction = relationship("Transaction", back_populates="prediction")

# ---------------------------------------------------------------------
# WeeklyReport – aggregated view of a user’s spending period
# ---------------------------------------------------------------------
class WeeklyReport(Base):
    __tablename__ = "weekly_reports"
    __table_args__ = (
        Index("ix_reports_user_id", "user_id"),
        Index("ix_reports_start_end", "start_date", "end_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_spending = Column(Numeric(15, 2), nullable=False)
    category_breakdown = Column(JSONB, nullable=False)  # {"Groceries": 123.45, ...}
    savings_recommendations = Column(JSONB, nullable=False)  # list of recommendation objects
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="reports")
    recommendations = relationship("Recommendation", back_populates="report", cascade="all, delete-orphan")

# ---------------------------------------------------------------------
# Recommendation – individual AI‑generated tips attached to a report
# ---------------------------------------------------------------------
class Recommendation(Base):
    __tablename__ = "recommendations"
    __table_args__ = (
        Index("ix_recommendations_report_id", "report_id"),
        Index("ix_recommendations_type", "recommendation_type"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id = Column(UUID(as_uuid=True), ForeignKey("weekly_reports.id", ondelete="CASCADE"), nullable=False)
    recommendation_type = Column(String(50), nullable=False)  # e.g., "budget_tweak" or "savings_idea"
    description = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(JSON, nullable=False)
    user_accepted = Column(Boolean, nullable=True)

    report = relationship("WeeklyReport", back_populates="recommendations")

# ---------------------------------------------------------------------
# Pydantic schemas (request/response models)
# ---------------------------------------------------------------------
from pydantic import BaseModel, Field
from datetime import date as pydate

class TransactionCreate(BaseModel):
    date: pydate
    description: str
    amount: float
    raw_csv_data: str

class TransactionOut(BaseModel):
    id: uuid.UUID
    date: pydate
    description: str
    amount: float
    predicted_category: str = Field(..., description="Category from AI model")
    confidence_score: float
    user_overridden_category: Optional[str] = None

    class Config:
        orm_mode = True

class CategorizeRequest(BaseModel):
    upload_id: str  # reference to a CSV processing batch – simplified for demo
    model_version: Optional[str] = None

class CategorizeResponse(BaseModel):
    transactions: List[TransactionOut]
    model_used: str

class SavingsPlanRequest(BaseModel):
    user_id: uuid.UUID
    timeframe_start: pydate
    timeframe_end: pydate

class SavingsPlanItem(BaseModel):
    description: str
    confidence: float
    estimated_monthly_savings: float

class SavingsPlanResponse(BaseModel):
    recommendations: List[SavingsPlanItem]
    model_used: str

class WeeklyReportResponse(BaseModel):
    start_date: pydate
    end_date: pydate
    total_spending: float
    category_breakdown: dict[str, float]
    savings_recommendations: List[dict]
    generated_at: datetime

    class Config:
        orm_mode = True
