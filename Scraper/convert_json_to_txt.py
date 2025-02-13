import json
import re
import argparse
import os
import pandas as pd

# Function to remove special characters and new line characters from a string
def clean_text(text):
    text = re.sub(r'[^\x00-\x7F]+', '', text)  # Remove non-ASCII characters
    text = text.replace('\n', ' ').strip()  # Remove new line characters and strip leading/trailing spaces
    text = re.sub(r'     .*', '', text)  # Remove text after multiple spaces
    text = re.sub(r'Home of the.*', '', text)  # Removes Indigenous Round additional location information
    return text

def convert_json_to_table(input_file):
    # Load JSON data
    with open(input_file, 'r') as file:
        json_data = json.load(file)

    # Convert JSON to table format
    table_data = []
    headers = ["Competition", "Year", "Round", "Details", "Date", "Home", "Home_Score", "Away", "Away_Score", "Venue"]

    for competition, years in json_data.items():
        for year_data in years:
            for year, rounds in year_data.items():
                for round_data in rounds:
                    for round_num, matches in round_data.items():
                        for match in matches:
                            # Clean the 'Venue' item
                            match['Venue'] = clean_text(match['Venue'])
                            row = [competition, year, round_num]
                            row.extend([match[header] for header in headers[3:]])
                            table_data.append(row)

    # Create a DataFrame
    df = pd.DataFrame(table_data, columns=headers)
    df_match_list = df[['Year', 'Round','Home','Away']]

    # Determine output file path
    output_file = os.path.splitext(input_file)[0] + '.txt'

    # Write DataFrame to txt file
    df.to_csv(output_file, sep='\t', index=False)

    print(f"Table has been written to {output_file}")

    if args.match_list:
        print("Match list requested")
        df_match_list.to_csv(os.path.splitext(input_file)[0] + '_match_list.txt', sep='\t', index=False)
    else:
        print("Match list not requested")
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert JSON to table format into a tab-delimited txt file.')
    parser.add_argument('input_file', type=str, help='Specify path to input JSON file')
    parser.add_argument('--list',dest='match_list', action='store_true', help='Output match list for extracting detailed data (default=False)')


    args = parser.parse_args()
    convert_json_to_table(args.input_file)