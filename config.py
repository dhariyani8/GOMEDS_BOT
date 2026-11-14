import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
)

CLASSIFIER_MODEL = "meta/muse-glimmer-30b"
PARSER_MODEL = "meta/muse-glimmer-30b"