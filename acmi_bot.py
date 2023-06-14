"""ACMI collection to Wikidata sync robot."""

import json
import pathlib
import time

import pandas
import pydash
import requests
import sentry_sdk
from wikibaseintegrator import WikibaseIntegrator, datatypes, wbi_login
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists


def value_extract(row, column):
    """Extract dictionary values."""
    return pydash.get(row[column], 'value')


def sparql_query(query, service):
    """Send sparql request, and formulate results into a dataframe."""
    response = requests.get(service, params={'format': 'json', 'query': query}, timeout=120)
    results = pydash.get(response.json(), 'results.bindings')
    data_frame = pandas.DataFrame.from_dict(results)
    for column in data_frame.columns:
        data_frame[column] = data_frame.apply(value_extract, column=column, axis=1)
    return data_frame


# wikidata bot login.
login_path = pathlib.Path.cwd() / 'bot_login.json'
if not login_path.exists():
    raise FileNotFoundError('Cannot find bot login credentials file: bot_login.json')

with open(login_path, encoding='utf-8') as credentials:
    credentials = json.load(credentials)

# setup error tracking
sentry_sdk.init(
    dsn=credentials.get('sentry', ''),
    traces_sample_rate=1.0,
)

# traverse api json to grab all acmi-side links.
acmi_path = pathlib.Path.cwd() / 'acmi-api' / 'app' / 'json' / 'works'
acmi_files = [filename for filename in acmi_path.iterdir() if filename.suffix == '.json']
acmi_api_links = pandas.DataFrame(columns=['wikidata_id', 'acmi_id'])

for acmi_file in acmi_files:
    with open(acmi_file, encoding='utf-8') as data:
        data = json.load(data)

    if 'external_references' in data and 'id' in data:
        for external_reference in data['external_references']:
            if pydash.get(external_reference, 'source.name') == 'Wikidata':
                formatted_work_id = f"works/{data['id']}"
                acmi_api_links.loc[len(acmi_api_links)] = [
                    (external_reference['source_identifier']),
                    formatted_work_id,
                ]

    if 'creators_primary' in data:
        for y in data['creators_primary']:
            if 'creator_wikidata_id' in y:
                if y['creator_wikidata_id']:
                    formatted_creator_id = f"creators/{y['creator_id']}"
                    acmi_api_links.loc[len(acmi_api_links)] = \
                        [(y['creator_wikidata_id']), formatted_creator_id]

# sparql query to wikidata query service to get all wikidata-side links.
QUERY = '''
  select ?acmi_id ?wikidata_id where
   {?wikidata_id wdt:P7003 ?acmi_id;
    service wikibase:label { bd:serviceParam wikibase:language "en" }
    }'''
acmi_wikidata_links = sparql_query(QUERY, 'https://query.wikidata.org/sparql')
acmi_wikidata_links['wikidata_id'] = acmi_wikidata_links['wikidata_id'].str.split('/').str[-1]

# identify candidates for acmi api -> wikidata statements to write across to wikidata.
candidates = pandas.merge(
    acmi_api_links,
    acmi_wikidata_links,
    on=acmi_wikidata_links.columns.to_list(),
    how='left',
    indicator=True,
)
candidates = candidates.loc[candidates._merge.isin(['left_only'])]  # pylint: disable=protected-access

# bot write code
if len(candidates):
    login_wikidata = wbi_login.Login(
        user=credentials['user'],
        password=credentials['pass'],
        mediawiki_api_url='https://www.wikidata.org/w/api.php',
    )
    wbi_config['USER_AGENT'] = 'ACMIsyncbot/1.0 (https://www.wikidata.org/wiki/User:Pxxlhxslxn)'

    # this limitation should be removed once bot is tested.
    for data in candidates.to_dict('records')[:10]:
        time.sleep(4)

        wbi = WikibaseIntegrator(login=login_wikidata)
        wd_item = wbi.item.get(
            str(data['wikidata_id']),
            mediawiki_api_url='https://www.wikidata.org/w/api.php',
            login=login_wikidata,
        )
        claim = datatypes.ExternalID(prop_nr='P7003', value=data['acmi_id'])
        wd_item.claims.add(claim, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
        wd_item.write(summary="added ACMI public identifier.")

        print(data['wikidata_id'], 'written.')
