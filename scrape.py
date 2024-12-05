#%%
# Scraper for Swiss Army Service Information

# TODO: 1) Better error handling, 2) logging instead of printing

#%%
import pandas as pd
import re
import datetime
import sqlite3
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#%%
# Function to initialize WebDriver
def initialize_driver(headless=True):
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
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
            print("Row does not have 3 columns.")

    # Return the data as a list of dictionaries
    return [{"language": language, "troopSchool": troop, "startDate": start, "endDate": end}
            for troop, start, end in zip(troop_school, start_date, end_date)]

# Function to click the second button (next page button)
def click_next_button(driver):
    try:
        # Find all buttons in the parent div
        buttons = driver.find_elements(By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center button")
        
        # Check if the second button exists and is clickable
        if len(buttons) >= 2:
            next_button = buttons[1]
            next_button_class = next_button.get_attribute('class') or ''
            if 'cursor-not-allowed' not in next_button_class:  # if not disabled
                next_button.click()
                print("Clicked next page button.")
                
                # Wait for the page to load the table element (should be what's changing)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
                )

            else:
                print("Next button is disabled or not clickable.")
        else:
            print("Second button not found.")
    except Exception as e:
        print("Error clicking next button:", e)

# Function to scrape all data across pages
def scrape_all_data(url, language, headless=True):
    driver = initialize_driver(headless=headless)
    driver.get(url)

    all_data = []  # Initialize list to store scraped data

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        while True:
            try:
                # Wait for the page to load and for the table body to be visible
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
                )
                # Scrape data from the current page
                page_data = scrape_data(driver, language)
                all_data.extend(page_data)  # Append the scraped data to the list
                
                # Get the current page and total pages from the page span text
                page_span = driver.find_element(By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center span")
                page_text = page_span.text  # "Seite X von Y" / "Page X de Y" / "Pagina X da Y"
                
                # Use regex to extract current and total page numbers
                match = re.search(r"\D+\s(\d+)\s\D+\s(\d+)", page_text)
                if match:
                    current_page = int(match.group(1))
                    total_pages = int(match.group(2))
                else:
                    print("Could not extract page numbers.")
                    break
                
                print(f"Current page: {current_page} / {total_pages}")
                
                # If we're not on the last page, click the "Next" button
                if current_page < total_pages:
                    click_next_button(driver)  # Click the next page button
                else:
                    print("Reached the last page.")
                    break
            
            except Exception as e:
                print("Error navigating or scraping:", e)
                break
    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()

    return all_data

# Function to insert into and update database
def update_database(data):
    # Connect to database
    conn = sqlite3.connect("service_dates.db")

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
    df["scrapeDate"] = datetime.date.today().strftime('%Y-%m-%d')  # Set scrapeDate as today
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
    print("Database updated successfully.")

# Function to save data to a JSON file
def save_data_to_json(data, filename="latest_service_dates.json"):
    try:
        with open(filename, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, indent=4, ensure_ascii=False)  # ensure_ascii=False to keep it human-readable
        print(f"Data successfully saved to {filename}.")
    except Exception as e:
        print(f"Error saving data to JSON: {e}")

# Function to start scraping, updating the database, and optionally save data as JSON file
def run_scraper(save_as_json=False, json_filename="latest_service_dates.json", hide_scraping_browser=True):
    # Languages and URLs to scrape
    urls = {
        "DE": "https://www.armee.ch/de/aufgebotsdaten",
        "FR": "https://www.armee.ch/fr/dates-de-convocation",
        "IT": "https://www.armee.ch/it/date-di-chiamata-in-servizio"
    }

    all_scraped_data = [] # List to store all scraped data

    try:
        # Scraping the data
        for language, url in urls.items():
            try:
                print(f"Scraping data for {language}...")
                all_scraped_data.extend(scrape_all_data(url, language, headless=hide_scraping_browser))
            except Exception as e:
                print(f"Error scraping {language} ({url}):\n{e}")

        # Updating the database
        if all_scraped_data: # if not empty
            # Update the database
            update_database(all_scraped_data)

            # Save data to JSON if requested (if True)
            if save_as_json:
                save_data_to_json(all_scraped_data, filename=json_filename)
        else:
            print("No data scraped. Skipped database and JSON update.")
    
    except Exception as e:
        print(f"An error occurred while running the scraper: {e}")

#%%
# Make script importable and callable
if __name__ == "__main__":
    run_scraper(save_as_json=True, hide_scraping_browser=False)  # args when script runs on its own
