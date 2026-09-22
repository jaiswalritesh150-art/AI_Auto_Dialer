from sqlalchemy import Column, Integer, String, DateTime
from datetime import datetime

from app.database import Base

class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    zoho_lead_id = Column(String(50), unique=True, nullable=False)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    company = Column(String(255), nullable=True)

    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)

    lead_source = Column(String(100), nullable=True)
    lead_status = Column(String(100), nullable=True)

    # Lead scoring
    lead_score = Column(Integer, default=0, nullable=False)
    priority = Column(String(20), default="LOW", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

class CallQueue(Base):
    __tablename__ = "call_queue"

    id = Column(Integer, primary_key=True, index=True)

    lead_id = Column(Integer, nullable=False)

    phone = Column(String(30), nullable=True)

    status = Column(String(50), default="queued", nullable=False)

    queued_at = Column(DateTime, default=datetime.utcnow)

    started_at = Column(DateTime, nullable=True)

    completed_at = Column(DateTime, nullable=True)

    failure_reason = Column(String(500), nullable=True)
    
class CallAttempt(Base):
    __tablename__ = "call_attempts"

    id = Column(Integer, primary_key=True, index=True)

    queue_id = Column(Integer, nullable=False)

    attempt_number = Column(Integer, default=1, nullable=False)

    status = Column(String(50), default="started", nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow)

    ended_at = Column(DateTime, nullable=True)

    result = Column(String(100), nullable=True)

    failure_reason = Column(String(500), nullable=True)