# Teaching_Job_Scanner

### Unified Higher-Ed SME & Cyber Job Scanner

A high-performance, asynchronous Python CLI tool designed to aggregate and discover remote **Subject Matter Expert (SME) contracts**, **Curriculum Author roles**, **Evaluator gigs**, and **Cybersecurity positions** from major university job portals (WGU, UMGC, Full Sail) and HigherEdJobs.

![Terminal UI Preview](https://img.shields.io/badge/UI-Rich_Terminal-magenta)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)

---

## Key Features

* **Dual Engine Aggregation:** Simultaneously queries Workday Job Portals (JSON API) and parses HigherEdJobs HTML search results.
* **TLS / Cloudflare Bypass:** Leverages `curl_cffi` browser impersonation (`chrome120`) to bypass anti-bot and Cloudflare checks without needing headless browsers.
* **Concurrent Execution:** Utilizes `concurrent.futures.ThreadPoolExecutor` to execute multi-keyword queries concurrently across multiple universities in seconds.
* **Smart Filtering:** Categorizes and filters positions based on work flexibility (Contract, Part-Time, Contingent, Temporary) and remote status.
* **Rich Terminal UI:** Displays real-time discovery results in a formatted, color-coded terminal table powered by `rich`.
* **Automated Export:** Cleans markup tags and exports discovered roles directly to `all_highered_jobs.csv` and `all_highered_jobs.json`.

---

## Target Platforms & Keywords

### Platforms
* **Workday Portals:** Western Governors University (WGU), University of Maryland Global Campus (UMGC), Full Sail University.
* **Aggregators:** HigherEdJobs Advanced Search (Cybersecurity & Remote filter preset).

### Role Target Keywords
* Subject Matter Expert (SME)
* Course Developer / Lab Author
* Curriculum Designer / Instructional Designer
* Evaluator / Grader / Assessment Specialist

---

## Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/your-username/highered-sme-scanner.git](https://github.com/your-username/highered-sme-scanner.git)
cd highered-sme-scanner
