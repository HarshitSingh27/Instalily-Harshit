import subprocess
import logging
import argparse
import sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s]: %(message)s')

AGENT_SCRIPTS = {
    "scout": "event_scout_agent.py",
    "hunter": "company_hunter_agent.py",
    "enrich": "company_enrichment_agent.py",
    "stakeholder": "stakeholderfinder_agent.py",
    "message": "message_agent.py"
}

def run_agent(agent_script):
    try:
        logging.info(f"Running {agent_script}...")
        subprocess.run(["python", f"agents/{agent_script}"], check=True)
        logging.info(f"Completed {agent_script} successfully.")
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running {agent_script}: {e}")

def parse_arguments():
    parser = argparse.ArgumentParser(description="Agentic AI Workflow Runner")
    parser.add_argument(
        "-a", "--agent",
        choices=list(AGENT_SCRIPTS.keys()) + ['all'],
        default='all',
        help="Specify an agent to run individually or 'all' to run all agents sequentially."
    )
    return parser.parse_args()

def main():
    args = parse_arguments()

    if args.agent == 'all':
        logging.info("Running all agents sequentially...")
        for script in AGENT_SCRIPTS.values():
            run_agent(script)
    else:
        script = AGENT_SCRIPTS[args.agent]
        logging.info(f"Running selected agent: {args.agent}")
        run_agent(script)

    logging.info("Agentic AI workflow execution completed successfully!")

if __name__ == "__main__":
    main()
