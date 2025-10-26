"""
Create alarm_commands table for device alarm management
Run this once to create the table
"""

from app.db import SessionLocal
from sqlalchemy import text

def create_alarm_commands_table():
    """Create the alarm_commands table"""
    
    with SessionLocal() as db:
        try:
            # Create table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS alarm_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    command TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT 0,
                    processed_at TIMESTAMP NULL
                )
            """))
            
            # Create indexes for faster lookups
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_alarm_commands_device 
                ON alarm_commands(device_id, processed)
            """))
            
            # Create index for cleanup queries
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_alarm_commands_created 
                ON alarm_commands(created_at)
            """))
            
            db.commit()
            print("alarm_commands table created successfully!")
            print("Indexes created successfully!")
            
        except Exception as e:
            db.rollback()
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    print("Creating alarm_commands table...")
    create_alarm_commands_table()

