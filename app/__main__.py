import asyncio

from llama_index.core.agent import FunctionAgent
from llama_index.core.agent.workflow import AgentStream
from llama_index.core.workflow import Context

from app.llm_model import llm
from db.config import MongoManager
from tools.database.tools import get_event_from_name, create_event, update_event
from utils.logger import get_logger
from utils.prompts import SYSTEM_PROMPT

logger = get_logger(__name__)


async def main():
    try:
        workflow = FunctionAgent(
            name="Event Agent",
            description="Useful for fetching, creating and updating events",
            llm=llm,
            tools=[get_event_from_name,create_event,update_event],
            system_prompt=SYSTEM_PROMPT,
        )
        ctx = Context(workflow)

        user_msg = input("Enter your message: ")
        handler = workflow.run(user_msg=user_msg, ctx=ctx)

        async for event in handler.stream_events():
            if isinstance(event, AgentStream):
                print(event.delta, end="", flush=True)

    except Exception:
        logger.exception("Something went wrong")
    finally:
        MongoManager.close()

if __name__ == "__main__":
    asyncio.run(main())
