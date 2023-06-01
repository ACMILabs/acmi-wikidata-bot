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
