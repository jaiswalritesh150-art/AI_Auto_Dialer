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

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )