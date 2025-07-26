from models import Session, User

# In-memory store for currently authenticated users
authenticated_users = set()

def is_authenticated(user_id: str) -> bool:
    return user_id in authenticated_users

def authenticate_user(user_id: str, pin: str) -> bool:
    session = Session()
    user = session.query(User).filter_by(telegram_id=user_id).first()

    if user and user.pin == pin:
        authenticated_users.add(user_id)
        return True
    return False

def logout_user(user_id: str):
    authenticated_users.discard(user_id)

def register_user(user_id: str, pin: str):
    session = Session()
    existing = session.query(User).filter_by(telegram_id=user_id).first()

    if existing:
        existing.pin = pin
    else:
        new_user = User(telegram_id=user_id, pin=pin)
        session.add(new_user)
    session.commit()
