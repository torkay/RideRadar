from src_scraper import retrieve_data

request = input("Enter desired vehicle make: ")
print("Searching...")

print(retrieve_data(request))