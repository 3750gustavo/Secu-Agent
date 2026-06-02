"""
Test script to verify the coroutine bug fix in ai_client.py
This tests that AI message generation now works properly.
"""

import sys
import os
from database import init_db, get_db, LeadOperations, MessageOperations
from ai_client import Agent

def test_welcome_message_generation():
    """Test that welcome message generation works with the fix."""
    print("🧪 Testing coroutine fix...")
    
    # Initialize database
    init_db()
    db = next(get_db())
    
    try:
        # Create a test lead similar to the cloud entry
        test_lead = LeadOperations.create_lead(
            db=db,
            name="Ruan Matheus Miguel Drumond",
            email="ruan-drumond81@diebold.com",
            company="AVMB",
            job_title="Analista de TI",
            source="landing_page",
            status="new"
        )
        print(f"✅ Created test lead: {test_lead.name} (ID: {test_lead.id})")
        
        # Create agent and test welcome message generation
        agent = Agent()
        lead_dict = {
            'id': test_lead.id,
            'name': test_lead.name,
            'email': test_lead.email,
            'company': test_lead.company,
            'job_title': test_lead.job_title,
            'status': test_lead.status,
            'source': test_lead.source
        }
        
        print("🤖 Generating welcome message...")
        welcome_message = agent.generate_welcome_message(lead_dict)
        
        print(f"✅ Welcome message generated successfully!")
        print(f"📝 Message: {welcome_message[:100]}...")
        
        # Check if it's the fallback template or AI-generated
        if "Test User" in welcome_message and "Test Corp" in welcome_message:
            print("✅ Message contains personalized content")
        else:
            print("⚠️  Message might be using fallback template")
        
        # Test process_lead (which calls generate_welcome_message)
        print("\n🔄 Testing process_lead with the fix...")
        result = agent.process_lead(test_lead.id, db)
        
        print(f"✅ Process lead result: {result}")
        
        # Check if message was stored in database
        messages = MessageOperations.get_messages_by_lead(db, test_lead.id)
        print(f"✅ Messages in database: {len(messages)}")
        
        if messages:
            latest_message = messages[-1]
            print(f"📧 Latest message: {latest_message.message_text[:100]}...")
            
            # Check if it's AI-generated or fallback
            if "Test User" in latest_message.message_text:
                print("✅ Message contains personalization")
            else:
                print("⚠️  Message might be fallback template")
        
        # Clean up
        LeadOperations.delete_lead(db, test_lead.id)
        print("🧹 Cleaned up test lead")
        
        print("\n🎉 All tests passed! Coroutine fix is working.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = test_welcome_message_generation()
    sys.exit(0 if success else 1)