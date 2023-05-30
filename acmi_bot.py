from wikibaseintegrator import wbi_login, datatypes, WikibaseIntegrator
from wikibaseintegrator.wbi_config import config as wbi_config
from wikibaseintegrator.wbi_enums import ActionIfExists
import json
import pandas
import pathlib
import pydash
import requests
import time

def value_extract(row, col):

    ''' Extract dictionary values. '''
  
    return pydash.get(row[col], "value")
   
def sparql_query(query, service):
 
    ''' Send sparql request, and formulate results into a dataframe. '''

    r = requests.get(service, params={"format": "json", "query": query})
    data = pydash.get(r.json(), "results.bindings")
    data = pandas.DataFrame.from_dict(data)
    for x in data.columns:
        data[x] = data.apply(value_extract, col=x, axis=1)

    return data

# wikidata bot login.

login_path = pathlib.Path.cwd() / 'bot_login.json'
if not login_path.exists():
    raise Exception('Cannot find bot login credentials.')
else:
    with open(login_path) as credentials:
        credentials = json.load(credentials)

# traverse api json to grab all acmi-side links.

acmi_path = pathlib.Path.cwd() / 'acmi-api' / 'app' / 'json' / 'works'
acmi_files = [x for x in acmi_path.iterdir() if x.suffix == '.json']
acmi_api_links = pandas.DataFrame(columns=['wikidata_id', 'acmi_id'])

for x in acmi_files:

    with open(x) as data:
        data = json.load(data)

    if 'external_references' in data and 'id' in data:
        for y in [y for y in data['external_references'] if pydash.get(y, 'source.name') == 'Wikidata']:
            formatted_work_id = f"works/{data['id']}"
            acmi_api_links.loc[len(acmi_api_links)] = [(y['source_identifier']), formatted_work_id]
    
    if 'creators_primary' in data:
        for y in data['creators_primary']:
            if 'creator_wikidata_id' in y:
                if y['creator_wikidata_id']:
                    formatted_creator_id = f"creators/{y['creator_id']}"
                    acmi_api_links.loc[len(acmi_api_links)] = [(y['creator_wikidata_id']), formatted_creator_id]

# sparql query to wikidata query service to get all wikidata-side links.

query = '''
  select ?acmi_id ?wikidata_id where 
  {?wikidata_id wdt:P7003 ?acmi_id; 
    service wikibase:label { bd:serviceParam wikibase:language "en" }
    }'''
acmi_wikidata_links = sparql_query(query, "https://query.wikidata.org/sparql")
acmi_wikidata_links['wikidata_id'] = acmi_wikidata_links['wikidata_id'].str.split('/').str[-1]

# identify candidates for acmi api -> wikidata statements to write across to wikidata.

candidates = pandas.merge(acmi_api_links, acmi_wikidata_links, on=acmi_wikidata_links.columns.to_list(), how='left', indicator=True)
candidates = candidates.loc[candidates._merge.isin(['left_only'])]

# bot write code

if len(candidates):

    login_wikidata = wbi_login.Login(user=credentials['user'], password=credentials['pass'], mediawiki_api_url='https://www.wikidata.org/w/api.php')
    wbi_config['USER_AGENT'] = 'ACMIsyncbot/1.0 (https://www.wikidata.org/wiki/User:Pxxlhxslxn)'

    for data in candidates.to_dict('records')[:10]: # this limitation should be removed once bot is tested.

        time.sleep(4)

        wbi = WikibaseIntegrator(login=login_wikidata)
        wd_item = wbi.item.get(str(data['wikidata_id']), mediawiki_api_url='https://www.wikidata.org/w/api.php', login=login_wikidata)
        claim = datatypes.ExternalID(prop_nr='P7003', value=data['acmi_id'])    
        wd_item.claims.add(claim, action_if_exists=ActionIfExists.APPEND_OR_REPLACE)
        wd_item.write(summary="added ACMI public identifier.")

        print(data['wikidata_id'], 'written.')
