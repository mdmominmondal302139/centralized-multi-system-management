# Run once after connecting to MongoDB.
# Example:
# from database.indexes import create_directory_indexes
# create_directory_indexes(db)

def create_directory_indexes(db):
    collection = db["district_directory_records"]
    collection.create_index([("category", 1), ("district", 1), ("upazila", 1)])
    collection.create_index([("verification_status", 1)])
    collection.create_index([("name", 1)])
    collection.create_index([("phone", 1)])
    collection.create_index([("institution", 1)])

    corrections = db["district_directory_corrections"]
    corrections.create_index([("status", 1), ("created_at", -1)])
