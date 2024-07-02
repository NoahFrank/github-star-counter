# GitHub Star Counter
GitHub Star Counter is a CLI tool that analyzes plaintext/markdown files for GitHub repository links and creates a report ranking them by star count.

## Table of Contents
- [Installation](#installation)
- [Usage](#usage)
- [FAQ](#faq)

## Installation
### Prerequisites
- Github Access Token
  - ([link](https://github.com/settings/tokens?type=beta)) Github -> top right Account -> Settings -> Developer settings -> Personal access tokens -> Fine-grained tokens -> Generate new token
  - Use the "Public Repositories (read-only)" scope
- Python 3.10 or higher (Tested on Python 3.12.4)
- pip

### Steps
1. Clone the repository:
    ```bash
    git clone https://github.com/NoahFrank/github-star-counter
    cd github-star-counter
    ```
2. Create a virtual environment:
    - `python -m venv venv`
3. Activate the virtual environment:
- On Windows:
  ```
  venv\Scripts\activate
  ```
- On MacOS and Linux:
  ```
  source venv/bin/activate
  ```
4. Install the required packages:
    - `pip install -r requirements.txt`
5. Set up your GitHub token:
    - Create `.env` file in the project root and add your GitHub token
    - `GITHUB_TOKEN=your_github_token_here`
    - Or simply set the `GITHUB_TOKEN` env var before running the python script

## Usage
```
usage: github_star_counter.py [-h] [--top TOP] [-o OUTPUT] [--max-requests MAX_REQUESTS] [--time-period TIME_PERIOD] files [files ...]

Rank GitHub repositories mentioned in plaintext/markdown files by star count.

positional arguments:
  files                 One or more plaintext/markdown file paths/URLs that contain Github repository links.

options:
  -h, --help            show this help message and exit
  --top TOP             Number of top repositories to display by stars (default: 20)
  -o OUTPUT, --output OUTPUT
                        File path to write the full ranking report
  --max-requests MAX_REQUESTS
                        Maximum number of requests in the given time period (default: 3)
  --time-period TIME_PERIOD
                        Time period in seconds for rate limiting (default: 1.0)
```

### Examples
1. Analyze a single file named `README.md` and display the top 10 repositories:
    - `python github_star_counter.py --top 10 README.md`
1. Analyze a single remote URL file and dispaly the default top 20 repositories:
    - `python github_star_counter.py https://raw.githubusercontent.com/markets/awesome-ruby/master/README.md`
1. Analyze multiple files and display the default top 20 repositories:
    - `python github_star_counter.py file1.md file2.md file3.md`
1. Analyze files with custom rate limiting (5 requests every 2 seconds):
    - `python github_star_counter.py --max-requests 5 --time-period 2 file1.md file2.md`
1. Analyze files and write the full report to an output file (in CSV format):
    - `python github_star_counter.py -o full_report.csv file1.md file2.md`

### Output File
You can use the `-o` or `--output` option to specify a file path where the full report will be written in CSV format. This report will include all repositories found, not just the top N displayed in the console output. Each line in the output file will contain a repository name and its star count, separated by a comma.

Example:
`python github_star_counter.py -o full_report.txt --top 10 README.md`

This command will display the top 10 repositories in the console and write the full report to `full_report.txt`.

### Rate Limiting
The `--max-requests` and `--time-period` options allow you to control the rate at which the script makes requests to the GitHub API:

- `--max-requests`: This sets the maximum number of requests that can be made in a given time period. Default is 3.
- `--time-period`: This sets the time period (in seconds) for the rate limiting. Default is 1.0 second.

For example, `--max-requests 5 --time-period 2` would allow a maximum of 5 requests every 2 seconds.

### Example Output
```md
Top 15 GitHub repositories by star count:

Rank  Repository                                         Stars      URL
-----------------------------------------------------------------------------------------------------------------------------
1.    sindresorhus/awesome                               309,205    https://github.com/sindresorhus/awesome
2.    rails/rails                                        55,266     https://github.com/rails/rails
3.    cantino/huginn                                     42,207     https://github.com/cantino/huginn
4.    discourse/discourse                                41,078     https://github.com/discourse/discourse
5.    homebrew/brew                                      40,073     https://github.com/homebrew/brew
6.    fastlane/fastlane                                  38,822     https://github.com/fastlane/fastlane
7.    rapid7/metasploit-framework                        33,238     https://github.com/rapid7/metasploit-framework
8.    seleniumhq/selenium                                29,742     https://github.com/seleniumhq/selenium
9.    heartcombo/devise                                  23,826     https://github.com/heartcombo/devise
10.   caskroom/homebrew-cask                             20,679     https://github.com/caskroom/homebrew-cask
11.   bbatsov/ruby-style-guide                           16,409     https://github.com/bbatsov/ruby-style-guide
12.   sstephenson/rbenv                                  15,925     https://github.com/sstephenson/rbenv
13.   cocoapods/cocoapods                                14,477     https://github.com/cocoapods/cocoapods
14.   atech/postal                                       14,381     https://github.com/atech/postal
15.   elastic/logstash                                   14,086     https://github.com/elastic/logstash
```

## FAQ
### Q: How long does the sqlite3 database cache the stars for a given repositroy?
For 7 days after the original star data was fetched.

### Q: What's the difference between the console output and the output file?
A: The console output shows only the top N repositories (as specified by the --top option), while the output file (if specified using -o or --output) contains all repositories found, regardless of the --top value.

### Q: How do I use the rate limiting options?
A: You can adjust the rate limiting by using the `--max-requests` and `--time-period` options. For example, to set a limit of 5 requests every 2 seconds, you would run:

`python github_star_counter.py --max-requests 5 --time-period 2 your_file.md`

### Q: Why do I need a GitHub token?
A: GitHub API has rate limits for unauthenticated requests. Using a token increases the rate limit and allows the script to fetch data for more repositories in a smaller amount of time.

### Q: I'm getting a "RateLimitExceeded" error. What should I do?
A: Ensure you've set up your GitHub token correctly in the `.env` file. If the error persists, you may need to wait for your rate limit to reset (usually 1 hour).

### Q: The script is running slowly. Can I speed it up?
A: The script uses caching in an sqlite3 db locally to improve performance. Subsequent runs will be faster. You can also try reducing the number of files processed at once.
