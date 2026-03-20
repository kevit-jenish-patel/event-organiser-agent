import asyncio
import sys

from llama_index.core.agent import FunctionAgent
from llama_index.core.agent.workflow import AgentStream
from llama_index.core.workflow import Context, HumanResponseEvent, InputRequiredEvent

from app.models.llm_model import llm
from db.config import MongoManager
from tools.database.tools import (
    create_event,
    delete_event,
    search_events,
    update_event,
)
from utils.logger import get_logger
from utils.prompts import SYSTEM_PROMPT_3

logger = get_logger(__name__)


async def main():
    try:
        # 1. Initialize the Function Agent with the unified toolset
        workflow = FunctionAgent(
            name="Event Agent",
            description=(
                "An intelligent assistant capable of querying events via semantic search, "
                "and securely creating, updating, or deleting database records."
            ),
            llm=llm,
            tools=[
                search_events,
                create_event,
                update_event,
                delete_event
            ],
            system_prompt=SYSTEM_PROMPT_3,
        )

        # 2. Initialize the workflow context
        ctx = Context(workflow)

        # 3. Chat Interface Bootup Sequence
        print("=" * 60)
        print("🚀 Event Management AI Assistant is Online.")
        print("Type 'quit' or 'exit' to terminate the session.")
        print("=" * 60)

        while True:
            # Get user input
            user_msg = input("\n👤 User: \n> ").strip()

            # Exit conditions
            if user_msg.lower() in {"exit", "quit"}:
                print("\n👋 Shutting down... Goodbye!")
                break

            # Skip empty inputs
            if not user_msg:
                continue

            print("\n🤖 Assistant: \n", end="", flush=True)

            try:
                # 4. Run the workflow with the user's message
                handler = workflow.run(user_msg=user_msg, ctx=ctx)

                # 5. Process the asynchronous event stream
                async for event in handler.stream_events():

                    # -> Handle standard text generation from the LLM
                    if isinstance(event, AgentStream):
                        print(event.delta, end="", flush=True)

                    # -> Handle Security Interceptions (HITL)
                    elif isinstance(event, InputRequiredEvent):
                        # The workflow has paused inside a database tool.
                        # Prompt the user using the prefix formulated by the tool.
                        user_approval = input(event.prefix).strip()

                        # Send the user's explicit response back into the workflow context
                        # This unpauses the tool so it can evaluate the 'y/n' answer.
                        handler.ctx.send_event(
                            HumanResponseEvent(
                                response=user_approval,
                                user_name=event.user_name,
                            )
                        )

                    # -> Handle backend/logging events (Tool calls starting, etc.)
                    else:
                        logger.info(
                            "Agent internal event triggered",
                            extra={"event_type": type(event).__name__, "event": str(event)}
                        )

                # Await the final completion of the handler for this turn
                await handler
                print()  # Print a final newline for clean formatting

            except Exception:
                logger.exception("An error occurred during agent execution.")
                print(f"\n❌ Error: Something went wrong while processing your request. Please try again.")

    except Exception:
        logger.exception("A critical failure occurred during initialization.")
        print("\n❌ Critical Failure: Could not start the AI Assistant. Check logs for details.")
    finally:
        try:
            MongoManager.close()
            logger.info("MongoDB connection safely closed.")
        except Exception:
            logger.exception(f"Failed to close MongoDB connection cleanly")


if __name__ == "__main__":
    # Ensure proper async loop execution
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSession terminated by user (Ctrl+C).")
        sys.exit(0)
    finally:
        try:
            MongoManager.close()
            logger.info("MongoDB connection safely closed.")
        except Exception as e:
            logger.exception(f"Failed to close MongoDB connection cleanly")
            pass