from app.db import Base, engine
from app.models.user import User

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")
