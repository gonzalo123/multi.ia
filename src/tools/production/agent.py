from strands import tool
from strands_tools import calculator, current_time, think
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

from modules.cl import get_agent
from settings import Dbnames, AWS_REGION
from tools.production.tools import ProductionTools

ASSISTANT_PROMPT = """
Eres un experto asistente sobre temas de producción en una empresa de manufactura.
Utiliza las herramientas disponibles para proporcionar respuestas precisas y detalladas a las consultas relacionadas con la producción.
"""


@tool
async def production_assistant(query: str):
    """
    A research assistant specialized in production topics with streaming support.
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
        tools += ProductionTools(Dbnames.LOCAL).get_tools()

        research_agent = get_agent(
            system_prompt=ASSISTANT_PROMPT,
            tools=tools
        )

        async for token in research_agent.stream_async(query):
            yield token

    except Exception as e:
        yield f"Error in research assistant: {str(e)}"
