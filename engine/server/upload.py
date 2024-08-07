from pymongo import MongoClient
import engine.scraper.src_scraper as scraper  # Import your scraper code

# Connect to MongoDB Atlas
client = MongoClient("mongodb+srv://<username>:<password>@cluster0.mongodb.net/myFirstDatabase?retryWrites=true&w=majority")
db = client["myFirstDatabase"]
collection = db["vehicles"]

# Scrape data
data = scraper.scrape()

# Check if the data already exists in the collection
existing_data = collection.find_one(data)

if existing_data is None:
    # Insert the data into MongoDB
    collection.insert_one(data)