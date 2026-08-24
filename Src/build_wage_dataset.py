from pathlib import Path

import pandas as pd



WAGE_DATA_FOLDER = Path("data/raw/wages")

def format_wage_season(season_string):
    """
    Convert a filename season into our standard format.

    Example:
    2013-2014 -> 13/14
    2025-2026 -> 25/26
    """

    start_year, end_year = season_string.split("-")

    return f"{start_year[-2:]}/{end_year[-2:]}"

def build_all_wage_data():
    """
    Automatically find every player/squad wage CSV pair,
    process each season, and combine them into one dataset.
    """

    all_club_wages = []
    all_player_wages = []

    player_files = sorted(
        WAGE_DATA_FOLDER.glob("*_player_wages.csv")
    )

    if not player_files:
        raise FileNotFoundError(
            "No player wage CSV files found in data/raw/wages/"
        )

    for player_file in player_files:

        season_string = player_file.name.replace(
            "_player_wages.csv",
            ""
        )

        season = format_wage_season(
            season_string
        )

        squad_file = (
            WAGE_DATA_FOLDER
            / f"{season_string}_squad_wages.csv"
        )

        if not squad_file.exists():

            print(
                f"WARNING | {season} | "
                f"Squad wage file missing - skipping season"
            )

            continue

        print(f"Processing {season}...")

        # -------------------------
        # Player wages
        # -------------------------

        wages = pd.read_csv(
            player_file
        )

        wages = clean_wage_data(
            wages
        )

        wages.insert(
            0,
            "Season",
            season
        )

        all_player_wages.append(
            wages
        )

        # -------------------------
        # Squad wages
        # -------------------------

        squad_wages = pd.read_csv(
            squad_file
        )

        # -------------------------
        # Club summary
        # -------------------------

        club_wages = build_club_wage_summary(
            wages,
            squad_wages
        )

        club_wages.insert(
            0,
            "Season",
            season
        )

        all_club_wages.append(
            club_wages
        )

    if not all_club_wages:
        raise ValueError(
            "No complete player/squad wage file pairs were found."
        )

    club_wage_data = pd.concat(
        all_club_wages,
        ignore_index=True
    )

    player_wage_data = pd.concat(
        all_player_wages,
        ignore_index=True
    )

    return club_wage_data, player_wage_data

def load_player_wages():
    """
    Load the raw FBref player wage data for 2013/14.
    """

    wages = pd.read_csv(PLAYER_WAGES_PATH)

    return wages

