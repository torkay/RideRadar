from src_scraper import retrieve_data
from colorama import init, Fore, Style
import logging

def console(colour, text: str):
    colors = {
        'black': '\033[30m',
        'red': '\033[31m',
        'green': '\033[32m',
        'yellow': '\033[33m',
        'blue': '\033[34m',
        'magenta': '\033[35m',
        'cyan': '\033[36m',
        'white': '\033[37m',
        'reset': '\033[0m'
    }
    
    if color.lower() in colors:
        color_code = colors[color.lower()]
        reset_code = colors['reset']
        print(color_code + text + reset_code)
    else:
        logging.error("Error occured during coloring console: Invalid Color")

# Example usage:
#print_colored_text('red', 'This text is red.')
#print_colored_text('blue', 'This text is blue.') 

