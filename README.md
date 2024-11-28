# Swiss Army Service Dates

Swiss Army Service Dates Scraper, Database, and GUI with Filters.

## Background and Problem

The Swiss military drafts its militia for yearly training and known events. Many students have to
reschedule theirs due to scheduling conflicts with their studies and exams.
Since the military rebuilt its website a little while ago, the lookup for the scheduled events for
the militia is not implemented properly. The problem seems to be an exact match instead of a
greater or less than of the date filters.

## Basic Idea

I want to provide a platform to…
- filter the data properly
- add further filter functionality for the troop type (if time allows)
- Reason: If one can’t do their service requirement with their battalion, it’s helpful
to find options outside of their direct alternatives

## Implementation Plan

This project will develop in phases as skills improve.
Phases 1-3 are required to be completed for the project's minimum requirements.

### Basic Setup

Version Control: Git, Remote Repo: GitHub

### Phase 1: Scraper and Cleaning

The data needs to be scraped from [armee.ch](https://www.armee.ch/de/aufgebotsdaten) (input) using Python with BeautifulSoup and probably
Selenium to navigate the table pages.
The data will be checked and cleaned using Pandas.

### Phase 2: Database and Queries

A local MySQL (or SQLite) DB will initially store the scraped data.
The data should have the following columns:
id, scrapeDate, language, troopType, troopSchool, startDate, endDate

### Phase 3: Local UI

UI to filter data and return queries as a table (output).

### Phase 4: Scheduled Updates and Backups

(might need to develop this further)
Option 1: Export and compress the existing data before scheduled scraping, then truncate and
insert the new data in the table.
Option 2: Create a backup table with the data before scheduled and move the existing data
before truncating and inserting the new data in the live table.

### Phase 5: Moving to the Web

- Option 1: GitHub hosted
Export the data as a JSON file, host it on GitHub, and build a site using GitHub Pages or
Vercel (would be completely free) to filter the data and display it as a table (output).
- Option 2: Self-hosted
- 5.1: Remote DB
I have a web server and can likely use it for a MariaDB at no additional cost.
- 5.2: Back-end Web Framework
Flask (might be a bit easier) / Django (more interesting for future projects).
- 5.3: Front-end
Static HTML --> HTML and JavaScript for dynamic results.

### Phase 6: Add Multi-Language Support

The data should be available in [German](https://www.armee.ch/de/aufgebotsdaten), [French](https://www.armee.ch/fr/dates-de-convocation), and [Italian](https://www.armee.ch/it/date-di-chiamata-in-servizio) (additional input).

### Phase 7: Assign troopType

Allows an additional filtering option. This must be assigned manually if common patterns aren’t
found (likely use regex for it). Those not assigned to a troopType can tentatively be assigned to "Other".