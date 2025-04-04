import os
import re
import pandas as pd
import openai
import requests
import logging
from time import sleep
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Dict, List
from pandas import Timestamp

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('enrichment.log'),
        logging.StreamHandler()
    ]
)

class EnhancedCompanyEnricher:
    def __init__(self):
        self.invalid_terms = [
            'skip', 'login', 'cart', 'menu', 'privacy', 'terms', 'cookie', 
            'account', 'search', 'read more', 'click here', 'email', 'http',
            '©', 'legal', 'careers', 'testimonials', 'blog', 'newsletter',
            'faq', '404', 'undefined', 'null', 'business management', 'contact',
            'skills', 'members', 'project management', 'wage', 'report', 'board',
            'directors', 'category', 'page', 'home', 'about', 'services', 'products'
        ]
        self.domain_pattern = re.compile(
            r'(https?://)?(www\.)?(?P<name>[a-zA-Z0-9-]+)\..{2,6}(/\S*)?$', 
            re.IGNORECASE
        )
        self.min_name_length = 3
        self.max_name_length = 35

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        try:
            # Convert relevance score and clean
            df['event_relevance_score'] = pd.to_numeric(
                df['event_relevance_score'], errors='coerce'
            ).fillna(0).clip(0, 10)
            
            # Clean company names
            df['company_name'] = df['company_name'].apply(self._clean_company_name)
            
            # Filter invalid entries
            df = df[df['company_name'].apply(self._is_valid_company)]
            df = df[df['event_name'].apply(self._is_valid_event)]
            
            return df.drop_duplicates(
                subset=['company_name', 'event_name'], 
                keep='last'
            ).reset_index(drop=True)
        
        except Exception as e:
            logging.error(f"Data cleaning failed: {str(e)}")
            return pd.DataFrame()

    def _clean_company_name(self, name: str) -> str:
        try:
            # Handle URL patterns first
            url_match = self.domain_pattern.search(str(name))
            if url_match:
                base_name = url_match.group('name')
                base_name = re.sub(r'-\w+$', '', base_name)  # Remove suffixes like -blog
                return base_name.capitalize()
            
            # General cleaning
            cleaned = re.sub(r'[^a-zA-Z0-9\s\.\&\,\-]', '', str(name)).strip()
            cleaned = re.sub(r'\b(?:{})\b'.format('|'.join(self.invalid_terms)), 
                            '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return cleaned[:self.max_name_length].strip(' -_')
        except:
            return ''

    def _is_valid_company(self, name: str) -> bool:
        try:
            name = str(name).lower()
            return all([
                len(name) >= self.min_name_length,
                len(name) <= self.max_name_length,
                not any(term in name for term in self.invalid_terms),
                not re.search(r'^\d+$', name),
                not re.match(r'^[\W_]+$', name)
            ])
        except:
            return False

    def _is_valid_event(self, event: str) -> bool:
        try:
            return len(str(event)) > 5 and not any(
                term in str(event).lower() for term in ['test', 'example', 'invalid'])
        except:
            return False

class CompanyEnrichmentAgent:
    def __init__(self, cleaned_df: pd.DataFrame):
        self.df = cleaned_df
        self.enrichment_cache: Dict = {}
        self.target_industries = {
            'yes': ['signage', 'vehicle wraps', 'architectural graphics', 
                   'large format printing', 'protective films'],
            'maybe': ['construction', 'automotive', 'manufacturing', 
                     'advertising', 'marine']
        }
        self.perplexity_config = {
            'api_key': os.getenv('PERPLEXITY_API_KEY'),
            'endpoint': 'https://api.perplexity.ai/chat/completions',
            'timeout': 30
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=30))
    def _get_company_intel(self, company_name: str) -> Dict:
        try:
            headers = {"Authorization": f"Bearer {self.perplexity_config['api_key']}"}
            payload = {
                "model": "sonar",
                "messages": [{
                    "role": "user",
                    "content": f"""Provide concise company info for {company_name}:
                    - Estimated annual revenue in USD
                    - Employee count
                    - Primary industry focus
                    - Key products/services
                    - Recent business developments"""
                }]
            }
            response = requests.post(
                self.perplexity_config['endpoint'],
                headers=headers,
                json=payload,
                timeout=self.perplexity_config['timeout']
            )
            return self._parse_intel_response(response.json()['choices'][0]['message']['content'])
        except Exception as e:
            logging.error(f"Perplexity API Error: {str(e)}")
            return {}

    def _parse_intel_response(self, content: str) -> Dict:
        intel = {'revenue': 0, 'employees': 0, 'industry': '', 'products': []}
        try:
            # Extract revenue
            rev_match = re.search(r'\$([\d\.]+)([BMK])', content, re.IGNORECASE)
            if rev_match:
                value = float(rev_match.group(1))
                multiplier = {'b': 1e9, 'm': 1e6, 'k': 1e3}.get(rev_match.group(2).lower(), 1)
                intel['revenue'] = value * multiplier
                
            # Extract other fields
            for line in content.split('\n'):
                line = line.lower().strip()
                if 'employee' in line and 'count' in line:
                    match = re.search(r'\d+', line)
                    if match:
                        intel['employees'] = int(match.group())
                elif 'industry' in line:
                    intel['industry'] = line.split(':')[-1].strip().title()
                elif 'product' in line or 'service' in line:
                    intel['products'] = [p.strip() for p in line.split(':')[-1].split(',')]
                    
            return intel
        except Exception as e:
            logging.error(f"Intel parsing error: {str(e)}")
            return intel

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _call_gpt(self, prompt: str, use_gpt4: bool = False) -> Dict:
        try:
            response = openai.chat.completions.create(
                model="gpt-4" if use_gpt4 else "gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": """Respond EXACTLY in this format:
                    
                    INDUSTRY FIT: [Yes/No/Maybe]
                    REVENUE: [$X.XX (B/M)]
                    QUALIFICATION SUMMARY:
                    - Industry Fit: [1-2 sentences]
                    - Size & Revenue: [1-2 sentences] 
                    - Strategic Relevance: [1-2 sentences]
                    - Market Activity: [1-2 sentences]
                    """
                }, {
                    "role": "user", 
                    "content": prompt
                }],
                temperature=0.3,
                max_tokens=300
            )
            return self._parse_gpt_response(response.choices[0].message.content)
        except Exception as e:
            logging.error(f"GPT Error: {str(e)}")
            return {}

    def _parse_gpt_response(self, text: str) -> Dict:
        parsed = {
            'industry_fit': 'No',
            'revenue_display': '',
            'qualification_summary': '',
            'strategic_relevance': ''
        }
        current_section = None
        
        for line in text.split('\n'):
            line = line.strip()
            if 'INDUSTRY FIT:' in line:
                parsed['industry_fit'] = line.split(':')[-1].strip()
            elif 'REVENUE:' in line:
                parsed['revenue_display'] = line.split(':')[-1].strip()
            elif 'QUALIFICATION SUMMARY:' in line:
                current_section = 'qualification_summary'
                parsed[current_section] = []
            elif line.startswith('-'):
                if current_section:
                    parsed[current_section].append(line.strip('- '))
                    
        # Convert lists to strings
        if parsed['qualification_summary']:
            parsed['qualification_summary'] = '\n'.join(parsed['qualification_summary'])
            
        return parsed

    def _calculate_industry_fit(self, industry: str) -> str:
        industry_lower = industry.lower()
        for fit, terms in self.target_industries.items():
            if any(term in industry_lower for term in terms):
                return fit.title()
        return 'No'

    def enrich_data(self) -> pd.DataFrame:
        results = []
        for idx, row in self.df.iterrows():
            try:
                if pd.isna(row['company_name']) or row['company_name'] in self.enrichment_cache:
                    continue

                # Get company intelligence
                intel = self._get_company_intel(row['company_name'])
                sleep(1)  # Rate limit protection
                
                # Generate qualification summary
                gpt_response = self._call_gpt(
                    f"Analyze {row['company_name']} for protective film sales potential:\n"
                    f"- Event: {row['event_name']} (Relevance: {row['event_relevance_score']}/10\n"
                    f"- Industry: {intel.get('industry', 'Unknown')}\n"
                    f"- Revenue: ${intel.get('revenue', 0)/1e6:.1f}M\n"
                    f"- Products: {', '.join(intel.get('products', []))}\n"
                    f"Focus on applications in signage, vehicle wraps, and architectural protection.",
                    row['event_relevance_score'] >= 8
                )

                # Compile final record
                enriched = {
                    **row.to_dict(),
                    **intel,
                    **gpt_response,
                    'qualified_lead_reasons': self._generate_lead_reasons(intel, gpt_response),
                    'revenue_usd': intel.get('revenue', 0),
                    'enrichment_timestamp': Timestamp.now().isoformat()
                }
                
                results.append(enriched)
                self.enrichment_cache[row['company_name']] = enriched
                sleep(2 if row['event_relevance_score'] >=8 else 1)

            except Exception as e:
                logging.error(f"Failed processing {row.get('company_name', 'unknown')}: {str(e)}")

        return pd.DataFrame(results)

    def _generate_lead_reasons(self, intel: Dict, gpt: Dict) -> str:
        reasons = []
        if gpt.get('industry_fit', 'No') != 'No':
            reasons.append(f"Industry Fit: {intel.get('industry', '')}")
        if intel.get('revenue', 0) > 1e7:
            reasons.append(f"Financial Size: {gpt.get('revenue_display', '')}")
        if 'protective' in str(intel.get('products', [])):
            reasons.append("Product Alignment: Existing protective product lines")
        return ' | '.join(reasons) if reasons else 'Needs further analysis'

if __name__ == "__main__":
    try:
        raw_df = pd.read_csv("data/discovered_companies.csv")
        cleaner = EnhancedCompanyEnricher()
        clean_df = cleaner.clean_data(raw_df)
        
        if clean_df.empty:
            logging.error("No valid data remaining after cleaning")
            exit()

        enricher = CompanyEnrichmentAgent(clean_df)
        enriched_df = enricher.enrich_data()
        
        # Final formatting
        enriched_df['revenue_usd'] = enriched_df['revenue_usd'].apply(
            lambda x: f"${x/1e6:.1f}M" if x < 1e9 else f"${x/1e9:.1f}B"
        )
        
        os.makedirs("data", exist_ok=True)
        clean_df.to_csv("data/cleaned_companies.csv", index=False)
        enriched_df.to_csv("data/enriched2_companies.csv", index=False)
        
        logging.info(f"""
        Processing Complete:
        - Original Records: {len(raw_df)}
        - Cleaned Records: {len(clean_df)}
        - Enriched Records: {len(enriched_df)}
        """)

    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
        exit(1)