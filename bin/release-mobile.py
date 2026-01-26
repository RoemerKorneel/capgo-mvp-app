#!/usr/bin/env python3
import os
import subprocess
import sys
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

init(autoreset=True)


def main() -> None:
    with Halo(text="Checking whether the GitHub CLI is installed...", spinner='dots', color='yellow') as spinner:
        if os.system("gh --version >/dev/null 2>&1") != 0:
            spinner.fail('You do not have the "gh" command installed. This is required to continue.')
            print("\U0001F3C4 A browser window will now open to install the GitHub CLI.")
            webbrowser.open_new_tab("https://cli.github.com")
            exit(1)
        else:
            spinner.succeed('GitHub CLI is installed.')

    with Halo(text="Checking for existing release PR...", spinner='dots', color='yellow',
              text_color='blue') as spinner:
        result = subprocess.run(
            ["gh", "pr", "list", "--head", "release-mobile", "--base", "dev", "--json", "number,url"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            import json
            prs = json.loads(result.stdout)
            if prs:
                spinner.fail(f"A release PR already exists: {prs[0]['url']}")
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
        result = subprocess.run(
            ["gh", "workflow", "run", "create-mobile-release.yml", "-f", f"release_type={release_type}"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            spinner.fail(f"Failed to trigger workflow: {result.stderr}")
            exit(1)
        spinner.succeed("Mobile release workflow triggered.")

    with Halo(text="Waiting for workflow to start...", spinner='dots', color='yellow',
              text_color='blue') as spinner:
        # Wait a moment for the workflow to register
        import time
        time.sleep(3)

        # Get the latest run
        result = subprocess.run(
            ["gh", "run", "list", "--workflow=create-mobile-release.yml", "--limit=1", "--json", "databaseId,url"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            import json
            runs = json.loads(result.stdout)
            if runs:
                run_url = runs[0]["url"]
                spinner.succeed("Workflow started.")
                print(f"\n{Fore.BLUE}\U00002139{Fore.RESET} View the workflow run: {run_url}")
                print(f"{Fore.BLUE}\U00002139{Fore.RESET} The PR will be created automatically when the workflow completes.")
                webbrowser.open_new_tab(run_url)
            else:
                spinner.warn("Workflow triggered but couldn't retrieve run URL.")
        else:
            spinner.warn("Workflow triggered but couldn't retrieve run URL.")


if __name__ == "__main__":
    main()
