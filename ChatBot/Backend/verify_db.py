from app.database import SessionLocal
from app import models
import time

def verify():
    db = SessionLocal()
    
    test_id = "test-session-" + str(int(time.time()))
    print(f"Creating session: {test_id}")
    
    # 1. Simulate Add Message (which creates session)
    from app.main import add_to_conversation, get_conversation_history
    
    add_to_conversation(test_id, "user", "Hello World", db)
    print("Message added.")
    
    # 2. Check Session Table
    session = db.query(models.ChatSession).filter(models.ChatSession.id == test_id).first()
    if session:
        print(f"✅ Session found in DB: {session.id}")
    else:
        print("❌ Session NOT found in DB")
        
    # 3. Check Message Table
    msgs = db.query(models.ChatMessage).filter(models.ChatMessage.session_id == test_id).all()
    print(f"Messages found: {len(msgs)}")
    for m in msgs:
        print(f" - [{m.role}] {m.content}")
        
    # 4. Check get_conversation_history helper
    hist = get_conversation_history(test_id, db)
    print("History Output:")
    print(hist)
    
    if "Hello World" in hist:
        print("✅ History Retrieval Success")
    else:
        print("❌ History Retrieval Failed")
        
    db.close()

if __name__ == "__main__":
    verify()
