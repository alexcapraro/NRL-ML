"""
Webscraper for detailed NRL match data. This includes team statistics, match details, and try scorers.
This script modified from Beau Hobba's script found here: https://github.com/beauhobba/NRL-Data/.
"""

import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
from bs4 import BeautifulSoup
import pandas as pd
import argparse
import os
from typing import List, Dict, Any
from dataclasses import dataclass
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@dataclass
class MatchInput:
    year: int
    round: int
    home_team: str
    away_team: str

def setup_argparse() -> argparse.Namespace:
    """Set up command line argument parsing."""
    parser = argparse.ArgumentParser(description='Scrape detailed match data from the Official NRL website including team statistics, match details, and try scorers.')
    parser.add_argument('input_file', type=str, 
                       help='Path to input file containing Year, Round, Home, Away Team columns')
    parser.add_argument('--output', '-o', dest='output_directory', type=str,
                       help='Specify the output directory path. Default is the current directory.',
                       default='.')
    return parser.parse_args()

def read_input_file(file_path: str) -> List[MatchInput]:
    """Read and validate the input file."""
    try:
        df = pd.read_csv(file_path, sep='\t')
        required_columns = ['Year', 'Round', 'Home', 'Away']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Input file must contain columns: {required_columns}")
        
        matches = []
        for _, row in df.iterrows():
            matches.append(MatchInput(
                year=int(row['Year']),
                round=int(row['Round']),
                home_team=row['Home'],
                away_team=row['Away']
            ))
        return matches
    except Exception as e:
        logging.error(f"Error reading input file: {e}")
        raise

def set_up_driver() -> webdriver.Chrome:
    """Set up the Chrome Web Driver for Scraping."""
    options = Options()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--headless')
    options.add_argument('log-level=3')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    return webdriver.Chrome(options=options)

# Constants for data structure
BARS_DATA: dict = {'time_in_possession': -1,
                   'all_runs': -1,
                   'all_run_metres': -1,
                   'post_contact_metres': -1,
                   'line_breaks': -1,
                   'tackle_breaks': -1,
                   'average_set_distance': -1,
                   'kick_return_metres': -1,
                   'offloads': -1,
                   'receipts': -1,
                   'total_passes': -1,
                   'dummy_passes': -1,
                   'kicks': -1,
                   'kicking_metres': -1,
                   'forced_drop_outs': -1,
                   'bombs': -1,
                   'grubbers': -1,
                   'tackles_made': -1,
                   'missed_tackles': -1,
                   'intercepts': -1,
                   'ineffective_tackles': -1,
                   'errors': -1,
                   'penalties_conceded': -1,
                   'ruck_infringements': -1,
                   'inside_10_metres': -1,
                   'interchanges_used': -1}

DONUT_DATA = {
        'Completion Rate': -1,
        'Average_Play_Ball_Speed': -1,
        'Kick_Defusal': -1,
        'Effective_Tackle': -1}

DONUT_DATA_2 = {'tries': -1,
                'conversions': -1,
                'penalty_goals':-1,
                'sin_bins': -1,
                '1_point_field_goals': -1,
                '2_point_field_goals': -1,
                'half_time': -1
                }

DONUT_DATA_2_WORDS = ['TRIES',
                      'CONVERSIONS',
                      'PENALTY GOALS', 
                      'SIN BINS',
                      '1 POINT FIELD GOALS',
                      '2 POINT FIELD GOALS',
                      'HALF TIME'
                      ]

