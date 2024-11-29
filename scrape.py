#%%
# Scraper for Swiss Army Service Information

"""
TODO:

1) scrape date & date format:
- add scrape date to df OR when importing in SQL
- change date format to YYYY-MM-DD

2) language column:
language = re.search(r"https:\/\/www\.armee\.ch\/(\w{2})/", url)[1].upper()

3) DB:
- Add data to MySQL DB (OR to SQLite <- might be better for GitHub?)
- Also generate a JSON file?

"""

#%%
import pandas as pd
import re
import time
import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

#%%
# Function to initialize WebDriver
def initialize_driver():
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # <- <- <- <- <- <- <- <- <- <- <- Uncomment in production <- <- <- <- <- <- <- <- <- <- <-
    driver = webdriver.Chrome(options=chrome_options)
    return driver

# Function to scrape data from the current page
def scrape_data(driver):
    # Extract all table rows on the current page
    table_rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")

    # Initialize lists to store the extracted data
    troop_school = []
    start_date = []
    end_date = []

    # Collect data from each row
    for row in table_rows:
        columns = row.find_elements(By.TAG_NAME, "td")
        
        if len(columns) >= 3:  # Make sure the row has enough columns
            troop_school.append(columns[0].text.strip())  # First column: Troop/School
            start_date.append(columns[1].text.strip())  # Second column: Start date
            end_date.append(columns[2].text.strip())  # Third column: End date

    # Return the data as a list of dictionaries
    return [{"troopSchool": troop, "startDate": start, "endDate": end}
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
                sleep_time = 3
                print(f"Page loaded successfully. Sleeping for {sleep_time}")
                time.sleep(sleep_time)  # Wait before next loop

            else:
                print("Next button is disabled or not clickable.")
        else:
            print("Second button not found.")
    except Exception as e:
        print("Error clicking next button:", e)

# Function to scrape all data across pages
def scrape_all_data(url):
    driver = initialize_driver()
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

    all_data = []  # Initialize list to store scraped data
    
    while True:
        try:
            # Scrape data from the current page
            page_data = scrape_data(driver)
            all_data.extend(page_data)  # Append the scraped data to the list

            # Wait for the page to load and for the page span to be visible
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span"))
            )
            
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
            
            print(f"Current Page: {current_page} / Total Pages: {total_pages}")
            
            # If we're not on the last page, click the "Next" button
            if current_page < total_pages:
                click_next_button(driver)  # Click the next page button
                time.sleep(2)  # Wait for the next page to load
            else:
                print("Reached the last page.")
                break
        
        except Exception as e:
            print("Error navigating or scraping:", e)
            break

    driver.quit()  # Close the browser
    return all_data

#%%
url = "https://www.armee.ch/de/aufgebotsdaten"
scraped_data = scrape_all_data(url)

# Convert the collected data to a DataFrame
df = pd.DataFrame(scraped_data)

# Output the DataFrame
print(df)

# %%
