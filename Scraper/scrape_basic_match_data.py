"""
Webscraper for match-level results from the Official NRL website.

This script modified from Beau Hobba's script found here: https://github.com/beauhobba/NRL-Data/.
"""

import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import json
import re
import argparse
import os
import logging
from typing import List, Dict, Any
from dataclasses import dataclass
import pandas as pd

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class MatchData:
    """Structure for match data."""
    details: str
    date: str
    home_team: str
    home_score: str
    away_team: str
    away_score: str
    venue: str

class NRLScraper:
    """Class to handle NRL data scraping operations."""
    
    HTML_ELEMENTS = ["h3", "p", "p", "div", "p", "div", "p"]
    CLASS_NAMES = [
        "u-visually-hidden",
        "match-header__title",
        "match-team__name--home",
        "match-team__score--home",
        "match-team__name--away",
        "match-team__score--away",
        "match-venue o-text"
    ]

    #def __init__(self): 
    #    chromedriver_autoinstaller.install() # Hashed to prevent message

    @staticmethod
    def set_up_driver() -> webdriver.Chrome:
        """Set up the Chrome Web Driver for Scraping."""
        options = Options()
        options.add_argument('--ignore-certificate-errors')
        options.add_argument('--headless')
        options.add_argument('log-level=3')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        return webdriver.Chrome(options=options)

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean venue text by removing unwanted characters and information."""
        text = re.sub(r'[^\x00-\x7F]+', '', text)
        text = text.replace('\n', ' ').strip()
        text = re.sub(r'     .*', '', text)
        text = re.sub(r'Home of the.*', '', text)
        return text

    def get_round_data(self, round_num: int, year: int) -> Dict[str, List[Dict[str, str]]]:
        """Fetch and parse match data for a specific round and year."""
        url = f"https://www.nrl.com/draw/?competition=111&round={round_num}&season={year}"
        
        driver = self.set_up_driver()
        try:
            driver.get(url)
            page_source = driver.page_source
        finally:
            driver.quit()

        soup = BeautifulSoup(page_source, "html.parser")
        match_elements = soup.find_all("div", class_="match o-rounded-box o-shadowed-box")

        matches_data = []
        for match_element in match_elements:
            match_info = [
                match_element.find(html_val, class_=class_val).text.strip()
                for html_val, class_val in zip(self.HTML_ELEMENTS, self.CLASS_NAMES)
            ]

            match = MatchData(
                details=match_info[0].replace("Match: ", ""),
                date=match_info[1],
                home_team=match_info[2],
                home_score=match_info[3].replace("Scored", "").replace("points", "").strip(),
                away_team=match_info[4],
                away_score=match_info[5].replace("Scored", "").replace("points", "").strip(),
                venue=match_info[6].replace("Venue:", "").strip()
            )

            matches_data.append(match.__dict__)

        return {str(round_num): matches_data}

    def scrape_season_data(self, years: List[int], rounds: range) -> Dict[str, List[Dict]]:
        """Scrape match data for specified seasons and rounds."""
        match_data = []

        for year in years:
            logging.info(f'Scraping data from the {year} season')
            year_data = []

            for round_num in rounds:
                try:
                    logging.info(f'Round {round_num}')
                    round_data = self.get_round_data(round_num, year)
                    year_data.append(round_data)
                except Exception as e:
                    logging.error(f"Error scraping round {round_num}: {e}")

            match_data.append({str(year): year_data})

        return {"NRL": match_data}

    def save_data(self, data: Dict[str, List[Dict]], output_dir: str, years: List[str], args: argparse.Namespace) -> None:
        """Save scraped data in both JSON and TXT formats."""

        # Create file name suffix based on whether specific rounds were requested
        if args.input_round:
            file_suffix = f'_{"_".join(years)}_rd{args.input_round}'
        else:
            file_suffix = f'_{"_".join(years)}'

        # Save JSON - Hashed out as not needed due to the table format below
        #json_data = json.dumps(data, indent=4)
        #json_path = os.path.join(output_dir, f'match_data{file_suffix}.json')
        
        #with open(json_path, "w") as f:
        #    f.write(json_data)
        #logging.info(f"JSON data written to {json_path}")

        # Convert to table format and save TXT
        headers = ["Competition", "Year", "Round", "Details", "Date", "Home", 
                  "Home_Score", "Away", "Away_Score", "Venue"]
        table_data = []
        
        for competition, years_data in data.items():
            for year_data in years_data:
                for year, rounds_data in year_data.items():
                    for round_data in rounds_data:
                        for round_num, matches in round_data.items():
                            for match in matches:
                                # Convert dictionary keys to match headers
                                match_dict = {
                                    'Details': match['details'],
                                    'Date': match['date'], 
                                    'Home': match['home_team'],
                                    'Home_Score': match['home_score'],
                                    'Away': match['away_team'], 
                                    'Away_Score': match['away_score'],
                                    'Venue': self.clean_text(match['venue'])
                                }
                                
                                row = [competition, year, round_num]
                                row.extend([match_dict[header] for header in headers[3:]])
                                table_data.append(row)

        # Save txt
        txt_path = os.path.join(output_dir, f'match_data{file_suffix}.txt')
        df = pd.DataFrame(table_data, columns=headers)
        df.to_csv(txt_path, sep='\t', index=False)
        logging.info(f"Table data written to {txt_path}")
        
        # Output match list
        if args.match_list:
            print("Match list requested")
            df_match_list = df[['Year', 'Round','Home','Away']]
            # For each year, map the 4 highest round numbers to finals names as NRL website doesn't use round numbers for these
            for year in df_match_list['Year'].unique():
                year_data = df_match_list[df_match_list['Year'] == year]
                top_4_rounds = sorted(year_data['Round'].unique(), reverse=True)[:4]
                
                if len(top_4_rounds) >= 4:
                    finals_map = {
                        top_4_rounds[0]: 'grand-final',
                        top_4_rounds[1]: 'finals-week-3', 
                        top_4_rounds[2]: 'finals-week-2',
                        top_4_rounds[3]: 'finals-week-1'
                    }
                    
                    for old_round, new_round in finals_map.items():
                        mask = (df_match_list['Year'] == year) & (df_match_list['Round'] == old_round)
                        df_match_list.loc[mask, 'Round'] = new_round
            match_list_path = os.path.splitext(txt_path)[0] + '_match_list.txt'
            df_match_list.to_csv(match_list_path, sep='\t', index=False)
            logging.info(f"Match list written to {match_list_path}")
        else:
            print("Match list not requested")

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Scrape the Official NRL website for match-level data')
    parser.add_argument('input_year', type=str, nargs='+',
                       help='Input one or more years to fetch data (e.g. 2022,2023,2024)')
    parser.add_argument('--round', dest='input_round', type=int,
                       help='Select single round to fetch data. Default is all rounds in the season')
    parser.add_argument('--o', dest='output_directory', type=str,
                       help='Output directory path', default='.')
    parser.add_argument('--list',dest='match_list', action='store_true',
                        help='Output match list for extracting detailed data (default=False)')

    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    input_years = [int(y) for y in args.input_year]
    def get_max_rounds(y):
        if 2014 <= y <= 2017:
            return 31  # 30 rounds + 1
        elif y in (2018, 2019, 2021, 2022):
            return 30  # 29 rounds + 1
        elif y == 2020:
            return 25  # 24 rounds + 1
        elif y in (2023, 2024):
            return 32  # 31 rounds + 1
        return 32  # Default fallback
        
    max_rounds = max(get_max_rounds(year) for year in input_years)
    round_range = range(args.input_round, args.input_round + 1) if args.input_round else range(1, max_rounds)

    scraper = NRLScraper()
    data = scraper.scrape_season_data(input_years, round_range)
    scraper.save_data(data, args.output_directory, args.input_year, args)

if __name__ == "__main__":
    main()