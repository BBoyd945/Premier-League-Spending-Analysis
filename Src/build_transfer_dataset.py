from pathlib import Path

import pandas as pd


RAW_TRANSFER_DATA = Path("data/raw/transfers/transfers.csv")

RAW_TRANSFER_DATA = Path("data/raw/transfers/transfers.csv")
RESULTS_DATA = Path("data/processed/club_season_results.csv")
SECONDARY_TRANSFER_DATA = Path("data/raw/transfers/premier-league.csv")

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

ACADEMY_PARENT_MAP = {
    "palace": "crystal palace",
    "man utd": "man united",
    "manchester united": "man united",
    "spurs": "tottenham",
    "boro": "middlesbrough",
    "hull": "hull city",
    "fulham fc": "fulham",
    "fc burnley": "burnley",
    "norwich city": "norwich",
    "southampt.": "southampton",
    "leeds united": "leeds",
    "nottingham": "nott'm forest"
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

def format_season(season, full_year=False):
    """
    Format season codes consistently.

    Examples:
    506  -> 05/06
    2223 -> 22/23

    With full_year=True:
    506  -> 2005/2006
    2223 -> 2022/2023
    """

    season = str(season).zfill(4)

    start = season[:2]
    end = season[2:]

    if full_year:
        return f"20{start}/20{end}"

    return f"{start}/{end}"


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

def filter_summer_transfers(transfers):

    transfers = transfers.copy()

    transfers["transfer_date"] = pd.to_datetime(
        transfers["transfer_date"]
    )

    transfers["season_start_year"] = (
        transfers["transfer_season"]
        .str[:2]
        .astype(int)
        + 2000
    )

    summer_transfers = transfers[
        (transfers["transfer_date"].dt.year ==
         transfers["season_start_year"])
        &
        (transfers["transfer_date"].dt.month >= 6)
    ]

    return summer_transfers

def load_secondary_transfers():
    """
    Load the older Premier League transfer dataset used
    as a secondary source for missing transfer fees.
    """

    transfers = pd.read_csv(SECONDARY_TRANSFER_DATA)

    return transfers

def find_secondary_fee(
    secondary_transfers,
    player_name,
    season,
    movement
):
    """
    Search the secondary Premier League transfer dataset
    for a matching summer transfer.

    Returns:
        fee_eur:
            Numeric transfer fee in euros, or None.

        fee_status:
            "known"           -> numeric fee found
            "no_fee_movement" -> loan return, loan transfer,
                                 or free transfer
            "unknown"         -> transfer exists but fee is unknown
            "not_found"       -> no matching transfer found
    """

    # Convert 22/23 -> 2022/2023 for the secondary dataset
    secondary_season = format_season(
        season.replace("/", ""),
        full_year=True
    )

    matches = secondary_transfers[
        (secondary_transfers["player_name"] == player_name) &
        (secondary_transfers["season"] == secondary_season) &
        (
            secondary_transfers["transfer_movement"]
            .str.lower() == movement.lower()
        ) &
        (
            secondary_transfers["transfer_period"]
            .str.lower() == "summer"
        )
    ]

    # No matching transfer found
    if matches.empty:
        return None, "not_found"

    # Check whether a numeric fee exists
    fees = (
        matches["fee_cleaned"]
        .dropna()
        .unique()
    )

    # Only accept an unambiguous numeric value
    if len(fees) == 1:
        fee_eur = float(fees[0]) * 1_000_000
        return fee_eur, "known"

    # Look at the original Transfermarkt fee description
    fee_descriptions = (
        matches["fee"]
        .dropna()
        .astype(str)
        .str.lower()
        .tolist()
    )

    # Movements that do not represent an unknown purchase/sale fee
    no_fee_phrases = [
        "end of loan",
        "loan transfer",
        "free transfer"
    ]

    for description in fee_descriptions:
        for phrase in no_fee_phrases:
            if phrase in description:
                return 0.0, "no_fee_movement"

    # '?' means Transfermarkt does not know/disclose the fee
    for description in fee_descriptions:
        if description.strip() == "?":
            return None, "unknown"

    # Matching transfer exists, but we still cannot determine the fee
    return None, "unknown"

def calculate_transfer_spending(
    summer_transfers,
    secondary_transfers,
    club_id,
    season
):
    """
    Calculate summer transfer spend, income and net spend
    for one club-season.

    Missing fees in the primary dataset are checked against
    the secondary Premier League transfer dataset.

    Academy promotions into the same club's first team are
    treated as zero-fee internal movements.

    Tracks:
    - recovered numeric fees
    - academy promotions
    - recognised no-fee movements
    - genuinely unknown fees
    - transfers not found in the secondary dataset
    """

    club_transfers = summer_transfers[
        (summer_transfers["transfer_season"] == season) &
        (
            (summer_transfers["from_club_id"] == club_id) |
            (summer_transfers["to_club_id"] == club_id)
        )
    ].copy()

    incoming = club_transfers[
        club_transfers["to_club_id"] == club_id
    ].copy()

    outgoing = club_transfers[
        club_transfers["from_club_id"] == club_id
    ].copy()

    # -------------------------
    # Quality-control counters
    # -------------------------

    recovered_incoming = 0
    recovered_outgoing = 0

    academy_promotions = 0

    unknown_incoming = 0
    unknown_outgoing = 0

    no_fee_incoming = 0
    no_fee_outgoing = 0

    not_found_incoming = 0
    not_found_outgoing = 0

    # -------------------------
    # Check missing incoming fees
    # -------------------------

    for index, row in incoming[
        incoming["transfer_fee"].isna()
    ].iterrows():

        # Internal academy promotion
        if is_internal_club_move(row):
            incoming.loc[index, "transfer_fee"] = 0.0
            academy_promotions += 1
            continue

        # Free-agent signing
        if is_non_transfer_move(row):
            incoming.loc[index, "transfer_fee"] = 0.0
            no_fee_incoming += 1
            continue

        recovered_fee, status = find_secondary_fee(
            secondary_transfers,
            row["player_name"],
            season,
            "in"
        )

        if status == "known":
            incoming.loc[index, "transfer_fee"] = recovered_fee
            recovered_incoming += 1

        elif status == "no_fee_movement":
            incoming.loc[index, "transfer_fee"] = 0.0
            no_fee_incoming += 1

        elif status == "unknown":
            unknown_incoming += 1

            print(
                f"UNKNOWN FEE | {season} | "
                f"IN | {row['player_name']} | "
                f"{row['from_club_name']} -> "
                f"{row['to_club_name']}"
            )

        elif status == "not_found":
            not_found_incoming += 1

            print(
                f"NOT FOUND | {season} | "
                f"IN | {row['player_name']} | "
                f"{row['from_club_name']} -> "
                f"{row['to_club_name']}"
            )

    # -------------------------
    # Check missing outgoing fees
    # -------------------------

    for index, row in outgoing[
        outgoing["transfer_fee"].isna()
    ].iterrows():

        # Player released / becomes a free agent

        if is_internal_club_move(row):
            outgoing.loc[index, "transfer_fee"] = 0.0
            no_fee_outgoing += 1
            continue

        if is_non_transfer_move(row):
            outgoing.loc[index, "transfer_fee"] = 0.0
            no_fee_outgoing += 1
            continue

        recovered_fee, status = find_secondary_fee(
            secondary_transfers,
            row["player_name"],
            season,
            "out"
        )

        if status == "known":
            outgoing.loc[index, "transfer_fee"] = recovered_fee
            recovered_outgoing += 1

        elif status == "no_fee_movement":
            outgoing.loc[index, "transfer_fee"] = 0.0
            no_fee_outgoing += 1

        elif status == "unknown":
            unknown_outgoing += 1

            print(
                f"UNKNOWN FEE | {season} | "
                f"OUT | {row['player_name']} | "
                f"{row['from_club_name']} -> "
                f"{row['to_club_name']}"
            )

        elif status == "not_found":
            not_found_outgoing += 1

            print(
                f"NOT FOUND | {season} | "
                f"OUT | {row['player_name']} | "
                f"{row['from_club_name']} -> "
                f"{row['to_club_name']}"
            )

    # -------------------------
    # Financial calculations
    # -------------------------

    summer_spend = incoming["transfer_fee"].sum()
    summer_income = outgoing["transfer_fee"].sum()

    net_spend = summer_spend - summer_income

    # -------------------------
    # Return summary
    # -------------------------

    return {
        "SummerSpend": summer_spend,
        "SummerIncome": summer_income,
        "NetSpend": net_spend,

        "RecoveredIncomingFees": recovered_incoming,
        "RecoveredOutgoingFees": recovered_outgoing,

        "AcademyPromotions": academy_promotions,

        "UnknownIncomingFees": unknown_incoming,
        "UnknownOutgoingFees": unknown_outgoing,

        "NoFeeIncomingMoves": no_fee_incoming,
        "NoFeeOutgoingMoves": no_fee_outgoing,

        "NotFoundIncomingFees": not_found_incoming,
        "NotFoundOutgoingFees": not_found_outgoing
    }

def calculate_season_transfer_spending(
    results,
    summer_transfers,
    secondary_transfers,
    season
):
    """
    Calculate summer transfer spending for every
    Premier League club in a given season.
    """

    season_results = results[
        results["Season"] == season
    ]

    season_data = []

    for _, row in season_results.iterrows():

        club = row["Club"]
        club_id = row["club_id"]

        transfer_summary = calculate_transfer_spending(
            summer_transfers,
            secondary_transfers,
            club_id,
            season
        )

        season_data.append({
            "Season": season,
            "Club": club,
            "club_id": club_id,
            **transfer_summary
        })

    return pd.DataFrame(season_data)

def calculate_all_transfer_spending(
    results,
    summer_transfers,
    secondary_transfers
):
    """
    Calculate summer transfer spending for every
    Premier League club-season in the results dataset.
    """

    all_seasons = []

    seasons = sorted(results["Season"].unique())

    for season in seasons:

        season_data = calculate_season_transfer_spending(
            results,
            summer_transfers,
            secondary_transfers,
            season
        )

        all_seasons.append(season_data)

    transfer_data = pd.concat(
        all_seasons,
        ignore_index=True
    )

    return transfer_data

def is_internal_club_move(row):
    """
    Return True when a player moves internally between a club's
    first team and one of its youth/reserve/academy teams.

    Examples:
    Liverpool U21 -> Liverpool       True
    Liverpool -> Liverpool U21       True
    Brentford B -> Brentford          True
    Burnley -> Burnley U21            True
    Chelsea U19 -> Wolves             False
    """

    from_club = str(row["from_club_name"]).strip().lower()
    to_club = str(row["to_club_name"]).strip().lower()

    internal_suffixes = [
        " u18",
        " u19",
        " u20",
        " u21",
        " u23",
        " academy",
        " youth",
        " yth.",
        " b",
        " res.",
        " reserves"
    ]

    def get_parent_club(club_name):
        """
        Remove youth/reserve suffixes and standardise known aliases.
        """

        parent = club_name

        for suffix in internal_suffixes:
            if parent.endswith(suffix):
                parent = parent.removesuffix(suffix).strip()
                break

        parent = ACADEMY_PARENT_MAP.get(
            parent,
            parent
        )

        return parent

    from_parent = get_parent_club(from_club)
    to_parent = get_parent_club(to_club)

    # At least one side must actually be a youth/reserve side
    from_is_internal_team = any(
        from_club.endswith(suffix)
        for suffix in internal_suffixes
    )

    to_is_internal_team = any(
        to_club.endswith(suffix)
        for suffix in internal_suffixes
    )

    if not (from_is_internal_team or to_is_internal_team):
        return False

    return from_parent == to_parent

def is_non_transfer_move(row):
    """
    Return True for movements that do not involve
    a transfer fee between two clubs.
    """

    from_club = str(row["from_club_name"]).strip().lower()
    to_club = str(row["to_club_name"]).strip().lower()

    non_club_destinations = [
        "without club",
        "career break",
        "retired"
    ]

    return (
        from_club in non_club_destinations or
        to_club in non_club_destinations
    )

def print_transfer_audit(transfer_data):
    """
    Print a concise terminal audit of the full
    Premier League transfer dataset.
    """

    print("\n" + "=" * 80)
    print("PREMIER LEAGUE TRANSFER DATASET AUDIT")
    print("=" * 80)

    # -------------------------
    # Overall summary
    # -------------------------

    club_seasons = len(transfer_data)
    seasons = transfer_data["Season"].nunique()
    clubs = transfer_data["Club"].nunique()

    total_spend = transfer_data["SummerSpend"].sum()
    total_income = transfer_data["SummerIncome"].sum()

    academy_promotions = transfer_data[
        "AcademyPromotions"
    ].sum()

    recovered_fees = (
        transfer_data["RecoveredIncomingFees"].sum()
        + transfer_data["RecoveredOutgoingFees"].sum()
    )

    unknown_fees = (
        transfer_data["UnknownIncomingFees"].sum()
        + transfer_data["UnknownOutgoingFees"].sum()
    )

    not_found = (
        transfer_data["NotFoundIncomingFees"].sum()
        + transfer_data["NotFoundOutgoingFees"].sum()
    )

    print(f"\nClub-seasons processed: {club_seasons}")
    print(f"Seasons processed:      {seasons}")
    print(f"Unique clubs:           {clubs}")

    print(f"\nTotal summer spend:     €{total_spend / 1e9:,.2f}bn")
    print(f"Total summer income:    €{total_income / 1e9:,.2f}bn")

    print(f"\nAcademy promotions:     {academy_promotions}")
    print(f"Recovered fees:         {recovered_fees}")
    print(f"Unknown fees:           {unknown_fees}")
    print(f"Not-found transfers:    {not_found}")

    # -------------------------
    # Quality by season
    # -------------------------

    print("\n" + "=" * 80)
    print("DATA QUALITY BY SEASON")
    print("=" * 80)

    quality_by_season = (
        transfer_data
        .groupby("Season")
        .agg(
            UnknownIn=("UnknownIncomingFees", "sum"),
            UnknownOut=("UnknownOutgoingFees", "sum"),
            NotFoundIn=("NotFoundIncomingFees", "sum"),
            NotFoundOut=("NotFoundOutgoingFees", "sum"),
            RecoveredIn=("RecoveredIncomingFees", "sum"),
            RecoveredOut=("RecoveredOutgoingFees", "sum")
        )
        .reset_index()
    )

    quality_by_season["NotFound"] = (
        quality_by_season["NotFoundIn"]
        + quality_by_season["NotFoundOut"]
    )

    quality_by_season["Recovered"] = (
        quality_by_season["RecoveredIn"]
        + quality_by_season["RecoveredOut"]
    )

    quality_display = quality_by_season[
        [
            "Season",
            "UnknownIn",
            "UnknownOut",
            "NotFound",
            "Recovered"
        ]
    ]

    print(
        quality_display.to_string(
            index=False
        )
    )

    # -------------------------
    # Highest spending club-seasons
    # -------------------------

    print("\n" + "=" * 80)
    print("TOP 10 SUMMER SPENDING CLUB-SEASONS")
    print("=" * 80)

    top_spenders = (
        transfer_data[
            [
                "Season",
                "Club",
                "SummerSpend",
                "SummerIncome",
                "NetSpend"
            ]
        ]
        .sort_values(
            "SummerSpend",
            ascending=False
        )
        .head(10)
        .copy()
    )

    print(
        top_spenders.to_string(
            index=False,
            formatters={
                "SummerSpend": lambda x: f"€{x / 1e6:,.1f}m",
                "SummerIncome": lambda x: f"€{x / 1e6:,.1f}m",
                "NetSpend": lambda x: f"€{x / 1e6:,.1f}m"
            }
        )
    )

    # -------------------------
    # Highest transfer-income club-seasons
    # -------------------------

    print("\n" + "=" * 80)
    print("TOP 10 SUMMER TRANSFER INCOME CLUB-SEASONS")
    print("=" * 80)

    top_sellers = (
        transfer_data[
            [
                "Season",
                "Club",
                "SummerSpend",
                "SummerIncome",
                "NetSpend"
            ]
        ]
        .sort_values(
            "SummerIncome",
            ascending=False
        )
        .head(10)
        .copy()
    )

    print(
        top_sellers.to_string(
            index=False,
            formatters={
                "SummerSpend": lambda x: f"€{x / 1e6:,.1f}m",
                "SummerIncome": lambda x: f"€{x / 1e6:,.1f}m",
                "NetSpend": lambda x: f"€{x / 1e6:,.1f}m"
            }
        )
    )

def main():

    transfers = load_transfers()
    secondary_transfers = load_secondary_transfers()
    results = load_results()

    results["Season"] = results["Season"].apply(format_season)

    results = add_club_ids(results)

    summer_transfers = filter_summer_transfers(
        transfers
    )

    transfer_data = calculate_all_transfer_spending(
        results,
        summer_transfers,
        secondary_transfers
    )

    print_transfer_audit(
        transfer_data
    )


if __name__ == "__main__":
    main()