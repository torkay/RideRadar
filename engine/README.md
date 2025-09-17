# RideRadar Server Engine
## Developer update log

Pickles engine update 0.0.3
1) Fixed pickles engine
2) Enchanced pickles engine scraping abilities
3) Updated webhook handler to handle new research

![Showcase Image](./storage/pickes-update.md)

Gumtree engine update 0.0.3
1) Fixed gumtree engine
2) Enhanced gumtree engine and webhook handler

## Engine usage
Refer to `Test.py` for example usage

### For easy individual assignment of a worker/crawler for research
Step 1. Declare to initialise the worker `worker = src_scraper.search_by.vehicle_brand("BMW")`

Step 2. Deploy and store worker's efforts `bmw_vehicles = await worker.search_pickles()`

Explaination: Worker will search by brand type 'BMW' on 'Pickles' and return data as 'bmw_vehicles'

### To scheduled a worker
Step 1. Append all desired both `brand` and `specific` type vehicles to `vehicles.txt` in existing format

Step 2. Configure secrets via environment variables (do not hardcode)

- Set `DISCORD_WEBHOOK_URL` to your custom Discord webhook URL
- Set `SUPABASE_DB_URL` if you want to persist to Postgres
- Optionally set `PROD_ORIGIN` for API CORS and `DB_BACKEND` (defaults to `postgres`)

Example: create `engine/.env` with these values when running locally. Never commit real secrets.

Step 3. Run `schedule_loop.py` on your local machine

Optionally, alter the wait time before shifts i.e. `next_run_time = time.time() + (60 * 60 * 3)  # 3 hours from now`

## ToDo:
* Add gumtree listing requirements before appenditure
* Enhance Manheim engine and webhook

## Machines to run on:
* MacOS (Primary)
* Windows
* Linux (Preferred)
