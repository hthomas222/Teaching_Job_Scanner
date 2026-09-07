import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from curl_cffi import requests
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# TARGET CONFIGURATIONS
# ---------------------------------------------------------------------------

HIGHERED_URL = (
    "https://www.higheredjobs.com/search/advanced_action.cfm?"
    "JobCat=159&JobCat=160&JobCat=162&JobCat=31&JobCat=144&JobCat=210&"
    "JobCat=102&JobCat=290&PosType=2&InstType=1&InstType=2&InstType=3&"
    "Keyword=CYBER&Remote=2&Submit=Search+Jobs"
)

TARGET_WORKDAY_SCHOOLS = [
    {
        "name": "WGU",
        "url": "https://wgu.wd5.myworkdayjobs.com/wday/cxs/wgu/External/jobs",
        "base_link": "https://wgu.wd5.myworkdayjobs.com/External",
    },
    {
        "name": "UMGC",
        "url": "https://umgc.wd1.myworkdayjobs.com/wday/cxs/umgc/UMGC_Careers/jobs",
        "base_link": "https://umgc.wd1.myworkdayjobs.com/en-US/UMGC_Careers",
    },
    {
        "name": "Full Sail",
        "url": "https://fullsail.wd1.myworkdayjobs.com/wday/cxs/fullsail/External/jobs",
        "base_link": "https://fullsail.wd1.myworkdayjobs.com/en-US/External",
    },
]

SME_KEYWORDS = [
    "Subject Matter Expert",
    "SME",
    "Course Developer",
    "Curriculum",
    "Lab Author",
    "Instructional Designer",
    "Evaluator",
    "Grader",
]

FLEX_TERMS = ["part time", "part-time", "contract", "contingent", "temporary", "adjunct"]
SME_TERMS = ["sme", "subject matter", "developer", "curriculum", "author", "designer"]
EVAL_TERMS = ["evaluator", "grader", "assessment"]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# ---------------------------------------------------------------------------
# HIGHEREDJOBS SCRAPER
# ---------------------------------------------------------------------------

def fetch_highered_jobs():
    """Scrapes job records from HigherEdJobs advanced search."""
    matches = []
    try:
        res = requests.get(
            HIGHERED_URL,
            headers=HEADERS,
            impersonate="chrome120",
            timeout=10,
        )
        if res.status_code != 200:
            return matches

        soup = BeautifulSoup(res.text, "html.parser")
        job_records = soup.find_all("div", class_="record")
        if not job_records:
            job_records = soup.select(".js-job-record, .row.record-row")

        for record in job_records:
            title_tag = record.find("a", href=True)
            if not title_tag:
                continue

            title = title_tag.get_text(strip=True)
            href = title_tag["href"]
            link = f"https://www.higheredjobs.com/search/{href}" if not href.startswith("http") else href

            inst_tag = record.find("span", class_="record-inst") or record.find("div", class_="facility")
            institution = inst_tag.get_text(strip=True) if inst_tag else "HigherEdJobs"

            loc_tag = record.find("span", class_="record-location") or record.find("div", class_="location")
            location = loc_tag.get_text(strip=True) if loc_tag else "Remote"

            date_tag = record.find("span", class_="record-date") or record.find("div", class_="date")
            posted = date_tag.get_text(strip=True) if date_tag else "Recently"

            # Categorize role
            title_lower = title.lower()
            is_sme = any(term in title_lower for term in SME_TERMS)
            role_type = (
                "[bold cyan]SME Contract[/bold cyan]"
                if is_sme
                else "[bold green]HigherEd Job[/bold green]"
            )

            matches.append({
                "school": institution[:12],  # truncate for formatting
                "type": role_type,
                "title": title,
                "location": location,
                "posted": posted,
                "url": link,
            })
    except Exception:
        pass
    return matches

# ---------------------------------------------------------------------------
# WORKDAY SCRAPER (PARALLEL)
# ---------------------------------------------------------------------------

def fetch_workday_jobs(school, search_text="", limit=50):
    """Query Workday API for target universities."""
    headers = {
        "User-Agent": HEADERS["User-Agent"],
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": school["url"].split("/wday")[0],
        "Referer": school["base_link"],
    }
    payload = {
        "appliedFacets": {},
        "limit": limit,
        "offset": 0,
        "searchText": search_text,
    }
    try:
        res = requests.post(
            school["url"],
            json=payload,
            headers=headers,
            impersonate="chrome120",
            timeout=10,
        )
        if res.status_code == 200:
            return res.json()
        return None
    except Exception:
        return None

