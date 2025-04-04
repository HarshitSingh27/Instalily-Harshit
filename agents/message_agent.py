"""
📨 StakeholderMessageAgent

This module creates **personalized outreach messages** for decision-makers identified during company enrichment.
It uses OpenAI’s GPT model to tailor each message based on stakeholder role, company details, strategic alignment,
and product synergy with DuPont Tedlar’s protective films.

🚀 What It Does:
1. Loads input CSV: `enriched_companies_with_stakeholders.csv`
   - Requires columns like `company_name`, `event_name`, `industry`, `products`, `qualified_lead_reasons`, and stakeholder contact info.
2. For each stakeholder, builds a contextualized prompt using:
   - Company background
   - Event interaction
   - Strategic relevance
3. Sends prompt to OpenAI Chat API and retrieves 150–200 word professional outreach message.
4. Appends result as `outreach_message` column.
5. Saves enriched file to: `enriched_companies_with_stakeholders_outreach.csv`

🧠 GPT Prompt Structure:
- Personal greeting
- DuPont Tedlar capabilities aligned to stakeholder’s industry/products
- Strategic synergies (e.g., shared market priorities)
- Friendly close with a clear next step
- Signoff:  
Best,
Harshit
DuPont Tedlar
"""

import os
import re
import csv
import json
import time
import random
import logging
import pandas as pd
from openai import OpenAI
from typing import Dict, Any, List
from dotenv import load_dotenv

###############################################################################
# Load environment variables
###############################################################################
load_dotenv()

###############################################################################
# Logging configuration
###############################################################################
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StakeholderMessageAgent:
    """
    A robust, 'production-level' agent that reads an enriched CSV of 
    stakeholder info and writes a custom outreach message using GPT.
    """

    def __init__(
        self,
        input_csv: str = "data/enriched_companies_with_stakeholders.csv",
        output_csv: str = "data/enriched_companies_with_stakeholders_outreach.csv",
        model: str = "gpt-3.5-turbo",  
        temperature: float = 0.6,
        max_tokens: int = 500,
        delay_seconds: float = 0.25
    ):
        self.input_csv = input_csv
        self.output_csv = output_csv
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.delay_seconds = delay_seconds
        self.system_prompt = (
            "You are DuPont Tedlar's sales outreach assistant. Generate personalized outreach messages that:\n"
            "1. Highlight how our solutions address the specific needs of the stakeholder's company\n"
            "2. Reference concrete details from their profile: industry, products, and event context\n"
            "3. Emphasize strategic synergies from the qualified lead reasons\n"
            "4. Maintain professional tone while being concise (150-200 words)\n"
            "5. Always conclude with:\n"
            "Best,\n"
            "Harshit\n"
            "DuPont Tedlar\n\n"
            "Handle missing data gracefully while maximizing relevance to available information."
        )
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def run(self) -> None:
        logger.info("Loading CSV from %s", self.input_csv)
        try:
            df = pd.read_csv(self.input_csv)
        except Exception as e:
            logger.error("Failed to read input CSV: %s", e)
            return

        messages = []
        for index, row in df.iterrows():
            try:
                msg = self.generate_message_for_row(row)
                row_dict = row.to_dict()
                row_dict["outreach_message"] = msg
                messages.append(row_dict)
                time.sleep(self.delay_seconds)
            except Exception as e:
                logger.error("Failed generating message for row %d / %s: %s", index, row.get("company_name", ""), e)
                row_dict = row.to_dict()
                row_dict["outreach_message"] = "ERROR: Could not generate message"
                messages.append(row_dict)

        logger.info("Saving final CSV to %s", self.output_csv)
        out_df = pd.DataFrame(messages)
        try:
            out_df.to_csv(self.output_csv, index=False)
        except Exception as e:
            logger.error("Failed to save output CSV: %s", e)
            return

        logger.info("Done. Wrote %d rows (with outreach messages) to %s", len(out_df), self.output_csv)

    def generate_message_for_row(self, row: pd.Series) -> str:
        user_prompt = self._build_prompt_from_row(row)
        logger.debug("User prompt:\n%s", user_prompt)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            content = response.choices[0].message.content
            return self._clean_message(content)
        except Exception as e:
            logger.error("OpenAI API error: %s", e)
            return "ERROR: GPT call failed"

    def _build_prompt_from_row(self, row: pd.Series) -> str:
        stakeholder_name = row.get("Decision_Maker", "Decision Maker")
        stakeholder_title = row.get("Title", "leadership position")
        company = row.get("company_name", "their organization")
        event = row.get("event_name", "industry event")
        industry = row.get("industry", "their industry")
        products = row.get("products", "their products")
        synergy_points = row.get("qualified_lead_reasons", "shared strategic priorities")
        strategy = row.get("strategic_relevance", "alignment with innovation goals")

        # Format context sections
        context_sections = [
            f"Company Context:",
            f"- Name: {company}",
            f"- Industry: {industry}",
            f"- Key Offerings: {products[:200]}" if len(str(products)) > 200 else f"- Key Offerings: {products}",
            "",
            f"Engagement Context:",
            f"- Met at: {event}",
            f"- Strategic Fit: {strategy}",
            f"- Synergy Points: {synergy_points[:300]}" if len(str(synergy_points)) > 300 else f"- Synergy Points: {synergy_points}",
            "",
            "Message Requirements:",
            "- Open with personalized greeting acknowledging their role",
            "- Connect Tedlar solutions to their specific operational context",
            "- Reference 1-2 specific synergy points from above",
            "- Propose clear next steps for collaboration",
            "- Maintain professional yet approachable tone"
        ]

        prompt = (
            f"Recipient: {stakeholder_name} ({stakeholder_title})\n\n"
            "Company Profile:\n"
            f"{'\n'.join(context_sections)}\n\n"
            "Generate outreach that positions Tedlar as the optimal solution partner "
            f"for {company}'s {industry} needs, specifically addressing:\n"
            f"- How our films enhance {products.split(',')[0]} if relevant\n"
            f"- Strategic alignment with {strategy}\n"
        )
        return prompt

    def _clean_message(self, content: str) -> str:
        msg = content.strip()
        required_signoff = "\nBest,\nHarshit\nDuPont Tedlar"
        
        # Ensure signoff is present and formatted correctly
        if not msg.endswith(required_signoff):
            msg = re.sub(r"(?i)(best\s*[,]?\s*harshit.*?dupont\s*tedlar.*?)$", "", msg)
            msg = msg.strip() + required_signoff
        
        # Remove any interim draft markers
        msg = re.sub(r"^(draft\s*:|proposed\s*text:)\s*", "", msg, flags=re.IGNORECASE)
        
        # Trim excessive length while preserving signoff
        if len(msg) > 1500:
            msg = msg[:1400] + "..." + required_signoff
            
        return msg

def main():
    agent = StakeholderMessageAgent()
    agent.run()

if __name__ == "__main__":
    main()