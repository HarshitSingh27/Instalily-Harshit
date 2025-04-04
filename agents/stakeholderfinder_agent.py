"""
🧑‍💼 StakeholderFinderAgent

This module finds potential decision-makers at each company identified during enrichment,
simulating how you'd integrate with LinkedIn Sales API and Hunter.io for contact discovery.

🔍 What It Does:
- Reads from a company enrichment CSV (e.g., `test.csv`)
- For each company, generates up to 5 stakeholder leads
- Populates fields like:
    - Decision_Maker (name)
    - Title (e.g., VP of Sales)
    - Email (generated using `firstname.lastname@companydomain.com`)
    - LinkedIn profile link
- Writes all results to a new enriched file with stakeholders (e.g., `enriched_companies_with_stakeholders.csv`)

🌐 In Production (Replace Stub Logic):
- Step 1: Query LinkedIn Sales API for relevant professionals by company name
- Step 2: Use Hunter.io’s Email Finder API to validate and return emails

🧪 Current Behavior (Demo Mode):
- Uses dummy name/title data
- Randomly generates 0–5 decision-makers per company
- Synthesizes a likely email based on company name
- Generates a LinkedIn URL using a random ID

📁 Input:
- `data/test.csv` or any CSV with a `company_name` column

📁 Output:
- `data/enriched_companies_with_stakeholders.csv` with 1+ rows per company if leads are found

🔁 Sample Output Columns:
- company_name, event_name, revenue, products, ...
- Decision_Maker, Title, Email, LinkedIn

🛠️ Run This:
```bash
python stakeholderfinder_agent.py
"""
import os
import pandas as pd
from time import sleep
from dotenv import load_dotenv
from typing import List, Dict

load_dotenv()

# Hypothetical environment variables for your production environment
LINKEDIN_API_KEY = os.getenv("LINKEDIN_API_KEY", "dummy-linkedin-key")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "dummy-hunter-key")

