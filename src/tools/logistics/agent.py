from strands import tool
from strands_tools import calculator, current_time, think
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

from modules.cl import get_agent, stream_to_step
from modules.prompts import SPARTAN_PROMPT
from settings import AWS_REGION
from settings import Dbnames
from tools.logistics.tools import LogisticsTools

ASSISTANT_PROMPT = f"""
You are an expert in logistics and supply chain topics.
Use the available tools to provide accurate and detailed responses to logistics-related queries.

{SPARTAN_PROMPT}
"""


@tool
@stream_to_step("logistics_assistant")
async def logistics_assistant(query: str):
    """
    A research assistant specialized in logistics topics with streaming support.
    Yields:
        Tokens (str) containing the answer progressively.
    """
    try:
        tools = [
            calculator,
            think,
            current_time,
            AgentCoreCodeInterpreter(region=AWS_REGION).code_interpreter
        ]
        tools += LogisticsTools(Dbnames.LOCAL).get_tools()

        research_agent = get_agent(
            system_prompt=ASSISTANT_PROMPT,
            tools=tools
        )

        async for token in research_agent.stream_async(query):
            yield token

    except Exception as e:
        yield f"Error in research assistant: {str(e)}"
