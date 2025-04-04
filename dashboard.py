import streamlit as st
import pandas as pd
import subprocess
import logging
import os
from datetime import datetime

# Configure Logging
logging.basicConfig(
    filename='dashboard_log.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s'
)

# Streamlit Config
st.set_page_config(page_title="DuPont Tedlar Outreach Dashboard", layout="wide", initial_sidebar_state="expanded")

# Path Constants
AGENTS_PATH = "agents"
DATA_PATH = "data"

# Agent scripts mapping
AGENTS = {
    "Event Scout": "event_scout_agent.py",
    "Company Hunter": "company_hunter_agent.py",
    "Company Enrichment": "company_enrichment_agent.py",
    "Stakeholder Finder": "stakeholderfinder_agent.py",
    "Message Generation": "message_agent.py"
}

DATA_FILES = {
    "Discovered Companies": "discovered_companies.csv",
    "Enriched Companies": "test.csv",
    "Companies with Stakeholders": "enriched_companies_with_stakeholders.csv",
    "Personalized Outreach Messages": "qualified_leads_scored.csv",
    "Event Information": "latest_leads.csv"
}

# Helper Functions
@st.cache_data
def load_csv(filename):
    path = os.path.join(DATA_PATH, filename)
    if os.path.exists(path):
        df = pd.read_csv(path)
        return df
    else:
        logging.error(f"{filename} not found.")
        return pd.DataFrame()

def run_agent(agent_script):
    try:
        subprocess.run(["python", os.path.join(AGENTS_PATH, agent_script)], check=True)
        st.success(f"✅ Successfully ran {agent_script}")
        logging.info(f"{agent_script} ran successfully.")
    except subprocess.CalledProcessError as e:
        st.error(f"❌ Error running {agent_script}: {e}")
        logging.error(f"Error running {agent_script}: {e}")

# Sidebar for Controls and Execution
st.sidebar.title("⚙️ DuPont Tedlar AI Controls")

st.sidebar.markdown("---")
st.sidebar.header("Run Agents")
selected_agent = st.sidebar.selectbox("Select an Agent to Run:", ["All Agents"] + list(AGENTS.keys()))

if st.sidebar.button("🚀 Execute Agent(s)"):
    if selected_agent == "All Agents":
        for agent_name, agent_script in AGENTS.items():
            with st.spinner(f"Running {agent_name}..."):
                run_agent(agent_script)
    else:
        with st.spinner(f"Running {selected_agent}..."):
            run_agent(AGENTS[selected_agent])

st.sidebar.markdown("---")
st.sidebar.header("Filter Dashboard")
# Load discovered companies to get event list, but user can pick from any event they want
events_for_filter = pd.concat([
    load_csv(DATA_FILES["Discovered Companies"]),
    pd.DataFrame({'event_name': []})
])['event_name'].unique()

event_filter = st.sidebar.multiselect(
    "Filter by Event",
    options=events_for_filter,
    default=None
)

# Main Dashboard
st.title("📊 DuPont Tedlar - Outreach AI Dashboard")
st.markdown("""
Welcome to the **DuPont Tedlar** AI-powered insights dashboard. Here, you can explore detailed information about events, companies, qualified leads, stakeholders, and personalized outreach messages.
""")

# Tabs Setup
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📍 Events & Companies", "🔍 Company Enrichment", "🧑‍💼 Stakeholders", "📨 Personalized Messages", "📅 All Events"])

