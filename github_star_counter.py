import os
import re
import sqlite3
import aiohttp
import asyncio
import argparse
from tqdm import tqdm
from dotenv import load_dotenv
from urllib.parse import urlparse
from collections import defaultdict
from aiolimiter import AsyncLimiter
from datetime import datetime, timedelta, timezone

# Load environment variables
load_dotenv()

async def fetch_url_content(session, url):
    # TODO: Could get blocked or bad response due to user agent (?)
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text()

async def extract_urls(session, file_path_or_url):
    if file_path_or_url.startswith(('http://', 'https://')):
        content = await fetch_url_content(session, file_path_or_url)
    else:
        with open(file_path_or_url, 'r', encoding='utf-8') as file:
            content = file.read()
    
    # Regex to match all URLs
    # Source: https://www.geeksforgeeks.org/python-check-url-string/
    pattern = r'(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:\'\".,<>?«»""'']))'
    return re.findall(pattern, content)

def is_github_repo_url(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    return (parsed_url.netloc == 'github.com' and 
            len(path_parts) >= 2 and 
            all(part for part in path_parts[:2]))

def get_repo_info(url):
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    return path_parts[0], path_parts[1]

def normalize_github_url(owner, repo):
    return f"{owner}/{repo}".lower()

def get_db_connection():
    db_path = 'github_stars.db'
    conn = sqlite3.connect(db_path)
    
    # Check if the table exists
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='star_cache'")
    table_exists = cursor.fetchone()
    
    if not table_exists:
        # Initialize the database if the table doesn't exist
        cursor.execute('''CREATE TABLE star_cache
                         (repo TEXT PRIMARY KEY, stars INTEGER, timestamp DATETIME, status INTEGER)''')
        conn.commit()
    
    return conn

def get_cached_stars(conn, repo):
    c = conn.cursor()
    c.execute("SELECT stars, timestamp, status FROM star_cache WHERE repo = ?", (repo,))
    result = c.fetchone()
    if result:
        stars, timestamp, status = result
        # cache is valid for 7 days from the original fetch date
        cached_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - cached_time < timedelta(days=7):
            return stars, status
    return None, None

def update_cache(conn, repo, stars, status):
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO star_cache (repo, stars, timestamp, status) VALUES (?, ?, datetime('now'), ?)",
              (repo, stars, status))
    conn.commit()

async def get_star_count(session, limiter, owner, repo, pbar, conn):
    normalized_repo = normalize_github_url(owner, repo)
    cached_stars, cached_status = get_cached_stars(conn, normalized_repo)
    
    if cached_stars is not None and cached_status is not None:
        pbar.update(1)
        if cached_status == 200:
            return owner, repo, cached_stars
        else:
            # Ignore repo, likely dead or kilt (typically 301/404)
            return owner, repo, None

    token = os.getenv('GITHUB_TOKEN')
    headers = {'Authorization': f'token {token}'} if token else {}
    
    url = f'https://api.github.com/repos/{owner}/{repo}'
    try:
        async with limiter:
            async with session.get(url, headers=headers, timeout=10) as response:
                status = response.status
                if status == 200:
                    data = await response.json()
                    stars = data['stargazers_count']
                else:
                    stars = None
                update_cache(conn, normalized_repo, stars, status)
                pbar.update(1)
                return owner, repo, stars
    except aiohttp.ClientError as e:
        print(f"\nError fetching data for {owner}/{repo}: {str(e)}")
        update_cache(conn, normalized_repo, None, 0)
        pbar.update(1)
        return owner, repo, None

async def process_file(file_path_or_url, session, limiter, conn):
    urls = await extract_urls(session, file_path_or_url)
    github_repos = [(get_repo_info(url[0])) for url in urls if is_github_repo_url(url[0])]
    
    unique_repos = set(normalize_github_url(owner, repo) for owner, repo in github_repos)
    print(f"Discovered {len(unique_repos)} Github links in {file_path_or_url}")
    
    star_counts = defaultdict(int)
    
    with tqdm(total=len(unique_repos), desc=f"Fetching Github star data") as pbar:
        tasks = [get_star_count(session, limiter, *repo.split('/'), pbar, conn) for repo in unique_repos]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in results:
        if isinstance(result, Exception):
            print(f"Error occurred: {str(result)}")
        else:
            owner, repo, stars = result
            if stars is not None:
                star_counts[f'{owner}/{repo}'] = stars
    
    return star_counts

def print_formatted_report(sorted_repos, top, output_file=None):
    result = []
    result.append(f"\nTop {top} GitHub repositories by star count:")
    result.append("\n{:<5} {:<50} {:<10} {:<60}".format("Rank", "Repository", "Stars", "URL"))
    result.append("-" * 125)
    
    for i, (repo, stars) in enumerate(sorted_repos[:top], 1):
        url = f"https://github.com/{repo}"
        result.append("{:<5} {:<50} {:<10,} {:<60}".format(f"{i}.", repo, stars, url))
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            for repo, stars in sorted_repos:
                url = f"https://github.com/{repo}"
                f.write(f"{url},{stars}\n")
        print(f"Full rankings written to -> {output_file}")
    
    print('\n'.join(result))

async def main(file_paths_or_urls, top, max_requests, time_period, output_file):
    limiter = AsyncLimiter(max_requests, time_period)
    conn = get_db_connection()

    all_star_counts = defaultdict(int)

    async with aiohttp.ClientSession() as session:
        for file_path_or_url in file_paths_or_urls:
            star_counts = await process_file(file_path_or_url, session, limiter, conn)
            for repo, stars in star_counts.items():
                all_star_counts[repo] += stars

    # Sort repositories by star count in descending order
    sorted_repos = sorted(all_star_counts.items(), key=lambda x: x[1], reverse=True)

    # Print top N repositories and optionally write full report to file
    print_formatted_report(sorted_repos, top, output_file)

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rank GitHub repositories mentioned in plaintext/markdown files by star count.")
    parser.add_argument("files", nargs="+", help="One or more plaintext/markdown file paths/URLs that contain Github repository links.")
    parser.add_argument("--top", type=int, default=20, help="Number of top repositories to display by stars (default: 20)")
    parser.add_argument("-o", "--output", help="File path to write the full ranking report")
    parser.add_argument("--max-requests", type=int, default=3, help="Maximum number of requests in the given time period (default: 3)")
    parser.add_argument("--time-period", type=float, default=1.0, help="Time period in seconds for rate limiting (default: 1.0)")

    args = parser.parse_args()

    try:
        asyncio.run(main(args.files, args.top, args.max_requests, args.time_period, args.output))
    except KeyboardInterrupt:
        print("Program interrupted by user")
    except Exception as e:
        print(f"An unexpected error occurred: {str(e)}")
