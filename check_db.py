from app import app, db, init_db
import os

def check_database():
    """Check the database and fix any issues"""
    print("Checking database...")
    
    # Check if instance directory exists
    if not os.path.exists('instance'):
        print("Instance directory not found. Creating it...")
        os.makedirs('instance')
    
    # Check if database file exists
    db_path = os.path.join('instance', 'gym.db')
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}. Initializing database...")
        with app.app_context():
            db.create_all()
            print("Database created successfully.")
    else:
        print(f"Database file exists at {db_path}")
        # Check if tables exist
        with app.app_context():
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"Existing tables: {tables}")
            
            if not tables:
                print("No tables found. Creating tables...")
                db.create_all()
                print("Tables created successfully.")
            else:
                print("Tables exist. Database appears to be working correctly.")

if __name__ == "__main__":
    check_database()
    print("Database check complete.") 