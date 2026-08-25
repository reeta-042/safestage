import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from app.database.connection import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")

class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    venue_name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    attendance = Column(Integer, nullable=False)
    start_datetime = Column(DateTime, nullable=False)
    end_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="events")
    analyses = relationship("HeatAnalysis", back_populates="event", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="event", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="event", cascade="all, delete-orphan")

class HeatAnalysis(Base):
    __tablename__ = "heat_analysis"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    provider = Column(String, nullable=False)  # "mock" or "fortyguard"
    analysis_status = Column(String, nullable=False, default="completed")
    temperature_data = Column(JSON, nullable=True)
    heat_risk = Column(JSON, nullable=True)
    readiness_score = Column(Float, nullable=False, default=0.0)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="analyses")
    recommendations = relationship("Recommendation", back_populates="analysis", cascade="all, delete-orphan")

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    analysis_id = Column(String, ForeignKey("heat_analysis.id"), nullable=True)
    recommendation_type = Column(String, nullable=False)  # date_time, venue_layout, operational, safety
    recommendation = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False, default=0.9)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="recommendations")
    analysis = relationship("HeatAnalysis", back_populates="recommendations")

class Report(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    event_id = Column(String, ForeignKey("events.id"), nullable=False)
    report_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    event = relationship("Event", back_populates="reports")

