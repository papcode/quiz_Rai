from pymongo import MongoClient
import logging
from config.config_reader import load_config

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_mongo_connection():
    config = load_config()
    mongo_uri = config['MONGO_URI']
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        client.server_info()  # Trigger a call to the server
        print("MongoDB connection successful!")
    except Exception as e:
        print(f"MongoDB connection failed: {e}")
        exit(1)  # Exit with error status if connection fails

if __name__ == "__main__":
    test_mongo_connection()
