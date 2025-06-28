from rich.console import Console
from rich.progress import Progress
import asyncio
import time
import platform
from utils import verbose, find, version, write
import os
from rich.panel import Panel
import RideRadar.engine.integrations.webhook_handler as webhook_handler

class Scheduler:
    def __init__(self):
        self.console = Console()

    def set_cmd_title(self, title):
        if platform.system() == 'Windows':
            os.system(f"title {title}")

    def print_header(self, header_text=f"Start {platform.system().capitalize()} server instance {version}", title="RideRadar", title_align="left", subtitle="Schedule Loop", border_style="bold cyan"):
        panel = Panel(header_text, title=title, title_align=title_align, subtitle=subtitle, border_style=border_style)
        self.console.print(panel)

    async def process_vehicles(self, file_path):
        vehicle_list = []
        with open(file_path, 'r') as file:
            for line in file:
                vehicle_make = line.strip()  # Remove leading/trailing whitespaces and newlines
                vehicle_list.append(vehicle_make)

        total_vehicles = len(vehicle_list)
        with Progress(console=self.console, transient=True) as progress:
            task = progress.add_task("[cyan]Searching internet...", total=total_vehicles)
            
            for vehicle_make in vehicle_list:
                # Update progress bar
                progress.update(task, description=f"Searching web for {vehicle_make}...", advance=1)
                
                # Perform the search operation (actual webhook handler function call)
                result = await webhook_handler.run(vehicle_make)  # Assuming this function is asynchronous
                
                if verbose:
                    self.console.print(f"Results for {vehicle_make}: {result}")

    async def run_handler(self):
        file_path = find.vehicle_text()
        if find.server_os() == 'windows':
            self.set_cmd_title("RideRadar: Scheduler (DO NOT CLOSE)")
        await self.process_vehicles(file_path)

async def main():
    scheduler = Scheduler()
    scheduler.print_header()
    while True:
        start_time = time.time()
        await scheduler.run_handler()
        end_time = time.time()
        elapsed_time = end_time - start_time
        formatted_elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed_time))
        next_run_time = time.time() + (60 * 60 * 24)  # 24 hours from now
        formatted_next_run_time = time.strftime("%I:%M%p %m/%d/%y", time.localtime(next_run_time))
        scheduler.print_header(header_text=f"Worker completed search | Time elapsed: {formatted_elapsed_time}", title="Completed Work", title_align="left", subtitle=f"Waiting until {formatted_next_run_time}", border_style="green")
        await asyncio.sleep(60 * 60 * 24)  # Sleep for 24 hours

if __name__ == "__main__":
    asyncio.run(main())
