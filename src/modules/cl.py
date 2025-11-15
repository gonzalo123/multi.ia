import logging
from typing import Any, List

import chainlit as cl
import jwt
from botocore.config import Config
from strands import Agent
from strands.agent import SlidingWindowConversationManager
from strands.hooks import (
    HookProvider)
from strands.models import BedrockModel
from strands_tools import calculator, current_time, think, stop
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

from settings import AWS_REGION, Models

logger = logging.getLogger(__name__)


def auth_callback(headers: dict, secret, jwt_algorithm) -> Any:
    if headers.get("x-user-jwt"):
        jwt_token = headers.get("x-user-jwt")
        try:
            decoded_payload = jwt.decode(jwt_token, secret, algorithms=[jwt_algorithm])
            user_info = decoded_payload['user_info']
            logger.info(f"Authenticated user: {user_info['display_name']} ({user_info['userid']})")
            user = cl.User(
                identifier=user_info['userid'],
                display_name=user_info['display_name'],
                metadata={"role": 'user', "provider": "header"})
            cl.user = user
            return user
        except jwt.ExpiredSignatureError:
            cl.logger.error("Token has expired.")
            return None


def get_orchestrator_tools() -> List[Any]:
    from tools.logistics.agent import logistics_assistant
    from tools.production.agent import production_assistant
    from tools.weather.agent import weather_assistant

    tools = [
        calculator,
        think,
        current_time,
        stop,
        AgentCoreCodeInterpreter(region=AWS_REGION).code_interpreter,
        logistics_assistant,
        production_assistant,
        weather_assistant
    ]

    return tools


def get_agent(
        system_prompt: str,
        model: str = Models.CLAUDE_45,
        tools: List[Any] = [],
        hooks: List[HookProvider] = [],
        temperature: float = 0.3,
        llm_read_timeout: int = 300,
        llm_connect_timeout: int = 60,
        llm_max_attempts: int = 10,
        maximum_messages_to_keep: int = 30,
        should_truncate_results: bool = True,
):
    return Agent(
        system_prompt=system_prompt,
        model=BedrockModel(
            model_id=model,
            temperature=temperature,
            boto_client_config=Config(
                read_timeout=llm_read_timeout,
                connect_timeout=llm_connect_timeout,
                retries={'max_attempts': llm_max_attempts}
            )
        ),
        conversation_manager=SlidingWindowConversationManager(
            window_size=maximum_messages_to_keep,
            should_truncate_results=should_truncate_results,
        ),
        tools=tools,
        hooks=hooks
    )