class StakeholderFinderAgent:
    """
    A class that demonstrates how we will integrate with
    LinkedIn's Sales API and Hunter.io to identify and enrich stakeholder data
    for each company.

    Steps:
      1. Read enriched CSV with company data.
      2. For each company, call `find_stakeholders_for_company()` to:
         - Query LinkedIn's Sales API for relevant employees/decision makers.
         - Use Hunter.io to find or verify emails for each stakeholder.
         - Return up to 5 leads with name/title/email/linkedin profile.
      3. Save the updated CSV with new stakeholder columns.

    NOTE: All API calls are commented out, replaced with dummy logic to illustrate
    the approach. Replace with real integration for a production environment.
    """

    def __init__(
        self,
        input_csv: str = "data/enriched_companies.csv",
        output_csv: str = "data/enriched_companies_with_stakeholders.csv",
        max_stakeholders: int = 5
    ):
        self.input_csv = input_csv
        self.output_csv = output_csv
        self.max_stakeholders = max_stakeholders

    def run(self):
        """
        Main execution: load CSV, process each company, find stakeholders,
        and write out the final CSV.
        """
        df = pd.read_csv(self.input_csv)

        # We'll expand the DataFrame with stakeholder columns
        all_records = []

        for _, row in df.iterrows():
            company_name = row.get("company_name", "")
            # Perform the stakeholder search
            leads = self.find_stakeholders_for_company(company_name, row)

            if not leads:
                # If no leads found, create a single row with 'no relevant person found'
                record = row.to_dict()
                record["Decision_Maker"] = "no relevant person found"
                record["Title"] = ""
                record["Email"] = ""
                record["LinkedIn"] = ""
                all_records.append(record)
            else:
                # Create multiple rows, one per stakeholder
                for lead in leads:
                    record = row.to_dict()
                    record["Decision_Maker"] = lead["name"]
                    record["Title"] = lead["title"]
                    record["Email"] = lead["email"]
                    record["LinkedIn"] = lead["linkedin"]
                    all_records.append(record)

            sleep(0.05)  # Throttle to simulate API rate limiting

        # Convert and save
        out_df = pd.DataFrame(all_records)
        out_df.to_csv(self.output_csv, index=False)

        print(f"✅ Stakeholder Finder complete. Wrote {len(out_df)} rows to {self.output_csv}")

    def find_stakeholders_for_company(
        self,
        company_name: str,
        row: Dict
    ) -> List[Dict]:
        """
        Hypothetically queries LinkedIn's Sales API and Hunter.io to find up to
        self.max_stakeholders stakeholder leads. Returns a list of dicts with:
          - name
          - title
          - email
          - linkedin
        """

        if not company_name:
            return []

        # ============================
        # Step 1: Query LinkedIn API
        # ============================
        # Pseudocode for real integration:
        # try:
        #     response = requests.get(
        #         "https://api.linkedin.com/v2/salesApiEndpoint",
        #         headers={"Authorization": f"Bearer {LINKEDIN_API_KEY}"},
        #         params={
        #             "company": company_name,
        #             "max": self.max_stakeholders
        #         }
        #     )
        #     response.raise_for_status()
        #     data = response.json()
        # except Exception as e:
        #     print(f"[LinkedIn Error] {e}")
        #     return []

        # For demonstration, let's create random placeholders
        # in place of real LinkedIn data:
        linkedin_stub_data = self._generate_dummy_linkedin_data(company_name)

        # ============================
        # Step 2: For each lead, call Hunter.io to find/verify email
        # ============================
        # leads = []
        # for person in linkedin_stub_data:
        #     email_response = requests.get(
        #         "https://api.hunter.io/v2/email-finder",
        #         params={
        #             "domain": domain_for_company,
        #             "first_name": person["first_name"],
        #             "last_name": person["last_name"],
        #             "api_key": HUNTER_API_KEY
        #         }
        #     )
        #     # parse email_response.json() for "email"
        #     leads.append({
        #         "name": f"{person['first_name']} {person['last_name']}",
        #         "title": person["title"],
        #         "email": found_email,
        #         "linkedin": person["linkedin"]
        #     })
        # return leads

        # We'll just return the dummy data with a guessed email
        leads = []
        for person in linkedin_stub_data:
            domain_part = self._domain_from_company(company_name) or "example"
            guessed_email = f"{person['first_name'].lower()}.{person['last_name'].lower()}@{domain_part}.com"
            leads.append({
                "name": f"{person['first_name']} {person['last_name']}",
                "title": person["title"],
                "email": guessed_email,
                "linkedin": person["linkedin"]
            })

        return leads

    def _generate_dummy_linkedin_data(self, company_name: str) -> List[Dict]:
        """
        Returns up to self.max_stakeholders dummy leads for a single company.
        Each lead has first_name, last_name, title, linkedin.
        """
        import random

        # Some random first/last name banks
        first_names = ["Alex", "Taylor", "Jordan", "Dana", "Morgan", "Harper", "Casey", "Cameron", "Riley", "Avery"]
        last_names = ["Smith", "Jones", "Lee", "Brown", "Garcia", "Wilson", "Davis", "Green", "Clark", "Miller"]
        titles = [
            "VP of Sales", "Director of Innovation", "Head of R&D", "Procurement Director",
            "Marketing Lead", "Sales Manager", "Senior Product Manager", "Chief Materials Engineer"
        ]

        leads = []
        num_leads = random.randint(0, self.max_stakeholders)

        for _ in range(num_leads):
            first = random.choice(first_names)
            last = random.choice(last_names)
            title = random.choice(titles)
            random_id = random.randint(1000, 9999)
            linkedin_url = f"https://www.linkedin.com/in/{first.lower()}-{last.lower()}-{random_id}"
            leads.append({
                "first_name": first,
                "last_name": last,
                "title": title,
                "linkedin": linkedin_url
            })

        return leads

    def _domain_from_company(self, company_name: str) -> str:
        """
        Creates a fake domain from the company name for the email address.
        E.g. "Avery Dennison" -> "averydennison"
        """
        # remove spaces and punctuation
        domain = "".join(ch for ch in company_name.lower() if ch.isalnum())
        return domain


if __name__ == "__main__":
    agent = StakeholderFinderAgent(
        input_csv="data/test.csv",
        output_csv="data/enriched_companies_with_stakeholders.csv",
        max_stakeholders=5
    )
    agent.run()
