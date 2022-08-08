#!/usr/bin/python3

import os
import tempfile
from lib.common import general
from lib.common.general import Result
from lib.common.general import list_cards_by_threads
from lib.sites.tatneft import TATNeft
from lib.sites.rosneft import RNCart
from lib.sites.petrolplus import PetrolPlus
from datetime import datetime
from datetime import timedelta
from flask import Flask
from flask import request
from flask import make_response
from threading import Thread


app = Flask(__name__)

chromedriver = '/srv/gate_pars/bin/chromedriver'

@app.route("/")
def index():
    return 'text: Hello'

@app.route("/api/<nameFunction>", methods=['GET'])
def api_get(nameFunction):
    
    startDate = datetime.now()
    nameSite = request.args.get('site')
    getListTransactionsByReport = request.args.get('ByReport')

    if (nameFunction == 'getDataCards' or
       (nameFunction == 'getListTransactions' and (nameSite == 'tatneft' and getListTransactionsByReport != 'true'))):

        if nameSite != 'tatneft':
            api_get('getListCards')
            threadCountRatio = 10
        else:
            if nameFunction == 'getListTransactions':
                threadCountRatio = 2
            else:
                threadCountRatio = 1

        nameParametrLogin = 'login'
        if nameSite == 'petrolplus':
            nameParametrLogin = 'api_key'
        
        dataThreads = list_cards_by_threads(
            nameSite,
            request.args.get(nameParametrLogin),
            threadCountRatio
        )

        if dataThreads.get('threads'):

            for indexThread in range(len(dataThreads['threads'])):
                with tempfile.TemporaryDirectory() as tempDir:
                    result = check_parameters(nameFunction, request.args, tempDir)
                    if result:
                        params = result.data
                        params['login'] = request.args.get('login')
                        params['password'] = request.args.get('password')
                        params['nameFunction'] = nameFunction
                        params['listCards'] = dataThreads['listsCards'][indexThread]

                        dataThreads['threads'][indexThread] = Thread(
                            target=general.thread_function,
                            args=(params, dataThreads['resultsThreads'], indexThread))
                        dataThreads['threads'][indexThread].start()

            for indexThread in range(len(dataThreads['threads'])):
                dataThreads['threads'][indexThread].join()

            result = Result('Successful', True, [])
            for resultThread in dataThreads['resultsThreads']:
                if resultThread:
                    result.data += resultThread.data
                else:
                    result = resultThread
                    break
    else:

        with tempfile.TemporaryDirectory() as tempDir:

            result = check_parameters(nameFunction, request.args, tempDir)
            if result:
                params = result.data
                site = params['site']

                if site.parsing:
                    result = site.login(params['login'], params['password'])
                else:
                    result = Result('OK',True)
                
                if result:
                    if nameFunction == 'getBalance':
                        result = site.getBalance()

                    elif nameFunction == 'getListCards':
                        result = site.getListCards()

                    elif nameFunction == 'getDataCard':
                        result = site.getDataCard(params['numberCard'])
                        
                    elif nameFunction == 'getListTransactions':
                        if getListTransactionsByReport == 'true':
                            result = site.getListTransactionsByReport(
                                params['periodStart'],
                                params['periodEnd'])
                        else:
                            result = site.getListTransactions(
                                params['periodStart'],
                                params['periodEnd'])

                    elif nameFunction == 'getListTransactionsByCard':
                        result = site.getListTransactionsByCard(
                            params['numberCard'],
                            params['periodStart'],
                            params['periodEnd'])

    result.description = ''.join([
        result.description,
        '; ',
        'Running time:', str(datetime.now() - startDate)
    ])

    codeResponse = 200
    if not result:
        codeResponse = 501

    response = make_response(result.json, codeResponse)
    response.headers['Content-Type'] = 'application/json'

    return response

@app.route("/api/<nameFunction>", methods=['POST'])
def api_post(nameFunction):
    
    startDate = datetime.now()

    with tempfile.TemporaryDirectory() as tempDir:

        result = check_parameters(nameFunction, request.args, tempDir)
        if result:
            params = result.data
            site = params['site']

            if site.parsing:
                result = site.login(params['login'], params['password'])
            else:
                result = Result('OK',True)
            
            if result:
                if nameFunction == 'setStatusCard':
                    result = site.setStatusCard(
                        params['numberCard'],
                        params['status'])

                elif nameFunction == 'setLimitCard':
                    result = site.setLimitCard(
                        params['numberCard'],
                        params['value'],
                        params['category'],
                        params['period'],
                        params['currency'],
                        request.args.get('group'))

                elif nameFunction == 'editLimitCard':
                    result = site.editLimitCard(
                        params['numberCard'],
                        params['limitID'],
                        params['value'])

                elif nameFunction == 'delLimitCard':
                    result = site.delLimitCard(
                        params['numberCard'],
                        params['limitID'])

    result.description = ''.join([
        result.description,
        '; ',
        'Running time:', str(datetime.now() - startDate)
    ])

    codeResponse = 200
    if not result:
        codeResponse = 501

    response = make_response(result.json, codeResponse)
    response.headers['Content-Type'] = 'application/json'

    return response

def check_parameters(nameFunction:str, args:dict, tempDir:str) -> Result:

    result = Result(''.join([
        'The "',
        nameFunction,
        '" function could not be executed']))

    paramsBase = [
        'site',
        'login',
        'password'
    ]

    availableFunctions = {
        'getListTransactions': [
            'periodStart',
            'periodEnd'
        ],
        'getListTransactionsByCard': [
            'numberCard',
            'periodStart',
            'periodEnd'
        ],
        'getBalance': [],
        'getListCards': [],
        'setStatusCard': [
            'numberCard',
            'status'
        ],
        'getDataCards': [],
        'getDataCard': [
            'numberCard'
        ],
        'setLimitCard': [
            'numberCard',
            'value',
            'category',
            'period',
            'currency'
        ],
        'delLimitCard': [
            'numberCard',
            'limitID'
        ],
        'editLimitCard': [
            'numberCard',
            'limitID',
            'value'
        ]
    }

    if availableFunctions.get(nameFunction) is None:
        result.description = ''.join([
            'Function "',
            nameFunction,
            '" not found'])
        return result

    paramsCheck = paramsBase + availableFunctions.get(nameFunction)
    params = {}

    for param in paramsCheck:
        inputParam = args.get(param)
        if not inputParam:
            if (param == 'login' or param == 'password') and args.get('site') == 'petrolplus':
                continue
            result.description = ''.join([
                'The "',
                param,
                '" parameter is not filled in correctly'])
            return result
        else:
            params[param] = inputParam

    if params['site'] == 'petrolplus':
        params.update({'site': PetrolPlus(
            general.arg_from_args(args, 'api_key','') 
        )})
        result.description = 'Successful'
        result.status = True
    elif params['site'] == 'tatneft':
        params.update({'site': TATNeft(chromedriver, tempDir)})
        result.description = 'Successful'
        result.status = True
    elif params['site'] == 'rosneft':
        params.update({'site': RNCart(
            general.arg_from_args(args, 'login',''),
            general.arg_from_args(args, 'password',''),
            general.arg_from_args(args, 'contract','')
        )})
        result.description = 'Successful'
        result.status = True
    else:
        result.description = ''.join([
            'Site "',
            params['site'],
            '" not found'])
        result.status = False
        params.update({'site': None})

    result.data = params

    return result

if __name__ == '__main__':
    app.run(debug=True)
