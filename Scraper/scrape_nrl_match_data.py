"""
This python script scrapes the Official NRL website for match-level results.

This script modified from Beau Hobba's script found here: https://github.com/beauhobba/NRL-Data/.

Future work may be needed to make this more efficient as it takes ~8 minutes to run each year.
"""

import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import sys
from bs4 import BeautifulSoup
import json
import re
import argparse
import os

chromedriver_autoinstaller.install()

def set_up_driver():
    """
    Set up the Chrome Web Driver for Scraping. This function sets up the Chrome Web Driver with specified options.
    """
    options = Options()
    # Ignore messages from the NRL website 
    options.add_argument('--ignore-certificate-errors')
    
    # Run Selenium in headless mode
    options.add_argument('--headless')
    options.add_argument('log-level=3')
    
    # Exclude logging to assist with errors caused by NRL website 
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = webdriver.Chrome(options=options)
    return driver

"""
Webscraper for finding NRL data related to team statistics
"""

sys.path.append('..')
sys.path.append('..')

def get_nrl_data(round, year):
    url = f"https://www.nrl.com/draw/?competition=111&round={round}&season={year}"
    # Scrape the NRL website
    driver = set_up_driver() 
    driver.get(url)
    page_source = driver.page_source

    driver.quit()

    # Use BeautifulSoup to parse the HTML
    soup = BeautifulSoup(page_source, "html.parser")
    # Get the NRL data box
    match_elements = soup.find_all(
        "div", class_="match o-rounded-box o-shadowed-box")

    # Name of html elements that contains match data
    find_data = ["h3", "p", "p", "div", "p", "div", "p"]
    class_data = ["u-visually-hidden", "match-header__title", "match-team__name--home",
                  "match-team__score--home", "match-team__name--away", "match-team__score--away", "match-venue o-text"]

    # Extract the match data
    matches_json = []
    for match_element in match_elements:
        match_details, match_date, home_team, home_score, away_team, away_score, venue = [match_element.find(
            html_val, class_=class_val).text.strip() for html_val, class_val in zip(find_data, class_data)]

        match = {
            "Details": match_details.replace("Match: ", ""),
            "Date": match_date,
            "Home": home_team,
            "Home_Score": home_score.replace("Scored", "").replace("points", "").strip(),
            "Away": away_team,
            "Away_Score": away_score.replace("Scored", "").replace("points", "").strip(),
            "Venue": venue.replace("Venue:", "").strip()
        }
        matches_json.append(match)
    round_data = {
        f"{round}": matches_json
    }
    return round_data

def scrape_nrl_data(input_years, round_range):
    if __name__ == "__main__":
        match_json_datas = []  # List to store JSON data for matches
        for year in input_years:
            print('Scraping data from the ' + str(year) + ' season')
            year_json_data = []  # List to store JSON data for a particular year
            for round_nu in round_range:  
                try:
                    print('Scraping Rd ' + str(round_nu))
                    # Attempt to fetch NRL data for a specific round and year
                    match_json = get_nrl_data(round_nu, year)
                    # Append fetched JSON to year's data list
                    year_json_data.append(match_json)
                except Exception as ex:
                    print(f"Error: {ex}")
            # Store year's data in a dictionary
            year_data = {
                f"{year}": year_json_data
            }
            # Append year's data to the main list
            match_json_datas.append(year_data)

        # Create overall data dictionary
        overall_data = {
            "NRL": match_json_datas
        }
        # Convert overall data to JSON format with indentation for better readability
        overall_data_json = json.dumps(overall_data, indent=4)

        # Determine output file path    
        if args.input_round is not None:
            output_file = args.output_directory + 'match_data_' + '_'.join(args.input_year) + f'_rd{args.input_round}.json'
        else:
            output_file = args.output_directory + 'match_data_' + '_'.join(args.input_year) + '.json'

        # Write JSON data to a file
        with open(output_file, "w") as file:
            file.write(overall_data_json)

        print(f"Table has been written to {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Scrape the Official NRL website for match-level data')
    parser.add_argument('input_year', type=str, nargs='+', help='Input one or more years to fetch data (e.g. 2022,2023,2024)')
    parser.add_argument('--round', dest='input_round', type=int, help='Select single round to fetch data. Default is all rounds in the season')
    parser.add_argument('--o', dest='output_directory', type=str, help='Output directory path', default='.')
    
    args = parser.parse_args()

    # Convert input year(s) into list
    input_years = [int(y) for y in args.input_year]

    # Convert input round(s) into range
    if args.input_round is None:
        round_range = range(1, 32)
    else:
        round_range = range(args.input_round, args.input_round + 1)

    scrape_nrl_data(input_years, round_range)