def workday_worker(school, kw):
    """Worker task processing Workday API payloads."""
    matches = []
    data = fetch_workday_jobs(school, search_text=kw)
    if not data or "jobPostings" not in data:
        return matches

    for job in data.get("jobPostings", []):
        title = job.get("title", "")
        bullet_fields = job.get("bulletFields", [])
        location = job.get("locationDescriptor", "")
        external_path = job.get("externalPath", "")

        metadata_str = " ".join(bullet_fields).lower()
        title_lower = title.lower()

        is_flexible_work = any(term in metadata_str or term in title_lower for term in FLEX_TERMS)
        is_remote = "remote" in location.lower() or "remote" in title_lower
        is_sme = any(term in title_lower for term in SME_TERMS)
        is_eval = any(term in title_lower for term in EVAL_TERMS)

        if is_remote and is_flexible_work and (is_sme or is_eval):
            job_url = f"{school['base_link']}{external_path}"
            role_type = (
                "[bold cyan]SME Contract[/bold cyan]"
                if is_sme
                else "[bold green]Evaluator Gig[/bold green]"
            )

            matches.append({
                "school": school["name"],
                "type": role_type,
                "title": title,
                "location": location,
                "posted": job.get("postedOn", "Recently"),
                "url": job_url,
            })
    return matches

# ---------------------------------------------------------------------------
# MAIN DISCOVERY ENGINE & EXPORT
# ---------------------------------------------------------------------------

def scan_all_roles():
    """Concurrently scans HigherEdJobs and Workday Portals."""
    discovered = {}

    with console.status(
        "[bold cyan]Scanning Workday Portals & HigherEdJobs...",
        spinner="dots",
    ):
        tasks = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            # Task 1: HigherEdJobs
            tasks.append(executor.submit(fetch_highered_jobs))

            # Task 2..N: Workday Portals
            for school in TARGET_WORKDAY_SCHOOLS:
                for kw in SME_KEYWORDS:
                    tasks.append(executor.submit(workday_worker, school, kw))

            for future in as_completed(tasks):
                results = future.result()
                for item in results:
                    discovered[item["url"]] = item

    return list(discovered.values())

def render_ui(jobs):
    """Renders formatted Rich UI."""
    console.clear()
    banner = Panel.fit(
        "[bold magenta]Unified Higher-Ed SME & Cyber Job Scanner[/bold magenta]\n"
        "[dim]Aggregating Workday Portals (WGU, UMGC, Full Sail) & HigherEdJobs[/dim]",
        border_style="bright_blue",
    )
    console.print(banner)
    console.print()

    if not jobs:
        console.print(
            Panel(
                "[yellow]No active SME or Evaluator openings found across target platforms right now.[/yellow]",
                border_style="yellow",
            )
        )
        return

    table = Table(
        title=f"Open Positions Discovered ({len(jobs)})",
        header_style="bold green",
        border_style="bright_black",
        expand=True,
    )

    table.add_column("Institution", style="bold magenta", width=14)
    table.add_column("Role Class", style="bold white", width=16)
    table.add_column("Position Title", style="bold white", ratio=2)
    table.add_column("Location", style="yellow", ratio=1)
    table.add_column("Posted", style="dim green", width=12)
    table.add_column("Apply Link", style="blue underline", ratio=2)

    for item in jobs:
        table.add_row(
            item["school"],
            item["type"],
            item["title"],
            item["location"],
            item["posted"],
            item["url"],
        )

    console.print(table)

def export_data(jobs):
    """Exports findings to CSV and JSON."""
    if not jobs:
        return

    cleaned = []
    for j in jobs:
        item = j.copy()
        # Remove rich formatting tags for CSV/JSON outputs
        item["type"] = item["type"].replace("[bold cyan]", "").replace("[/bold cyan]", "").replace("[bold green]", "").replace("[/bold green]", "")
        cleaned.append(item)

    with open("all_highered_jobs.json", "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)

    pd.DataFrame(cleaned).to_csv("all_highered_jobs.csv", index=False)
    console.print(
        "\n[dim]Saved unified results to [bold white]all_highered_jobs.csv[/bold white] and [bold white]all_highered_jobs.json[/bold white][/dim]"
    )

if __name__ == "__main__":
    results = scan_all_roles()
    render_ui(results)
    export_data(results)
