from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
CORS(app)

def fetch_matches_from_page(page_number):
    base_url = 'https://pt.betsapi.com/ce/table-tennis'
    url = f'{base_url}/p.{page_number}'
    response = requests.get(url)

    if response.status_code == 200:
        print(f"Successfully fetched page {page_number}")
        soup = BeautifulSoup(response.content, 'html.parser')
        tables = soup.find_all('table')

        if tables:
            print(f"Found {len(tables)} tables on page {page_number}")
            table = tables[0]
            matches = []

            for row in table.find_all('tr'):
                cells = row.find_all('td')

                if len(cells) >= 6:
                    competition = cells[0].text.strip()
                    date_time = cells[1].text.strip()
                    players = cells[2].text.strip()
                    result_link = cells[4].find('a')
                    result = cells[4].text.strip() if result_link is None else result_link.text.strip()

                    if result in ["3-0", "0-3"]:
                        try:
                            date_time_obj = datetime.strptime(date_time, '%d/%m %H:%M')
                            date_time_obj = date_time_obj.replace(year=datetime.now().year)
                        except ValueError:
                            date_time_obj = None

                        if date_time_obj:
                            match_details = {
                                'competition': competition,
                                'date_time': date_time_obj,
                                'players': players,
                                'result': result
                            }

                            if result_link and 'href' in result_link.attrs:
                                match_details['result_link'] = 'https://pt.betsapi.com' + result_link['href']

                            matches.append(match_details)

            return matches
        else:
            print(f"Nenhuma tabela encontrada na página {page_number}.")
            return []
    else:
        print(f"Failed to retrieve data from page {page_number}: {response.status_code}")
        return []

def fetch_set_results(result_url):
    response = requests.get(result_url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')

        set_results = []
        cards = soup.find_all('div', class_='card')

        for card in cards:
            rows = card.find_all('tr')
            if rows:
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) > 1:
                        player_name = cells[0].text.strip()
                        scores = [int(cell.text.strip()) for cell in cells[1:] if cell.text.strip().isdigit()]
                        set_results.append((player_name, scores))

        return set_results
    else:
        print(f"Failed to retrieve set results from {result_url}: {response.status_code}")
        return []

def is_matching_pattern(set_results):
    """
    Checks if the set results match the desired pattern (Set 1: 11-4 or less, Set 2: 11-4 or less, Set 3: 11-8 or less).

    Args:
        set_results (list): List of tuples containing player names and their set scores.

    Returns:
        bool: True if the set results match the pattern, False otherwise.
    """
    if len(set_results) != 2:  # Check for exactly 2 players
        print("Invalid number of players. Expected 2.")
        return False

    player1_scores = None
    player2_scores = None

    for player, scores in set_results:
        if player1_scores is None:
            player1_scores = scores
        else:
            player2_scores = scores

    if player1_scores is None or player2_scores is None:
        print("Could not determine player scores.")
        return False

    if len(player1_scores) != 3 or len(player2_scores) != 3:
        print(f"Invalid number of sets. Expected 3, found: {len(player1_scores)}")
        return False

    return (
        (player1_scores[0] == 11 and player2_scores[0] <= 4) and
        (player1_scores[1] == 11 and player2_scores[1] <= 4) and
        (player1_scores[2] == 11 and player2_scores[2] <= 8)
    ) or (
        (player2_scores[0] == 11 and player1_scores[0] <= 4) and
        (player2_scores[1] == 11 and player1_scores[1] <= 4) and
        (player2_scores[2] == 11 and player1_scores[2] <= 8)
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/fetch_matches', methods=['GET'])
def fetch_matches():
    found_matches = []
    page_number = 1

    while True:
        print(f"Fetching matches from page {page_number}...")
        new_matches = fetch_matches_from_page(page_number)

        if not new_matches:
            print(f"No more matches found on page {page_number}.")
            break

        for match in new_matches:
            if 'result_link' in match:
                result_url = match['result_link']
                match['set_results'] = fetch_set_results(result_url)

                if is_matching_pattern(match['set_results']):
                    print(f"Match found that matches the pattern: {match['competition']} on {match['date_time'].strftime('%d/%m %H:%M')}")
                    print(f"Players: {match['players']}")
                    found_matches.append(match)

        page_number += 1

    if found_matches:
        print("Matches found that meet the criteria:")
        for match in found_matches:
            print(f"Competition: {match['competition']}, Date and Time: {match['date_time'].strftime('%d/%m %H:%M')}")
            print(f"Players: {match['players']}")
    else:
        print("No matches found that meet the criteria.")

    return jsonify(found_matches)

if __name__ == '__main__':
    app.run(debug=True)
