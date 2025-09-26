#%%
# Scraper for Swiss Army Service Information

#%%
import pandas as pd
import re
import datetime
import sqlite3
import json
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Configure logging
log_file = os.path.join("logs", "scraper.log")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=log_file,
    filemode="a"  # Append to the log file
)

# Today's date for scrapeDate field and JSON filename
today_date = datetime.date.today().strftime('%Y-%m-%d')

#%%
# Function to initialize WebDriver
def initialize_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    
    # Working options from successful test (but keep JavaScript enabled)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--allow-running-insecure-content")
    chrome_options.add_argument("--disable-web-security")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-plugins")
    chrome_options.add_argument("--disable-images")  # Keep this - images aren't needed for scraping
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--no-zygote")
        
    # Don't specify user-data-dir - let Chrome handle it
    chrome_options.binary_location = "/usr/bin/chromium"
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Function to scrape data from the current page
def scrape_data(driver, language):
    # Extract all table rows on the current page
    table_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    # Initialize lists to store the extracted data
    troop_school = []
    start_date = []
    end_date = []

    # Collect data from each row
    for row in table_rows:
        columns = row.find_elements(By.TAG_NAME, "td")
        
        if len(columns) == 3:  # Make sure the row has 3 columns
            troop_school.append(columns[0].text.strip())  # First column: Troop/School

            start_date_raw = columns[1].text.strip()  # Second column: Start date
            start_date.append(datetime.datetime.strptime(start_date_raw, "%d.%m.%Y").strftime("%Y-%m-%d"))

            end_date_raw = columns[2].text.strip()  # Third column: End date
            end_date.append(datetime.datetime.strptime(end_date_raw, "%d.%m.%Y").strftime("%Y-%m-%d"))
        
        else:
            logging.warning("Row does not have 3 columns.")

    # Return the data as a list of dictionaries
    return [{"language": language, "troopSchool": troop, "startDate": start, "endDate": end}
            for troop, start, end in zip(troop_school, start_date, end_date)]

