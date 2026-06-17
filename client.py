from dotenv import load_dotenv
from pydomo import Domo

import os

load_dotenv()

class DomoClass:
    def __init__(self):
        self.domo_api_url = os.getenv("DOMO_API_URL")
        self.domo_client_id = os.getenv("DOMO_CLIENT_ID")
        self.domo_client_secret = os.getenv("DOMO_CLIENT_SECRET")

    def get_domo_client(self):
        domo_client = Domo(self.domo_client_id, self.domo_client_secret, api_host=self.domo_api_url)
        return domo_client