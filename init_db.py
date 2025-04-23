from app import app, db

with app.app_context():
    # Create all tables
    db.create_all()
    print("Database initialized successfully!") 