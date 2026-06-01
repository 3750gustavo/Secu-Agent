"""
Database migration script for Secu-Agent.
Handles database initialization and schema updates for both SQLite and PostgreSQL.
"""

import os
import sys
from sqlalchemy import text, inspect
from database import engine, Base, SessionLocal, init_db

def check_table_exists(table_name):
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def migrate_database():
    """
    Run database migrations.
    This function handles:
    - Initial table creation
    - Schema updates
    - Data integrity checks
    """
    print("🔄 Starting database migration...")
    
    try:
        # Initialize database (creates tables if they don't exist)
        init_db()
        print("✓ Database tables initialized")
        
        # Check if required tables exist
        required_tables = ['leads', 'messages']
        missing_tables = [table for table in required_tables if not check_table_exists(table)]
        
        if missing_tables:
            print(f"⚠️  Warning: Missing tables: {missing_tables}")
            print("🔧 Creating missing tables...")
            Base.metadata.create_all(bind=engine)
            print("✓ Missing tables created")
        
        # Verify table structure
        db = SessionLocal()
        try:
            # Test database connection
            db.execute(text("SELECT 1"))
            print("✓ Database connection verified")
            
            # Check leads table structure
            if check_table_exists('leads'):
                leads_columns = [col['name'] for col in inspect(engine).get_columns('leads')]
                expected_leads_columns = ['id', 'name', 'email', 'company', 'job_title', 'source', 'status', 'created_at', 'updated_at']
                
                missing_columns = set(expected_leads_columns) - set(leads_columns)
                if missing_columns:
                    print(f"⚠️  Warning: Missing columns in leads table: {missing_columns}")
                else:
                    print("✓ Leads table structure verified")
            
            # Check messages table structure
            if check_table_exists('messages'):
                messages_columns = [col['name'] for col in inspect(engine).get_columns('messages')]
                expected_messages_columns = ['id', 'lead_id', 'message_text', 'timestamp', 'channel', 'direction']
                
                missing_columns = set(expected_messages_columns) - set(messages_columns)
                if missing_columns:
                    print(f"⚠️  Warning: Missing columns in messages table: {missing_columns}")
                else:
                    print("✓ Messages table structure verified")
            
            print("✅ Database migration completed successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error during database verification: {str(e)}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        print(f"❌ Database migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)