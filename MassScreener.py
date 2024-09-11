import asyncio
import argparse
from urllib.parse import urlparse
import re
import os
from playwright.async_api import async_playwright
from colorama import init, Fore

# Initialize colorama
init()

def sanitize_filename(url):
    """Sanitize a URL to be used as a valid filename, including port number if present."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path.replace("/", "_")
    port = f"_{parsed_url.port}" if parsed_url.port else ""

    # Join domain, port, and path to create a unique filename, and remove invalid characters
    sanitized_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', f"{domain}{port}{path}")
    
    # Limit the filename length to prevent OS issues
    return sanitized_name[:150]  # 150 characters max

async def add_url_overlay(page, url):
    """Add an overlay on the right side of the page to display the visited URL at the bottom."""
    overlay_script = f"""
    let urlBar = document.createElement('div');
    urlBar.style.position = 'fixed';
    urlBar.style.bottom = '0';  /* Move the URL bar to the bottom */
    urlBar.style.right = '0';
    urlBar.style.width = '250px'; /* Decrease the width */
    urlBar.style.height = 'auto'; /* Allow height to adjust based on content */
    urlBar.style.backgroundColor = 'rgba(0, 0, 0, 0.2)'; /* 20% transparency */
    urlBar.style.color = 'black';
    urlBar.style.fontSize = '20px';
    urlBar.style.padding = '10px';
    urlBar.style.zIndex = '9999';
    urlBar.style.fontFamily = 'Arial, sans-serif';
    urlBar.style.overflowY = 'auto'; /* Ensure the text can scroll if too long */
    urlBar.style.textAlign = 'center'; /* Center-align text */
    urlBar.innerText = '{url}';
    document.body.appendChild(urlBar);
    """
    await page.evaluate(overlay_script)

async def take_screenshot(browser, url):
    """Take a screenshot of a single URL and save it to the appropriate directory."""
    page = await browser.new_page()
    try:
        # Visit the URL with a 20-minute timeout
        response = await page.goto(url, timeout=1200000, wait_until="load")

        # Check if the page was successfully loaded
        if response.status >= 400:  # Check if status indicates a problem
            screenshot_name = f"Not Reachable/{sanitize_filename(url)}_not_reachable.png"
            print(Fore.RED + f"URL not reachable: {url}")
        else:
            screenshot_name = f"Reachable/{sanitize_filename(url)}.png"
            print(Fore.GREEN + f"URL reachable: {url}")

        # Add the URL overlay to the page
        await add_url_overlay(page, url)

        # Save the screenshot
        await page.screenshot(path=screenshot_name, full_page=True)
        print(f"Screenshot saved as {screenshot_name}")

    except Exception as e:
        # If an exception occurs, mark it as not reachable
        screenshot_name = f"Not Reachable/{sanitize_filename(url)}_not_reachable.png"
        print(Fore.RED + f"Error visiting {url}: {e}")
        await page.screenshot(path=screenshot_name, full_page=True)
    finally:
        await page.close()

async def take_screenshots(urls):
    async with async_playwright() as p:
        # Launch Firefox browser in headless mode
        browser = await p.firefox.launch(headless=True)

        # Create 'Reachable' and 'NR' directories if they don't exist
        if not os.path.exists('Reachable'):
            os.makedirs('Reachable')
        if not os.path.exists('Not Reachable'):
            os.makedirs('Not Reachable')

        # Process URLs one at a time
        for url in urls:
            await take_screenshot(browser, url)

        # Close the browser when done
        await browser.close()

def read_urls_from_file(file_path):
    """Read URLs from the given file, one URL per line."""
    with open(file_path, 'r') as file:
        urls = [line.strip() for line in file.readlines() if line.strip()]
    return urls

def print_ascii_art():
    """Print ASCII art for the program."""
    ascii_art = r"""
    
  __  __                _____                                    
 |  \/  |              / ____|                                   
 | \  / | __ _ ___ ___| (___   ___ _ __ ___  ___ _ __   ___ _ __ 
 | |\/| |/ _` / __/ __|\___ \ / __| '__/ _ \/ _ \ '_ \ / _ \ '__|
 | |  | | (_| \__ \__ \____) | (__| | |  __/  __/ | | |  __/ |   
 |_|  |_|\__,_|___/___/_____/ \___|_|  \___|\___|_| |_|\___|_|
                                                                    
    """
    print(Fore.CYAN + ascii_art)

def main():
    # Print ASCII art
    print_ascii_art()

    # Argument parser for command-line arguments
    parser = argparse.ArgumentParser(description="MASS WEBSITE SCREENSHOTER - Take screenshots of URLs from a file.")
    parser.add_argument('-u', '--urls', required=True, help="Path to the text file containing URLs (one URL per line)")

    # Parse the arguments
    args = parser.parse_args()

    # Read URLs from the provided file
    urls = read_urls_from_file(args.urls)

    # Run the asynchronous screenshot task sequentially
    asyncio.run(take_screenshots(urls))

if __name__ == "__main__":
    main()
