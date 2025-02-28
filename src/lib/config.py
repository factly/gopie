import os

from dotenv import load_dotenv
from portkey_ai import createHeaders

load_dotenv()

class Config:

    def __init__(self):
        self.model = "gpt-4o"

        # groq_api_key = os.getenv("GROQ_API_KEY")
        # if not groq_api_key:
        #     raise ValueError("GROQ_API_KEY is not set")
        # self.groq_api_key = groq_api_key

        portkey_api_key = os.getenv("PORTKEY_API_KEY")
        virtual_key = os.getenv("VIRTUAL_KEY")
        self.portkey_headers = createHeaders(api_key=portkey_api_key, virtual_key=virtual_key)

config = Config()
