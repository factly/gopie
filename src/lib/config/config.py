import os

from dotenv import load_dotenv
from portkey_ai import createHeaders

load_dotenv()


class Config:
    def __init__(self):
        self.model = "gpt-4o"

        portkey_api_key = os.getenv("PORTKEY_API_KEY")
        virtual_key = os.getenv("VIRTUAL_KEY")

        self.gemini_api_key = os.getenv("GOOGLE_API_KEY")
        self.portkey_headers = createHeaders(
            api_key=portkey_api_key, virtual_key=virtual_key
        )


config = Config()
