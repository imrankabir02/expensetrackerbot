from sqlalchemy import create_engine, Column, Integer, String, Float, Date, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import date

Base = declarative_base()

class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    amount = Column(Float)
    category = Column(String)
    description = Column(String)
    date = Column(Date, default=date.today)

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True)
    user_id = Column(String, unique=True)
    is_enabled = Column(Boolean, default=True)

class User(Base):
    __tablename__ = 'users'
    telegram_id = Column(String, primary_key=True)
    pin = Column(String, nullable=True)

# ✅ Setup database engine and session
engine = create_engine('sqlite:///expenses.db')
Base.metadata.create_all(engine)  # ✅ Now creates all 3 tables: expenses, reminders, users
Session = sessionmaker(bind=engine)