# Function to click the second button (next page button)
def click_next_button(driver):
    try:
        # Get current page number before clicking
        page_span = driver.find_element(By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center span")
        current_page_text = page_span.text
        
        # Try multiple approaches to find and click the next button
        next_button = None
        
        # Method 1: Use the XPath you provided
        try:
            next_button = driver.find_element(By.XPATH, '//*[@id="__nuxt"]/div[2]/div[2]/div[5]/div[2]/div/div/div[2]/button[2]')
            logging.info("Found next button using XPath method")
        except:
            pass
        
        # Method 2: CSS selector approach (fallback)
        if not next_button:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center button")
                if len(buttons) >= 2:
                    next_button = buttons[1]  # Second button
                    logging.info("Found next button using CSS selector method")
            except:
                pass
        
        # Method 3: Find by looking for enabled button (not disabled)
        if not next_button:
            try:
                buttons = driver.find_elements(By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center button:not([disabled])")
                if buttons:
                    next_button = buttons[-1]  # Last enabled button should be next
                    logging.info("Found next button using enabled button method")
            except:
                pass
        
        if next_button:
            # Check if button is clickable
            next_button_class = next_button.get_attribute('class') or ''
            disabled_attr = next_button.get_attribute('disabled')
            
            if disabled_attr is None and 'cursor-not-allowed' not in next_button_class:
                # Scroll to button to ensure it's visible
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                
                # Try clicking with JavaScript if regular click fails
                try:
                    next_button.click()
                    logging.info("Clicked next button with regular click")
                except Exception as click_error:
                    logging.info(f"Regular click failed, trying JavaScript click: {click_error}")
                    driver.execute_script("arguments[0].click();", next_button)
                    logging.info("Clicked next button with JavaScript")
                
                # Wait for page number to change
                try:
                    WebDriverWait(driver, 15).until(
                        lambda driver: (
                            driver.find_element(By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center span")
                            .text != current_page_text
                        )
                    )
                    logging.info("Page navigation confirmed - page number changed")
                    return True
                except Exception as wait_error:
                    logging.error(f"Page number did not change after clicking: {wait_error}")
                    return False
            else:
                logging.info("Next button is disabled or not clickable.")
                return False
        else:
            logging.warning("Could not find next button with any method.")
            return False
            
    except Exception as e:
        logging.error(f"Error clicking next button: {e}")
        return False

# Function to scrape all data across pages
def scrape_all_data(url, language, headless=True, max_pages=200, show_progress=True):
    """
    Scrape data from all pages with safety limits and progress indicators.
    
    Args:
        url (str): URL to scrape
        language (str): Language code (DE, FR, IT)
        headless (bool): Run browser in headless mode
        max_pages (int): Maximum pages to scrape (safety limit / avoid infinite loops)
        show_progress (bool): Show progress messages
    """
    driver = initialize_driver(headless=headless)
    driver.get(url)

    all_data = []  # Initialize list to store scraped data
    pages_scraped = 0
    actual_max_pages = max_pages  # Will be updated with website's total pages
    
    if show_progress:
        print(f"Starting to scrape {language} data from {url}")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Debug: Check if page loaded correctly
        if show_progress:
            print(f"Page loaded. Title: {driver.title}")
            
        # Get total pages from the first page load
        try:
            # Wait for pagination element to be present
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center span"))
            )
            
            page_span = driver.find_element(By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center span")
            page_text = page_span.text  # "Seite X von Y" / "Page X de Y" / "Pagina X da Y"
            
            if show_progress:
                print(f"Found pagination text: '{page_text}'")
            
            # Use regex to extract current and total page numbers
            match = re.search(r"\D+\s(\d+)\s\D+\s(\d+)", page_text)
            if match:
                total_pages_on_site = int(match.group(2))
                # Use the smaller of max_pages or actual total pages
                actual_max_pages = min(max_pages, total_pages_on_site)
                
                if show_progress:
                    if total_pages_on_site < max_pages:
                        print(f"Website has {total_pages_on_site} pages - will scrape all pages")
                    else:
                        print(f"Website has {total_pages_on_site} pages - limiting to {max_pages} pages")
                        
                logging.info(f"Total pages available: {total_pages_on_site}, will scrape: {actual_max_pages}")
            else:
                if show_progress:
                    print(f"Could not parse pagination text: '{page_text}'")
                logging.warning(f"Could not parse pagination text: '{page_text}'")
                
        except Exception as e:
            if show_progress:
                print(f"Could not find pagination element, will use default max_pages: {e}")
            logging.warning(f"Could not determine total pages, using max_pages limit: {e}")
        
        # Debug: Check if table exists
        try:
            table_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            if show_progress:
                print(f"Found {len(table_rows)} table rows on first page")
        except Exception as e:
            if show_progress:
                print(f"Error finding table: {e}")
            logging.error(f"Error finding table: {e}")
            return all_data
        
        while pages_scraped < actual_max_pages:
            try:
                # Wait for the page to load and for the table body to be visible
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
                )
                
                # Scrape data from the current page
                page_data = scrape_data(driver, language)
                
                if show_progress:
                    print(f"Scraped {len(page_data)} records from current page")
                
                all_data.extend(page_data)  # Append the scraped data to the list
                
                # Get the current page and total pages from the page span text
                page_span = driver.find_element(By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center span")
                page_text = page_span.text  # "Seite X von Y" / "Page X de Y" / "Pagina X da Y"
                
                # Use regex to extract current and total page numbers
                match = re.search(r"\D+\s(\d+)\s\D+\s(\d+)", page_text)
                if match:
                    current_page = int(match.group(1))
                    total_pages = int(match.group(2))
                    
                    if show_progress:
                        print(f"Scraped page {current_page}/{total_pages} - {len(page_data)} records (Total: {len(all_data)})")
                    
                    logging.info(f"Page {current_page}/{total_pages}: {len(page_data)} records scraped")
                    
                    # Check if we should continue
                    if current_page < total_pages and pages_scraped < actual_max_pages - 1:
                        if show_progress:
                            print(f"Attempting to navigate to page {current_page + 1}...")
                        
                        if click_next_button(driver):
                            pages_scraped += 1
                            if show_progress:
                                print(f"Successfully navigated to next page")
                        else:
                            if show_progress:
                                print("Failed to navigate to next page - stopping")
                            logging.error("Navigation failed - stopping scraper")
                            break
                    else:
                        if current_page >= total_pages:
                            if show_progress:
                                print("Reached the last page.")
                            logging.info("Reached the last page.")
                        else:
                            if show_progress:
                                print(f"Reached page limit ({actual_max_pages} pages).")
                            logging.info(f"Reached page limit ({actual_max_pages} pages).")
                        break
                else:
                    logging.warning("Could not extract page numbers.")
                    break
                    
            except Exception as e:
                logging.error(f"Error on page {pages_scraped + 1}: {e}")
                if show_progress:
                    print(f"Error on page {pages_scraped + 1}: {e}")
                break
                
    except Exception as e:
        logging.error(f"Error during scraping initialization: {e}")
        if show_progress:
            print(f"Error during scraping initialization: {e}")
    finally:
        driver.quit()

    if show_progress:
        print(f"Completed {language}: {len(all_data)} total records from {pages_scraped + 1} pages")
    
    return all_data

# Function to insert into and update database
def update_database(data):
    # Connect to database
    conn = sqlite3.connect("data/service_dates.db") # creates DB if it doesn't exist

    conn.execute("""
    CREATE TABLE IF NOT EXISTS serviceDates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        language TEXT NOT NULL,
        troopSchool TEXT NOT NULL,
        startDate TEXT,     -- can be NULL if date not yet decided
        endDate TEXT,       -- can be NULL if date not yet decided
        scrapeDate TEXT NOT NULL,
        active BOOLEAN NOT NULL DEFAULT FALSE,
        UNIQUE(language, troopSchool, startDate, endDate)
    )
    """)

    # Conversion to df
    df = pd.DataFrame(data)
    df = df.drop_duplicates()  # Deduplicate (based on all columns)
    df["scrapeDate"] = today_date  # Set scrapeDate as today
    df["active"] = True  # Mark all scraped data as active

    # Transform df to SQL format and add to activeServiceDates table (creates it if not exists)
    df.to_sql("activeServiceDates", conn, if_exists="replace", index=False)

    # Insert new records or update the historical serviceDates table
    conn.execute("""
    INSERT OR REPLACE INTO serviceDates (language, troopSchool, startDate, endDate, scrapeDate, active)
    SELECT language, troopSchool, startDate, endDate, scrapeDate, active
    FROM activeServiceDates
    """)

    # "Deactivate" old records in the historical table that are not in activeServiceDates
    conn.execute("""
    UPDATE serviceDates
    SET active = false
    WHERE (language, troopSchool, startDate, endDate) NOT IN (
        SELECT language, troopSchool, startDate, endDate
        FROM activeServiceDates
    )
    """)

    # Commit changes and close the connection
    conn.commit()
    conn.close()
    logging.info("Database updated successfully.")

# Function to save data to a JSON file
def save_data_to_json(data, filename=f"latest_service_dates_{today_date}.json"):
    try:
        # Files will be saved in the json_exports folder (created in Dockerfile)
        filepath = os.path.join("json_exports", filename)
        
        with open(filepath, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)  # ensure_ascii=False to keep it human-readable
        logging.info(f"Data successfully saved to {filepath}.")
    except Exception as e:
        logging.error(f"Error saving data to JSON: {e}")

# Function to start scraping, updating the database, and optionally save data as JSON file
def run_scraper(save_as_json=False, json_filename=f"latest_service_dates_{today_date}.json", 
                hide_scraping_browser=True, max_pages=200, show_progress=True):
    """
    Run the scraper with configurable page limits.
    
    Args:
        save_as_json (bool): Save results to JSON file
        json_filename (str): JSON filename
        hide_scraping_browser (bool): Run browser in headless mode
        max_pages (int): Maximum pages to scrape per language
        show_progress (bool): Show progress messages
    """
    # Languages and URLs to scrape
    urls = {
        "DE": "https://www.armee.ch/de/aufgebotsdaten",
        "FR": "https://www.armee.ch/fr/dates-de-convocation",
        "IT": "https://www.armee.ch/it/date-di-chiamata-in-servizio"
    }

    all_scraped_data = [] # List to store all scraped data

    try:
        if show_progress:
            print(f"Starting scraper with max {max_pages} pages per language")
            
        # Scraping the data
        for language, url in urls.items():
            try:
                logging.info(f"Scraping data for {language} (max {max_pages} pages)...")
                language_data = scrape_all_data(url, language, 
                                              headless=hide_scraping_browser, 
                                              max_pages=max_pages,
                                              show_progress=show_progress)
                all_scraped_data.extend(language_data)
                
                if show_progress:
                    print(f"Completed {language}: {len(language_data)} records")
                    
            except Exception as e:
                logging.error(f"Error scraping {language} ({url}): {e}")
                if show_progress:
                    print(f"Error scraping {language}: {e}")

        # Update database if we have data
        if all_scraped_data: # if not empty
            if show_progress:
                print(f"Total records scraped: {len(all_scraped_data)}")
                print("Updating database...")
                
            update_database(all_scraped_data)

            # Save data to JSON if requested (if True)
            if save_as_json:
                save_data_to_json(all_scraped_data, filename=json_filename)
                if show_progress:
                    print(f"Data saved to {json_filename}")
            
            logging.info(f"Scraper completed successfully. {len(all_scraped_data)} records processed.")
            return {"status": "success", "message": f"Scraping completed successfully. {len(all_scraped_data)} records processed."}

        else:
            logging.warning("No data scraped. Skipped database and JSON update.")
            return {"status": "warning", "message": "Scraper ran but no data was found."}

    except Exception as e:
        logging.error(f"An error occurred while running the scraper: {e}")
        return {"status": "error", "message": f"An error occurred: {e}"}

#%%
# Make script importable and callable
if __name__ == "__main__":
    # For testing: limit to 3 pages per language
    result = run_scraper(save_as_json=True, hide_scraping_browser=True, 
                        max_pages=3, show_progress=True) # args when script runs on its own
    
    if result["status"] == "error":
        logging.error(f"Scraper failed: {result['message']}")
        print("ERROR:", result["message"])
    elif result["status"] == "warning":
        logging.warning(result["message"])
        print("WARNING:", result["message"])
    else:
        logging.info(result["message"])
        print("SUCCESS:", result["message"])

# Example call: run_scraper(save_as_json=True, hide_scraping_browser=True, max_pages=50, show_progress=True)
