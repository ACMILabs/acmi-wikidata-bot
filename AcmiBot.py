import json
import pandas
import pathlib
import pydash
import requests
import subprocess
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

# pull acmi api data.

subprocess.call(['git', 'clone', 'https://github.com/ACMILabs/acmi-api.git', '--depth', '1'])

# traverse api json to grab all acmi-side work links.

acmi_path = pathlib.Path.cwd() / 'acmi-api' / 'app' / 'json' / 'works'
acmi_files = [x for x in acmi_path.iterdir() if x.suffix == '.json']
acmi_api_links = pandas.DataFrame(columns=['acmi_id', 'wikidata_id'])

for x in acmi_files:
    with open(x) as data:
        data = json.load(data)
    if 'external_references' in data and 'id' in data:
        for y in [y for y in data['external_references'] if pydash.get(y, 'source.name') == 'Wikidata']:
            acmi_api_links.loc[len(acmi_api_links)] = [(data['id']), (pydash.get(y, 'source_identifier'))]

acmi_api_links['acmi_id'] = 'works/'+acmi_api_links['acmi_id'].astype('str')

# sparql query to wikidata query service to get all wikidata-side work links.

query = '''
  select ?acmi_id ?wikidata_id where 
  {?wikidata_id wdt:P7003 ?acmi_id; 
    service wikibase:label { bd:serviceParam wikibase:language "en" }
    }'''
acmi_wikidata_links = sparql_query(query, "https://query.wikidata.org/sparql")
acmi_wikidata_links['wikidata_id'] = acmi_wikidata_links['wikidata_id'].str.split('/').str[-1]

# identify a candidate acmi api -> wikidata statements to write across in wikidata.

candidates = pandas.merge(acmi_api_links, acmi_wikidata_links, on=acmi_wikidata_links.columns.to_list(), how='left', indicator=True)
candidate = candidates.loc[candidates._merge.isin(['left_only'])][:1].to_dict('records')

print(candidate)

# wikibaseintegrator bot code goes here