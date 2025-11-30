"""
Quick test script for chatbot with A-111 drawings
Usage: python test_chatbot_quick.py [old_version_id] [new_version_id]
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.chatbot_service import ChatbotService
from gcp.database import get_db_session
from gcp.database.models import DrawingVersion
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    # Get drawing version IDs from command line
    if len(sys.argv) >= 3:
        old_version_id = sys.argv[1]
        new_version_id = sys.argv[2]
    elif len(sys.argv) == 2:
        # Single drawing
        old_version_id = sys.argv[1]
        new_version_id = None
    else:
        # Find A-111 drawings
        with get_db_session() as db:
            old_version = db.query(DrawingVersion).filter(
                DrawingVersion.drawing_name == 'A-111',
                DrawingVersion.version_number == 1
            ).first()
            
            new_version = db.query(DrawingVersion).filter(
                DrawingVersion.drawing_name == 'A-111',
                DrawingVersion.version_number == 2
            ).first()
            
            if not old_version or not new_version:
                print("❌ A-111 drawings not found!")
                print("\nTo test:")
                print("1. Run: python upload_and_process_a111.py")
                print("2. Then run: python test_chatbot_quick.py <old_id> <new_id>")
                return
            
            old_version_id = old_version.id
            new_version_id = new_version.id
            print(f"📄 Found A-111 drawings:")
            print(f"   Old: {old_version.drawing_name} v{old_version.version_number} ({old_version_id})")
            print(f"   New: {new_version.drawing_name} v{new_version.version_number} ({new_version_id})\n")
    
    # Initialize chatbot
    try:
        chatbot = ChatbotService()
        print("✅ Chatbot initialized\n")
    except Exception as e:
        print(f"❌ Failed to initialize chatbot: {e}")
        return
    
    print("=" * 60)
    print("CHATBOT TEST - Option 1 (Simple Context Injection)")
    print("=" * 60)
    print()
    
    # Test with single drawing (old version)
    print("TEST 1: Questions about OLD version (single drawing context)")
    print("-" * 60)
    
    test_questions_single = [
        "What is this drawing about?",
        "What are the key notations on this drawing?",
        "What are the dimensions?",
        "What revision is this drawing?"
    ]
    
    for i, question in enumerate(test_questions_single, 1):
        print(f"\nQ{i}: {question}")
        print("-" * 60)
        
        response = chatbot.send_message(
            user_message=question,
            drawing_version_id=old_version_id
        )
        
        print(f"Response: {response.get('response')}")
        print(f"Context used: {response.get('context_used')}")
        if response.get('tokens_used'):
            print(f"Tokens used: {response.get('tokens_used')}")
    
    # Test with both drawings (comparison)
    if new_version_id:
        print("\n\n" + "=" * 60)
        print("TEST 2: Questions about BOTH versions (comparison context)")
        print("-" * 60)
        
        test_questions_comparison = [
            "What are the differences between these two versions?",
            "What changed in the keynotes between old and new?",
            "Compare the dimensions between the two versions"
        ]
        
        for i, question in enumerate(test_questions_comparison, 1):
            print(f"\nQ{i}: {question}")
            print("-" * 60)
            
            response = chatbot.send_message(
                user_message=question,
                drawing_version_ids=[old_version_id, new_version_id]
            )
            
            print(f"Response: {response.get('response')}")
            print(f"Context used: {response.get('context_used')}")
            if response.get('tokens_used'):
                print(f"Tokens used: {response.get('tokens_used')}")
    
    # Interactive mode
    print("\n\n" + "=" * 60)
    print("INTERACTIVE MODE - Type your questions (or 'quit' to exit)")
    print("=" * 60)
    print()
    print("Commands:")
    print("  'old' - Switch to old version context")
    print("  'new' - Switch to new version context")
    print("  'both' - Use both versions for comparison")
    print("  'quit' - Exit")
    print()
    
    conversation_history = []
    current_drawing_id = old_version_id
    current_drawing_ids = None
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            break
        
        if not user_input:
            continue
        
        # Handle context switching
        if user_input.lower() == 'old':
            current_drawing_id = old_version_id
            current_drawing_ids = None
            print(f"✓ Switched to OLD version context (v1)")
            continue
        elif user_input.lower() == 'new' and new_version_id:
            current_drawing_id = new_version_id
            current_drawing_ids = None
            print(f"✓ Switched to NEW version context (v2)")
            continue
        elif user_input.lower() == 'both' and new_version_id:
            current_drawing_id = None
            current_drawing_ids = [old_version_id, new_version_id]
            print(f"✓ Switched to BOTH versions context (comparison mode)")
            continue
        
        print("\n🤔 Thinking...\n")
        
        if current_drawing_ids:
            response = chatbot.send_message(
                user_message=user_input,
                drawing_version_ids=current_drawing_ids,
                conversation_history=conversation_history
            )
        else:
            response = chatbot.send_message(
                user_message=user_input,
                drawing_version_id=current_drawing_id,
                conversation_history=conversation_history
            )
        
        print(f"Assistant: {response.get('response')}\n")
        
        # Update conversation history
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": response.get('response')})

if __name__ == '__main__':
    main()

