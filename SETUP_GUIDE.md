# SIP Tickets Miner Setup Guide

This guide covers installing the project dependencies, setting up GitHub
Copilot CLI, and starting SIP Tickets Miner locally on Windows. It assumes the
application is for local evaluation on the user's computer.

## Requirements

- Windows and PowerShell 6 or later (required by Copilot CLI on Windows).
- Git, if you need to clone the repository.
- Python 3; Python 3.14 is recommended. The web server uses only the Python
  standard library, so no Python packages need to be installed with `pip`.
- A GitHub account with an active Copilot subscription.
- GitHub Copilot CLI. If it is not already installed, the app can install it
  using Node.js 22 or later and npm.
- The included ticket export, `resources/issues_export.csv`.
- An available local port, `8765`.

Check installed tools in PowerShell:

```powershell
git --version
python --version
node --version
npm --version
```

Node.js and npm are only required if Copilot CLI needs to be installed. If
`python` is not recognized, try `py --version` and use `py` in the commands
below.

## Get the Project

If the repository is not already on your computer, clone it and enter the
project directory:

```powershell
git clone https://github.com/djoNikola/ai_workshop_26.git
Set-Location .\ai_workshop_26
```

If you already have the repository, open PowerShell in its root directory (the
directory containing `README.md`). Confirm the ticket export is present:

```powershell
Test-Path .\resources\issues_export.csv
```

The result should be `True`.

## Start the Application

From the repository root, run:

```powershell
python chatbot/sip-chatbot-web.py
```

If `python` is not available, use:

```powershell
py chatbot/sip-chatbot-web.py
```

The server listens on `127.0.0.1:8765` and attempts to open the home page in a
browser. If it does not, open <http://localhost:8765/> manually. Keep the
PowerShell window open while using the app; press `Ctrl+C` in that window to
stop the server. Always use the local URL rather than opening an HTML file
directly.

## Set Up Copilot CLI

The home page displays a setup panel. The analysis pages become available when
Copilot CLI is installed and signed in.

1. If the panel says Copilot is not installed, select **Yes, install**. The app
   runs `npm install -g @github/copilot` and displays the install output.
2. Wait for the panel to update. If it reports that Copilot is not in `PATH`,
   restart PowerShell and the app, then check the panel again.
3. If the panel says you are not signed in, select **Sign in**.
4. Open the device sign-in URL shown in the panel, enter the displayed code,
   and approve access using the intended GitHub account.
5. Wait until the panel reports **Ready**. The **Send** control is disabled
   until setup is complete.

For Copilot CLI installation details and requirements, see the
[official GitHub installation guide](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli).

## Verify the Setup

With the server running, confirm that `http://localhost:8765/` opens and the
setup panel reports **Ready**. The application pages are:

- Ticket lookup: <http://localhost:8765/>
- Issue categorization: <http://localhost:8765/categorize>
- Assignee recommendations: <http://localhost:8765/recommend>

To run the unit tests, open a second PowerShell window at the repository root
and run:

```powershell
python -m unittest discover -s chatbot
```

## Troubleshooting

| Problem | Resolution |
|---|---|
| `python` is not recognized | Try `py chatbot/sip-chatbot-web.py`; otherwise install Python 3 and reopen PowerShell. |
| `npm was not found` | Install Node.js 22 or later, reopen PowerShell, and check `npm --version`. npm is needed only to install Copilot CLI through the app. |
| Copilot is installed but not detected | Restart PowerShell and the server so they see the current `PATH`. |
| Device sign-in fails | Repeat sign-in and confirm you approved it with the GitHub account that has an active Copilot subscription. |
| The page cannot reach the server | Confirm the server process is still running and use `http://localhost:8765/`. |
| Port `8765` is already in use | Stop the other local process using that port, then restart the app. |
| The setup panel does not reach **Ready** | Read the panel and server terminal for installation or login errors; analysis requests require the CLI to be ready. |

## Data Privacy

The CSV is read locally, but each analysis request can send the query and up to
30 relevant ticket excerpts to GitHub Copilot. Excerpts may contain ticket
IDs, summaries, descriptions, statuses, issue types, and assignees. Use the
real export only if the data owner has approved this; otherwise, use an approved
anonymized or synthetic export.

## Why This Guide Does Not Cover Deployment

The current application is a local proof of concept: it binds only to
`127.0.0.1`, has no authentication or multi-user controls, and the project
scope excludes hosting. It also processes ticket data through the signed-in
Copilot account. Deployment instructions would suggest a level of security and
operational readiness that this application does not currently provide. This
guide therefore covers installation and local startup only; deployment would
need a separate scope decision, data approval, and security review.