# test_mongo.py

import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load variables from .env file
load_dotenv()

# Get the connection string from the environment
MONGO_URI = os.getenv("MONGO_CONNECTION_STRING")

if not MONGO_URI:
    print("❌ ERROR: Could not find MONGO_CONNECTION_STRING in your .env file.")
else:
    print("✅ Found connection string. Attempting to connect...")
    client = None  # Initialize client to None
    try:
        # Create a new client and connect to the server
        client = MongoClient(MONGO_URI)

        # Send a ping to confirm a successful connection
        client.admin.command('ping')
        print("✅ Ping successful. You are connected to MongoDB!")

        # Define the database and collection
        db = client['CloudResourceOptimizationDB']
        test_collection = db['test_collection']

        # Insert a test document
        test_doc = {"name": "test_from_script", "status": "success"}
        result = test_collection.insert_one(test_doc)

        print(f"✅ Successfully inserted a document with _id: {result.inserted_id}")
        print("Please check your MongoDB Atlas dashboard now.")

    except Exception as e:
        print(f"❌ An error occurred: {e}")
    
    finally:
        # Ensures that the client will close when you finish/error
        if client:
            client.close()
