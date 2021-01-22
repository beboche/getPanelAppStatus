import os
import sys
import re
import argparse
import urllib3
import certifi
import json
import time
from datetime import datetime

# Connect to panelApp REST API with a list of genes and of panels and
# returns a part of the JSONs in a tabulated txt file

panel_app_api = 'https://panelapp.genomicsengland.co.uk/api/v1/'


def log(level, text):
    localtime = time.asctime( time.localtime(time.time()) )
    if level == 'ERROR':
        sys.exit('[{0}]: {1} - {2}'.format(level, localtime, text))
    print('[{0}]: {1} - {2}'.format(level, localtime, text))


def getListFormArgs(arg_type=None, arg_value=None):
    #arg_value can be a txt file or a coma-separated list of panel IDs (numeric) or gene symbols (alpha-numeric)
    if arg_type in ('panel', 'gene') and \
            arg_value:
        match_obj = None
        if arg_type == 'gene':
            match_obj = re.search(r'^([\w\.,-]+)$', arg_value)
        else:
            match_obj = re.search(r'^([\d,]+)$', arg_value)
        if match_obj:
            return re.split(',', match_obj.group(1))
        else:
            # check if file has an extension
            match_obj = re.search(r'\.txt$', arg_value)
            if match_obj and \
                    os.path.isfile(arg_value):
                # read the file and returns a list of genes/panels
                file = arg_value
                entity_list = []
                for entity in open(file).readlines():
                    # log('DEBUG', entity.rstrip())
                    entity_list.append(entity.rstrip())
                entity_list.sort()
                return entity_list
    else:
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Connect to panelApp REST API with a list of genes and of panels and returns a part of the JSONs in a tabulated txt file',
        usage='python3 getPanelAppStatus.py -g <gene symbol[,gene_symbol]>, -p <panelApp_id[,panelApp_id]>'
    )
    parser.add_argument('-g', '--gene-symbols', default='', required=True,
                        help='Path to a gene list as a .txt file (one gene HGNC symbol per line), OR list of gene symbols coma-separated if mutliple symbols')
    parser.add_argument('-p', '--panel-ids', default='', required=True,
                        help='Path to a panelApp panel ID list as a .txt file (one ID per line), OR list of panel IDs coma-separated if mutliple IDs')
    args = parser.parse_args()
    #headers
    header = {
        'Accept': 'application/json',
        'User-Agent': 'python-requests Python/{}.{}.{}'.format(sys.version_info[0], sys.version_info[1], sys.version_info[2]),
    }

    http = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where())
    match_obj = None
    if args.gene_symbols and \
            args.panel_ids:
        # check whether we have a list or a path
        gene_list = getListFormArgs('gene', args.gene_symbols)        
        panel_list = getListFormArgs('panel', args.panel_ids)
       
        if not panel_list or \
                not gene_list:
            log('ERROR', 'Bad format for gene symbols or panel IDs')
        log('INFO', 'Gene symbols: {}'.format(gene_list))
        log('INFO', 'paneApp IDs: {}'.format(panel_list))
        log('INFO', '{0} genes and {1} panels submitted'.format(len(gene_list), len(panel_list)))
        # panel_app_summary = {}
        panel_app_content = 'Gene Symbol\tpanelApp Name\tpanelApp ID\tConfidence level\tPenetrance\tMode of inheritence\tevidence\n'
        for gene_symbol in gene_list:
            panel_app_url = '{0}genes/{1}'.format(panel_app_api, gene_symbol)
            panel_app_json = None
            try:
                panel_app_json = json.loads(http.request('GET', panel_app_url, headers=header).data.decode('utf-8'))
            except Exception:
                log('WARNING', 'No panelApp answer for gene {}'.format(gene_symbol))
            # log('DEBUG', panel_app_json)
            if panel_app_json['count'] == 0:
                log('WARNING', 'panelApp does not know gene {} -- Check HGNC validity?'.format(gene_symbol))
            for panel_dict in panel_app_json['results']:
                # log('DEBUG', 'Panel: {}'.format(panel_dict['panel']))
                if 'id' in panel_dict['panel']:
                    if str(panel_dict['panel']['id']) in panel_list:
                        # log('DEBUG', 'Panel ID {0} found for gene {1}'.format(panel_dict['panel']['id'], gene_symbol))
                        # panel_app_summary['{0}_{1}'.format(gene_symbol, panel_dict['panel']['id'])] = {
                        #     'gene_symbol': gene_symbol,
                        #     'panelApp_id': panel_dict['panel']['id'],
                        #     'confidence_level': panel_dict['confidence_level'],
                        #     'penetrance': panel_dict['penetrance'],
                        #     'panelApp_name': panel_dict['panel']['name'],
                        #     'evidence': panel_dict['evidence'][0],
                        #     'mode_of_inheritance': panel_dict['mode_of_inheritance']
                        # }
                        panel_app_content += '{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\n'.format(
                            gene_symbol,
                            panel_dict['panel']['name'],
                            panel_dict['panel']['id'],
                            panel_dict['confidence_level'],
                            panel_dict['penetrance'],
                            panel_dict['mode_of_inheritance'],
                            ','.join(panel_dict['evidence'])
                            #panel_dict['evidence'][0]
                        )
        # log('DEBUG', panel_app_summary)
        now = datetime.now()
        dt_string = now.strftime("%Y_%m_%d_%H_%M_%S")
        panelAppFile = open('results/panelApp_{0}.tsv'.format(dt_string), "w")
        panelAppFile.write(panel_app_content)
        panelAppFile.close()

if __name__ == '__main__':
    main()