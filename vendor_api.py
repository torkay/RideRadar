# TODO: Have situated here: Function for each vendor "pickles", "manheim" under a class "search" have each vendor then dynamically called upon request

class search:
    def __init__(self):
        self.vendor_order = []

    def register_vendor(self, func):
        self.vendor_order.append(func.__name__)
        return func

    def crawl_registered_vendors(self, vendor_names):
        for name in vendor_names:
            if name in self.vendor_order:
                getattr(self, name)()

    @register_vendor
    def pickles(self):
        print("pickles called") # Scraper here

    @register_vendor
    def manheim(self):
        print("manheim called") # Scraper here

# Example usage:
search_instance = Search()
search_instance.crawl_registered_vendors(['pickles', 'manheim'])
