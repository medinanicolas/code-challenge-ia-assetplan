from langchain.chat_models import init_chat_model
from dotenv import load_dotenv

load_dotenv()

gpt_5_mini = init_chat_model("gpt-5-mini", model_provider="openai")

gpt_5_nano = init_chat_model("gpt-5-nano", model_provider="openai")

# omni_moderation = init_chat_model("omni-moderation-latest", model_provider="openai")
