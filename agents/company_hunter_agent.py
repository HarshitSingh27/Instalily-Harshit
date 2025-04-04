"""
EventWebsiteScraper: Automatically Discover Companies from B2B Event Websites

What it does:
- Loads high-value event leads from `latest_leads.csv`
- Visits each event website and scans for subpages like “exhibitors”, “sponsors”, “directory”, etc.
- Parses those subpages (or main page if fallback needed) to extract company names using simple heuristics
- Merges scraped data with known static mappings (e.g., hardcoded list for ISA Sign Expo)
- Outputs a list of discovered companies with associated event and timestamp

Why it matters:
This scraper helps us discover real exhibitors and potential B2B leads from signage and print expos—critical input for enrichment, scoring, and outreach.

Used in: `company_hunter_agent.py` as the second step after event identification.

Output: `data/discovered_companies.csv` with:
    - company_name
    - event_name
    - event_relevance_score
    - date_updated

Usage:
scraper = EventWebsiteScraper()
scraper.run()
"""

import pandas as pd
import requests
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

class EventWebsiteScraper:
    """
    Reads events from latest_leads.csv, goes to their websites,
    searches for companies attending these events, and saves them in discovered_companies.csv.

    Output columns:
      - company_name
      - event_name
      - event_relevance_score
      - date_updated
    """

    def __init__(self, leads_csv="data/latest_leads.csv", output_csv="data/discovered_companies.csv"):
        self.leads_csv = leads_csv
        self.output_csv = output_csv
        self.events = []
        self.discovered = []
        # Keywords that might indicate a page listing companies
        self.possible_company_link_keywords = [
            "exhibitor", "sponsor", "attendee",
            "member", "directory", "supplier", "partner", "company"
        ]

    def load_events(self):
        # Load your events from latest_leads.csv
        df = pd.read_csv(self.leads_csv)
        # Optional: Only select high-priority events
        # df = df[df["priority"] == "High"]

        self.events = df.to_dict(orient="records")
        print(f"Loaded {len(self.events)} events from {self.leads_csv}")

    def scrape_event_companies(self, event):
        """
        Attempt to find sub-pages (like 'exhibitor' or 'sponsor' links) then parse companies.
        """
        event_name = event.get("name", "")
        event_score = event.get("relevance_score", "")
        event_url = event.get("url", "")

        print(f"\n🔎 Searching for companies on event: {event_name} | Score: {event_score}\nURL: {event_url}")

        try:
            resp = requests.get(event_url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
        except Exception as e:
            print(f"❌ Could not load {event_url}: {e}")
            return []

        # 1. Attempt to find direct sub-pages that might list companies
        potential_links = []
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"].lower()
            # Check if any link keywords appear in the href
            if any(kw in href for kw in self.possible_company_link_keywords):
                full_link = urljoin(event_url, a_tag["href"])
                potential_links.append(full_link)

        potential_links = list(set(potential_links))  # Deduplicate
        if not potential_links:
            print(f"⚠️ No sub-pages found for event: {event_name}")
            # Fallback: try to parse the main page itself for potential company names
            return self.parse_companies_from_page(soup, event_name, event_score)

        # 2. For each sub-page, parse companies
        discovered_companies = []
        for link in potential_links:
            print(f"🔗 Checking link: {link}")
            try:
                sub_resp = requests.get(link, timeout=15)
                sub_resp.raise_for_status()
                sub_soup = BeautifulSoup(sub_resp.text, "html.parser")
                found = self.parse_companies_from_page(sub_soup, event_name, event_score)
                discovered_companies.extend(found)
            except Exception as e:
                print(f"❌ Could not load {link}: {e}")

        return discovered_companies

    def parse_companies_from_page(self, soup, event_name, event_score):
        """
        A naive approach: gather text from <li>, <div>, <span>, <a>.
        If the text looks like a potential company name, record it.
        """
        results = []
        # Basic filtering logic
        blacklist = {"home", "faq", "contact", "register", "events", "about", "info", "policy"}

        tags = soup.find_all(["li", "div", "span", "a"], text=True)
        for t in tags:
            txt = t.get_text(strip=True)
            # Heuristics: length, alpha characters, skip blacklisted
            if len(txt) > 2 and len(txt) < 60 and any(c.isalpha() for c in txt.lower()):
                lower_txt = txt.lower()
                if not any(b in lower_txt for b in blacklist):
                    # Possibly a company
                    results.append({
                        "company_name": txt,
                        "event_name": event_name,
                        "event_relevance_score": event_score,
                        "date_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    })
        print(f"   Found {len(results)} potential companies in page for {event_name}")
        return results

    def run(self):
        self.load_events()
        all_companies = []

        # Existing scraping logic
        for event in self.events:
            comp_list = self.scrape_event_companies(event)
            all_companies.extend(comp_list)

        # Add predefined companies for specific events
        event_mappings = {
            'ISA Sign Expo 2025': [
                'CUTWORX USA', 'General Formulations', 'Laguna Tools Inc.',
                'Lintec of America, Inc.', 'Signage Details', '3A Composites USA, Inc.',
                '3M Commercial Solutions', 'A.R.K. Ramos Foundry & Mfg. Co.', 'Abitech',
                'ADMAX Exhibit & Display Ltd.', 'Advanced Greig Laminators, Inc.',
                'Advantage Innovations, Inc', 'Aludecor', 'Arlon Graphics',
                'Avery Dennison Graphics Solutions'
            ],
            'International Sign Association (ISA)': [
                'International Sign Association (ISA)'
            ]
        }

        for event_name, companies in event_mappings.items():
            event = next((e for e in self.events if e['name'] == event_name), None)
            if event:
                for company_name in companies:
                    all_companies.append({
                        "company_name": company_name,
                        "event_name": event['name'],
                        "event_relevance_score": event['relevance_score'],
                        "date_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    })

        # Rest of the processing
        if not all_companies:
            print("No companies discovered.")
            return pd.DataFrame()

        df = pd.DataFrame(all_companies)
        df.drop_duplicates(subset=["company_name", "event_name"], inplace=True)

        os.makedirs("data", exist_ok=True)
        df.to_csv(self.output_csv, index=False)
        print(f"\n✅ Discovered {len(df)} unique companies total. Saved to {self.output_csv}")
        return df

if __name__ == "__main__":
    scraper = EventWebsiteScraper(
        leads_csv="data/latest_leads.csv",
        output_csv="data/discovered_companies.csv"
    )
    scraper.run()
