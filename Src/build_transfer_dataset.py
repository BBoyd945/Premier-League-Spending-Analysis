from pathlib import Path

import pandas as pd


RAW_TRANSFER_DATA = Path("data/raw/transfers/transfers.csv")

RAW_TRANSFER_DATA = Path("data/raw/transfers/transfers.csv")
RESULTS_DATA = Path("data/processed/club_season_results.csv")

CLUB_DATA = Path("data/raw/transfers/clubs.csv")

CLUB_NAME_MAP = {
    "Hull": "Hull City",
    "Man United": "Manchester United",
    "Stoke": "Stoke City"
}

CLUB_ID_MAP = {
    "Arsenal": 11,
    "Aston Villa": 405,
    "Birmingham": 337,
    "Blackburn": 164,
    "Blackpool": 1181,
    "Bolton": 355,
    "Bournemouth": 989,
    "Brentford": 1148,
    "Brighton": 1237,
    "Burnley": 1132,
    "Cardiff": 603,
    "Charlton": 358,
    "Chelsea": 631,
    "Crystal Palace": 873,
    "Derby": 22,
    "Everton": 29,
    "Fulham": 931,
    "Huddersfield": 1110,
    "Hull": 3008,
    "Ipswich": 677,
    "Leeds": 399,
    "Leicester": 1003,
    "Liverpool": 31,
    "Luton": 1031,
    "Man City": 281,
    "Man United": 985,
    "Middlesbrough": 641,
    "Newcastle": 762,
    "Norwich": 1123,
    "Nott'm Forest": 703,
    "Portsmouth": 1020,
    "QPR": 1039,
    "Reading": 1032,
    "Sheffield United": 350,
    "Southampton": 180,
    "Stoke": 512,
    "Sunderland": 289,
    "Swansea": 2288,
    "Tottenham": 148,
    "Watford": 1010,
    "West Brom": 984,
    "West Ham": 379,
    "Wigan": 1071,
    "Wolves": 543,
}

def add_club_ids(results):
    """
    Add verified Transfermarkt club IDs to each club-season.
    """

    results["club_id"] = results["Club"].map(CLUB_ID_MAP)

    return results

def standardise_club_names(results):
    """
    Standardise Football-Data club names to match Transfermarkt.
    """

    results["Club"] = results["Club"].replace(CLUB_NAME_MAP)

    return results

def load_clubs():
    clubs = pd.read_csv(CLUB_DATA)
    return clubs

def load_transfers():
    """
    Load the raw Premier League transfer dataset.
    """

    transfers = pd.read_csv(RAW_TRANSFER_DATA)

    return transfers

def load_results():
    """
    Load the processed Premier League club-season results.
    """

    results = pd.read_csv(RESULTS_DATA)

    return results

def format_season(season):
    """
    Convert results season codes to Transfermarkt format.

    Example:
    506  -> 05/06
    2223 -> 22/23
    """

    season = str(season).zfill(4)

    return f"{season[:2]}/{season[2:]}"


def compare_club_names(results, transfers):
    """
    Compare Premier League club names with club names
    appearing in the Transfermarkt transfer dataset.
    """

    result_clubs = set(results["Club"].dropna().unique())

    transfer_clubs = set(
        transfers["from_club_name"].dropna().unique()
    ) | set(
        transfers["to_club_name"].dropna().unique()
    )

    matching_clubs = sorted(result_clubs & transfer_clubs)
    unmatched_clubs = sorted(result_clubs - transfer_clubs)

    return matching_clubs, unmatched_clubs

def find_club_candidates(missing_clubs, clubs):

    for club in missing_clubs:

        candidates = clubs[
            clubs["name"].str.contains(
                club,
                case=False,
                na=False,
                regex=False
            )
        ][["club_id", "name"]]

        print(f"\n{club}:")
        print(candidates.to_string(index=False))


def main():

    results = load_results()

    results["Season"] = results["Season"].apply(format_season)

    results = add_club_ids(results)

    print("\nTotal rows:", len(results))
    print("Matched IDs:", results["club_id"].notna().sum())
    print("Missing IDs:", results["club_id"].isna().sum())

    print("\nMissing clubs:")
    print(
        results.loc[
            results["club_id"].isna(),
            ["Season", "Club"]
        ]
    )
if __name__ == "__main__":
    main()