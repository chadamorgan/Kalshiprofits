import requests
import json
import os

# --- 1. GET YOUR API KEY (from GitHub Secrets) ---
try:
    ODDS_API_KEY = os.environ['ODDS_API_KEY']
except KeyError:
    print("CRITICAL ERROR: ODDS_API_KEY not found. Set it in GitHub Secrets.")
    ODDS_API_KEY = 'DUMMY_KEY_SCRIPT_WILL_FAIL'

# --- 2. DEFINE YOUR PARAMETERS ---
SPORTS_TO_CHECK = ['americanfootball_nfl', 'basketball_nba', 'baseball_mlb', 'icehockey_nhl']
KALSHI_API_URL = "https://api.elections.kalshi.com/trade-api/v2/markets"
ODDS_API_URL = "https://api.the-odds-api.com/v4/sports/{sport}/odds"

# --- 3. HELPER FUNCTION TO CONVERT ODDS ---
def get_moneyline(decimal_price):
    if decimal_price >= 2.0:
        return int((decimal_price - 1) * 100)
    else:
        return int(-100 / (decimal_price - 1))

def get_kalshi_markets():
    """Fetches all open sports markets from Kalshi."""
    print("Fetching Kalshi markets...")
    params = {'status': 'open', 'category': 'sports'}
    
    try:
        response = requests.get(KALSHI_API_URL, params=params)
        response.raise_for_status() 
        all_markets = response.json().get('markets', [])
        
        # --- THIS IS YOUR NEW, FIXED LOGIC ---
        # Find all markets trading under 40 cents
        cheap_markets = []
        for market in all_markets:
            kalshi_yes_price = market.get('yes_price', 100)
            # The bad " win " filter is now REMOVED.
            # We just check the price.
            if 0 < kalshi_yes_price < 40:
                cheap_markets.append(market)
                
        print(f"Found {len(cheap_markets)} Kalshi markets trading < 40 cents.")
        return cheap_markets
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Kalshi data: {e}")
        return []

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
            'regions': 'us',
            'markets': 'h2h'
        }
        try:
            response = requests.get(ODDS_API_URL.format(sport=sport), params=params)
            requests_remaining = response.headers.get('x-requests-remaining')
            print(f"  ...requests remaining this month: {requests_remaining}")
            response.raise_for_status()
            all_odds[sport] = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds for {sport}: {e}")
            continue 
    return all_odds

def match_markets(kalshi_markets, all_sports_odds):
    """Matches cheap Kalshi markets to sportsbook games and saves all odds."""
    all_market_data = []
    
    for sport_key, games in all_sports_odds.items():
        for game in games:
            home_team = game.get('home_team')
            away_team = game.get('away_team')
            
            for kalshi_market in kalshi_markets:
                title = kalshi_market.get('title').lower()
                
                team_on_kalshi = None
                
                # Simple matching logic. This is the most fragile part.
                # It checks if "cowboys" from Kalshi is in "Dallas Cowboys" from API
                if home_team.lower() in title or any(part in title for part in home_team.lower().split()):
                    team_on_kalshi = home_team
                elif away_team.lower() in title or any(part in title for part in away_team.lower().split()):
                    team_on_kalshi = away_team
                else:
                    continue # This Kalshi market doesn't match this game

                # --- NEW LOGIC: WE FOUND A MATCH! NOW GET ALL ODDS ---
                
                market_data = {
                    "event": f"{away_team} @ {home_team}",
                    "team_on_kalshi": team_on_kalshi,
                    "kalshi_market": kalshi_market.get('title'),
                    "kalshi_price": kalshi_market.get('yes_price') / 100.0, # Convert cents to dollar
                    "kalshi_url": f"https://kalshi.com/markets/{kalshi_market.get('ticker')}",
                    "bookmakers": []
                }
                
                for bookmaker in game.get('bookmakers', []):
                    # Find the 'h2h' (moneyline) market
                    h2h_market = next(
                        (m for m in bookmaker.get('markets', []) if m.get('key') == 'h2h'), 
                        None
                    )
                    if not h2h_market:
                        continue # This bookmaker doesn't have moneyline odds

                    # Find the odds for our specific team
                    team_odds = next(
                        (o for o in h2h_market.get('outcomes', []) if o.get('name') == team_on_kalshi),
                        None
                    )
                    
                    if team_odds:
                        moneyline = get_moneyline(team_odds.get('price'))
                        market_data['bookmakers'].append({
                            "name": bookmaker.get('title'),
                            "moneyline": moneyline
                        })
                
                if market_data['bookmakers']: # Only add if we found at least one bookmaker
                    all_market_data.append(market_data)
                    print(f"Found match for {team_on_kalshi}, saving {len(market_data['bookmakers'])} odds.")

    return all_market_data

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    print("--- Starting Market Scanner Script ---")
    kalshi_markets = get_kalshi_markets()
    all_sports_odds = get_sportsbook_odds()
    final_data = match_markets(kalshi_markets, all_sports_odds)
    
    with open('opportunities.json', 'w') as f:
        json.dump(final_data, f, indent=2)
        
    print(f"\n--- Process complete. Saved data for {len(final_data)} markets. ---")
    print("--- Wrote results to opportunities.json ---")
