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

    def __init__(self):
        chromedriver_autoinstaller.install()

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

    def save_data(self, data: Dict[str, List[Dict]], output_dir: str, years: List[str]) -> None:
        """Save scraped data in both JSON and TXT formats."""
        # Save JSON
        json_data = json.dumps(data, indent=4)
        json_path = os.path.join(output_dir, f'match_data_{"_".join(years)}.json')
        
        with open(json_path, "w") as f:
            f.write(json_data)
        logging.info(f"JSON data written to {json_path}")

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
                                match['Venue'] = self.clean_text(match['Venue'])
                                row = [competition, year, round_num]
                                row.extend([match[header] for header in headers[3:]])
                                table_data.append(row)

        txt_path = os.path.join(output_dir, f'match_data_{"_".join(years)}.txt')
        with open(txt_path, "w") as f:
            f.write("\t".join(headers) + "\n")
            for row in table_data:
                f.write("\t".join(str(item) for item in row) + "\n")
        logging.info(f"Table data written to {txt_path}")

def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Scrape the Official NRL website for match-level data')
    parser.add_argument('input_year', type=str, nargs='+',
                       help='Input one or more years to fetch data (e.g. 2022,2023,2024)')
    parser.add_argument('--round', dest='input_round', type=int,
                       help='Select single round to fetch data. Default is all rounds in the season')
    parser.add_argument('--o', dest='output_directory', type=str,
                       help='Output directory path', default='.')
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    input_years = [int(y) for y in args.input_year]
    round_range = range(args.input_round, args.input_round + 1) if args.input_round else range(1, 32)

    scraper = NRLScraper()
    data = scraper.scrape_season_data(input_years, round_range)
    scraper.save_data(data, args.output_directory, args.input_year)

if __name__ == "__main__":
    main()