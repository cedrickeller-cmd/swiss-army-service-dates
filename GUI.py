#%%
# GUI for Swiss Army Service Information

# TODO: 1) Insanely slow at the moment but not sure if it's just my machine 2) cleanup

#%%
from scrape import run_scraper

import tkinter as tk
from tkinter import ttk
from tkcalendar import Calendar
from tkinter import messagebox

import sqlite3
import pandas as pd
import datetime

import threading

#%%
# Database connection function
def get_filtered_data(filters):
    conn = sqlite3.connect("service_dates.db")

    query = """SELECT 
        language,
        troopSchool, 
        strftime('%d.%m.%Y', startDate) as startDate, 
        strftime('%d.%m.%Y', endDate) as endDate 
        FROM activeServiceDates
        WHERE 1=1
        """
    params = []

    # Apply filters dynamically
    for column, value in filters.items():
        if column == "language" and value != "All":
            query += " AND language = ?"
            params.append(value)
        elif column == "troopSchool" and value:
            query += " AND troopSchool LIKE ?"
            params.append(f"%{value}%")
        elif column == "startDate" and value:
            query += " AND startDate >= ?"
            params.append(value)
        elif column == "endDate" and value:
            query += " AND endDate <= ?"
            params.append(value)

    try:
        # Execute the query and load data into a DataFrame
        cursor = conn.execute(query, params)
        # Fetch all the rows
        rows = cursor.fetchall()

        # Get column names from the cursor description
        columns = [desc[0] for desc in cursor.description]

        # Convert the rows to a pandas DataFrame
        df = pd.DataFrame(rows, columns=columns)


        if df.empty:
            print("Query returned no results.")
        else:
            print(f"Returned DataFrame:\n{df.head()}")

    except Exception as e:
        print(f"Error executing query: {e}")
        df = pd.DataFrame()  # Return empty DataFrame on failure

    finally:
        conn.close()

    return df

#%%
# Function to populate Treeview
def populate_treeview(tree, df):
    # Clear tree
    tree.delete(*tree.get_children())  # get_children() gets all rows, * makes each an arg to delete
    
    if not df.empty:  # Check if DataFrame is not empty
        # Insert new rows
        for _, row in df.iterrows():
            tree.insert("", "end", values=row.tolist())  # added to the end, series to list
    else:
        # Message if no data returned
        tree.insert("", "end", values=("No data found",))

# Function to update the table with filters
def update_table():
    filters = {
        "language": language_var.get(),
        "troopSchool": troop_school_var.get(),
        "startDate": start_date_var.get(),
        "endDate": end_date_var.get(),
    }

# Run database fetching in a separate thread
    threading.Thread(target=fetch_and_update, args=(filters,)).start()

def fetch_and_update(filters):
    filtered_data = get_filtered_data(filters)
    root.after(0, lambda: populate_treeview(tree, filtered_data))


# Open a date picker calendar in dropdown style
def pick_date(entry_widget, variable):
    def set_date():
        selected_date = cal.get_date()
        
        # Convert the selected date to datetime object
        date_obj = datetime.datetime.strptime(selected_date, "%m/%d/%y")  # Input format from tkcalendar

        query_format_date = date_obj.strftime("%Y-%m-%d")  # Format for query: YYYY-MM-DD
        display_format_date = date_obj.strftime("%d.%m.%Y")  # Format for display: DD.MM.YYYY

        
        # Update the variable with query format (for filtering purposes)
        variable.set(query_format_date)

        # Update the entry widget with display format directly (to prevent auto-sync with StringVar)
        entry_widget.delete(0, tk.END)
        entry_widget.insert(0, display_format_date)

        # Close the calendar dropdown
        date_window.destroy()

    # Create a new top-level window for the calendar
    date_window = tk.Toplevel(root)
    date_window.overrideredirect(True)  # Remove window decorations to make it look like a dropdown
    date_window.transient(root)  # Link it to the root window so it doesn't show in taskbar

    # Get the coordinates of the entry widget to position the calendar dropdown
    x = entry_widget.winfo_rootx()
    y = entry_widget.winfo_rooty() + entry_widget.winfo_height()

    # Set the position of the new window directly below the entry widget
    date_window.geometry(f"300x250+{x}+{y}")  # Set size and position

    # Configure a custom style for the calendar
    style = ttk.Style(date_window)
    style.theme_use('default')

    # Customizing calendar colors
    style.configure('CalStyle', 
                    background='white', 
                    foreground='black', 
                    selectforeground='white', 
                    selectbackground='darkgray',
                    weekendbackground='lightgray',
                    weekendforeground='black',
                    headersbackground='darkgray',
                    headersforeground='white'
                    )

    # Add the calendar to the window
    cal = Calendar(date_window, selectmode="day", style='CalStyle')
    cal.pack(pady=10)

    # Add a button to confirm the date selection
    tk.Button(date_window, text="Select Date", command=set_date).pack(pady=5)

    # Function to close the dropdown when clicking anywhere else
    def close_dropdown(event):
        if event.widget not in (entry_widget, date_window):
            date_window.destroy()

    # Bind a click event to the root window to close the dropdown when clicking outside
    root.bind("<Button-1>", close_dropdown)

    # Bring the new window to the front and focus
    date_window.lift()
    date_window.focus_force()

