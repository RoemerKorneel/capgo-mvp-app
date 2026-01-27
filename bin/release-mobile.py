#!/usr/bin/env python3
import os
import subprocess
import sys
import time
import webbrowser

# Automatically install dependencies before continuing (without printing the output of the command).
# (And use the currently running Python interpreter via sys.executable to install the dependencies, instead of the system Python.)
requirements_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
subprocess.run(
    [sys.executable, "-m", "pip", "install", "-r", requirements_path],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    check=True
)

from halo import Halo
from colorama import Fore, init
from github import Github, Auth

init(autoreset=True)

REPO_NAME = "Roempie/capgo-mvp-app"
WORKFLOW_FILE = "create-mobile-release-pr.yml"


def get_github_token() -> str:
    token = os.popen("gh auth token").read().strip()
    return token


def main() -> None:
    with Halo(text="Checking whether the GitHub CLI is installed...", spinner='dots', color='yellow') as spinner:
        if os.system("gh --version >/dev/null 2>&1") != 0:
            spinner.text_color = 'red'
            spinner.fail('You do not have the "gh" command installed. This is required to continue.')
            print("\U0001F3C4 A browser window will now open to install the GitHub CLI.")
            webbrowser.open_new_tab("https://cli.github.com")
            exit(1)
        else:
            spinner.succeed('GitHub CLI is installed.')

    g = Github(auth=Auth.Token(get_github_token()))
    repo = g.get_repo(REPO_NAME)

    with Halo(text="Checking for existing release PR...", spinner='dots', color='yellow',
              text_color='blue') as spinner:
        prs = list(repo.get_pulls(state='open', base='dev', head='release-mobile'))
        existing_pr = next((pr for pr in prs if pr.head.ref == 'release-mobile'), None)
        if existing_pr:
            spinner.fail(f"A release PR already exists: {existing_pr.html_url}")
            print(f"{Fore.BLUE}\U00002139{Fore.RESET} Close the existing PR before creating a new release.")
            exit(1)
        spinner.succeed("No existing release PR found.")

    # Get release type from user
    print(f"\n{Fore.CYAN}Select release type:{Fore.RESET}")
    print("  1. patch (default)")
    print("  2. minor")
    print("  3. major")
    choice = input(f"{Fore.YELLOW}Enter choice [1]: {Fore.RESET}").strip() or "1"
    release_type = {"1": "patch", "2": "minor", "3": "major"}.get(choice, "patch")

    with Halo(text=f"Triggering mobile release workflow ({release_type})...", spinner='arrow3', color='yellow',
              text_color='blue') as spinner:
        workflow = repo.get_workflow(WORKFLOW_FILE)
        success = workflow.create_dispatch(ref="dev", inputs={"release_type": release_type})
        if not success:
            spinner.fail("Failed to trigger workflow")
            exit(1)
        spinner.succeed("Mobile release workflow triggered.")

    with Halo(text="Waiting for release PR to be created... (~30s)", spinner='dots', color='yellow',
              text_color='blue') as spinner:
        release_pr = None
        for i in range(30):  # Try for ~60 seconds
            spinner.text = f"Waiting for release PR to be created, may take up to 60s... ({(i + 1) * 2}s)"
            time.sleep(2)
            prs = list(repo.get_pulls(state='open', base='dev', head='release-mobile'))
            release_pr = next((pr for pr in prs if pr.head.ref == 'release-mobile'), None)
            if release_pr:
                break

        if release_pr:
            spinner.succeed(f"Release PR created: {release_pr.html_url}")
            webbrowser.open_new_tab(release_pr.html_url)
        else:
            spinner.fail("Timed out waiting for PR. Check GitHub Actions for errors.")
            webbrowser.open_new_tab(f"https://github.com/{REPO_NAME}/actions/workflows/{WORKFLOW_FILE}")


if __name__ == "__main__":
    main()
