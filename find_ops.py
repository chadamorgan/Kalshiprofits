import requests
import json
import os

# --- 1. GET YOUR API KEY (from GitHub Secrets) ---
try:
    # This is the secure way GitHub lets us use the API key
    ODDS_API_KEY = os.environ['ODDS_API_KEY']
except KeyError:
    # This error means the script is being run locally without the key.
    # For our purposes, we'll just stop the script.
    print("CRITICAL ERROR: ODDS_API_KEY not found. Set it in GitHub Secrets.")
    # We'll create a dummy key to prevent the script from crashing
    # But it will fail the request, which is fine.
    ODDS_API_KEY = 'DUMMY_KEY_SCRIPT_WILL_FAIL'


# --- 2. DEFINE YOUR PARAMETERS ---
# Sport keys from The Odds API documentation
SPORTS_TO_CHECK = ['americanfootball_nfl', 'basketball_nba', 'baseball_mlb', 'icehockey_nhl']
KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/{sport}/odds"


def get_kalshi_markets():
    """Fetches all open sports markets from Kalshi."""
    print("Fetching Kalshi markets...")
    params = {'status': 'open', 'category': 'sports'}
    
    try:
        response = requests.get(KALSHI_API_URL, params=params)
        response.raise_for_status() # Stop if there's an error
        all_markets = response.json().get('markets', [])
        
        team_markets = []
        for market in all_markets:
            # Find markets that are a YES/NO on a team winning
            if " win " in market.get('title', '').lower() and market.get('yes_price', 0) > 0:
                team_markets.append(market)
        print(f"Found {len(team_markets)} relevant Kalshi markets.")
        return team_markets
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Kalshi data: {e}")
        return [] # Return an empty list on failure

def get_sportsbook_odds():
    """Fetches all moneyline odds for the sports we care about."""
    print("Fetching sportsbook odds...")
    all_odds = {}
    
    if ODDS_API_KEY == 'DUMMY_KEY_SCRIPT_WILL_FAIL':
        print("Skipping odds fetch, API key is missing.")
        return all_odds
        
    for sport in SPORTS_TO_CHECK:
        print(f"  ...fetching {sport}")
        params = {
            'apiKey': ODDS_API_KEY,
            'regions': 'us',  # US-based bookmakers
            'markets': 'h2h'    # h2h is 'head-to-head', i.e., moneyline
        }
        try:
            response = requests.get(ODDS_API_URL.format(sport=sport), params=params)
            requests_remaining = response.headers.get('x-requests-remaining')
            print(f"  ...requests remaining this month: {requests_remaining}")
            response.raise_for_status()
            all_odds[sport] = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds for {sport}: {e}")
            # Don't stop the whole script, just skip this sport
            continue 
    return all_odds

def find_opportunities(kalshi_markets, all_sports_odds):
    """Compares Kalshi prices to sportsbook moneylines."""
    opportunities = []
    
    for sport_key, games in all_sports_odds.items():
        for game in games:
            home_team = game.get('home_team')
            away_team = game.get('away_team')
            
            bookmaker_odds = next(
                (book['markets'][0]['outcomes'] for book in game.get('bookmakers', []) 
                 if book.get('markets') and book['markets'][0].get('key') == 'h2h'),
                None
            )
            
            if not bookmaker_odds:
                continue # No moneyline odds found for this game

            odds_map = {item['name']: item['price'] for item in bookmaker_odds}
            
            for kalshi_market in kalshi_markets:
                title = kalshi_market.get('title').lower()
                kalshi_yes_price = kalshi_market.get('yes_price', 100) / 100.0 # Convert cents to dollar
                
                team_in_title = None
                moneyline_decimal = None
                
                # This logic is simple. It matches "Dallas Cowboys" from the API 
                # with a Kalshi title containing "cowboys". This may need refinement.
                if home_team.lower() in title or any(part in title for part in home_team.lower().split()):
                    team_in_title = home_team
                    moneyline_decimal = odds_map.get(home_team)
                elif away_team.lower() in title or any(part in title for part in away_team.lower().split()):
                    team_in_title = away_team
                    moneyline_decimal = odds_map.get(away_team)
                else:
                    continue # This Kalshi market doesn't match this game
                
                if not moneyline_decimal:
                    continue # No odds found for the matched team

                # Convert American odds (decimal) to moneyline format (e.g., +300)
                if moneyline_decimal >= 2.0:
                    moneyline = (moneyline_decimal - 1) * 100
                else:
                    moneyline = -100 / (moneyline_decimal - 1)
                
                # --- THIS IS YOUR NEW, UPDATED LOGIC ---
                # We are now looking for underdogs (moneyline > 100)
                # that are LESS than +300 (moneyline < 300)
                if kalshi_yes_price < 0.40 and moneyline < 300 and moneyline > 100:
                    print(f"!!! OPPORTUNITY FOUND: {team_in_title} !!!")
                    op = {
                        "event": f"{away_team} @ {home_team}",
                        "market": kalshi_market.get('title'),
                        "kalshi_price": kalshi_yes_price,
                        "moneyline": int(moneyline),
                        "kalshi_url": f"https://kalshi.com/markets/{kalshi_market.get('ticker')}"
                    }
                    print(json.dumps(op, indent=2))
                    opportunities.append(op)

    return opportunities


# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- Starting Opportunity Finder Script ---")
    kalshi_markets = get_kalshi_markets()
    all_sports_odds = get_sportsbook_odds()
    opportunities = find_opportunities(kalshi_markets, all_sports_odds)
    
    # Write the final list to our "database" file
    # This file will be read by the script.js on the website
    with open('opportunities.json', 'w') as f:
        json.dump(opportunities, f, indent=2)
        
    print(f"\n--- Process complete. Found {len(opportunities)} opportunities. ---")
    print("--- Wrote results to opportunities.json ---")