# Function to get the last updated date from the database
def get_last_updated_date():
    try:
        conn = sqlite3.connect("service_dates.db")
        cursor = conn.cursor()
        cursor.execute("SELECT strftime('%d.%m.%Y', MAX(scrapeDate)) FROM activeServiceDates")
        last_date = cursor.fetchone()[0]
        conn.close()

        if last_date:
            return last_date
        else:
            return "No data available"
    except Exception as e:
        return f"Error: {e}"

# Function to update the last updated date label
def update_last_updated_label():
    last_updated_date = get_last_updated_date()
    last_updated_label.config(text=f"Last Updated: {last_updated_date}")

# Function to run the scraper and update the UI
def run_scraper_and_update():
    try:
        result = run_scraper(save_as_json=True, hide_scraping_browser=False)
        status_message = ""

        if result["status"] == "error":
            status_message = f"ERROR: {result['message']}"
            print(status_message)
        elif result["status"] == "warning":
            status_message = f"WARNING: {result['message']}"
            print(status_message)
        else:
            status_message = f"SUCCESS: {result['message']}"
            print(status_message)

        # Update the last updated label after running the scraper
        update_last_updated_label()

        # Reload the data in the Treeview to reflect the new updates
        updated_data = get_filtered_data({})  # Get all data without filters
        populate_treeview(tree, updated_data)

        # Display a popup with the status message
        messagebox.showinfo("Scraper Status", status_message)

    except Exception as e:
        error_message = f"Scraper failed with an exception: {e}"
        print(error_message)
        messagebox.showerror("ERROR:", error_message)

# Initialize the GUI
root = tk.Tk()
root.title("Service Dates Filter")

# Frame for filters
frame_filters = tk.Frame(root)
frame_filters.pack(pady=10)

# Dynamic filters creation
language_var = tk.StringVar(value="All")
troop_school_var = tk.StringVar()
start_date_var = tk.StringVar()
end_date_var = tk.StringVar()

conn = sqlite3.connect("service_dates.db")
languages = ["All"] + [row[0] for row in conn.execute("SELECT DISTINCT language FROM activeServiceDates")]
conn.close()

# Set a consistent width for all input fields
input_width = 25

# Language filter
tk.Label(frame_filters, text="Language", width=15, anchor="e").grid(row=0, column=0, padx=5, pady=5, sticky="e")
language_menu = ttk.Combobox(frame_filters, textvariable=language_var, values=languages, state="readonly", width=input_width)
language_menu.grid(row=0, column=1, padx=5, pady=5, sticky="w")

# Troop/School filter
tk.Label(frame_filters, text="Troop/School", width=15, anchor="e").grid(row=1, column=0, padx=5, pady=5, sticky="e")
troop_school_entry = ttk.Entry(frame_filters, textvariable=troop_school_var, width=input_width)
troop_school_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

# Start Date filter (Entry that opens date picker)
tk.Label(frame_filters, text="Start Date", width=15, anchor="e").grid(row=2, column=0, padx=5, pady=5, sticky="e")
start_date_entry = ttk.Entry(frame_filters, width=input_width)  # No direct link to start_date_var for display purposes
start_date_entry.grid(row=2, column=1, padx=5, pady=5, sticky="w")
start_date_entry.bind("<Button-1>", lambda event: pick_date(start_date_entry, start_date_var))  # Bind click event to open calendar

# End Date filter (Entry that opens date picker)
tk.Label(frame_filters, text="End Date", width=15, anchor="e").grid(row=3, column=0, padx=5, pady=5, sticky="e")
end_date_entry = ttk.Entry(frame_filters, width=input_width)  # No direct link to end_date_var for display purposes
end_date_entry.grid(row=3, column=1, padx=5, pady=5, sticky="w")
end_date_entry.bind("<Button-1>", lambda event: pick_date(end_date_entry, end_date_var))  # Bind click event to open calendar

# Button to apply filters
filter_button = ttk.Button(frame_filters, text="Apply Filters", command=update_table)
filter_button.grid(row=4, column=0, columnspan=2, pady=10)

# Frame for the table
frame_table = tk.Frame(root)
frame_table.pack(fill="both", expand=True)

# Treeview for displaying the data
columns = ["language", "troopSchool", "startDate", "endDate"]
tree = ttk.Treeview(frame_table, columns=columns, show="headings", height=15)

# Define column headers
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=120, anchor="center")

tree.pack(fill="both", expand=True)

# Frame for last updated info and update button
frame_info = tk.Frame(root)
frame_info.pack(pady=10, fill="x")

# Label to display last updated date
last_updated_label = tk.Label(frame_info, text="Last Updated: ", anchor="w")
last_updated_label.pack(side="left", padx=10)

# Button to update the data by running the scraper
update_button = ttk.Button(frame_info, text="Update Now", command=run_scraper_and_update)
update_button.pack(side="right", padx=10)

# Display initial last updated date
update_last_updated_label()

# Display initial data (no filters applied)
initial_data = get_filtered_data({})
populate_treeview(tree, initial_data)

# Start the application
root.mainloop()

# %%
