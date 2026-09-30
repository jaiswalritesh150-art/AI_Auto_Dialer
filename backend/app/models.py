from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.database import Base


# =====================================================
# LEAD
# =====================================================

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    zoho_lead_id = Column(
        String(50),
        unique=True,
        nullable=False
    )

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    company = Column(String(255), nullable=True)

    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)

    lead_source = Column(String(100), nullable=True)
    lead_status = Column(String(100), nullable=True)

    # Lead scoring
    lead_score = Column(
        Integer,
        default=0,
        nullable=False
    )

    priority = Column(
        String(20),
        default="LOW",
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# =====================================================
# CALL QUEUE
# =====================================================

class CallQueue(Base):
    __tablename__ = "call_queue"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    lead_id = Column(
        Integer,
        nullable=False
    )

    phone = Column(
        String(30),
        nullable=True
    )

    status = Column(
        String(50),
        default="queued",
        nullable=False
    )

    queued_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    started_at = Column(
        DateTime,
        nullable=True
    )

    completed_at = Column(
        DateTime,
        nullable=True
    )

    failure_reason = Column(
        String(500),
        nullable=True
    )

    # Callback information
    callback_at = Column(
        DateTime,
        nullable=True
    )

    callback_status = Column(
        String(50),
        nullable=True
    )


# =====================================================
# CALL ATTEMPT
# =====================================================

class CallAttempt(Base):
    __tablename__ = "call_attempts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    queue_id = Column(
        Integer,
        nullable=False
    )

    # Attempt number: 1, 2, 3
    attempt_number = Column(
        Integer,
        default=1,
        nullable=False
    )

    # Call state
    status = Column(
        String(50),
        default="started",
        nullable=False
    )

    # -------------------------------------------------
    # TELEPHONY PROVIDER
    # -------------------------------------------------

    provider = Column(
        String(50),
        nullable=True
    )

    provider_call_id = Column(
        String(100),
        nullable=True
    )

    # -------------------------------------------------
    # CALL TIMING
    # -------------------------------------------------

    started_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    ended_at = Column(
        DateTime,
        nullable=True
    )

    # Duration in seconds
    duration_seconds = Column(
        Integer,
        nullable=True
    )

    # -------------------------------------------------
    # CALL RESULT
    # -------------------------------------------------

    result = Column(
        String(100),
        nullable=True
    )

    failure_reason = Column(
        String(500),
        nullable=True
    )

    # -------------------------------------------------
    # RECORDING
    # -------------------------------------------------

    recording_url = Column(
        String(1000),
        nullable=True
    )

    recording_reference = Column(
        String(255),
        nullable=True
    )

    # -------------------------------------------------
    # HUMAN AGENT TRANSFER
    # -------------------------------------------------

    transfer_status = Column(
        String(50),
        nullable=True
    )

    agent_id = Column(
        Integer,
        nullable=True
    )

    # -------------------------------------------------
    # AI / CUSTOMER INFORMATION
    # -------------------------------------------------

    customer_notes = Column(
        String(3000),
        nullable=True
    )

    customer_intent = Column(
        String(100),
        nullable=True
    )

    next_action = Column(
        String(500),
        nullable=True
    )


# =====================================================
# CALL INTELLIGENCE
# =====================================================

class CallIntelligence(Base):
    __tablename__ = "call_intelligence"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    queue_id = Column(
        Integer,
        nullable=False
    )

    attempt_id = Column(
        Integer,
        nullable=False
    )

    # Full conversation transcript
    transcript = Column(
        String(10000),
        nullable=True
    )

    # AI generated summary
    summary = Column(
        String(2000),
        nullable=True
    )

    # AI sentiment
    sentiment = Column(
        String(50),
        nullable=True
    )

    # Final call outcome
    outcome = Column(
        String(100),
        nullable=True
    )

    # Customer intent
    customer_intent = Column(
        String(100),
        nullable=True
    )

    # Important customer notes
    customer_notes = Column(
        String(3000),
        nullable=True
    )

    # Recommended next action
    next_action = Column(
        String(500),
        nullable=True
    )

    analyzed_at = Column(
        DateTime,
        default=datetime.utcnow
    )