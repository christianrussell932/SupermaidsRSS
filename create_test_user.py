from sqlalchemy.orm import sessionmaker
from werkzeug.security import generate_password_hash
from app.models.models import User, init_db
from app.config.settings import DATABASE_URL

# Init DB engine and session
engine = init_db(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# Create test user
test_user = User(
    email="admin@example.com",
    password_hash=generate_password_hash("password123")
)

# Add to DB
session.add(test_user)
session.commit()
session.close()

print("✅ Test user created!")
