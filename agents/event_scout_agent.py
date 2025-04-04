"""
EventScoutAgent: Intelligent B2B Event Discovery + Scoring Module for DuPont Tedlar

What it does:
- Loads manually identified events from `manual_events.csv`
- Uses Perplexity AI to discover NEW expos relevant to signage, vehicle wraps, and graphics
- Deduplicates against existing events
- Scores events using GPT-4/GPT-3.5 to rate relevance (0–10) + generate reasoning
- Assigns priority (High / Medium / Low) based on relevance score
- Merges and saves all results into `latest_leads.csv` for the dashboard

Used in: Agentic AI workflow for identifying qualified B2B trade shows
Why it matters: Finds where DuPont Tedlar's protective film business has the best chance to meet partners + customers

Output: `data/latest_leads.csv` with name, URL, relevance_score, reasoning, priority, and event_id

Usage:
agent = EventScoutAgent()
agent.run()
"""

import pandas as pd
import openai
import os
import requests
import hashlib
from time import sleep
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class EventScoutAgent:
    def __init__(self, manual_events_path: str = "data/manual_events.csv"):
        self.manual_events_path = manual_events_path
        self.events = []

    def load_manual_events(self):
        df = pd.read_csv(self.manual_events_path)
        for _, row in df.iterrows():
            name = row["name"].strip().lower().replace('"', '')
            url = row["url"].strip().lower().replace('"', '')
            event_id = hashlib.md5((name + url).encode()).hexdigest()
            self.events.append({
                "name": row["name"].strip(),
                "url": row["url"].strip(),
                "source": "manual",
                "event_id": event_id,
                "relevance_score": row.get("relevance_score", ""),
                "reasoning": row.get("reasoning", "")
            })

    def gpt_relevance_score(self, event_name, url):
        system_prompt = "You are an expert in B2B marketing and event lead generation."
        user_prompt = (
            "DuPont Tedlar manufactures protective films used in signage, architectural graphics, and vehicle wraps. "
            "Given the event below, rate how relevant it is (0–10) for identifying B2B customers or industry partners. "
            "Provide a numeric score and a short reason.\n\n"
            f"Event Name: {event_name}\n"
            f"URL: {url}\n\n"
            "Respond in the following format:\n"
            "Score: <number>\nReason: <short reason>"
        )

        def get_score_with_model(model_name):
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3
            )
            content = response.choices[0].message.content
            lines = content.splitlines()
            score = float(lines[0].replace("Score:", "").strip())
            reason = lines[1].replace("Reason:", "").strip()
            return score, reason

        try:
            return get_score_with_model("gpt-4")
        except Exception as e:
            print(f"[Fallback to 3.5] GPT-4 failed for '{event_name}': {e}")
            try:
                return get_score_with_model("gpt-3.5-turbo")
            except Exception as e2:
                print(f"[ERROR] GPT-3.5 also failed for '{event_name}': {e2}")
                return 0.0, "GPT error fallback."

    def real_time_llm_search(self, query="2025 signage and print expos in the US"):
        url = "https://api.perplexity.ai/chat/completions"
        headers = {
            "Authorization": f"Bearer {os.getenv('PERPLEXITY_API_KEY')}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "sonar",
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Query: {query}.\n\n"
                        "DuPont Tedlar manufactures protective films for signage, vehicle wraps, and architectural graphics. "
                        "Find upcoming 2025 expos or trade shows in the US that are relevant to these industries. "
                        "For each event, respond in this structured CSV format:\n\n"
                        "name,url,relevance_score,reasoning\n"
                        "ISA Sign Expo 2025,https://isasignexpo2025.mapyourshow.com/,9.5,Major event for large-format signage and wraps, ideal for DuPont’s target market.\n"
                        "Return only up to 10 new entries in this format. No explanation."
                    )
                }
            ]
        }

        try:
            res = requests.post(url, json=body, headers=headers)
            res.raise_for_status()
            content = res.json()["choices"][0]["message"]["content"]

            new_events = []
            for line in content.splitlines():
                if line.lower().startswith("name") or not line.strip():
                    continue

                parts = line.split(",", maxsplit=3)
                if len(parts) < 4:
                    continue

                name = parts[0].replace('"', '').strip()
                url = parts[1].replace('"', '').strip()
                try:
                    score = float(parts[2].strip())
                except ValueError:
                    score = 0.0
                reason = parts[3].replace('"', '').strip()

                if url.lower() == "not available" or not url.startswith("http"):
                    continue

                norm_name = name.lower()
                norm_url = url.lower()
                event_id = hashlib.md5((norm_name + norm_url).encode()).hexdigest()

                new_events.append({
                    "name": name,
                    "url": url,
                    "source": "perplexity",
                    "relevance_score": score,
                    "reasoning": reason,
                    "event_id": event_id
                })

            return new_events

        except Exception as e:
            print(f"[Perplexity API Error] {e}")
            return []

    def deduplicate_and_merge_events(self, new_events):
        def normalize(text):
            return text.strip().lower().replace('"', '') if isinstance(text, str) else ""

        existing_ids = {event["event_id"] for event in self.events}

        for event in new_events:
            norm_name = normalize(event["name"])
            norm_url = normalize(event["url"])
            event_id = hashlib.md5((norm_name + norm_url).encode()).hexdigest()

            if event_id not in existing_ids:
                event["name"] = event["name"].replace('"', '').strip()
                event["url"] = event["url"].replace('"', '').strip()
                event["event_id"] = event_id
                self.events.append(event)

    def score_events(self):
        for event in self.events:
            if not event.get("relevance_score"):
                score, reason = self.gpt_relevance_score(event["name"], event["url"])
                event["relevance_score"] = score
                event["reasoning"] = reason
                sleep(1.5)

    def enrich_rankings(self):
        def classify_priority(score):
            try:
                score = float(score)
                if score >= 9:
                    return "High"
                elif score >= 7:
                    return "Medium"
                else:
                    return "Low"
            except:
                return "Unknown"

        for event in self.events:
            event["priority"] = classify_priority(event.get("relevance_score", 0))

    def save_to_latest_leads(self):
        df = pd.DataFrame(self.events)
        output_path = "data/latest_leads.csv"
        df.to_csv(output_path, index=False)
        print(f"✅ Merged leads saved to {output_path}")

    def run(self):
        self.load_manual_events()
        new_events = self.real_time_llm_search()
        self.deduplicate_and_merge_events(new_events)
        self.score_events()
        self.enrich_rankings()  
        self.save_to_latest_leads()
        return self.events
