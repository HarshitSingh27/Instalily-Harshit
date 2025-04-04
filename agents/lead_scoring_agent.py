"""
Lead Scoring Agent

This module scores and ranks enriched B2B company leads for DuPont Tedlar based on 
multiple strategic dimensions and stakeholder data.

Purpose:
Assigns a numeric `lead_score` to each company + stakeholder row using robust scoring 
rules tailored to DuPont Tedlar’s priorities: signage, vehicle wraps, architectural graphics.

Input:
- `enriched_companies_with_stakeholders_outreach.csv` (must include these columns):
  - industry_fit
  - revenue-estimated
  - employees
  - strategic_relevance
  - event_relevance_score
  - market_activity
  - Decision-Maker

Output:
- `qualified_leads_scored.csv` — same data with added `lead_score` column, sorted descending.

Scoring Dimensions:
| Criteria                  | Max Score |
|---------------------------|-----------|
| Industry Fit              | 15        |
| Revenue (estimated)       | 15        |
| Employee Count            | 10        |
| Strategic Relevance       | 15        |
| Industry Engagement (event) | 10     |
| Market Activity (e.g., durable films) | 10 |
| Decision Maker Identified | 10        |
| **Total Max**             | **85**    |

A score above 60 is considered a highly qualified lead.

Behavior:
- Handles missing data gracefully
- Logs errors and steps for transparency
- Designed for production workflows and integrates with downstream dashboard

Run This:
```bash
python lead_scoring_agent.py
"""
import pandas as pd
import numpy as np
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Robust scoring function with detailed criteria
def calculate_lead_score(row):
    scores = {}

    # Industry Fit Scoring
    industry_fit = str(row.get('industry_fit', '')).strip().lower()
    scores['industry_fit'] = {
        'yes': 15,
        'maybe': 7,
        'no': 0
    }.get(industry_fit, 0)

    # Revenue Scoring
    revenue = row.get('revenue-estimated', 0)
    if pd.isna(revenue):
        revenue = 0
    if revenue >= 8_000_000_000:
        scores['revenue'] = 15
    elif revenue >= 1_000_000_000:
        scores['revenue'] = 12
    elif revenue >= 100_000_000:
        scores['revenue'] = 9
    elif revenue >= 10_000_000:
        scores['revenue'] = 6
    elif revenue >= 1_000_000:
        scores['revenue'] = 3
    else:
        scores['revenue'] = 1

    # Employee Count Scoring
    employees = row.get('employees', 0)
    if pd.isna(employees):
        employees = 0
    if employees >= 10000:
        scores['employees'] = 10
    elif employees >= 1000:
        scores['employees'] = 8
    elif employees >= 200:
        scores['employees'] = 6
    elif employees >= 50:
        scores['employees'] = 4
    else:
        scores['employees'] = 2

    # Strategic Relevance
    strategic_relevance = str(row.get('strategic_relevance', '')).lower()
    if 'major player' in strategic_relevance or 'high' in strategic_relevance:
        scores['strategic_relevance'] = 15
    elif strategic_relevance:
        scores['strategic_relevance'] = 8
    else:
        scores['strategic_relevance'] = 0

    # Industry Engagement (trade show attendance)
    event_relevance_score = row.get('event_relevance_score', 0)
    if event_relevance_score >= 8:
        scores['industry_engagement'] = 10
    elif event_relevance_score >= 5:
        scores['industry_engagement'] = 7
    else:
        scores['industry_engagement'] = 4

    # Market Activity Scoring
    market_activity = str(row.get('market_activity', '')).lower()
    if 'weather-resistant' in market_activity or 'durable' in market_activity:
        scores['market_activity'] = 10
    elif market_activity:
        scores['market_activity'] = 5
    else:
        scores['market_activity'] = 2

    # Decision Maker Identified
    decision_maker = str(row.get('Decision-Maker', '')).lower()
    if decision_maker and 'no relevant' not in decision_maker:
        scores['decision_maker'] = 10
    else:
        scores['decision_maker'] = 0

    # Total score
    total_score = sum(scores.values())
    return total_score

def robust_load_csv(input_csv):
    try:
        df = pd.read_csv(input_csv)
        logging.info(f"Loaded data from {input_csv} successfully with {len(df)} records.")
        return df
    except FileNotFoundError:
        logging.error(f"File not found: {input_csv}")
        raise
    except pd.errors.ParserError as e:
        logging.error(f"CSV parsing error: {e}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error loading CSV: {e}")
        raise

def save_sorted_leads(df, output_csv):
    try:
        df.to_csv(output_csv, index=False)
        logging.info(f"Successfully saved sorted leads to {output_csv}")
    except Exception as e:
        logging.error(f"Error saving file {output_csv}: {e}")
        raise

def run_lead_scoring(input_csv, output_csv):
    logging.info("Starting the Lead Scoring Process...")

    # Load data
    df = robust_load_csv(input_csv)

    # Clean and handle missing data
    df.fillna({'industry_fit': 'no', 'revenue_usd': 0, 'employees': 0,
               'strategic_relevance': '', 'market_activity': '',
               'Decision-Maker': 'No relevant person found'}, inplace=True)

    # Calculate lead scores
    logging.info("Calculating lead scores...")
    df['lead_score'] = df.apply(calculate_lead_score, axis=1)

    # Sort leads by lead_score descending
    df_sorted = df.sort_values(by='lead_score', ascending=False).reset_index(drop=True)

    # Save to output
    save_sorted_leads(df_sorted, output_csv)

    logging.info("Lead scoring completed successfully.")

# Main execution point
if __name__ == "__main__":
    input_csv = 'data/enriched_companies_with_stakeholders_outreach.csv'
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_csv = f'data/qualified_leads_scored.csv'

    run_lead_scoring(input_csv, output_csv)
