from pathlib import Path
import pandas as pd


RAW_DATA = Path("data/raw/results")
OUTPUT = Path("data/processed/club_season_results.csv")

def load_season(season_code):
    """
    Load one Premier League season into a pandas DataFrame.
    """

    season_file = RAW_DATA / f"premier_league_{season_code}.csv"

    matches = pd.read_csv(season_file)

    return matches


def initialise_team_stats():
    """
    create empty dictionary for storing stats
    """

    return{}

def add_team(team_stats, team):
    """
    add club to dict if doesnt exist
    """

    if team not in team_stats:

        team_stats[team] = {
        "Played": 0,
        "Wins": 0,
        "Draws": 0,
        "Losses": 0,
        "GF": 0,
        "GA": 0,
        "GD": 0,
        "Points": 0   
        }

def main():

    matches = load_season("2223")

    team_stats = initialise_team_stats()

    print(team_stats)

if __name__ == "__main__":
    main()

