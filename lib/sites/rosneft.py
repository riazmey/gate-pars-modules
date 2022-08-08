#!/usr/bin/python3

import requests
import json
from datetime import datetime, timedelta
from lib.common import parsing
from lib.common.general import Result
from lib.common.general import arg_from_args
from lib.common.general import json_to_structure
from lib.common.general import convert_to_numeric_str
from lib.common.general import convert_to_lower_simple_chars
from lib.common.general import write_list_cards_to_file
from lib.common.general import get_list_cards_from_file

class RNCart():

    def __init__(self, login:str, password:str, contract:str):
        self.url = 'https://lkapi.rn-card.ru'
        self.siteLogin = login
        self.sitePassword = password
        self.siteContract = contract
        self.parsing = False

    @property
    def urns(self) -> dict:
        return {
            'setStatusCard': {
                'active': '/api/emv/v1/UnblockingCard',
                'block': '/api/emv/v1/BlockingCard'
            },
            'getListCards': '/api/emv/v1/GetCardsByContract',
            'getBalance': '/api/emv/v1/ContractBalance',
            'getLimits': '/api/emv/v1/GetCardLimits',
            'getListTransactionsByCard': '/api/emv/v2/GetOperByCard',
            'getListTransactions': '/api/emv/v2/GetOperByContract',
            'setLimitCard': '/api/emv/v1/CreateCardLimit',
            'editLimitCard': '/api/emv/v1/EditCardLimit',
            'delLimitCard': '/api/emv/v1/DeleteCardLimit'
        }

    def setStatusCard(self, numberCard:str, status:str) -> Result:
        
        urn = self.urns.get('setStatusCard').get(status)

        argsRequest = {
            'u': self.siteLogin,
            'p': self.sitePassword,
            'contract': self.siteContract,
            'card': numberCard,
            'type': 'JSON'
        }

        data = ''
        for item in argsRequest:
            if data:
                data += '&'
            data += ''.join([item, '=', argsRequest.get(item)])

        response = requests.post(
            ''.join([
                self.url,
                urn
            ]),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
            },
            json=json.dumps(argsRequest),
            params=argsRequest,
            data=data
        )

        return Result(
            response.reason,
            response.status_code == 200,
            response.text
        )

    def getListCards(self) -> Result:
        
        listCards = []
        result = Result(
            'Couldn\'t get the list cards',
            False,
            listCards
        )

        urn = self.urns.get('getListCards')

        argsRequest = {
            'u': self.siteLogin,
            'p': self.sitePassword,
            'contract': self.siteContract,
            'type': 'JSON'
        }

        response = requests.get(
            ''.join([
                self.url,
                urn
            ]),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
            },
            json=json.dumps(argsRequest),
            params=argsRequest
        )

        if not response.status_code == 200:
            return result

        jsonData = json_to_structure(response.text)

        for data in jsonData:
            listCards.append(
                {
                    'id': str(data['Num']),
                    'number': data['Num'],
                    'status': parsing.code_status(self, data['SCode'])
                }
            )
        
        if listCards:
            result = Result(
                'Successfull',
                True,
                listCards
            )
            write_list_cards_to_file(
                'rosneft',
                self.siteLogin,
                listCards
            )

        return result

    def getBalance(self) -> Result:
        
        result = {
            'balance': 0.0,
            'credit': 0.0,
            'available': 0.0
        }
        urn = self.urns.get('getBalance')

        argsRequest = {
            'u': self.siteLogin,
            'p': self.sitePassword,
            'contract': self.siteContract,
            'type': 'JSON'
        }

        response = requests.get(
            ''.join([
                self.url,
                urn
            ]),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
            },
            json=json.dumps(argsRequest),
            params=argsRequest
        )

        if response.status_code == 200:
            jsonData = json_to_structure(response.text)
            result['balance'] = jsonData['Balance']
            result['credit'] = jsonData['CreditLimit']
            result['available'] = jsonData['Available']

        return Result(
            response.reason,
            response.status_code == 200,
            result
        )

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
            self.getListCards()
            listCards = get_list_cards_from_file('rosneft', self.siteLogin)
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

        argsRequest = {
            'u': self.siteLogin,
            'p': self.sitePassword,
            'card': numberCard,
            'contract': self.siteContract,
            'type': 'JSON'
        }

        response = requests.get(
            ''.join([
                self.url,
                urn
            ]),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
            },
            json=json.dumps(argsRequest),
            params=argsRequest
        )

        if not response.status_code == 200:
            return result

        jsonData = json_to_structure(response.text)

        for dataLimit in jsonData:
            dataCard['limits'].append(
                {
                    'id': str(dataLimit['Code']),
                    'code': str(dataLimit['Code']),
                    'category': parsing.code_category(self, dataLimit['GCat']),
                    'categoryDescription': parsing.repres_category(self,  parsing.code_category(self, dataLimit['GCat'])),
                    'group': '',
                    'groupDescription': '',
                    'item': '',
                    'itemDescription': '',
                    'currency': parsing.code_currency(self, dataLimit['Currency']),
                    'period': parsing.code_period(self, dataLimit['Prd']),
                    'value': convert_to_numeric_str(dataLimit['Val']),
                    'balance': convert_to_numeric_str(dataLimit['CurValue']),
                    'spending': '0.0'
                }
            )
        
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

        argsRequest = {
            'u': self.siteLogin,
            'p': self.sitePassword,
            'contract': self.siteContract,
            'begin': dateStart.isoformat(),
            'end': dateEnd.isoformat(),
            'type': 'JSON'
        }

        response = requests.get(
            ''.join([
                self.url,
                urn
            ]),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
            },
            json=json.dumps(argsRequest),
            params=argsRequest
        )

        if not response.status_code == 200:
            return result

        jsonData = json_to_structure(response.text)

        for dataTransaction in jsonData['OperationList']:
            items = []
            
            amountWithDiscount = dataTransaction['Sum'] - dataTransaction['DSum']
            if dataTransaction['Value'] != 0:
                priceWithDiscount = amountWithDiscount / dataTransaction['Value']
            else:
                priceWithDiscount = 0
            
            items.append({
                'id': convert_to_numeric_str(1),
                'category': parsing.code_category(self, dataTransaction['GCat']),
                'categoryDescription': parsing.repres_category(self,  parsing.code_category(self, dataTransaction['GCat'])),
                'group': '',
                'groupDescription': '',
                'item': dataTransaction['GCode'],
                'itemDescription': dataTransaction['GName'],
                'quantity': convert_to_numeric_str(dataTransaction['Value']),
                'price': convert_to_numeric_str(dataTransaction['Price']),
                'priceWithDiscount': convert_to_numeric_str(priceWithDiscount),
                'amount': convert_to_numeric_str(dataTransaction['Sum']),
                'amountWithDiscount': convert_to_numeric_str(amountWithDiscount),
            })

            listTransactions.append({
                'id': convert_to_numeric_str(dataTransaction['Code']),
                'dateTime': dataTransaction['Date'].strip(),
                'cardNumber': convert_to_numeric_str(dataTransaction['Card']),
                'type': parsing.code_type_transaction(self, dataTransaction['Type']),
                'details': dataTransaction['Address'].strip(),
                'amount': convert_to_numeric_str(dataTransaction['Sum']),
                'discount': convert_to_numeric_str(dataTransaction['DSum']),
                'items': items
            })
        
        if listTransactions:
            result = Result('Successful', True, listTransactions)

        return result

    def getListTransactionsByCard(self, numberCard:str, periodStart:str, periodEnd:str) -> Result:

        listTransactions = []
        result = Result('Couldn\'t get a list of transactions for fuel cards')
        urn = self.urns.get('getListTransactionsByCard')

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

        argsRequest = {
            'u': self.siteLogin,
            'p': self.sitePassword,
            'contract': self.siteContract,
            'begin': dateStart.isoformat(),
            'end': dateEnd.isoformat(),
            'card': numberCard,
            'type': 'JSON'
        }

        response = requests.get(
            ''.join([
                self.url,
                urn
            ]),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
            },
            json=json.dumps(argsRequest),
            params=argsRequest
        )

        if not response.status_code == 200:
            return result

        jsonData = json_to_structure(response.text)

        if not jsonData['OperationList']:
            return Result('Successful', True, listTransactions)

        for dataTransaction in jsonData['OperationList']:
            items = []
            
            amountWithDiscount = dataTransaction['Sum'] - dataTransaction['DSum']
            if dataTransaction['Value'] != 0:
                priceWithDiscount = amountWithDiscount / dataTransaction['Value']
            else:
                priceWithDiscount = 0
            
            items.append({
                'id': convert_to_numeric_str(1),
                'category': parsing.code_category(self, dataTransaction['GCat']),
                'categoryDescription': parsing.repres_category(self,  parsing.code_category(self, dataTransaction['GCat'])),
                'group': '',
                'groupDescription': '',
                'item': dataTransaction['GCode'],
                'itemDescription': dataTransaction['GName'],
                'quantity': convert_to_numeric_str(dataTransaction['Value']),
                'price': convert_to_numeric_str(dataTransaction['Price']),
                'priceWithDiscount': convert_to_numeric_str(priceWithDiscount),
                'amount': convert_to_numeric_str(dataTransaction['Sum']),
                'amountWithDiscount': convert_to_numeric_str(amountWithDiscount),
            })

            listTransactions.append({
                'id': convert_to_numeric_str(dataTransaction['Code']),
                'number': convert_to_numeric_str(dataTransaction['Code']),
                'dateTime': dataTransaction['Date'].strip(),
                'cardNumber': convert_to_numeric_str(dataTransaction['Card']),
                'type': parsing.code_type_transaction(self, dataTransaction['Type']),
                'details': dataTransaction['Address'].strip(),
                'amount': convert_to_numeric_str(dataTransaction['Sum']),
                'discount': convert_to_numeric_str(dataTransaction['DSum']),
                'items': items
            })
        
        if listTransactions:
            result = Result('Successful', True, listTransactions)

        return result

    def setLimitCard(self,
                     numberCard: str, value: str,
                     category: str, period: str,
                     currency: str, group: str = '') -> Result:
        
        currency = convert_to_lower_simple_chars(currency)
        if currency.lower() == 'rub':
            currency = 'C'
        elif currency.lower() == 'litre':
            currency = 'V'
        else:
            return  Result(
                ''.join([
                    'The parameter "currency" was not passed correctly'
                    ' to the setLimitCard function'
                ])
            )

        category = convert_to_lower_simple_chars(category)
        GFlag = 'C'
        if category.lower() == 'fuel':
            category = 'FUEL'
        elif category.lower() == 'goods':
            category = 'GOODS'
        elif category.lower() == 'service':
            category = 'SERVICE'
        else:
            GFlag = 'A'

        period = convert_to_lower_simple_chars(period)
        if period.lower() == 'nonrenewable':
            period = 'N'
        elif period.lower() == 'day':
            period = 'F'
        elif period.lower() == 'month':
            period = 'M'
        elif period.lower() == 'quarter':
            period = 'Q'
        else:
            return  Result(
                ''.join([
                    'The parameter "period" was not passed correctly'
                    ' to the setLimitCard function'
                ])
            )
        
        result = Result(
            ''.join([
                'Failed to create a new limit for the fuel card #',
                numberCard
            ])
        )

        urn = self.urns.get('setLimitCard')

        argsRequest = {
            'u': self.siteLogin,
            'p': self.sitePassword,
            'contract': self.siteContract,
            'card': numberCard,
            'prd': period,
            'currency': currency,
            'GCode': category,
            'GFlag': GFlag,
            'val': value,
            'type': 'JSON'
        }
        
        data = ''
        for item in argsRequest:
            if data:
                data += '&'
            data += ''.join([item, '=', argsRequest.get(item)])
        
        response = requests.post(
            ''.join([
                self.url,
                urn
            ]),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
            },
            json=json.dumps(argsRequest),
            params=argsRequest,
            data=data
        )

        if not response.status_code == 200:
            result.data = response.text
            return result
        
        jsonData = json_to_structure(response.text)
        return Result(
            'Successful',
            True,
            {'id': str(jsonData['LimitCode'])}
        )

    def editLimitCard(self, numberCard: str, idLimit: str, value: str) -> Result:

        result = Result(
            ''.join([
                'Failed to edit a limit for the fuel card #',
                numberCard
            ])
        )

        dataLimit = None
        dataCard = self.getDataCard(numberCard)
        if dataCard.data['limits']:
            for limit in dataCard.data['limits']:
                if limit['id'] == idLimit:
                    dataLimit = limit
                    break

        if not dataLimit:
            return Result(
                ''.join([
                    'Fuel card #',
                    numberCard,
                    'has no limit with ID #',
                    idLimit
                ])
            )
        
        urn = self.urns.get('editLimitCard')

        currency = convert_to_lower_simple_chars(dataLimit['currency'])
        if currency.lower() == 'rub':
            currency = 'C'
        elif currency.lower() == 'litre':
            currency = 'V'
        else:
            return  Result(
                ''.join([
                    'The parameter "currency" was not passed correctly'
                    ' to the editLimitCard function'
                ])
            )

        category = convert_to_lower_simple_chars(dataLimit['category'])
        if category.lower() == 'fuel':
            category = 'FUEL'
        elif category.lower() == 'goods':
            category = 'GOODS'
        elif category.lower() == 'service':
            category = 'SERVICE'

        period = convert_to_lower_simple_chars(dataLimit['period'])
        if period.lower() == 'nonrenewable':
            period = 'N'
        elif period.lower() == 'day':
            period = 'F'
        elif period.lower() == 'month':
            period = 'M'
        elif period.lower() == 'quarter':
            period = 'Q'
        else:
            return  Result(
                ''.join([
                    'The parameter "period" was not passed correctly'
                    ' to the editLimitCard function'
                ])
            )

        argsRequest = {
            'u': self.siteLogin,
            'p': self.sitePassword,
            'contract': self.siteContract,
            'card': numberCard,
            'prd': period,
            'currency': currency,
            'GCode': '', # Item
            'GFlag': category,
            'LimitCode': idLimit,
            'val': value,
            'CurValue': float(convert_to_numeric_str(dataLimit['value'])),
            'type': 'JSON'
        }

        data = ''
        for item in argsRequest:
            if data:
                data += '&'
            data += ''.join([
                item,
                '=',
                str(argsRequest.get(item))
            ])
        
        response = requests.post(
            ''.join([
                self.url,
                urn
            ]),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
            },
            json=json.dumps(argsRequest),
            params=argsRequest,
            data=data
        )

        if not response.status_code == 200:
            result.data = response.text
            return result
        
        jsonData = json_to_structure(response.text)
        return Result(
            'Successful',
            True,
            {'id': str(jsonData['LimitCode'])}
        )

    def delLimitCard(self, numberCard: str, idLimit: str) -> Result:

        result = Result(
            ''.join([
                'Failed to edit a limit for the fuel card #',
                numberCard
            ])
        )

        dataLimit = None
        dataCard = self.getDataCard(numberCard)
        if dataCard.data['limits']:
            for limit in dataCard.data['limits']:
                if limit['id'] == idLimit:
                    dataLimit = limit
                    break

        if not dataLimit:
            return Result(
                ''.join([
                    'Fuel card #',
                    numberCard,
                    'has no limit with ID #',
                    idLimit
                ])
            )
        
        urn = self.urns.get('delLimitCard')

        currency = convert_to_lower_simple_chars(dataLimit['currency'])
        if currency.lower() == 'rub':
            currency = 'C'
        elif currency.lower() == 'litre':
            currency = 'V'
        else:
            return  Result(
                ''.join([
                    'The parameter "currency" was not passed correctly'
                    ' to the editLimitCard function'
                ])
            )

        category = convert_to_lower_simple_chars(dataLimit['category'])
        if category.lower() == 'fuel':
            category = 'FUEL'
        elif category.lower() == 'goods':
            category = 'GOODS'
        elif category.lower() == 'service':
            category = 'SERVICE'

        period = convert_to_lower_simple_chars(dataLimit['period'])
        if period.lower() == 'nonrenewable':
            period = 'N'
        elif period.lower() == 'day':
            period = 'F'
        elif period.lower() == 'month':
            period = 'M'
        elif period.lower() == 'quarter':
            period = 'Q'
        else:
            return  Result(
                ''.join([
                    'The parameter "period" was not passed correctly'
                    ' to the editLimitCard function'
                ])
            )

        argsRequest = {
            'u': self.siteLogin,
            'p': self.sitePassword,
            'contract': self.siteContract,
            'card': numberCard,
            'prd': period,
            'currency': currency,
            'GCode': '', # Item
            'GFlag': category,
            'LimitCode': idLimit,
            'val': 0,
            'CurValue': float(convert_to_numeric_str(dataLimit['value'])),
            'type': 'JSON'
        }

        data = ''
        for item in argsRequest:
            if data:
                data += '&'
            data += ''.join([
                item,
                '=',
                str(argsRequest.get(item))
            ])
        
        response = requests.post(
            ''.join([
                self.url,
                urn
            ]),
            headers={
                'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8'
            },
            json=json.dumps(argsRequest),
            params=argsRequest,
            data=data
        )

        if not response.status_code == 200:
            result.data = response.text
            return result
        
        return Result(
            'Successful',
            True,
            {'id': idLimit}
        )
