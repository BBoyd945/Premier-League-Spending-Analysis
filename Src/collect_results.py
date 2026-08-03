"""Download historical Premier League match results.

Data source:
https://www.football-data.co.uk/

Each downloaded CSV contains match-level results for one Premier League
season. The raw files are saved unchanged so the data collection process
remains reproducible.
"""

from pathlib import Path
import time

import requests


BASE_URL = "https://www.football-data.co.uk/mmz4281"
OUTPUT_DIRECTORY = Path("data/raw/results")

# Football-Data uses compact season codes:
# 2023/24 -> 2324
SEASONS = [
    "0506",
    "0607",
    "0708",
    "0809",
    "0910",
    "1011",
    "1112",
    "1213",
    "1314",
    "1415",
    "1516",
    "1617",
    "1718",
    "1819",
    "1920",
    "2021",
    "2122",
    "2223",
    "2324",
    "2425",
    "2526",
]


def download_season(
    season_code: str,
    session: requests.Session,
) -> Path:
    """Download one Premier League season as a CSV file."""

    url = f"{BASE_URL}/{season_code}/E0.csv"
    output_path = OUTPUT_DIRECTORY / f"premier_league_{season_code}.csv"

    response = session.get(url, timeout=30)
    response.raise_for_status()

    # Avoid saving an HTML error page under a .csv filename.
    content_type = response.headers.get("Content-Type", "").lower()
    if "html" in content_type:
        raise ValueError(
            f"Expected CSV data for {season_code}, "
            f"but received HTML from {url}."
        )

    output_path.write_bytes(response.content)
    return output_path


def main() -> None:
    """Download all configured seasons."""

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        session.headers.update(
            {
                "User-Agent": (
                    "Premier-League-Spending-Analysis/1.0 "
                    "(educational data project)"
                )
            }
        )

        for season_code in SEASONS:
            try:
                saved_path = download_season(season_code, session)
                print(f"Downloaded {season_code}: {saved_path}")
            except (requests.RequestException, ValueError) as error:
                print(f"Failed to download {season_code}: {error}")

            # Small pause to avoid making rapid consecutive requests.
            time.sleep(1)


if __name__ == "__main__":
    main()