import streamlit as st
import asyncio
import os
import sys

# Ensure app can be imported
sys.path.append(os.getcwd())

from langchain_core.messages import HumanMessage
from app.agents.router.graph import router_graph
from uuid import uuid4

# Setup page
st.set_page_config(page_title="VetCare AI", page_icon="🐾", layout="centered")

st.title("🐾 VetCare AI")
st.caption("Asistente virtual para clínicas veterinarias")

# Sidebar
with st.sidebar:
    st.header("Configuración")

    # Check for API Key
    api_key_env = os.environ.get("OPENAI_API_KEY")
    api_key_input = st.text_input(
        "OpenAI API Key", type="password", value=api_key_env if api_key_env else ""
    )

    if api_key_input:
        os.environ["OPENAI_API_KEY"] = api_key_input

    st.markdown("---")
    st.markdown("[View Source](https://github.com/your-repo)")

    if st.button("Reiniciar Conversación", type="primary"):
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "¡Hola! Soy VetCare AI. ¿En qué puedo ayudarte hoy con tu mascota?",
            }
        ]
        st.session_state.thread_id = str(uuid4())
        st.rerun()

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "¡Hola! Soy VetCare AI. ¿En qué puedo ayudarte hoy con tu mascota?",
        }
    ]

if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid4())

# Display Chat History
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])


# Helper function to run the graph
async def get_agent_response(prompt, thread_id):
    inputs = {"messages": [HumanMessage(content=prompt)]}
    config = {"configurable": {"thread_id": thread_id}}

    # We use ainvoke to get the final state
    try:
        result = await router_graph.ainvoke(inputs, config)
        messages = result.get("messages", [])
        if messages and len(messages) > 0:
            last_msg = messages[-1]
            return last_msg.content
        return "No se recibió respuesta del agente."
    except Exception as e:
        return f"Error al procesar la solicitud: {str(e)}"


# User Input
if prompt := st.chat_input():
    if not os.environ.get("OPENAI_API_KEY"):
        st.info("Por favor ingresa tu OpenAI API Key para continuar.")
        st.stop()

    # Append and display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.chat_message("user").write(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("VetCare AI está escribiendo..."):
            # Run async function in sync context
            response_text = asyncio.run(
                get_agent_response(prompt, st.session_state.thread_id)
            )
            st.write(response_text)

    # Append assistant response
    st.session_state.messages.append({"role": "assistant", "content": response_text})
