# ACMI Wikidata Bot

Sync bot to push ACMI API Wikidata links to Wikidata.

## Run locally

* Install a virtual environment: `virtualenv venv -p 3.9`
* Activate that environment: `source venv/bin/activate`
* Install the Python dependencies: `pip install -r requirements.txt`
* Copy the login JSON template and fill in your details: `cp bot_login.tmpl.json bot_login.json`
* Run the sync: `./run.sh`

## Check the code for errors

* Run the code linting: `./lint.sh`

## Exception tracking

To keep track of exceptions when running the sync, add your Sentry DSN to `bot_login.json` under `sentry`.

ACMI exceptions are sent to: https://acmi.sentry.io/projects/wikidata-bot
