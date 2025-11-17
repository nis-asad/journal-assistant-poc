from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

# MongoDB URI from .env
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://kasad_db_user:tD5GqXzUqX697Z2C@basic.su6r0wq.mongodb.net/journal_poc?retryWrites=true&w=majority&ssl=true")
if not MONGO_URI:
    raise RuntimeError("Missing MONGO_URI in .env file")

DB_NAME = os.getenv("DB_NAME", "journal_poc")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collection for journal entries
journal_collection = db["journal_entries"]
