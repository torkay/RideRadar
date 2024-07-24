# RideRadar
### Let us do the searching 🔎; Comparitive car buy and sell.

RideRadar expands your options by comparing the entire market, providing listings from every popular car-market site in Australia.
Get the most from your sold car and quickly by comparing offers across every car sales platform instantaneously after posting.

## Developer apparatus
Early developer rideradar library support for database content, data analysis, scheduled automative listing services.
### Importing libraries
```
from rideradar.engine.utils import *
from rideradar.engine.src_scraper import search_by
```
### Request vehicle data
Yield results based on `keyword` or `keywords`
```
search = search_by.specific(vehicle_make)
current_data = await search.search_by_specific()
```
Yield results based on `brand type`
```
search = search_by.vehicle_brand(vehicle_make)
current_data = await search.search_by_brand()  # Call the correct method here
```
### Schedule automative listing service
1. Update `vehicles.txt` to yield results based on interchangeably `brand type` and `keyword type` in the according format
2. Run `schedule_loop.py`
Additionally, point `webhook_handler.py` toward desired web address for personal use


## Developmental outline of RideRadar.
![Showcase Image](mindmap.md)

## Features
### Buy
- Manheim
- Pickles
- Carsales
- Autotrader
- Gumtree
- FB Marketplace
### Sell
- Carsales
- Autotrader
- Gumtree
- FB Marketplace

## Value a deal? 🏷️ Every car, one click away.

### Dev log:
> Manheim, Pickles completed. Simply upon requesting a vehicle brand, returned to you will be a list of vehicles each including information containing the title, the link to sale, and image.

> Interact with the service via discord, request information via a discord bot programmed with Discord.py, and recieve extensive sale returns via discord webhook's.

> Development on 24/7 vehicle scout service is in fruition, just bought a Raspberry Pi 5, in hopes to host this locally!

### To do:
> Init linux server in virtual environment for packages and install 24/7 schedule.

> Extend the scope of web-crawler to various other used car vendors including: Facebook marketplace via their developer api, Carsales.com.au, Grays.com and Gumtree.com.au!

> Have the service hosted via my Raspberry Pi 5 server, and have a full-stack portal hosted in conjunction with torkay.com that'll connect to my local server in order to crawl the web.

> Be able to create accounts, save listings to that account, and keep fingers in each listing to discover if they've sold yet and delete them from the server. 



