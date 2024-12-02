#%%
# Scraper for Swiss Army Service Information

# TODO: 1) Better error handling, 2) not creating duplicates if scraped twice in one day.

#%%
import pandas as pd
import re
import time
import datetime
import sqlite3
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#%%
# Function to initialize WebDriver
def initialize_driver():
    chrome_options = Options()
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
    return [{"scrapeDate": datetime.date.today().strftime('%Y-%m-%d'), "language": language, "troopSchool": troop, "startDate": start, "endDate": end}
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
            if 'cursor-not-allowed' not in next_button_class:
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
def scrape_all_data(url, language):
    driver = initialize_driver()
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    all_data = []  # Initialize list to store scraped data
    
    while True:
        try:
            # Wait for the page to load and for the table body to be visible
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody"))
            )
            # Scrape data from the current page
            page_data = scrape_data(driver, language)
            all_data.extend(page_data)  # Append the scraped data to the list
            
            # Get the current page and total pages from the page span text
            page_span = driver.find_element(By.CSS_SELECTOR, "div.my-5.flex.items-center.justify-center span")
            page_text = page_span.text  # "Seite X von Y" / "Page X de Y" / "Pagina X da Y"
            
            # Use regex to extract current and total page numbers
            match = re.search(r"\D+ (\d+) \D+ (\d+)", page_text)
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
                time.sleep(1)  # Wait for the next page to load
            else:
                print("Reached the last page.")
                break
        
        except Exception as e:
            print("Error navigating or scraping:", e)
            break

    driver.quit()  # Close the browser
    return all_data

#%%
# List to store all scraped data
scraped_data = []

# Languages and URLs to scrape
urls = {
    "DE": "https://www.armee.ch/de/aufgebotsdaten",
    "FR": "https://www.armee.ch/fr/dates-de-convocation",
    "IT": "https://www.armee.ch/it/date-di-chiamata-in-servizio"
    }

# Scraping the data
for language in urls:
    try:
        print(f"Language accessing: {language} | Website link: {urls[language]}")
        scraped_data.extend(scrape_all_data(urls[language], language))
    except Exception as e:
        print(f"Error scraping {language} {urls[language]}: {e}")

# Convert the collected data to a DataFrame
scraped_data_df = pd.DataFrame(scraped_data)

# Output the DataFrame head
print("Here are the first 5 rows of the extracted data:")
print(scraped_data_df.head(5))

# Connect to database and append the scraped data
conn = sqlite3.connect("service_dates.db")
print("Connected to the database.")

# Transform df to SQL format and add to (new) table (if not exists)
scraped_data_df.to_sql("serviceDates", conn, if_exists="append", index=False) # or replace if we don't care about historical data
print("Inserted data into DB.")

print("First row of each language in DB:")
for language in urls:
    try:
        res = conn.execute("""
                           SELECT * FROM serviceDates
                           WHERE CAST(scrapeDate AS DATE) = (
                                    SELECT MAX(CAST(scrapeDate AS DATE)) FROM serviceDates
                                )
                                AND language = ?
                            LIMIT 5
                           """,(language,)).fetchone()
        print(res)
    except Exception as e:
        print(f"Error querying {language} data: {e}")

conn.close()
print("Closed DB connection.")
