#!/usr/bin/python3

from hashlib import new
import requests
import json
import uuid
from datetime import datetime, timedelta
from lib.common import parsing
from lib.common.general import Result
from lib.common.general import arg_from_args
from lib.common.general import json_to_structure
from lib.common.general import convert_to_numeric_str
from lib.common.general import convert_to_lower_simple_chars
from lib.common.general import write_list_cards_to_file
from lib.common.general import get_list_cards_from_file

class PetrolPlus():

    def __init__(self, api_key:str):
        self.url = 'https://online.petrolplus.ru'
        self.api_key = api_key
        self.parsing = False

    @property
    def urns(self) -> dict:
        return {
            'setStatusCard': {
                'active': '/public-api/v2/recording/cards/{cardNumber}/status',
                'block': '/public-api/v2/recording/cards/{cardNumber}/status'
            },
            'getListCards': '/api/public-api/v2/cards',
            'getBalance': '/api/public-api/v2/balance',
            'getLimits': '/api/public-api/v2/cards/{cardNumber}/limits',
            'getListTransactionsByCard': '/api/public-api/v2/cards/{cardNumber}/transactions',
            'getListTransactions': '/api/public-api/v2/transactions',
            'setLimitCard': '/public-api/v2/recording/cards/{cardNumber}/purse-balance',
            'editLimitCard': '/public-api/v2/recording/cards/{cardNumber}/purse-balance',
            'delLimitCard': '/public-api/v2/recording/cards/{cardNumber}/purse-balance'
        }
    
    @property
    def listGroupServicesFuel(self) -> list:
        return [3, 4, 5, 6, 7, 8, 33, 51, 52, 97, 273, 309]

    def setStatusCard(self, numberCard:str, status:str) -> Result:
        
        urn = self.urns.get('setStatusCard').get(status)
        urn = urn.replace('{cardNumber}', numberCard)

        idStatus = 1
        if status == 'block':
            idStatus = 0

        params = {
            'format': 'json'
        }

        argsRequest = {
            'idStatus': idStatus
        }

        response = requests.post(
            ''.join([self.url, urn]),
            headers = {
                'Content-Type': 'Application/JSON',
                'Authorization': self.api_key
            },
            params = params,
            data = json.dumps(argsRequest)
        )

        return Result(response.reason, response.status_code == 200, response.text)

    def getListCards(self) -> Result:
        
        listCards = []
        result = Result(
            'Couldn\'t get the list cards',
            False,
            listCards
        )

        urn = self.urns.get('getListCards')

        params = {
            'format': 'json'
        }

        response = requests.get(
            ''.join([self.url, urn]),
            headers = {
                'Content-Type': 'Application/JSON',
                'Authorization': self.api_key
            },
            params = params
        )

        if not response.status_code == 200:
            return result

        jsonData = json_to_structure(response.text)

        for data in jsonData.get('cards'):
            listCards.append(
                {
                    'id': str(data['cardNum']),
                    'number': str(data['cardNum']),
                    'status': parsing.code_status(self, data['idStatus'])
                }
            )
        
        if listCards:
            result = Result('Successfull', True, listCards)
            write_list_cards_to_file('petrolplus', self.api_key, listCards)

        return result

    def getBalance(self) -> Result:
        
        result = {
            'balance': 0,
            'credit': 0,
            'available': 0
        }
        urn = self.urns.get('getBalance')

        params = {
            'format': 'json'
        }

        response = requests.get(
            ''.join([self.url, urn]),
            headers = {
                'Content-Type': 'Application/JSON',
                'Authorization': self.api_key
            },
            params = params
        )

        if response.status_code == 200:
            jsonData = json_to_structure(response.text)
            result['balance'] = jsonData['balance']

        return Result(response.reason, response.status_code == 200, result)

    def getDataCards(self, cards: list) -> Result:

        dataCards = []
        for cardData in cards:
            result = self.getDataCard(cardData['number'], cardData['status'])
            if result:
                dataCards.append(result.data)
            else:
                break

        if dataCards and result:
            return Result('Successful', True, dataCards)
        else:
            return Result(
                'Couldn\'t get a list of limits for fuel cards')

    def getDataCard(self, numberCard: str, status:str = None) -> Result:

        if not status:
            listCards = get_list_cards_from_file('petrolplus', self.api_key)
            for dataCard in listCards:
                if dataCard['number'] == numberCard:
                    status = dataCard['status']
                    break

        dataCard = {
            'number': numberCard,
            'status': status,
            'limits': []
        }

        result = Result('Couldn\'t get a data for fuel cards')
        urn = self.urns.get('getLimits')
        urn = urn.replace('{cardNumber}', numberCard)

        params = {
            'format': 'json'
        }

        response = requests.get(
            ''.join([self.url, urn]),
            headers = {
                'Content-Type': 'Application/JSON',
                'Authorization': self.api_key
            },
            params = params
        )

        if not response.status_code == 200:
            return result

        jsonData = json_to_structure(response.text)

        for dataLimit in jsonData.get('cardLimits'):
            if not dataLimit.get('groupNum') == 0:
                continue

            foundedElements = [x for x in dataCard.get('limits') if x.get('id') == str(dataLimit.get('groupNum'))]
            if len(foundedElements) == 0:
                newLimit = {
                    'id': str(dataLimit.get('groupNum')),
                    'code': str(dataLimit.get('groupNum')),
                    'category': 'fuel',
                    'categoryDescription': 'fuel',
                    'group': '',
                    'groupDescription': '',
                    'item': '',
                    'itemDescription': '',
                    'currency': 'rub',
                    'period': parsing.code_period(self, dataLimit.get('limType')),
                    'value': 0,
                    'balance': 0
                }

                for limit in dataLimit.get('limList'):
                    if not parsing.code_currency(self, limit.get('limType')) == 'rub':
                        continue
                    if limit.get('lim') == 999999:
                        continue
                    newLimit['value'] = newLimit.get('value') + limit.get('lim')
                
                newLimit['value'] = convert_to_numeric_str(newLimit['value'])
                newLimit['balance'] = convert_to_numeric_str(newLimit['balance'])

                dataCard['limits'].append(newLimit)
        
        if dataCard:
            result = Result('Successful', True, dataCard)

        return result

    def getListTransactions(self, periodStart: str, periodEnd: str) -> Result:

        listTransactions = []
        result = Result('Couldn\'t get a list of transactions for fuel cards')
        urn = self.urns.get('getListTransactions')

        dateStart = datetime.strptime(periodStart, '%d.%m.%Y')
        dateStart = datetime(
            year=dateStart.year, 
            month=dateStart.month,
            day=dateStart.day,
            hour=0,
            minute=0,
            second=0
        )

        dateEnd = datetime.strptime(periodEnd, '%d.%m.%Y')
        dateEnd = datetime(
            year=dateEnd.year, 
            month=dateEnd.month,
            day=dateEnd.day,
            hour=23,
            minute=59,
            second=59
        )

        params = {
            'format': 'json',
            'dateFrom': dateStart.strftime("%Y-%m-%d"),
            'dateTo': dateEnd.strftime("%Y-%m-%d")
        }

        response = requests.get(
            ''.join([self.url, urn]),
            headers = {
                'Content-Type': 'Application/JSON',
                'Authorization': self.api_key
            },
            params = params
        )

        if not response.status_code == 200:
            return result

        jsonData = json_to_structure(response.text)

        for dataTransaction in jsonData['transactions']:
            items = []
            
            amount = dataTransaction.get('sum')
            if amount < 0:
                amount = amount * -1
            
            quantity = dataTransaction.get('amount')
            if quantity < 0:
                quantity = quantity * -1
            
            amountWithDiscount = dataTransaction.get('pricePos') * quantity
            amountDiscount = amountWithDiscount - amount
            
            items.append({
                'id': convert_to_numeric_str(1),
                'category': 'fuel',
                'categoryDescription': 'fuel',
                'group': '',
                'groupDescription': '',
                'item': dataTransaction.get('serviceId'),
                'itemDescription': dataTransaction.get('serviceName'),
                'quantity': convert_to_numeric_str(quantity),
                'price': convert_to_numeric_str(dataTransaction.get('price')),
                'priceWithDiscount': convert_to_numeric_str(dataTransaction.get('pricePos')),
                'amount': convert_to_numeric_str(amount),
                'amountWithDiscount': convert_to_numeric_str(amountWithDiscount),
            })

            listTransactions.append({
                'id': dataTransaction.get('idTrans'),
                'dateTime': dataTransaction.get('date').strip(),
                'cardNumber': convert_to_numeric_str(dataTransaction.get('cardNum')),
                'type': parsing.code_type_transaction(self, dataTransaction.get('typeId')),
                'details': dataTransaction['posAddress'].strip(),
                'amount': convert_to_numeric_str(amount),
                'discount': convert_to_numeric_str(amountDiscount),
                'items': items
            })
        
        if listTransactions:
            result = Result('Successful', True, listTransactions)

        return result

    def getListTransactionsByCard(self, numberCard:str, periodStart:str, periodEnd:str) -> Result:

        listTransactions = []
        result = Result('Couldn\'t get a list of transactions for fuel cards')

        urn = self.urns.get('getListTransactionsByCard')
        urn = urn.replace('{cardNumber}', numberCard)

        dateStart = datetime.strptime(periodStart, '%d.%m.%Y')
        dateStart = datetime(
            year=dateStart.year, 
            month=dateStart.month,
            day=dateStart.day,
            hour=0,
            minute=0,
            second=0
        )

        dateEnd = datetime.strptime(periodEnd, '%d.%m.%Y')
        dateEnd = datetime(
            year=dateEnd.year, 
            month=dateEnd.month,
            day=dateEnd.day,
            hour=23,
            minute=59,
            second=59
        )

        params = {
            'format': 'json',
            'dateFrom': dateStart.strftime("%Y-%m-%d"),
            'dateTo': dateEnd.strftime("%Y-%m-%d")
        }

        response = requests.get(
            ''.join([self.url, urn]),
            headers = {
                'Content-Type': 'Application/JSON',
                'Authorization': self.api_key
            },
            params = params
        )

        if not response.status_code == 200:
            return result

        jsonData = json_to_structure(response.text)

        for dataTransaction in jsonData['transactions']:
            items = []
            
            amount = dataTransaction.get('sum')
            if amount < 0:
                amount = amount * -1
            
            quantity = dataTransaction.get('amount')
            if quantity < 0:
                quantity = quantity * -1
            
            amountWithDiscount = dataTransaction.get('pricePos') * quantity
            amountDiscount = amountWithDiscount - amount
            
            items.append({
                'id': convert_to_numeric_str(1),
                'category': 'fuel',
                'categoryDescription': 'fuel',
                'group': '',
                'groupDescription': '',
                'item': dataTransaction.get('serviceId'),
                'itemDescription': dataTransaction.get('serviceName'),
                'quantity': convert_to_numeric_str(quantity),
                'price': convert_to_numeric_str(dataTransaction.get('price')),
                'priceWithDiscount': convert_to_numeric_str(dataTransaction.get('pricePos')),
                'amount': convert_to_numeric_str(amount),
                'amountWithDiscount': convert_to_numeric_str(amountWithDiscount),
            })

            listTransactions.append({
                'id': dataTransaction.get('idTrans'),
                'dateTime': dataTransaction.get('date').strip(),
                'cardNumber': convert_to_numeric_str(dataTransaction.get('cardNum')),
                'type': parsing.code_type_transaction(self, dataTransaction.get('typeId')),
                'details': dataTransaction['posAddress'].strip(),
                'amount': convert_to_numeric_str(amount),
                'discount': convert_to_numeric_str(amountDiscount),
                'items': items
            })
        
        if listTransactions:
            result = Result('Successful', True, listTransactions)

        return result

    def setLimitCard(self,
                     numberCard: str, value: str,
                     category: str, period: str,
                     currency: str, group: str = '') -> Result:
        
        if not currency.lower() == 'rub':
            return Result('Only rubles are allowed for this API!')

        if not period.lower() == 'nonrenewable':
            return Result('Only nonrenewable period are allowed for this API!')

        if not category.lower() == 'fuel':
            return Result('Only FUEL category are allowed for this API!')

        dataCard = self.getDataCard(numberCard)

        if not dataCard:
            return Result('Failed to get fuel card limit data')

        result = Result(
            ''.join([
                'Failed to create a new limit for the fuel card #',
                numberCard
            ])
        )

        urn = self.urns.get('setLimitCard')
        urn = urn.replace('{cardNumber}', numberCard)
        
        currentAmountLimit = 0
        for limit in dataCard.data.get('limits'):
            if not limit.get('id') == '0':
                continue
            currentAmountLimit = currentAmountLimit + float(limit.get('value'))
        
        operationId = 1
        targetAmmount = float(value)
        summa = targetAmmount - currentAmountLimit

        if summa < 0:
            summa = summa * -1
            operationId = 2

        params = {
            'format': 'json'
        }

        data = {
            'idUsl': 0,
            'operationId': operationId,
            'summa': summa
        }

        response = requests.post(
            ''.join([self.url, urn]),
            headers = {
                'Content-Type': 'Application/JSON',
                'Authorization': self.api_key
            },
            params = params,
            data = json.dumps(data)
        )

        if not response.status_code == 200:
            result.data = response.text
            return result

        return Result('Successful', True, {'id': str(uuid.uuid4())})

    def editLimitCard(self, numberCard: str, idLimit: str, value: str) -> Result:

        dataCard = self.getDataCard(numberCard)

        if not dataCard:
            return Result('Failed to get fuel card limit data')

        result = Result(
            ''.join([
                'Failed to create a new limit for the fuel card #',
                numberCard
            ])
        )

        urn = self.urns.get('setLimitCard')
        urn = urn.replace('{cardNumber}', numberCard)
        
        currentAmountLimit = 0
        for limit in dataCard.data.get('limits'):
            if not limit.get('id') == '0':
                continue
            currentAmountLimit = currentAmountLimit + float(limit.get('value'))
        
        operationId = 1
        targetAmmount = float(value)
        summa = targetAmmount - currentAmountLimit

        if summa < 0:
            summa = summa * -1
            operationId = 2

        params = {
            'format': 'json'
        }

        data = {
            'idUsl': 0,
            'operationId': operationId,
            'summa': summa
        }

        response = requests.post(
            ''.join([self.url, urn]),
            headers = {
                'Content-Type': 'Application/JSON',
                'Authorization': self.api_key
            },
            params = params,
            data = json.dumps(data)
        )

        if not response.status_code == 200:
            result.data = response.text
            return result

        return Result('Successful', True, {'id': idLimit})

    def delLimitCard(self, numberCard: str, idLimit: str) -> Result:

        dataCard = self.getDataCard(numberCard)

        if not dataCard:
            return Result('Failed to get fuel card limit data')

        result = Result(
            ''.join([
                'Failed to create a new limit for the fuel card #',
                numberCard
            ])
        )

        urn = self.urns.get('setLimitCard')
        urn = urn.replace('{cardNumber}', numberCard)
        
        currentAmountLimit = 0
        for limit in dataCard.data.get('limits'):
            if not limit.get('id') == '0':
                continue
            currentAmountLimit = currentAmountLimit + float(limit.get('value'))
        
        operationId = 1
        targetAmmount = 0
        summa = targetAmmount - currentAmountLimit

        if summa < 0:
            summa = summa * -1
            operationId = 2

        params = {
            'format': 'json'
        }

        data = {
            'idUsl': 0,
            'operationId': operationId,
            'summa': summa
        }

        response = requests.post(
            ''.join([self.url, urn]),
            headers = {
                'Content-Type': 'Application/JSON',
                'Authorization': self.api_key
            },
            params = params,
            data = json.dumps(data)
        )

        if not response.status_code == 200:
            result.data = response.text
            return result

        return Result('Successful', True, {'id': idLimit})
