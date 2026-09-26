"""
The steps (nodes) of the agent graph. Each node takes the state and returns the fields it updates.
"""

from langchain_core.messages import AIMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app import config
from app.agent.prompts import CLASSIFIER_PROMPT, DESTRUCTIVE_MESSAGE, OUT_OF_SCOPE_MESSAGE
from app.agent.state import AgentState, IntentClassification
from app.db.database import get_schema

classifier_llm = ChatGoogleGenerativeAI(
    model=config.CLASSIFIER_MODEL, temperature=0
).with_structured_output(IntentClassification)


def classify_intent(state: AgentState) -> dict:
    """Decide what kind of request the latest message is, and extract any SQL it contains."""
    system = SystemMessage(CLASSIFIER_PROMPT.format(table_names=", ".join(get_schema())))
    result = classifier_llm.invoke([system, *state["messages"]])
    return {"intent": result.intent, "user_sql": result.user_sql}


def refuse(state: AgentState) -> dict:
    """Politely decline destructive or out-of-scope requests. Fixed text, no LLM call."""
    message = DESTRUCTIVE_MESSAGE if state["intent"] == "destructive" else OUT_OF_SCOPE_MESSAGE
    return {"messages": [AIMessage(message)]}


def not_implemented_yet(state: AgentState) -> dict:
    """Temporary stand-in for the paths we have not built yet."""
    return {"messages": [AIMessage(f"The '{state['intent']}' path is not built yet.")]}
