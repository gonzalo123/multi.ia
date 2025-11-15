import asyncio
import logging
from typing import Dict, Optional

import chainlit as cl
from strands.hooks import (
    HookProvider, HookRegistry, BeforeToolCallEvent,
    AfterToolCallEvent)

from modules.cl import auth_callback, get_agent, get_orchestrator_tools
from modules.prompts import MAIN_SYSTEM_PROMPT
from settings import (
    ENVIRONMENT, SECRET,
    JWT_ALGORITHM, FAKE_USER, DEBUG)

logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',
    level='INFO',
    datefmt='%d/%m/%Y %X')

logger = logging.getLogger(__name__)


class LoggingHooks(HookProvider):
    def register_hooks(self, registry: HookRegistry) -> None:
        registry.add_callback(BeforeToolCallEvent, self.before_tool)
        registry.add_callback(AfterToolCallEvent, self.after_tool)

    async def before_tool(self, event: BeforeToolCallEvent) -> None:
        step = cl.Step(
            name=f"Using tool: {event.tool_use['name']}",
            type="tool",
        )
        await step.send()
        cl.user_session.set(f"step_{event.tool_use['name']}", step)
        logger.debug(f"Request started for {event.tool_use['name']}")

    async def after_tool(self, event: AfterToolCallEvent) -> None:
        step: cl.Step = cl.user_session.get(f"step_{event.tool_use['name']}")
        if step:
            await step.remove()
        logger.debug(f"Request completed for {event.tool_use['name']}")


@cl.header_auth_callback
def header_auth_callback(headers: Dict) -> Optional[cl.User]:
    if ENVIRONMENT == 'local' and FAKE_USER:
        user = cl.User(
            identifier=FAKE_USER,
            display_name=FAKE_USER,
            metadata={"role": 'admin', "provider": "local"})
        cl.User = user
        return user
    else:
        return auth_callback(headers=headers, secret=SECRET, jwt_algorithm=JWT_ALGORITHM)


@cl.on_chat_start
async def start_chat():
    cl.user_session.set("should_stop", False)
    cl.user_session.set("current_task", None)

    agent = get_agent(
        system_prompt=MAIN_SYSTEM_PROMPT,
        hooks=[LoggingHooks()],
        tools=get_orchestrator_tools()
    )
    cl.user_session.set("agent", agent)

    cl.user_session.set(
        "message_history",
        [{"role": "system", "content": "You are a helpful assistant."}],
    )


@cl.on_chat_end
async def on_chat_end():
    current_task = cl.user_session.get("current_task")
    if current_task and not current_task.done():
        current_task.cancel()

    task = cl.user_session.get("task")
    if task and not task.done():
        task.cancel()


@cl.on_message
async def handle_message(message: cl.Message):
    agent = cl.user_session.get("agent")

    message_history = cl.user_session.get("message_history")
    message_history.append({"role": "user", "content": message.content})

    async def user_task(debug):
        msg = cl.Message(content="")
        await msg.send()

        question = message.content
        extra = (f"Si hay algun error en alguna tool para la ejecución del agente y "
                 f"explicame el error para que pueda corregirlo.")
        question = f"{question}\n{extra}" if debug else question

        async for event in agent.stream_async(question):
            if "data" in event:
                await msg.stream_token(str(event["data"]))
            elif "message" in event:
                await msg.stream_token("\n")
                message_history.append(event["message"])
            else:
                ...

        await msg.update()

    task = asyncio.create_task(user_task(DEBUG))
    cl.user_session.set("task", task)
    try:
        await task
    except asyncio.CancelledError:
        logger.info("User task was cancelled.")
