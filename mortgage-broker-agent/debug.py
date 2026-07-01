from app.agents.conversation_state import ConversationState

session_id = "test-123"

state = ConversationState(session_id)

print("STATE:", state.__dict__)
print("MESSAGES:", state.get_messages())
print("PROGRESS:", state.get_progress_percent())