def clean_wage_data(wages):
    """
    Clean FBref player wage data and extract numeric GBP wages.
    """

    wages = wages.copy()

    # Extract the GBP amount from the wage strings
    wages["WeeklyWageGBP"] = (
        wages["Weekly Wages"]
        .str.extract(r"£\s*([\d,]+)")[0]
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    wages["AnnualWageGBP"] = (
        wages["Annual Wages"]
        .str.extract(r"£\s*([\d,]+)")[0]
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    return wages

def load_squad_wages():
    """
    Load the raw FBref squad wage data for 2013/14.
    """

    squad_wages = pd.read_csv(SQUAD_WAGES_PATH)

    return squad_wages

def validate_player_vs_squad_wages(wages, squad_wages):
    """
    Compare wages calculated from individual player records
    against FBref's published squad wage totals.
    """

    squad_wages = squad_wages.copy()

    # Extract GBP values from FBref squad wage strings
    squad_wages["PublishedWeeklyWageGBP"] = (
        squad_wages["Weekly Wages"]
        .str.extract(r"£\s*([\d,]+)")[0]
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    squad_wages["PublishedAnnualWageGBP"] = (
        squad_wages["Annual Wages"]
        .str.extract(r"£\s*([\d,]+)")[0]
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    # Calculate totals from individual player records
    calculated = (
        wages
        .groupby("Squad")
        .agg(
            PlayerRecords=("Player", "count"),
            CalculatedAnnualWageGBP=("AnnualWageGBP", "sum")
        )
        .reset_index()
    )

    # Merge with FBref squad totals
    comparison = squad_wages[
        [
            "Squad",
            "# Pl",
            "PublishedAnnualWageGBP",
            "% Estimated"
        ]
    ].merge(
        calculated,
        on="Squad",
        how="left"
    )

    comparison = comparison.rename(
        columns={"# Pl": "PublishedPlayers"}
    )

    # Difference in player coverage
    comparison["MissingPlayerRecords"] = (
        comparison["PublishedPlayers"]
        - comparison["PlayerRecords"]
    )

    # Difference in wage totals
    comparison["WageDifferenceGBP"] = (
        comparison["PublishedAnnualWageGBP"]
        - comparison["CalculatedAnnualWageGBP"]
    )

    comparison["PlayerWageCoveragePct"] = (
        comparison["CalculatedAnnualWageGBP"]
        / comparison["PublishedAnnualWageGBP"]
        * 100
    )

    return comparison

def build_club_wage_summary(wages, squad_wages):
    """
    Build club-level wage features using:

    - FBref Squad Wages as the published total wage bill
    - Player Wages for individual wage-distribution features
    - The difference between the two as a reconciliation measure

    Also creates data-quality flags for club-seasons where
    player-level wage coverage looks unusually low/high or
    the reconciliation difference is large.
    """

    squad_wages = squad_wages.copy()

    # --------------------------------------------------
    # Clean published squad wage data
    # --------------------------------------------------

    squad_wages["TotalWageBill"] = (
        squad_wages["Annual Wages"]
        .str.extract(r"£\s*([\d,]+)")[0]
        .str.replace(",", "", regex=False)
        .astype(float)
    )

    squad_wages["PublishedPlayers"] = pd.to_numeric(
        squad_wages["# Pl"],
        errors="coerce"
    )

    # --------------------------------------------------
    # Build player-level wage statistics
    # --------------------------------------------------

    player_summary = (
        wages
        .groupby("Squad")
        .agg(
            KnownPlayerWageRecords=(
                "Player",
                "count"
            ),

            KnownPlayerWages=(
                "AnnualWageGBP",
                "sum"
            ),

            MeanKnownAnnualWage=(
                "AnnualWageGBP",
                "mean"
            ),

            MedianKnownAnnualWage=(
                "AnnualWageGBP",
                "median"
            ),

            HighestKnownAnnualWage=(
                "AnnualWageGBP",
                "max"
            ),

            LowestKnownAnnualWage=(
                "AnnualWageGBP",
                "min"
            ),

            WageStdDev=(
                "AnnualWageGBP",
                "std"
            )
        )
        .reset_index()
    )

    # --------------------------------------------------
    # Top-five wage calculations
    # --------------------------------------------------

    top_five = (
        wages
        .sort_values(
            ["Squad", "AnnualWageGBP"],
            ascending=[True, False]
        )
        .groupby("Squad")
        .head(5)
        .groupby("Squad")["AnnualWageGBP"]
        .sum()
        .reset_index(
            name="Top5KnownWages"
        )
    )

    player_summary = player_summary.merge(
        top_five,
        on="Squad",
        how="left"
    )

    # --------------------------------------------------
    # Merge squad and player-level information
    # --------------------------------------------------

    summary = squad_wages[
        [
            "Squad",
            "PublishedPlayers",
            "TotalWageBill",
            "% Estimated"
        ]
    ].merge(
        player_summary,
        on="Squad",
        how="left"
    )

    # --------------------------------------------------
    # Coverage and reconciliation
    # --------------------------------------------------

    summary["PlayerRecordDifference"] = (
        summary["PublishedPlayers"]
        - summary["KnownPlayerWageRecords"]
    )

    summary["KnownWageCoveragePct"] = (
        summary["KnownPlayerWages"]
        / summary["TotalWageBill"]
        * 100
    )

    summary["WageReconciliationDifference"] = (
        summary["TotalWageBill"]
        - summary["KnownPlayerWages"]
    )

    # --------------------------------------------------
    # Optional diagnostic:
    # implied average wage of unlisted records
    #
    # Do NOT treat this as a model feature.
    # It is only useful as a data-quality diagnostic.
    # --------------------------------------------------

    valid_implied_estimate = (
        (summary["PlayerRecordDifference"] > 0)
        &
        (summary["WageReconciliationDifference"] > 0)
    )

    summary["ImpliedUnlistedAnnualWage"] = float("nan")

    summary.loc[
        valid_implied_estimate,
        "ImpliedUnlistedAnnualWage"
    ] = (
        summary.loc[
            valid_implied_estimate,
            "WageReconciliationDifference"
        ]
        /
        summary.loc[
            valid_implied_estimate,
            "PlayerRecordDifference"
        ]
    )

    summary["ImpliedUnlistedWeeklyWage"] = (
        summary["ImpliedUnlistedAnnualWage"]
        / 52
    )

    # --------------------------------------------------
    # Wage-distribution features
    # --------------------------------------------------

    summary["HighestToMedianWageRatio"] = (
        summary["HighestKnownAnnualWage"]
        / summary["MedianKnownAnnualWage"]
    )

    summary["Top5KnownWageShare"] = (
        summary["Top5KnownWages"]
        / summary["KnownPlayerWages"]
    )

    summary["ObservedWageRange"] = (
        summary["HighestKnownAnnualWage"]
        - summary["LowestKnownAnnualWage"]
    )

    # --------------------------------------------------
    # Data-quality flags
    # --------------------------------------------------

    summary["LowCoverageFlag"] = (
        summary["KnownWageCoveragePct"] < 85
    )

    summary["HighCoverageFlag"] = (
        summary["KnownWageCoveragePct"] > 105
    )

    summary["LargeReconciliationFlag"] = (
        (
            summary["WageReconciliationDifference"].abs()
            / summary["TotalWageBill"]
        ) > 0.15
    )

    summary["WageDataFlag"] = (
        summary[
            [
                "LowCoverageFlag",
                "HighCoverageFlag",
                "LargeReconciliationFlag"
            ]
        ]
        .any(axis=1)
    )

    return summary

def print_wage_audit(club_wages):
    """
    Print a concise audit of the complete
    Premier League wage dataset.
    """

    print("\n" + "=" * 95)
    print("PREMIER LEAGUE WAGE DATASET AUDIT")
    print("=" * 95)

    # ==================================================
    # Overall summary
    # ==================================================

    club_seasons = len(
        club_wages
    )

    seasons = club_wages[
        "Season"
    ].nunique()

    clubs = club_wages[
        "Squad"
    ].nunique()

    average_coverage = club_wages[
        "KnownWageCoveragePct"
    ].mean()

    lowest_coverage = club_wages[
        "KnownWageCoveragePct"
    ].min()

    highest_coverage = club_wages[
        "KnownWageCoveragePct"
    ].max()

    flagged_count = int(
        club_wages["WageDataFlag"].sum()
    )

    low_flags = int(
        club_wages["LowCoverageFlag"].sum()
    )

    high_flags = int(
        club_wages["HighCoverageFlag"].sum()
    )

    recon_flags = int(
        club_wages[
            "LargeReconciliationFlag"
        ].sum()
    )

    print(
        f"\nClub-seasons processed:       {club_seasons}"
    )

    print(
        f"Seasons processed:            {seasons}"
    )

    print(
        f"Unique clubs:                 {clubs}"
    )

    print(
        f"\nAverage wage coverage:        "
        f"{average_coverage:.1f}%"
    )

    print(
        f"Lowest wage coverage:         "
        f"{lowest_coverage:.1f}%"
    )

    print(
        f"Highest wage coverage:        "
        f"{highest_coverage:.1f}%"
    )

    print(
        f"\nFlagged club-seasons:         "
        f"{flagged_count}"
    )

    print(
        f"Low coverage flags:           "
        f"{low_flags}"
    )

    print(
        f"High coverage flags:          "
        f"{high_flags}"
    )

    print(
        f"Large reconciliation flags:   "
        f"{recon_flags}"
    )

    # ==================================================
    # Quality by season
    # ==================================================

    print("\n" + "=" * 95)
    print("DATA QUALITY BY SEASON")
    print("=" * 95)

    quality_by_season = (
        club_wages
        .groupby("Season")
        .agg(
            Clubs=(
                "Squad",
                "count"
            ),

            AvgCoverage=(
                "KnownWageCoveragePct",
                "mean"
            ),

            LowestCoverage=(
                "KnownWageCoveragePct",
                "min"
            ),

            Flagged=(
                "WageDataFlag",
                "sum"
            ),

            LowCov=(
                "LowCoverageFlag",
                "sum"
            ),

            HighCov=(
                "HighCoverageFlag",
                "sum"
            ),

            LargeRecon=(
                "LargeReconciliationFlag",
                "sum"
            )
        )
        .reset_index()
    )

    print(
        quality_by_season
        .to_string(
            index=False,
            formatters={
                "AvgCoverage":
                    lambda x: f"{x:.1f}%",

                "LowestCoverage":
                    lambda x: f"{x:.1f}%"
            }
        )
    )

    # ==================================================
    # Flagged club-seasons
    # ==================================================

    print("\n" + "=" * 95)
    print("CLUB-SEASONS REQUIRING REVIEW")
    print("=" * 95)

    flagged = club_wages[
        club_wages["WageDataFlag"]
    ].copy()

    if flagged.empty:

        print(
            "\nNo club-seasons require review."
        )

    else:

        def create_flag_label(row):

            labels = []

            if row["LowCoverageFlag"]:
                labels.append("LOW")

            if row["HighCoverageFlag"]:
                labels.append("HIGH")

            if row[
                "LargeReconciliationFlag"
            ]:
                labels.append("RECON")

            return " + ".join(labels)

        flagged["Flags"] = flagged.apply(
            create_flag_label,
            axis=1
        )

        flagged_display = flagged[
            [
                "Season",
                "Squad",
                "KnownWageCoveragePct",
                "WageReconciliationDifference",
                "PlayerRecordDifference",
                "Flags"
            ]
        ].copy()

        flagged_display = (
            flagged_display
            .sort_values(
                [
                    "Season",
                    "KnownWageCoveragePct"
                ]
            )
        )

        print(
            flagged_display
            .to_string(
                index=False,
                formatters={
                    "KnownWageCoveragePct":
                        lambda x: f"{x:.1f}%",

                    "WageReconciliationDifference":
                        lambda x: (
                            f"£{x / 1_000_000:+.1f}m"
                        )
                }
            )
        )

    # ==================================================
    # Top wage bills
    # ==================================================

    print("\n" + "=" * 95)
    print("TOP 10 CLUB-SEASON WAGE BILLS")
    print("=" * 95)

    top_wage_bills = (
        club_wages[
            [
                "Season",
                "Squad",
                "TotalWageBill",
                "HighestKnownAnnualWage",
                "MedianKnownAnnualWage"
            ]
        ]
        .sort_values(
            "TotalWageBill",
            ascending=False
        )
        .head(10)
        .copy()
    )

    print(
        top_wage_bills
        .to_string(
            index=False,
            formatters={
                "TotalWageBill":
                    lambda x: (
                        f"£{x / 1_000_000:.1f}m"
                    ),

                "HighestKnownAnnualWage":
                    lambda x: (
                        f"£{x / 1_000_000:.2f}m"
                    ),

                "MedianKnownAnnualWage":
                    lambda x: (
                        f"£{x / 1_000_000:.2f}m"
                    )
            }
        )
    )

    # ==================================================
    # Wage disparity
    # ==================================================

    print("\n" + "=" * 95)
    print("TOP 10 WAGE DISPARITY CLUB-SEASONS")
    print("=" * 95)

    disparity = (
        club_wages[
            [
                "Season",
                "Squad",
                "HighestToMedianWageRatio",
                "Top5KnownWageShare",
                "KnownWageCoveragePct"
            ]
        ]
        .sort_values(
            "HighestToMedianWageRatio",
            ascending=False
        )
        .head(10)
        .copy()
    )

    print(
        disparity
        .to_string(
            index=False,
            formatters={
                "HighestToMedianWageRatio":
                    lambda x: f"{x:.2f}x",

                "Top5KnownWageShare":
                    lambda x: f"{x * 100:.1f}%",

                "KnownWageCoveragePct":
                    lambda x: f"{x:.1f}%"
            }
        )
    )


def main():

    # --------------------------------------------------
    # Build datasets
    # --------------------------------------------------

    club_wages, player_wages = (
        build_all_wage_data()
    )

    # --------------------------------------------------
    # Audit
    # --------------------------------------------------

    print_wage_audit(
        club_wages
    )

    # --------------------------------------------------
    # Save processed data
    # --------------------------------------------------

    output_folder = Path(
        "data/processed"
    )

    output_folder.mkdir(
        parents=True,
        exist_ok=True
    )

    club_output = (
        output_folder
        / "club_season_wages.csv"
    )

    player_output = (
        output_folder
        / "player_season_wages.csv"
    )

    club_wages.to_csv(
        club_output,
        index=False
    )

    player_wages.to_csv(
        player_output,
        index=False
    )

    print(
        f"\nSaved club wage dataset to: "
        f"{club_output}"
    )

    print(
        f"Saved player wage dataset to: "
        f"{player_output}"
    )


if __name__ == "__main__":
    main()