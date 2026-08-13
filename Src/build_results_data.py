from pathlib import Path
import pandas as pd
from pprint import pprint

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


def process_match(team_stats, match):
    """
    Update team statistics using the result of one match.
    """

    home_team = match["HomeTeam"]
    away_team = match["AwayTeam"]

    home_goals = match["FTHG"]
    away_goals = match["FTAG"]

    result = match["FTR"]

    # Make sure both teams exist in our dictionary
    add_team(team_stats, home_team)
    add_team(team_stats, away_team)

    # Both teams have played one match
    team_stats[home_team]["Played"] += 1
    team_stats[away_team]["Played"] += 1

    # Update goals
    team_stats[home_team]["GF"] += home_goals
    team_stats[home_team]["GA"] += away_goals

    team_stats[away_team]["GF"] += away_goals
    team_stats[away_team]["GA"] += home_goals

        # Update result statistics and points
    if result == "H":
        team_stats[home_team]["Wins"] += 1
        team_stats[away_team]["Losses"] += 1
        team_stats[home_team]["Points"] += 3

    elif result == "A":
        team_stats[away_team]["Wins"] += 1
        team_stats[home_team]["Losses"] += 1
        team_stats[away_team]["Points"] += 3

    elif result == "D":
        team_stats[home_team]["Draws"] += 1
        team_stats[away_team]["Draws"] += 1
        team_stats[home_team]["Points"] += 1
        team_stats[away_team]["Points"] += 1


def calculate_goal_difference(team_stats):
    """
    Calculate goal difference for every team.
    """
     

    for team in team_stats:
        team_stats[team]["GD"] = (
            team_stats[team]["GF"] - team_stats[team]["GA"]
        )

def main():

    matches = load_season("2223")

    team_stats = initialise_team_stats()

    for _, match in matches.iterrows():
        process_match(team_stats, match)

    calculate_goal_difference(team_stats)

    print(pd.DataFrame.from_dict(team_stats, orient="index"))



if __name__ == "__main__":
    main()

