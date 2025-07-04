import requests
import json

url = "https://www.bikesales.com.au/_next/data/QEoQIyQo-R7ShAHSyqMYm/bikes.json"
params = {
    "pathname": "/bikes/",
    "initialBreakpoint": "wide",
    "sort": "Price",
    "trackingAction": "sortby",
    "allRoutes": "bikes"
}

headers = {
    "accept": "*/*",
    "referer": "https://www.bikesales.com.au/bikes/?q=Service.bikesales.",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "x-nextjs-data": "1"
}

cookies = {
    "csncidcf": "75AECF3C-7114-4CD3-ABE4-AC5789BF9F54",
    "datadome": "9cxYjNCJqjy9xvSHyjkhBK7IY1swnmRg2pSz9Cmv_YP0lLUK0yo5O4ikv5~k68stuwxzAawI_Dj9HMqoyzQkNI893cf4k1zbiSSp2fVdjTKZNbJAQkrrk4wg9WgHbPaE",
    # Include any other required cookies as needed
}

response = requests.get(url, headers=headers, params=params, cookies=cookies)

if response.ok:
    with open("bikesales_dump.json", "w") as f:
        json.dump(response.json(), f, indent=4)
    print("✅ JSON response saved to bikesales_dump.json")
else:
    print(f"Request failed: {response.status_code}")