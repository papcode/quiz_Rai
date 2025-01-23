from pymongo import MongoClient
from config.config_reader import load_config

# Load configuration
config = load_config()

# MongoDB setup
mongo_uri = config['MONGO_URI']
database_name = config['DATABASE_NAME']
collection_name = config['COLLECTION_NAME']

# Initialize MongoDB connection
client = MongoClient(mongo_uri)
db = client[database_name]
users_collection = db[collection_name]