###############################################################################
# Tab 1: Landing Dashboard -> read from qualified_leads_scored.csv
###############################################################################
with tab1:
    st.subheader("📍 Qualified Companies Overview")

    df_tab1 = load_csv(DATA_FILES["Personalized Outreach Messages"])
    if event_filter and 'event_name' in df_tab1.columns:
        df_tab1 = df_tab1[df_tab1['event_name'].isin(event_filter)]

    # Step 1: Drop duplicates just for display
    unique_companies = df_tab1.drop_duplicates(subset=["company_name"])

    display_cols = [
        "company_name", "event_name", "qualification_summary", "industry_fit", 
        "strategic_relevance", "lead_score"
    ]
    st.dataframe(unique_companies[display_cols], use_container_width=True)

    # Step 2: Interactive preview
    st.markdown("### 📬 Company Outreach & Stakeholder Preview")
    selected_company = st.selectbox("Select a Company", unique_companies['company_name'].unique())

    company_data = df_tab1[df_tab1['company_name'] == selected_company]

    for _, row in company_data.iterrows():
        with st.expander(f"👤 {row.get('Decision_Maker', 'Unknown')} - {row.get('Title', 'No Title')}"):
            st.markdown(f"**Email:** {row.get('Email', 'Not Available')}")
            st.markdown(f"**LinkedIn:** {row.get('Linkedin', 'Not Available')}")
            st.markdown(f"**Outreach Message:**\n\n{row['outreach_message']}")


###############################################################################
# Tab 2: Enriched Company Insights (unchanged)
###############################################################################
with tab2:
    st.subheader("🔍 Enriched Company Insights")
    df_enriched = load_csv(DATA_FILES["Enriched Companies"])
    if event_filter and 'event_name' in df_enriched.columns:
        df_enriched = df_enriched[df_enriched['event_name'].isin(event_filter)]
    st.dataframe(df_enriched, use_container_width=True)

###############################################################################
# Tab 3: Stakeholders & Decision Makers 
###############################################################################
with tab3:
    st.subheader("🧑‍💼 Stakeholders & Decision Makers")
    df_stakeholders = load_csv(DATA_FILES["Companies with Stakeholders"])
    if event_filter and 'event_name' in df_stakeholders.columns:
        df_stakeholders = df_stakeholders[df_stakeholders['event_name'].isin(event_filter)]
    
    # Show only these columns
    stakeholder_cols = [
        "company_name", "event_name", 
        "Decision_Maker", "Title", "Email", "LinkedIn"
    ]
    valid_stakeholder_cols = [col for col in stakeholder_cols if col in df_stakeholders.columns]
    st.dataframe(df_stakeholders[valid_stakeholder_cols], use_container_width=True)

###############################################################################
# Tab 4: Tailored Outreach Messages (unchanged except minor variable rename)
###############################################################################
with tab4:
    st.subheader("📨 Tailored Outreach Messages")
    df_messages = load_csv(DATA_FILES["Personalized Outreach Messages"])
    if event_filter and 'event_name' in df_messages.columns:
        df_messages = df_messages[df_messages['event_name'].isin(event_filter)]
    
    st.dataframe(df_messages, use_container_width=True)

    st.markdown("### 🖋️ Message Preview")
    if 'company_name' in df_messages.columns:
        selected_company = st.selectbox(
            "Select a Company to Preview Message:", 
            df_messages['company_name'].unique()
        )
        if 'outreach_message' in df_messages.columns:
            message_preview = df_messages[df_messages['company_name'] == selected_company]['outreach_message'].values
            if message_preview.size > 0:
                st.info(message_preview[0])
            else:
                st.warning("No message found for this selection.")
        else:
            st.warning("'outreach_message' column not found in data.")
    else:
        st.warning("'company_name' column not found in data.")
###############################################################################
# Tab 5: Events Identified
###############################################################################
with tab5:
    try:
        df_events = load_csv(DATA_FILES["Event Information"])
        if not df_events.empty:
            display_cols = [
                "name", "url", "reasoning", "priority", "relevance_score"
            ]
            # Filter out missing columns safely
            valid_event_cols = [col for col in display_cols if col in df_events.columns]
            st.dataframe(df_events[valid_event_cols], use_container_width=True)
        else:
            st.warning("No data found in latest_leads.csv.")
    except Exception as e:
        st.error(f"Error loading events: {e}")
# Footer
    st.markdown("---")
    st.markdown("© 2025 DuPont Tedlar AI Dashboard | All rights reserved.")
