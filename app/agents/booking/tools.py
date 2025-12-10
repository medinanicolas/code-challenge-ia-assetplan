import random
from langchain.tools import tool
from app.core.utils import create_handoff_tool


@tool
async def check_availability(date: str):
    """Checks if the input date is available in the schedule

    Args:
        date: Date to verify (Convert to ISO format)"""
    try:
        if random.randint(0, 1) == 0:
            return {"status": "not available"}
        return {"status": "available"}
    except Exception as e:
        return {"status": f"Error checking availability: {str(e)}"}


@tool
async def schedule_appointment(date: str, name: str, pet_name: str, reason: str):
    """Schedule a meet in the input date

    Args:
        date: Date schedule the meet (Convert it to ISO format)
        name: The name of the human
        pet_name: The pet name
        reason: The reason of the appointment"""
    try:
        return {"status": f"scheduled to {date}"}
    except Exception as e:
        return {"status": f"Error scheduling appointment: {str(e)}"}


transfer_to_parent = create_handoff_tool(
    name="transfer_to_parent",
    agent_name="router",
    graph="parent",
    description="Transfers the control back to the parent controller",
)
