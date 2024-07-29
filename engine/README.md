# RideRadar Server Engine
## Developer update log

Pickles engine update 0.0.3
1) Fixed pickles engine
2) Enchanced pickles engine scraping abilities
3) Updated webhook handler to handle new research

![Showcase Image](./storage/pickes-update.md)

## Engine usage
Refer to `Test.py` for example usage

### For easy assignment of a worker for research

Step 1. Declare to initialise the worker `worker = src_scraper.search_by.vehicle_brand("BMW")`

Step 2. Deploy and store worker's efforts `bmw_vehicles = await worker.search_pickles()`

Explaination: Worker will search by brand type 'BMW' on 'Pickles' and return data as 'bmw_vehicles'

## ToDo:
* Fix Gumtree engine
* Enhance Manheim engine