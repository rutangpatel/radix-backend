from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

def get_database():
    mongo_url = os.getenv("MONGO_DB_CONNECTION")
    client = MongoClient(mongo_url)
    return client['radix']

if __name__ == '__main__':
    radix = get_database()