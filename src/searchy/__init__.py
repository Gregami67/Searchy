from dotenv import load_dotenv

# TODO: Not necessary for docker compose (I think)
load_dotenv()

from .app import Searchy as Searchy