def get_detailed_nrl_data(matches: List[MatchInput], output_dir: str) -> None:
    """
    Main function to scrape detailed NRL match data.
    
    Args:
        matches: List of MatchInput objects containing match details
        output_dir: Directory to save output files
    """

    # Initialise competition level data
    competition_stats_data = []
    competition_match_data = []
    competition_try_data = []

    # Group matches by year for more efficient processing
    matches_by_year = {}
    for match in matches:
        if match.year not in matches_by_year:
            matches_by_year[match.year] = []
        matches_by_year[match.year].append(match)

    for year, year_matches in matches_by_year.items():
        logging.info(f'Scraping data from the {year} season')
        
        year_stats_data = []
        year_match_data = []
        year_try_data = []

        # Group matches by round
        matches_by_round = {}
        for match in year_matches:
            if match.round not in matches_by_round:
                matches_by_round[match.round] = []
            matches_by_round[match.round].append(match)

        for round_num, round_matches in matches_by_round.items():
            round_stats_data = []
            round_match_data = []
            round_try_data = []

            for match in round_matches:
                home = match.home_team.replace(" ", "-")
                away = match.away_team.replace(" ", "-")
                url = f"https://www.nrl.com/draw/nrl-premiership/{year}/round-{round_num}/{home}-v-{away}/"
                logging.info(f"Scraping Round {round_num}: {match.home_team} v {match.away_team}")

                # Setup the driver and get page content
                driver = set_up_driver()
                driver.get(url)
                page_source = driver.page_source
                driver.quit()
                soup = BeautifulSoup(page_source, "html.parser")

                home_possession, away_possession = None, None
                try:
                    # Home possession
                    home_possession = soup.find(
                        'p', class_='match-centre-card-donut__value--home').text.strip()
                    away_possession = soup.find(
                        'p', class_='match-centre-card-donut__value--away').text.strip()
                except BaseException as BE:
                    print(f"Error in home possession {BE}")

                home_all_run_metres_list = soup.find_all(
                    'dd',
                    class_=[
                        "stats-bar-chart__label stats-bar-chart__label--home u-font-weight-700",
                        "stats-bar-chart__label stats-bar-chart__label--home"])
                away_all_run_metres_list = soup.find_all(
                    'dd',
                    class_=[
                        "stats-bar-chart__label stats-bar-chart__label--away u-font-weight-700",
                        "stats-bar-chart__label stats-bar-chart__label--away"])

                home_bars, away_bars = BARS_DATA.copy(), BARS_DATA.copy()

                try:
                    # Loop through each element
                    for item, bar_name in zip(home_all_run_metres_list, home_bars.keys()):
                        # Get the text of each element and strip any whitespace
                        home_all_run_metres = item.get_text(strip=True)
                        # Do whatever you want with the text
                        home_bars[bar_name] = home_all_run_metres

                    for item, bar_name in zip(away_all_run_metres_list, away_bars.keys()):
                        # Get the text of each element and strip any whitespace
                        home_all_run_metres = item.get_text(strip=True)
                        # Do whatever you want with the text
                        away_bars[bar_name] = home_all_run_metres
                except BaseException:
                    print(f"Error with home bars")

                home_donut = DONUT_DATA.copy()
                away_donut = DONUT_DATA.copy()
                
                try:
                    elements = soup.find_all("p", class_="donut-chart-stat__value")
                    # Loop through each element to extract the numbers
                    numbers = []
                    for element in elements:
                        # Extract the text from the element
                        text = element.get_text()
                        # Find the number in the text
                        number = ''.join(filter(lambda x: x.isdigit() or x == '.', text))
                        numbers.append(number)
                    home_donut.update({k: v for k, v in zip(home_donut, numbers[::2])})
                    away_donut.update({k: v for k, v in zip(away_donut, numbers[1::2])})
                except BaseException:
                    logging.error(f"Error in donuts")

                # Initialise a list to store all names
                home_try_names_list, home_try_minute_list = [], []

                try:
                    li_elements = soup.find(
                        "ul", class_="match-centre-summary-group__list--home").find_all("li")

                    # Loop through each <li> element and extract the name
                    for li in li_elements:
                        # Extract the text and remove leading/trailing whitespace
                        text = li.get_text(strip=True)
                        # Split the text at the space character
                        parts = text.split()
                        # Join the parts except the last one (which is the number) to get the
                        # name
                        name = ' '.join(parts[:-1])
                        # Get the last part as the number
                        number = parts[-1]
                        # Append name and number to their respective lists
                        home_try_names_list.append(name)
                        home_try_minute_list.append(number)
                except BaseException:
                    logging.error(f"Error in home try scorers")
                home_first_try_scorer = home_try_names_list[0] if len(
                    home_try_names_list) > 0 else None
                home_first_minute_scorer = home_try_minute_list[0] if len(
                    home_try_minute_list) > 0 else None

                away_try_names_list = []
                away_try_minute_list = []
                try:
                    li_elements = soup.find(
                        "ul", class_="match-centre-summary-group__list--away").find_all("li")
                    # Initialise a list to store all names

                    # Loop through each <li> element and extract the name
                    for li in li_elements:
                        # Extract the text and remove leading/trailing whitespace
                        text = li.get_text(strip=True)
                        # Split the text at the space character
                        parts = text.split()
                        # Join the parts except the last one (which is the number) to get the
                        # name
                        name = ' '.join(parts[:-1])
                        # Get the last part as the number
                        number = parts[-1]
                        # Append name and number to their respective lists
                        away_try_names_list.append(name)
                        away_try_minute_list.append(number)
                except BaseException:
                    logging.error(f"Error in away try scorers")
                away_first_try_scorer = away_try_names_list[0] if len(
                    away_try_names_list) > 0 else None
                away_first_minute_scorer = away_try_minute_list[0] if len(
                    away_try_minute_list) > 0 else None

                overall_first_try_scorer, overall_first_try_minute, overall_first_scorer_team = None, None, None
                if away_first_try_scorer is None and home_first_try_scorer is None:
                    overall_first_try_scorer = None
                else:
                    if away_first_minute_scorer is None:
                        overall_first_try_scorer = home_first_try_scorer
                        overall_first_try_minute = home_first_minute_scorer
                        overall_first_scorer_team = home
                    elif home_first_minute_scorer is None:
                        overall_first_try_scorer = away_first_try_scorer
                        overall_first_try_minute = away_first_minute_scorer
                        overall_first_scorer_team = away
                    elif away_first_minute_scorer > home_first_minute_scorer:
                        overall_first_try_scorer = away_first_try_scorer
                        overall_first_try_minute = away_first_minute_scorer
                        overall_first_scorer_team = away
                    else:
                        overall_first_try_scorer = home_first_try_scorer
                        overall_first_try_minute = home_first_minute_scorer
                        overall_first_scorer_team = home

                # Find all span elements with the specified class
                span_elements = soup.find_all('span', class_='match-centre-summary-group__name')

                # Check if any span element contains the desired text
                for word in DONUT_DATA_2_WORDS:
                    exists = any(span.text.strip().upper() == word for span in span_elements)
                    if not exists:
                        DONUT_DATA_2[word.lower().replace(' ', '_')] = -10
                
                home_game_stats, away_game_stats = DONUT_DATA_2.copy(), DONUT_DATA_2.copy()
                
                
                numbers = []
                try:
                    span_elements = soup.find_all(
                        "span", class_="match-centre-summary-group__value")
                    # Loop through each <span> element and extract the number
                    for span_element in span_elements:
                        numbers.append(span_element.span.get_text(strip=True))
                        
                    filtered_home_stats = {key: value for key, value in home_game_stats.items() if value != -10}

                    for k, v in zip(filtered_home_stats, numbers[::2]):
                        home_game_stats[k] = v

                    for k, v in zip(filtered_home_stats, numbers[1::2]):
                        away_game_stats[k] = v
                        
                except BaseException as Be:
                    logging.error(f"Error with match top data {Be}")
                    

                main_ref_name, ref_names, ref_positions = None, [], []
                try:
                    a_elements = soup.find_all("a", class_="card-team-mate")
                    for a in a_elements:
                        # Extract the name from <h3> element
                        name = a.find("h3",
                                    class_="card-team-mate__name").get_text(strip=True)
                        ref_names.append(name)

                        # Extract the position from <p> element
                        position = a.find(
                            "p", class_="card-team-mate__position").get_text(strip=True)
                        ref_positions.append(position)
                    main_ref_name = ref_names[0]
                except BaseException:
                    logging.error("error with ref data")

                # Initialise variables to store ground condition and weather condition
                ground_condition, weather_condition = "", ""
                try:
                    # Find all <p> elements with class 'match-weather__text'
                    p_elements = soup.find_all("p", class_="match-weather__text")

                    # Loop through each <p> element and extract the text
                    for p_element in p_elements:
                        # Extract the text from the <span> element within the <p>
                        condition_type = p_element.get_text(
                            strip=True).split(":")[0].strip()
                        condition_value = p_element.span.get_text(strip=True)

                        # Check condition type and assign values accordingly
                        if condition_type == "Ground Conditions":
                            ground_condition = condition_value
                        elif condition_type == "Weather":
                            weather_condition = condition_value
                except BaseException:
                    logging.error("error with conditions")

                # Join all the data togethor into an export
                stats_data_temp ={
                    home+'.v.'+away: {
                        home: {
                                'home/away': 'home',
                                'possession': home_possession,
                                'first_try_scorer': home_first_try_scorer,
                                'first_try_time': home_first_minute_scorer,
                                **home_bars,
                                **home_donut,
                                **home_game_stats
                            },
                        away: {
                                'home/away': 'away',
                                'possession': away_possession,
                                'first_try_scorer': away_first_try_scorer,
                                'first_try_time': away_first_minute_scorer,
                                **away_bars,
                                **away_donut,
                                **away_game_stats
                            }
                        }
                    }
                
                # Append the game data to the round data
                round_stats_data.append(stats_data_temp)

                match_data_temp = {
                    home+'.v.'+away: {
                        'overall_first_try_scorer': overall_first_try_scorer,
                        'overall_first_try_minute': overall_first_try_minute,
                        'overall_first_try_round': overall_first_scorer_team,
                        'ref_names': ref_names,
                        'ref_positions': ref_positions,
                        'main_ref': main_ref_name,
                        'ground_condition': ground_condition,
                        'weather_condition': weather_condition
                    }
                }

                # Append the game data to the round data
                round_match_data.append(match_data_temp)

                try_data_temp ={
                    home+'.v.'+away: {
                        home: {
                                'home/away': 'home',
                                'try_names': home_try_names_list, 
                                'try_minutes': home_try_minute_list, 
                            },
                        away: {
                                'home/away': 'away',
                                'try_names': away_try_names_list,
                                'try_minutes': away_try_minute_list,
                            }
                        }
                }
                                
                # Append the game data to the round data
                round_try_data.append(try_data_temp)
                logging.info(f"Match scraping complete")

            # Add round level hierarchy to json
            match_stats_data_combined = {
                f"{round_num}": round_stats_data
            }

            match_detailed_data_combined = {
                f"{round_num}": round_match_data
            }

            match_try_data_combined = {
                f"{round_num}": round_try_data
            }

        # Append round data to year data
        year_stats_data.append(match_stats_data_combined)
        year_match_data.append(match_detailed_data_combined)
        year_try_data.append(match_try_data_combined)

        # Add year level hierarchy to json
        year_stats_data_combined = {
                    f"{year}": year_stats_data
                }
        
        year_match_data_combined = {
                    f"{year}": year_match_data
                }
        
        year_try_data_combined = {
                    f"{year}": year_try_data
                }

    competition_stats_data.append(year_stats_data_combined)
    competition_match_data.append(year_match_data_combined)
    competition_try_data.append(year_try_data_combined)

    master_stats_data = {
        "NRL": competition_stats_data
    }

    master_match_data = {
        "NRL": competition_match_data
    }

    master_try_data = {
        "NRL": competition_try_data
    }

    # Write JSON data to a file
    #with open(f"{output_dir}{year}{round}_match_statistics.json", "w") as file:
    #    file.write(json.dumps(master_stats_data, indent=4))

    #with open(f"{output_dir}{year}{round}_match_detailed.json", "w") as file:
    #    file.write(json.dumps(master_match_data, indent=4))

    #with open(f"{output_dir}{year}{round}_match_try.json", "w") as file:
    #    file.write(json.dumps(master_try_data, indent=4))

    #logging.info(f"Tables has been written as {output_dir}")

    # Convert JSON to table format and export to txt file

    # Initialise lists to store data and headers
    stats_data_df = []
    stats_data_headers = ["Competition", "Year", "Round", "Game", "Home/Away", "Possession","First Try Scorer",
                         "First Try Time", "Time In Possession", "All Runs", "All Run Metres", "Post Contact Metres",
                         "Line Breaks", "Tackle Breaks", "Average Set Distance", "Kick Return Metres", "Offloads",
                         "Receipts", "Total Passes", "Dummy Passes", "Kicks", "Kicking Metres", "Forced Drop Outs",
                         "Bombs", "Grubbers", "Tackles Made", "Missed Tackles", "Intercepts", "Ineffective Tackles",
                         "Errors", "Penalties Conceded", "Ruck Infringements", "Inside 10 Metres", "Interchanges Used",
                         "Completion Rate", "Average Play Ball Speed", "Kick Defusal", "Effective Tackle", "Tries",
                         "Conversions", "Penalty Goals", "Sin Bins", "1 Point Field Goals", "2 Point Field Goals", "Half Time"]
    
    match_data_df = []
    match_data_headers = ["Competition", "Year", "Round", "Game", "Overall First Try Scorer", "Overall First Try Minute",
                          "Overall First Try Round", "Main Ref", "Ground Condition", "Weather Condition"]
    
    try_data_df = []
    try_data_headers = ["Competition", "Year", "Round", "Game", "Home/Away", "Try Names", "Try Minutes"]
    
    # Fix the nested dictionary iteration
    stats_data_df = []
    for competition, years_list in master_stats_data.items():
        for year_dict in years_list:
            for year, rounds_list in year_dict.items():
                for round_dict in rounds_list:
                    for round_num, games_list in round_dict.items():
                        for game_dict in games_list:
                            for game, teams_dict in game_dict.items():
                                for team, team_stats in teams_dict.items():
                                    row = [competition, year, round_num, game]
                                    row.append(team_stats.get('home/away', ''))
                                    for header in stats_data_headers[5:]:
                                        header_key = header.lower().replace(' ', '_')
                                        row.append(team_stats.get(header_key, ''))
                                    stats_data_df.append(row)

    match_data_df = []
    for competition, years_list in master_match_data.items():
        for year_dict in years_list:
            for year, rounds_list in year_dict.items():
                for round_dict in rounds_list:
                    for round_num, games_list in round_dict.items():
                        for game_dict in games_list:
                            for game, game_stats in game_dict.items():
                                row = [competition, year, round_num, game]
                                for header in match_data_headers[4:]:
                                    header_key = header.lower().replace(' ', '_')
                                    row.append(game_stats.get(header_key, ''))
                                match_data_df.append(row)

    try_data_df = []
    for competition, years_list in master_try_data.items():
        for year_dict in years_list:
            for year, rounds_list in year_dict.items():
                for round_dict in rounds_list:
                    for round_num, games_list in round_dict.items():
                        for game_dict in games_list:
                            for game, teams_dict in game_dict.items():
                                for team, team_stats in teams_dict.items():
                                    try_names = team_stats.get('try_names', [])
                                    try_minutes = team_stats.get('try_minutes', [])
                                    
                                    # Create a row for each try
                                    for try_name, try_minute in zip(try_names, try_minutes):
                                        row = [
                                            competition,
                                            year,
                                            round_num,
                                            game,
                                            team,
                                            try_name,
                                            try_minute.replace("'", "")  # Remove the ' from minutes
                                        ]
                                        try_data_df.append(row)

    # Create DataFrames
    df_stats = pd.DataFrame(stats_data_df, columns=stats_data_headers)
    # Clean up First Try Time and Time In Possession columns
    df_stats['First Try Time'] = df_stats['First Try Time'].str.replace("'", "")
    df_stats['Time In Possession'] = df_stats['Time In Possession'].str.replace(",", "")

    df_match = pd.DataFrame(match_data_df, columns=match_data_headers)
    # Clean up First Try Time and Time In Possession columns
    df_match['Overall First Try Minute'] = df_match['Overall First Try Minute'].str.replace("'", "")

    df_try = pd.DataFrame(try_data_df, columns=try_data_headers)

    # Save to files
    base_path = os.path.join(output_dir, f"nrl_data")
    
    df_stats.to_csv(f"{base_path}_statistics.txt", sep='\t', index=False)
    df_match.to_csv(f"{base_path}_detailed.txt", sep='\t', index=False)
    df_try.to_csv(f"{base_path}_try.txt", sep='\t', index=False)

def main():
    """Main entry point for the script."""
    #chromedriver_autoinstaller.install() # Commented out to prevent message
    
    args = setup_argparse()
    
    try:
        matches = read_input_file(args.input_file)
        get_detailed_nrl_data(matches, args.output_directory)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    main()