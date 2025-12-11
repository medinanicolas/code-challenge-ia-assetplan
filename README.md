# VetCare AI (Challenge IA AssetPlan)

## Instalación y Ejecución

Sigue estos pasos para instalar y ejecutar el chatbot en tu entorno local.

### Prerrequisitos

*   **Python**: 3.13 o superior.
*   **Gestor de paquetes**: [uv](https://docs.astral.sh/uv/getting-started/installation/).

### Instalación

1.  **Clonar el repositorio**

    ```bash
    git clone https://github.com/medinanicolas/code-challenge-ia-assetplan.git
    cd code-challenge-ia-assetplan
    ```

2.  **Instalar dependencias**

    ```bash
    uv sync
    ```

### Configuración

Copia el archivo de ejemplo `.env.example` a `.env` y edítalo con tus propias credenciales:

```bash
cp .env.example .env
```

### Ejecutar el Chatbot

Para levantar la interfaz de usuario:

```bash
uv run streamlit run app/ui/streamlit_app.py
```

---

## LangChain o LangGraph

Para este desafío utilicé LangGraph, ya que considero que ofrece un enfoque mucho más robusto que LangChain para chatbots, el cual suelo utilizar principalmente para flujos de trabajo estáticos que no requieren una interacción continua con el usuario.

## Arquitectura

Como arquitectura me basé principalmente en los patrones de [Multi-Agent](https://docs.langchain.com/oss/python/langchain/multi-agent) listados en la documentación oficial, como son [Tool Calling](https://docs.langchain.com/oss/python/langchain/multi-agent#tool-calling) y [Handoffs](https://docs.langchain.com/oss/python/langchain/multi-agent#handoffs). Aunque este último, al día de hoy (7 Dic 25), todavía no está documentado oficialmente, su implementación se puede encontrar en el código fuente de sistemas como [Swarm](https://github.com/langchain-ai/langgraph-swarm-py) y [Supervisor](https://github.com/langchain-ai/langgraph-supervisor-py).

Esto se fundamenta en los siguientes puntos:

1.  Consideré importante que el Router respondiera a inputs sencillos como "Hola", sin necesidad de que su única función fuera entregar el siguiente nodo mediante un output estructurado. Si bien sospecho que implementaciones actuales como `create_agent` lo realizan internamente mediante `Tool Calling`, se buscaba habilitar también el punto 2.
2.  Se buscaba que el Router transfiriera el control total de la interacción con el usuario al agente de Booking.

Para lograr esto, se implementó el siguiente enfoque:

*   Por un lado, se utilizó [Tool Calling](https://docs.langchain.com/oss/python/langchain/multi-agent#tool-calling) para el agente RAG, dado que este no requiere interactuar directamente con el usuario, sino utilizar la solicitud para buscar información relevante, procesarla y devolverla.

*   Por otro lado, se empleó [Handoff](https://docs.langchain.com/oss/python/langchain/multi-agent#handoffs) para el agente de Booking. Si bien este devuelve el resultado de la interacción al agente coordinador, también permite mantener al agente de Booking como el activo.

*   Se implementó una propiedad de estado (`active_agent`) basada en [Swarm](https://github.com/langchain-ai/langgraph-swarm-py) para mantener la interacción del usuario con el agente correspondiente.

*   Se utilizó un [entrypoint condicional](https://docs.langchain.com/oss/python/langgraph/graph-api#conditional-edges) para dirigir la interacción del usuario hacia el agente activo.

*   Se implementó un sistema de guardrails para detectar y prevenir posibles situaciones inapropiadas. No se usó un Middleware ya que la documentación solo muestra ejemplos de uso con [create_agent](https://docs.langchain.com/oss/python/langchain/agents), el cual es un `CompiledStateGraph` y que además tiene su propio `ToolNode` interno, el cual ejecuta la función y devuelve el resultado. Lo que dificulta el `Handoff` hacia el agente Booking.

#### ¿Por qué no se utilizaron solo los componentes built-in de alto nivel de LangChain/LangGraph?

> En primer lugar, las opciones built-in pueden limitar los flujos complejos. En segundo lugar, el código base ha evolucionado significativamente, destacando el último release de [LangChain v1](https://docs.langchain.com/oss/python/releases/langchain-v1), donde muchas funcionalidades, especialmente de la comunidad, se encuentran en paquetes separados o [legados](https://reference.langchain.com/python/langchain_classic/).

## Sistema RAG

### Procesamiento de documentos

Se seleccionó `GPT-5-mini` para el OCR del PDF tras realizar pruebas en el playground y revisar la tabla de precios de los modelos actuales de OpenAI.

El pre-procesamiento de documentos se realizó en [RAG-preprocessing.ipynb](./notebooks/RAG-preprocessing.ipynb).

> **Nota de Ingesta:** La base de conocimiento ya ha sido generada e incluida en el repositorio (ver carpeta `data/`). No es necesario ejecutar procesos de ingesta para levantar el proyecto. Los notebooks se incluyen solo como referencia del trabajo realizado manualmente.

### Chunking y VectorStore

Se eligió un enfoque de [ParentDocumentRetriever](https://medium.aiplanet.com/advanced-rag-providing-broader-context-to-llms-using-parentdocumentretriever-cc627762305a) con búsqueda híbrida. Se combinó la búsqueda por similitud de vectores con el algoritmo BM25 mediante `EnsembleRetriever`, privilegiando levemente la búsqueda vectorial.

Se optó por este enfoque debido a:

1.  Permite que los documentos hijos sean específicos, manteniendo el contexto mediante sus documentos padres.
2.  La búsqueda por similitud de vectores es potente, pero puede ser generalista en temas cercanos (e.g., "salud de perros" vs "salud de gatos"). El algoritmo BM25 ayuda a diferenciar mediante palabras clave exactas.
3.  El re-ranking permite refinar los resultados obtenidos.

Para el VectorStore se utilizó ChromaDB.

El chunking e indexación se encuentran en [RAG](./notebooks/RAG.ipynb).

### Retriever

Se añadió un algoritmo de re-ranking, el cual asegura la calidad de los datos recuperados. Si bien conlleva un mayor costo computacional, el modelo [BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) presenta un rendimiento superior en contextos multilenguaje.

Adicionalmente, se utilizó `Query enhancement` para asistir al algoritmo BM25 en la recuperación de documentos.

## Modelos usados y alternativas

*   **GPT-5-mini**:
    *   Velocidad moderada.
    *   Resultados superiores a versiones anteriores en tool calls.
    *   Costo eficiente.
*   **GPT-5-nano**:
    *   Modelo ultra ligero y rápido.
    *   Utilizado para tareas de clasificación (Guardrails).

## Observabilidad

Se utilizó [LangSmith](https://smith.langchain.com/) para observar el flujo de la aplicación.

## ¿Dónde se usó "Vibe-Coding"?

* Gran parte de la ingesta de datos se hizo mediante "Vibe-Coding", ya que su implementación es bastante estándar y replicable.
* Muchos de los prompts fueron generados y mejorados en un proceso iterativo.
* Tareas repetitivas como creación de carpetas y archivos, así como importación de librerías.
* La UI de Streamlit se modificó a partir de este [template](https://llm-examples.streamlit.app/?ref=streamlit-io-gallery-llms).

## Notas finales

Algunos aspectos no pulidos se relacionan con el comportamiento inherente del modelo, lo cual requeriría un proceso iterativo de prueba y corrección más extenso. Se considera que el prompt engineering podría mejorar varios de estos puntos. Sin embargo, la base actual es sólida y escalable. 
