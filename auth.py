from models import Session, User
import bcrypt

def is_authenticated(user_id: str) -> bool:
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        return bool(user and user.session_active)
    finally:
        session.close()

def authenticate_user(user_id: str, pin: str) -> bool:
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user and user.pin and bcrypt.checkpw(pin.encode('utf-8'), user.pin.encode('utf-8')):
            user.session_active = True
            session.commit()
            return True
        return False
    finally:
        session.close()

def logout_user(user_id: str):
    session = Session()
    try:
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user:
            user.session_active = False
            session.commit()
    finally:
        session.close()

def register_user(user_id: str, pin: str):
    session = Session()
    try:
        hashed_pin = bcrypt.hashpw(pin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        user = session.query(User).filter_by(telegram_id=user_id).first()
        if user:
            user.pin = hashed_pin
        else:
            user = User(telegram_id=user_id, pin=hashed_pin, session_active=False)
            session.add(user)
        session.commit()
    finally:
        session.close()
