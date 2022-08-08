#!/usr/bin/python3

import os.path
from datetime import datetime
import json
import multiprocessing


class Result:

    def __init__(self, description, status=False, data=None):

        self.data = data

        if not isinstance(status, type(True)):
            self.status = False
            self.description = ('Parameters not passed correctly '
                                'to the class "Result"')
        else:
            self.status = status
            self.description = str(description).strip()

    def __eq__(self, other):

        if isinstance(other, type(True)):
            return self.status
        else:
            return self is other

    def __bool__(self):
        return self.status

    def __str__(self):

        result = ''

        if self.data:
            if self.description:
                result = ''.join([
                    'Result: ',
                    str(self.status),
                    ' (',
                    self.description.strip(),
                    '), data: ',
                    str(self.data)
                ])
            else:
                result = ''.join([
                    'Result: ',
                    str(self.status),
                    ', data: ',
                    str(self.data)
                ])
        else:
            if self.description:
                result = ''.join([
                    'Result: ',
                    str(self.status),
                    ' (',
                    self.description.strip(),
                    ')'
                ])
            else:
                result = ''.join([
                    'Result: ',
                    str(self.status)
                ])

        return result

    def __repr__(self):
        return self.json
    
    @property
    def json(self) -> str:
        result = ''
        if self.data:
            result = json.dumps(
                {
                    'status': self.status,
                    'description': self.description,
                    'data': self.data
                }
            )
        else:
            result = json.dumps(
                {
                    'status': self.status,
                    'description': self.description
                }
            )
        return result

def json_to_structure(strJSON: str) -> dict or list:

    try:
        return json.loads(strJSON)
    except:
        return {}

def str_to_datetime(value: str, formatStr: str) -> datetime:

    nullDate = datetime(1, 1, 1)

    if not isinstance(value, type('')) or not value:
        return nullDate

    if not isinstance(formatStr, type('')) or not formatStr:
        return nullDate

    try:
        return datetime.strptime(value.strip(), formatStr)
    except:
        return nullDate

def convert_to_numeric_str(value: str or int or float) -> str:

    if ((not isinstance(value, str) and not isinstance(value, int) and
        not isinstance(value, float)) or not value):
        return '0'

    strValue = value
    if not isinstance(value, str):
        strValue = str(value)

    if not strValue or strValue == '0':
        return '0'
    
    try:
        clearText = ''.join([x for x in strValue if x.isdigit()
                             or x == '.'
                             or x == ','
                             or x == '-'])
        clearText = clearText.replace(',', '.')

        if len(clearText.split('.')) > 2:
            return ''

        leadingZeros = True
        counter = 0
        resultText = ''
        for symbol in clearText:
            counter += 1
            if symbol == '-' and counter > 1:
                return ''
            if symbol != '0' and symbol != '-' and leadingZeros:
                leadingZeros = False
            if symbol == '0' and leadingZeros:
                continue
            resultText = ''.join([resultText, symbol])

        if resultText and resultText[0] == '.':
            resultText = ''.join(['0',resultText])
        
        return resultText

    except:
        return ''

def convert_to_lower_simple_chars(value: str) -> str:

    if not isinstance(value, type('')) or not value:
        return ''

    allowedChars = 'abcdefghijklmnopqrstuvwxyz'
    allowedChars += 'абвгдеёжзийклмнопрстуфхцчшщъыьэюя'

    try:
        return ''.join([
            x.lower() for x in value if not allowedChars.find(x.lower()) == -1
        ])

    except:
        return ''

def list_cards_by_threads(site:str, login:str, threadCountRatio:int = 1) -> dict:

    result = {
        'listsCards': [],
        'threads': [],
        'resultsThreads': []
    }

    listCards = get_list_cards_from_file(site, login)
    if not listCards:
        return result
    
    totalThreads = round(multiprocessing.cpu_count() * threadCountRatio, 0)
    if totalThreads > 1:
        if len(listCards) >= totalThreads:
            lenList = len(listCards) // (totalThreads - 1)
        else:
            lenList = 1
    else:
        lenList = len(listCards)

    listCardsNew = []
    for i in range(1, len(listCards) + 1):

        listCardsNew.append(listCards[i - 1])

        if (i // lenList) == (i / lenList):
            result['listsCards'].append(listCardsNew)
            listCardsNew = []

        if len(result['listsCards']) == totalThreads:
            break

    if listCardsNew:
        result['listsCards'].append(listCardsNew)

    if i < len(listCards) and i > 1:
        counterLists = 0
        for n in range(i + 1, len(listCards) + 1):
            listCardCurrent = result['listsCards'][counterLists]
            listCardCurrent.append(listCards[n - 1])
            result['listsCards'][counterLists] = listCardCurrent
            counterLists += 1

    result['threads'] = [None] * len(result['listsCards'])
    result['resultsThreads'] = [None] * len(result['listsCards'])

    return result

def thread_function(args, resultsThreads: list, indexThread) -> None:

    site = args['site']
    if site.parsing:
        result = site.login(args['login'], args['password'])
    else:
        result = Result('OK', True)
    
    if result:
        if args['nameFunction'] == 'getDataCards':
            resultsThreads[indexThread] = site.getDataCards(args['listCards'])
        elif args['nameFunction'] == 'getListTransactions':
            resultsThreads[indexThread] = site.getListTransactions(
                args['listCards'],
                args['periodStart'],
                args['periodEnd'])
        else:
            resultsThreads[indexThread] = Result(''.join([
                'The function "',
                args['nameFunction'],
                '" is not found']))
    else:
        resultsThreads[indexThread] = result
    
    if site.parsing:
        site.__del__()

def id_card(site:str, login:str, cardNumber: str) -> str:
    
    result = ''
    if not site or not login:
        return result

    listCards = get_list_cards_from_file(site, login)

    for cardData in listCards:
        if convert_to_numeric_str(cardData['number']) == convert_to_numeric_str(cardNumber):
            result = convert_to_numeric_str(cardData['id'])
            break

    return result

def write_list_cards_to_file(site:str, login:str, listCards:list) -> None:

    listCardsToWrite = []
    for cardData in listCards:
        listCardsToWrite.append({
            'id': cardData['id'],
            'number': cardData['number'],
            'status': cardData['status'],
            'site': site,
            'login': login
        })

    if os.path.exists('data_cards.json'):
        jsonData = []
        with open('data_cards.json', 'r', encoding='utf-8') as text:
            jsonData = json.load(text)

        for data in jsonData:
            if data['site'] != site or data['login'] != login:
                listCardsToWrite.append(data)
    
    with open('data_cards.json', 'w', encoding='utf-8') as jsonFile:
        json.dump(listCardsToWrite, jsonFile)

def get_list_cards_from_file(site:str, login:str) -> list:

    listCards = []

    if os.path.exists('data_cards.json'):
        jsonData = []
        with open('data_cards.json', 'r', encoding='utf-8') as text:
            jsonData = json.load(text)

        for data in jsonData:
            if data['site'] == site and data['login'] == login:
                listCards.append(data)
    
    return listCards

def arg_from_args(kwagrs, nameArg:str, defaultValue):

    result = kwagrs.get(nameArg)
    
    if result:
        return result
    else:
        return defaultValue
