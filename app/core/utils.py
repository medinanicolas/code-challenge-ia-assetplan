from langchain.tools import tool, InjectedState, InjectedToolCallId
from langchain.messages import ToolMessage, AIMessage, HumanMessage
from langgraph.types import Command
from typing import Literal, Annotated
from dateutil import parser
from rich import print as rprint
from rich.panel import Panel
from rich.text import Text
from rich.console import Group
from rich.rule import Rule


def create_handoff_tool(
    *,
    name: str,
    agent_name: str,
    graph: Literal["child", "parent"],
    description: str | None = None,
):
    if description is None:
        description = f"Ask agent '{name}' for help"

    @tool(name, description=description)
    async def handoff_to_agent(
        state: Annotated[dict, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ):
        f"""Transfer the control to {name} agent"""
        print(f"[DEBUG] Action: handoff_to_agent | To: {agent_name}")
        tool_message = ToolMessage(
            content=f"Successfully transferred to {agent_name} agent",
            name=name,
            tool_call_id=tool_call_id,
        )
        return Command(
            goto=agent_name,
            graph=Command.PARENT if graph == "parent" else None,
            update={
                "messages": state["messages"] + [tool_message],
                "active_agent": agent_name,
            },
        )

    return handoff_to_agent


def print_debug_event(event):
    """
    Versión 'Compacta': Usa print() normal para logs de sistema para evitar
    el exceso de espaciado vertical en Jupyter, y Rich solo para el contenido real.
    """
    path, chunk = event

    # 1. Extracción de Datos
    event_type = chunk.get("type")
    payload = chunk.get("payload", {})
    step = chunk.get("step", "N/A")

    # Timestamp simple
    ts_str = chunk.get("timestamp", "")
    try:
        ts_dt = parser.parse(ts_str)
        timestamp = ts_dt.strftime("%H:%M:%S")
    except:
        timestamp = "Time: N/A"

    # Detectar Scope
    if len(path) == 0:
        graph_scope = "ROOT"
    else:
        current_subgraph = path[-1].split(":")[0].upper()
        graph_scope = f"SUB:{current_subgraph}"

    node_name = payload.get("name", "System")

    # ---------------------------------------------------------
    # CASO A: Eventos de Sistema (Checkpoints, Task Start)
    # USAMOS print() NORMAL para evitar saltos de línea HTML en Jupyter
    # ---------------------------------------------------------
    if event_type in ["checkpoint", "task"]:
        icon = "💾" if event_type == "checkpoint" else "🎬"
        # Imprimimos texto plano para que quede compacto
        print(
            f"{timestamp} | {graph_scope:<8} | Step: {step:<2} | {icon} {event_type.upper()} -> Node: {node_name}"
        )
        return

    # ---------------------------------------------------------
    # CASO B: Resultado de Tarea (Paneles con Rich)
    # ---------------------------------------------------------
    if event_type == "task_result":
        result = payload.get("result", {})

        if not result or not isinstance(result, dict):
            return

        messages = result.get("messages", [])
        if not isinstance(messages, list):
            messages = [messages]

        if not messages:
            # Log simple si no hay mensajes
            print(f"{timestamp} | ✅ Task Completed: {node_name}")
            return

        # ⚠️ FILTRO: Solo el último mensaje
        msg = messages[-1]

        # --- Visualización Rich (Solo para contenido real) ---
        content_display = []

        # Header y colores según Scope
        scope_color = "blue" if graph_scope == "ROOT" else "dark_red"

        header = Text()
        header.append(f"{graph_scope} ", style=f"bold {scope_color}")
        header.append(f"• Step {step} • Node: {node_name}", style="bold navy_blue")
        content_display.append(header)
        content_display.append(Rule(style="grey70"))

        # Estilos Tema Claro
        if isinstance(msg, HumanMessage):
            title = "👤 User Input"
            border_color = "dark_cyan"
            content_display.append(Text(f"{msg.content}", style="dark_green"))

        elif isinstance(msg, AIMessage):
            title = "🤖 AI Response"
            border_color = "royal_blue1"
            if msg.content:
                content_display.append(Text(f"{msg.content}", style="blue"))

            if msg.tool_calls:
                for tc in msg.tool_calls:
                    tc_text = Text()
                    tc_text.append("\n🛠️  Tool Request: ", style="bold dark_magenta")
                    tc_text.append(f"{tc['name']}", style="dark_magenta")
                    tc_text.append(f"\n    Args: {tc['args']}", style="italic purple")
                    tc_text.append(f"\n    ID:   {tc['id']}", style="dim grey42")
                    content_display.append(tc_text)

        elif isinstance(msg, ToolMessage):
            title = "⚙️ Tool Output"
            border_color = "purple"
            content_display.append(Text(f"{msg.content}", style="indigo"))

        # Footer
        footer = ""
        if hasattr(msg, "usage_metadata") and msg.usage_metadata:
            u = msg.usage_metadata
            footer = f"💎 Usage: {u.get('total_tokens')} tokens"

        # Imprimir Panel (Esto sí usa HTML, pero como es un bloque grande, el margen no molesta)
        rprint(
            Panel(
                Group(*content_display),
                title=f"[bold {border_color}]{title}[/]",
                subtitle=f"[grey42]{footer}[/]",
                border_style=border_color,
                padding=(0, 2),  # Padding vertical reducido
                expand=False,
            )
        )
