# Swiss Army Service Dates

Swiss Army Service Dates Scraper, Database, and GUI with Filters.

## Background and Problem

The Swiss military drafts its militia for yearly training and known events.
Many students have to reschedule their service due to scheduling conflicts with their studies and exams.
Since the military rebuilt its website in 2022/2023, the lookup for the scheduled events for the militia is not implemented properly.
The problem appears to be an exact match instead of a greater or less than in the date filters.

## Basic Idea

I want to provide a platform to…
- filter the data properly
- add further filter functionality for the troop type

Reasoning: If one can’t do their service requirement with their battalion, it’s helpful to find options outside of their direct alternatives.

## Implementation Plan

### Basic Setup

- Version Control: Git
- Remote Repo: GitHub
- Hosting: VPS

### Scraper and Cleaning

The data is scraped from [armee.ch](https://www.armee.ch/) using Python with Selenium to navigate the table pages. All languages are considered by scraping the data from multiple sources: [German](https://www.armee.ch/de/aufgebotsdaten), [French](https://www.armee.ch/fr/dates-de-convocation), and [Italian](https://www.armee.ch/it/date-di-chiamata-in-servizio)
The data is checked and cleaned using Pandas.

### Database and Queries

A SQLite database stores the scraped data.
The data contains the following columns:
id, scrapeDate, language, troopSchool, startDate, endDate, active

There is a table for the latest (active) data, and a table for historical data with an active status (1 = included in latest scrape, 0 = not on website anymore). `troopType` may be added in the future if `troopSchool` is grouped meaningfully.

### GUI

GUI to filter data and return queries as a table.

Filters should include language (single choice), troopSchool (%LIKE%), startDate (>=), and endDate (<=). Streamlit components easily filter the cached active table.

### Scheduled Scraping, Updates, and Backups

Cron jobs are used for scheduled scraping once a day.

Updates are pushed to Github and the VPS using Github Actions. Similarily, backups in the form of flat files are created.
