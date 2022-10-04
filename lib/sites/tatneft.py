#!/usr/bin/python3

import os
import re
import time
import requests
import json
import openpyxl
from lib.common import parsing
from lib.common.general import Result
from lib.common.general import id_card
from lib.common.general import json_to_structure
from lib.common.general import convert_to_numeric_str
from lib.common.general import write_list_cards_to_file
from lib.common.general import convert_to_lower_simple_chars
from selenium.webdriver.common.by import By
from datetime import datetime, timedelta
from bs4 import BeautifulSoup as bs4


class URNs:

    def __init__(self):
        self.login = '/login'
        self.mainMenuURNs = {
            'главная': '/tnp.mainData',
            'карты': '/tnp.cardsData',
            'сетьазс': '/tnp.terminalNetworkData',
            'организация': '/tnp.companyData',
            'отчетность': '/tnp.reportData'
        }

    def mainMenu(self, nameSection=None) -> dict or str:

        if not isinstance(nameSection, type('')) or not nameSection:
            return self.mainMenuURNs

        searchKey = nameSection.strip().lower().replace(' ', '')
        return self.mainMenuURNs.get(searchKey, '')


class TATNeft():

    def __init__(self, driverWebBrowser=None, tempDir=None):

        self.url = 'http://lk.tatneft.ru/solar-portal'
        self.clientId = '217429'
        self.driverWebBrowser = driverWebBrowser
        self.webBrowser = None
        self.tempDir = tempDir
        self.loginOn = False
        self.urns = URNs()
        self.predefinedIDs = {
            'username': 'slqusername',
            'password': 'slqpassword'
        }
        self.classErrors = [
            'login__error-message',
            'notification--error'
        ]
        self.token = ''
        self.parsing = True

    def __del__(self):
        for i in range(10):
            if i != 1:
                time.sleep(0.5)
            try:
                self.webBrowser.quit()
                break
            except:
                pass

    def login(self, login: str, password: str) -> Result:
        result = parsing.login(self, login, password, self.driverWebBrowser)
        self.loginOn = result.status
        self.siteLogin = login
        if not result:
            return result
        try:
            request = None
            for x in range(1, 20):
                if x != 1:
                    time.sleep(0.3)
                entries = parsing.find_requests(
                    self,
                    uri='api/util/loadData/tnp.menuData'
                )
                if not entries:
                    continue
                else:
                    request = entries[0]
                    break
            if not request:
                return
            self.basicHeaders = self.convert_headers_to_dict(
                request['request']['headers'])
            self.token = self.get_token_from_headers(self.basicHeaders)
            self.sessionRequest = requests.Session()
            return Result('Successful', True)
        except:
            return Result('Error initialization WEB token')

    def setStatusCard(self, numberCard: str, status: str) -> Result:
        functions = {
            'function1': self.setStatusCardBySiteAPI,
            'function2': self.setStatusCardBySelenium
        }
        for function in functions:
            result = functions[function](numberCard, status)
            if result: break
        return result

    def setStatusCardBySiteAPI(self, numberCard: str, status: str) -> Result:

        result = Result(
            ''.join([
                'Failed to set new status for fuel card #',
                numberCard
            ])
        )

        if status == 'active':
            status = 'C_00'
        elif status == 'block':
            status = 'C_05MC'
        else:
            return  Result(
                ''.join([
                    'The "status" parameter of the fuel ',
                    'card is not specified correctly'
                ])
            )

        for i in range(1, 10):
            if i != 1:
                time.sleep(0.3)
            try:
                cardID = id_card('tatneft', self.siteLogin, numberCard)
                if not cardID:
                    continue

                response = self.send_request(
                    'api/util/loadForm/tnp.customerCard')
                if not response.status_code == 200:
                    continue

                uri = ''.join([
                    'api/util/loadData/tnp.customerCard?id=',
                    cardID,
                    '&clientId=',
                    self.clientId
                ])
                response = self.send_request(uri)
                if not response.status_code == 200:
                    continue

                jsonData = json_to_structure(response.text)
                if not 'data' in jsonData:
                    continue

                currentStatus = jsonData['data'].get('status', '')
                if not currentStatus:
                    continue

                response = self.send_request(
                    'api/action/changeStatus/tnp.customerCard/$all',
                    json.dumps(
                        {
                            'contractId': cardID,
                            'cardNumber': numberCard,
                            'product': 'FLEET_CARD',
                            'status': currentStatus,
                            'id': cardID,
                            'newStatus': status.upper()
                        }
                    )
                )

                if not response.status_code == 200:
                    continue
                
                newStatus = parsing.code_status(self, status)
                result = Result(
                    'Successful',
                    True,
                    newStatus
                )

                dataCard = self.getDataCard(numberCard)
                if not dataCard:
                    break

                if not dataCard.data.get('status') == newStatus:
                    result = Result(
                        ''.join([
                            'The status was set, but the site ',
                            'server did not process it!'
                        ])
                    )
                
                self.send_request('api/util/loadData/tnp.mainData')
                break

            except:
                pass

        return result

    def setStatusCardBySelenium(self, numberCard: str, status: str) -> Result:

        result = parsing.open_section_card_data(self, numberCard)

        if not result:
            return result

        strStatus = 'блокирована'
        if status == 'active':
            strStatus = 'активна'

        try:
            elementStatus = None
            for element in self.webBrowser.find_elements(By.CLASS_NAME, 'field-md-dropdown'):
                elementLabel = element.find_element(
                    By.CLASS_NAME, 'field-md-dropdown__label')
                if convert_to_lower_simple_chars(elementLabel.text) == 'статускарты':
                    elementStatus = element
                    break

            openChangeCardForm = False
            if elementStatus:
                elementStatusSpan = elementStatus.find_element(
                    By.TAG_NAME, 'span')
                if convert_to_lower_simple_chars(elementStatusSpan.text) == strStatus:
                    return Result(
                        ''.join([
                            'The "',
                            status,
                            '" status is already set. ',
                            'There\'s nothing to do.'
                        ]),
                        True,
                        status)
                else:
                    elementDIV = self.webBrowser.find_element(
                        By.CLASS_NAME, 'field-action-button--changeStatus')
                    if elementDIV:
                        elementSVG = elementDIV.find_element(
                            By.TAG_NAME, 'td-svg-icon')
                        result = parsing.click_element(self, elementSVG)
                        if not result:
                            return result
                        else:
                            openChangeCardForm = True
                    else:
                        return Result('Couldn\'t find the "change status" button')
            else:
                return Result('Couldn\'t find the "card status" field')
        except:
            return Result('Couldn\'t open the card status change form')

        if not openChangeCardForm:
            return Result('Couldn\'t open the card status change form')

        try:
            result = Result('Couldn\'t find the "status" check box')

            elementList = self.webBrowser.find_element(
                By.CLASS_NAME, 'field-md-dropdown-select')
            if elementList:
                result = parsing.select_value_from_list(
                    self,
                    elementList,
                    'mat-option',
                    strStatus
                )

            if result:
                buttonSave = None
                for element in self.webBrowser.find_elements(By.TAG_NAME, 'button'):
                    if convert_to_lower_simple_chars(element.text) == 'сохранить':
                        buttonSave = element
                        break

                if buttonSave:
                    result = parsing.click_element(self, buttonSave)
                else:
                    result = Result('Couldn\'t find the "save" button')

        except:
            result = Result('Failed to set new status')

        if result:
            if convert_to_lower_simple_chars(elementStatusSpan.text) != strStatus:
                result = Result(
                    'The new status was set, but the '
                    'server did not accept the new data'
                )

        return result
    
    def setLimitCard(self,
                     numberCard: str, value: str,
                     category: str, period: str,
                     currency: str, group: str = '') -> Result:
        functions = {
            'function1': self.setLimitCardBySiteAPI,
            'function2': self.setLimitCardBySelenium
        }
        for function in functions:
            result = functions[function](
                numberCard,
                value,
                category,
                period,
                currency,
                group
            )
            if result: break
        return result

    def setLimitCardBySiteAPI(self,
                     numberCard: str, value: str,
                     category: str, period: str,
                     currency: str, group: str = '') -> Result:
        
        currency = convert_to_lower_simple_chars(currency)
        if currency == 'rub':
            currency = 'RLI_CURR'
        elif currency == 'litre':
            currency = 'RLI_ITEM'
        else:
            return  Result(
                ''.join([
                    'The parameter "currency" was not passed correctly'
                    ' to the setLimitCard function'
                ])
            )

        category = convert_to_lower_simple_chars(category)
        if category == 'fuel':
            category = '01'
        elif category == 'gas':
            category = '02'
        elif category == 'goods':
            category = '03'
        elif category == 'service':
            category = '04'
        else:
            return  Result(
                ''.join([
                    'The parameter "category" was not passed correctly'
                    ' to the setLimitCard function'
                ])
            )

        period = convert_to_lower_simple_chars(period)
        if period == 'nonrenewable':
            period = 'E'
        elif period == 'day':
            period = 'F'
        elif period == 'month':
            period = 'M'
        elif period == 'quarter':
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

        for i in range(1, 10):
            if i != 1:
                time.sleep(0.3)
            try:
                cardID = id_card('tatneft', self.siteLogin, numberCard)
                if not cardID:
                    continue

                response = self.send_request(
                    'api/util/loadForm/tnp.customerCard')
                if not response.status_code == 200:
                    continue

                uri = ''.join([
                    'api/util/loadData/tnp.customerCard?id=',
                    cardID,
                    '&clientId=',
                    self.clientId
                ])
                response = self.send_request(uri)
                if not response.status_code == 200:
                    continue

                response = self.send_request(
                    'api/util/loadForm/tnp.limit')
                if not response.status_code == 200:
                    continue

                response = self.send_request(
                    'api/action/editCardLimit/tnp.customerCard/$all',
                    json.dumps(
                        {
                            'contractId': cardID,
                            'globalControlCode': currency,
                            'maxSingleAmountControlCode': currency,
                            'usedAmountControlCode': currency,
                            'goodsCategory': category,
                            'maxAmount': convert_to_numeric_str(value),
                            'periodUnit': period,
                            'periodValue': 1,
                            'restrictionType': 'R',
                            'monday': True,
                            'tuesday': True,
                            'wednesday': True,
                            'thursday': True,
                            'friday': True,
                            'saturday': True,
                            'sunday': True
                        }
                    )
                )

                if not response.status_code == 200:
                    continue
                
                jsonData = json_to_structure(response.text)
                if not 'data' in jsonData:
                    continue

                idLimit = str(jsonData['data'].get('id', ''))
                if not idLimit:
                    continue

                dataCard = self.getDataCardBySiteAPI(numberCard)
                if not dataCard:
                    continue
                
                dataLimit = None
                for limit in dataCard.data['limits']:
                    if limit['id'] == idLimit:
                        dataLimit = limit
                        break

                if dataLimit:
                    result = Result(
                        'Successful',
                        True,
                        {'id': idLimit}
                    )
                else:
                    result = Result(
                        'The "create limit" command was successfully '
                        'executed by the server, but the limit was not '
                        'actually created'
                    )

                self.send_request('api/util/loadData/tnp.mainData')
                break

            except:
                pass
        
        return result

    def setLimitCardBySelenium(self,
                     numberCard: str, value: str,
                     category: str, period: str,
                     currency: str, group: str = '') -> Result:

        category = parsing.repres_category(self, category)
        currency = parsing.repres_currency(self, currency)
        period = parsing.repres_period(self, period)

        for i in range(1, 5):
            if i != 1:
                time.sleep(2)

            try:
                result = parsing.open_section_card_data(self, numberCard)
                if not result:
                    continue

                resultSearch = parsing.find_element_by_tag_and_text(
                    self.webBrowser,
                    'button',
                    'ДобавитьЛимит')

                if resultSearch:
                    resultClick = parsing.click_element(
                        self, resultSearch.data)
                    if not resultClick:
                        continue
                else:
                    continue

                result = self.set_value_in_list('КатегорияТовара', category)
                if not result:
                    continue

                if group:
                    result = self.set_value_in_list('ГруппаТовара', group)
                    if not result:
                        continue

                result = self.set_value_in_list('ТипОграничителя',
                                                'Разрешено в заданных пределах')
                if not result:
                    continue

                result = self.get_modal_form()
                if not result:
                    continue
                else:
                    form = result.data

                result = parsing.set_value_to_input(
                    self,
                    (form.find_element(By.CSS_SELECTOR, 'div.dynamic-element--maxAmount').
                        find_element(By.TAG_NAME, 'input')),
                    value
                )
                if not result:
                    continue

                try:
                    field = None
                    for elementGroup in form.find_elements(By.CLASS_NAME, 'group__row'):
                        elementsGroup = elementGroup.find_elements(
                            By.CLASS_NAME, 'group__dynamic-element')
                        if elementsGroup:
                            dataField = elementsGroup[0].text.split('\n')
                            if dataField:
                                if convert_to_lower_simple_chars(dataField[0]) == convert_to_lower_simple_chars('МаксимальноеЗначениеЗаПериод'):
                                    field = elementsGroup[1]
                                    break
                            else:
                                continue
                        else:
                            continue
                except:
                    continue

                if not field:
                    continue

                result = parsing.select_value_from_list(
                    self, field, 'mat-option', currency.title())

                if not result:
                    continue

                try:
                    field = None
                    for elementGroup in form.find_elements(By.CLASS_NAME, 'group__row'):
                        elementsGroup = elementGroup.find_elements(
                            By.CLASS_NAME, 'group__dynamic-element')
                        if elementsGroup:
                            dataField = elementsGroup[0].text.split('\n')
                            if dataField:
                                if convert_to_lower_simple_chars(dataField[0]) == convert_to_lower_simple_chars('ПериодДействия'):
                                    field = elementsGroup[1]
                                    break
                            else:
                                continue
                        else:
                            continue
                except:
                    continue

                if not field:
                    continue

                result = parsing.select_value_from_list(
                    self, field, 'mat-option', period.title())

                if not result:
                    continue

                result = parsing.find_element_by_tag_and_text(
                    form,
                    'button',
                    'Сохранить')

                if not result:
                    continue

                if not parsing.click_element(self, result.data, True):
                    continue

                entries = None
                for x in range(1, 10):
                    if x != 1:
                        time.sleep(1)

                    entries = parsing.find_requests(
                        self,
                        uri='api/action/editCardLimit/tnp.customerCard/$all'
                    )
                    if not entries:
                        continue
                    else:
                        break

                if not entries:
                    continue

                try:
                    strJSON = entries[0]['response']['content']['text']
                    jsonData = json_to_structure(strJSON)

                    if not jsonData:
                        continue

                    idLimit = str(jsonData['data'].get('id', ''))
                    if idLimit:
                        return Result('Successful', True, {'id': idLimit})
                    else:
                        continue
                except:
                    continue

            except:
                continue

        return Result('Couldn\'t create a limit')

    def delLimitCard(self, numberCard: str, idLimit: str) -> Result:
        functions = {
            'function1': self.delLimitCardBySiteAPI,
            'function2': self.delLimitCardBySelenium
        }
        for function in functions:
            result = functions[function](numberCard, idLimit)
            if result: break
        return result

    def delLimitCardBySiteAPI(self, numberCard: str, idLimit: str) -> Result:

        result = Result(
            ''.join([
                'Failed to delete limit for the fuel card #',
                numberCard
            ])
        )

        for i in range(1, 10):
            if i != 1:
                time.sleep(0.3)
            try:
                cardID = id_card('tatneft', self.siteLogin, numberCard)
                if not cardID:
                    continue
                
                dataCard = self.getDataCardBySiteAPI(numberCard)
                if not dataCard:
                    continue
                
                dataLimit = None
                for limit in dataCard.data['limits']:
                    if limit['id'] == idLimit:
                        dataLimit = limit
                        break
                
                if not dataLimit:
                    result = Result(
                        ''.join([
                            'There is no limit for the fuel card #',
                            numberCard,
                            ' with the ID "',
                            idLimit,
                            '"'
                        ])
                    )
                    break
                
                response = self.send_request(
                    'api/util/loadForm/tnp.removeLimit')
                if not response.status_code == 200:
                    continue

                response = self.send_request(
                    ''.join([
                        'api/util/loadData/tnp.removeLimit?id=',
                        idLimit
                    ])
                )
                if not response.status_code == 200:
                    continue

                response = self.send_request(
                    'api/action/removeLimit/tnp.customerCard/limits',
                    json.dumps(
                        {
                            'id': dataLimit['id'],
                            'templateCode': dataLimit['code'],
                            'contractId': cardID
                        }
                    )
                )

                if not response.status_code == 200:
                    continue
                
                dataCard = self.getDataCardBySiteAPI(numberCard)
                if not dataCard:
                    continue
                
                dataLimit = None
                for limit in dataCard.data['limits']:
                    if limit['id'] == idLimit:
                        dataLimit = limit
                        break

                if dataLimit:
                    result = Result(
                        'The "delete limit" command was successfully '
                        'executed by the server, but the limit was not '
                        'actually deleted'
                    )
                else:
                    result = Result(
                        'Successful',
                        True,
                        {'id': idLimit}
                    )

                self.send_request('api/util/loadData/tnp.mainData')
                break
            except:
                pass
        
        return result

    def delLimitCardBySelenium(self, numberCard: str, idLimit: str) -> Result:

        for i in range(1, 12):
            if i != 1:
                time.sleep(0.3)

            try:
                result = parsing.open_section_card_data(self, numberCard)
                if not result:
                    continue

                limits = []
                result = self.get_limits_from_proxy_log()
                if result:
                    limits = result.data
                else:
                    continue

                resultNotFound = Result(
                    ''.join([
                        'There is no limit for the fuel card #',
                        numberCard,
                        ' with the ID "',
                        idLimit,
                        '"'
                    ])
                )
                if not limits:
                    return resultNotFound

                indexLimit = -1
                for x in range(len(limits)):
                    if limits[x]['id'] == idLimit:
                        indexLimit = x
                        break

                if indexLimit == -1:
                    return resultNotFound

                wrapper = self.webBrowser.find_element(
                    By.CSS_SELECTOR, 'td-inline-group.group--limits')

                indexRow = -1
                buttonRemove = None
                for row in wrapper.find_elements(By.TAG_NAME, 'mat-row'):
                    indexRow += 1
                    if indexRow == indexLimit:
                        buttons = row.find_elements(
                            By.CSS_SELECTOR, 'div.table-row__action-btn')
                        if buttons:
                            buttonRemove = buttons[1]
                            break

                if not buttonRemove:
                    continue

                if not parsing.click_element(self, buttonRemove):
                    continue

                result = self.get_modal_form()
                if not result:
                    continue
                else:
                    form = result.data

                result = parsing.find_element_by_tag_and_text(
                    form,
                    'button',
                    'Удалить')

                if not result:
                    continue

                if not parsing.click_element(self, result.data, True):
                    continue
                else:
                    return Result('Successful', True, {'id': idLimit})

            except:
                continue

        return Result('Couldn\'t delete a limit')
    
    def editLimitCard(self, numberCard: str, idLimit: str, value: str) -> Result:
        functions = {
            'function1': self.editLimitCardBySiteAPI,
            'function2': self.editLimitCardBySelenium
        }
        for function in functions:
            result = functions[function](numberCard, idLimit, value)
            if result: break
        return result
    
    def editLimitCardBySiteAPI(self, numberCard: str, idLimit: str, value: str) -> Result:

        result = Result(
            ''.join([
                'Failed to edit a limit for the fuel card #',
                numberCard
            ])
        )

        for i in range(1, 10):
            if i != 1:
                time.sleep(0.3)
            try:
                cardID = id_card('tatneft', self.siteLogin, numberCard)
                if not cardID:
                    continue
                
                dataCard = self.getDataCardBySiteAPI(numberCard)
                if not dataCard:
                    continue
                
                dataLimit = None
                for limit in dataCard.data['limits']:
                    if limit['id'] == idLimit:
                        dataLimit = limit
                        break
                
                if not dataLimit:
                    result = Result(
                        ''.join([
                            'There is no limit for the fuel card #',
                            numberCard,
                            ' with the ID "',
                            idLimit,
                            '"'
                        ])
                    )
                    break
                
                response = self.send_request(
                    'api/util/loadForm/tnp.limit')
                if not response.status_code == 200:
                    continue

                response = self.send_request(
                    ''.join([
                        'api/util/loadData/tnp.limit?id=',
                        idLimit
                    ])
                )
                if not response.status_code == 200:
                    continue

                category = convert_to_lower_simple_chars(dataLimit['category'])
                if category == 'fuel':
                    category = '01'
                elif category == 'gas':
                    category = '02'
                elif category == 'goods':
                    category = '03'
                elif category == 'service':
                    category = '04'
                else:
                    continue

                response = self.send_request(
                    'api/action/$save/tnp.limit/$all',
                    json.dumps(
                        {
                            'id': dataLimit['id'],
                            'templateCode': dataLimit['code'],
                            'contractId': cardID,
                            'maxAmount': value,
                            'maxSingleAmount': None,
                            'goodsCategory': category,
                            'goodsGroup': None,
                            'goodsItem': None,
                            'terminal': None,
                            'terminalGroup': None,
                            'cardGroup': None,
                            'country': None,
                            'region': None,
                            'merchant': None,
                            'timeIntervalFrom': None,
                            'timeIntervalTo': None,
                            'maxTxnQuantity': None,
                            'currentTxnQuantity': 0,
                            'periodValue': 1,
                            'restrictionType': 'R',
                            'monday': True,
                            'tuesday': True,
                            'wednesday': True,
                            'thursday': True,
                            'friday': True,
                            'saturday': True,
                            'sunday': True
                        }
                    )
                )

                if not response.status_code == 200:
                    continue
                
                dataCard = self.getDataCardBySiteAPI(numberCard)
                if not dataCard:
                    continue
                
                dataLimit = None
                for limit in dataCard.data['limits']:
                    if limit['id'] == idLimit:
                        dataLimit = limit
                        break

                if not dataLimit:
                    continue

                if dataLimit['value'] == value:
                    result = Result(
                        'Successful',
                        True,
                        {'id': idLimit}
                    )
                else:
                    result = Result(
                        'The "edit limit" command was successfully '
                        'executed by the server, but the limit was not '
                        'actually edited'
                    )

                self.send_request('api/util/loadData/tnp.mainData')
                break
            except:
                pass
        
        return result
    
    def editLimitCardBySelenium(self, numberCard: str, idLimit: str, value: str) -> Result:

        for i in range(1, 10):
            
            if i != 1:
                time.sleep(1)

            try:
                result = parsing.open_section_card_data(self, numberCard)
                if not result:
                    continue

                limits = []
                result = self.get_limits_from_proxy_log()
                if result:
                    limits = result.data

                resultNotFound = Result(''.join([
                    'The fuel card limit could not be found ',
                    numberCard,
                    ' with id #',
                    idLimit
                ]))
                if not limits:
                    return resultNotFound

                indexLimit = -1
                for x in range(len(limits)):
                    if limits[x]['id'] == idLimit:
                        indexLimit = x
                        break

                if indexLimit == -1:
                    return resultNotFound

                wrapper = self.webBrowser.find_element(
                    By.CSS_SELECTOR, 'td-inline-group.group--limits')

                indexRow = -1
                buttonEdit = None
                for row in wrapper.find_elements(By.TAG_NAME, 'mat-row'):
                    indexRow += 1
                    if indexRow == indexLimit:
                        buttons = row.find_elements(
                            By.CSS_SELECTOR, 'div.table-row__action-btn')
                        if buttons:
                            buttonEdit = buttons[0]
                            break

                if not buttonEdit:
                    continue

                if not parsing.click_element(self, buttonEdit):
                    continue

                result = self.get_modal_form()
                if not result:
                    continue
                else:
                    form = result.data

                result = self.set_value_in_list('ТипОграничителя',
                                                'Разрешено в заданных пределах')
                if not result:
                    continue

                result = parsing.set_value_to_input(
                    self,
                    (form.find_element(By.CSS_SELECTOR, 'div.dynamic-element--maxAmount').
                        find_element(By.TAG_NAME, 'input')),
                    value
                )
                if not result:
                    continue

                result = parsing.find_element_by_tag_and_text(
                    form,
                    'button',
                    'Сохранить')

                if not result:
                    continue

                if not parsing.click_element(self, result.data, True):
                    continue
                else:
                    return Result('Successful', True, {'id': idLimit})

            except:
                continue

        return Result('Couldn\'t delete a limit')

    def getBalance(self) -> Result:
        
        functions = {
            'function1': self.getBalanceBySiteAPI,
            'function2': self.getBalanceBySelenium
        }

        for function in functions:
            result = functions[function]()
            if result: break
            
        return result

    def getBalanceBySiteAPI(self) -> Result:

        data = {
            'balance': 0.0,
            'credit': 0.0,
            'available': 0.0
        }

        result = Result('Couldn\'t get the balance', False, data)

        for attemptCounter in range(1, 10):

            if attemptCounter != 1:
                time.sleep(0.3)
            
            try:

                response = self.send_request(
                    'api/util/loadData/tnp.mainData')
                if not response.status_code == 200:
                    continue

                jsonData = json_to_structure(response.text)
                if not 'data' in jsonData:
                    continue

                if not 'balanceAmount' in jsonData['data']:
                    continue
                
                data['balance'] = convert_to_numeric_str(jsonData['data']['balanceAmount'])

                result = Result(
                    'Successfull',
                    True,
                    data
                )

                self.send_request('api/util/loadData/tnp.mainData')
                break

            except:
                pass

        return result

    def getBalanceBySelenium(self) -> Result:

        data = {
            'balance': 0.0,
            'credit': 0.0,
            'available': 0.0
        }

        result = Result('Couldn\'t get the balance', False, data)

        for attemptCounter in range(1, 50):

            if attemptCounter != 1:
                time.sleep(0.3)
            
            try:

                entries = parsing.find_requests(
                    self,
                    uri='api/util/loadData/tnp.menuData')

                if not entries:
                    continue

                strJSON = entries[0]['response']['content']['text']
                jsonData = json_to_structure(strJSON)

                data['balance'] = jsonData['data']['balance']

                if jsonData:

                    result = Result(
                        'Successful',
                        True,
                        data)

                    break
            
            except:
                pass
        
        return result

    def getListCards(self) -> Result:

        functions = {
            'function1': self.getListCardsBySiteAPI,
            'function2': self.getListCardsBySelenium
        }

        for function in functions:
            result = functions[function]()
            if result: break
        
        return result
    
    def getListCardsBySiteAPI(self) -> Result:

        listCards = []
        result = Result('Couldn\'t get the list cards', False, listCards)

        dataIsAvailable = True
        requestCounter=0

        while dataIsAvailable:
            
            requestCounter += 1

            for attemptCounter in range(1, 10):

                if attemptCounter != 1:
                    time.sleep(0.3)
                
                try:
                    response = self.send_request(
                        'api/util/loadData/tnp.cardsData')
                    if not response.status_code == 200:
                        continue

                    response = self.send_request(
                        'api/data/customerCardList/tnp.cardsData/$all',
                        json.dumps(
                            {
                                'pager': {
                                    'page': requestCounter,
                                    'pageSize': 99
                                }
                            }
                        )
                    )

                    if not response.status_code == 200:
                        continue

                    jsonData = json_to_structure(response.text)
                    if not 'data' in jsonData:
                        continue
                    
                    if len( jsonData['data'] ) == 0:
                        dataIsAvailable = False
                        break

                    for data in jsonData['data']:
                        listCards.append(
                            {
                                'id': str(data['id']),
                                'number': data['cardNumber'],
                                'status': parsing.code_status(self, data['status'])
                            }
                        )
                    
                    result = Result(
                        'Successfull',
                        True,
                        listCards
                    )

                    self.send_request('api/util/loadData/tnp.mainData')
                    
                    break

                except:
                    pass

        if listCards:
            write_list_cards_to_file(
                'tatneft',
                self.siteLogin,
                listCards
            )

        return result

    def getListCardsBySelenium(self) -> Result:

        openSection = False
        for i in range(1, 5):
            if i != 1:
                time.sleep(1)

            try:
                resultOpenSection = parsing.open_main_section(self, 'Карты')
                if resultOpenSection:
                    openSection = True
                    break
                else:
                    parsing.open_main_section(self, 'Главная')
            except:
                pass

        if not openSection:
            return Result('Couldn\'t open the Cards page')

        for i in range(1, 5):
            if i != 1:
                time.sleep(1)

            totalLi = 0
            try:
                elementsLi = self.webBrowser.find_elements(
                    By.CLASS_NAME, 'page-link')
                for elementLi in elementsLi:
                    strNumberLi = convert_to_numeric_str(elementLi.text)
                    if strNumberLi:
                        totalLi = max(int(strNumberLi), totalLi)
            except:
                pass

        if not totalLi:
            return Result('Couldn\'t get pagination of fuel card list')

        listCards = []
        for counterLi in range(1, totalLi + 1):

            successAttempt = False

            for i in range(1, 5):
                if successAttempt:
                    break
                if i != 1:
                    time.sleep(2)

                elementLi = None
                for element in self.webBrowser.find_elements(By.CLASS_NAME, 'page-link'):
                    strNumberLi = convert_to_numeric_str(element.text)
                    if strNumberLi:
                        if int(strNumberLi) == counterLi:
                            elementLi = element
                            break

                if not elementLi:
                    continue
                else:
                    if elementLi.text.find('current') == -1:
                        resultClick = parsing.click_element(self, elementLi)
                        if not resultClick:
                            continue

                try:
                    entries = parsing.find_requests(
                        self,
                        uri='api/data/customerCardList/tnp.cardsData/$all'
                    )

                    if not entries:
                        continue

                    strJSON = entries[0]['response']['content']['text']
                    jsonData = json_to_structure(strJSON)

                    if not jsonData:
                        continue

                    for entryJSON in jsonData['data']:

                        status = 'block'
                        if entryJSON['status'] == 'C_00':
                            status = 'active'

                        listCards.append(
                            {
                                'id': str(entryJSON['id']),
                                'number': entryJSON['cardNumber'],
                                'status': status
                            }
                        )

                    successAttempt = True

                except:
                    pass

            if not successAttempt:
                return Result('Couldn\'t get the list cards')

        if listCards:
            write_list_cards_to_file(
                'tatneft',
                self.siteLogin,
                listCards
            )

            return Result('Successful', True, listCards)
        else:
            return Result('Couldn\'t get the list cards')

    def getListTransactions(self, cards: list, periodStart: str, periodEnd: str) -> Result:

        transactionsList = []
        for numberCard in cards:
            result = self.getListTransactionsBySiteAPI(
                numberCard['number'],
                periodStart,
                periodEnd
            )
            if result:
                if result.data:
                    transactionsList += result.data
            else:
                break

        if result:
            return Result('Successful', True, transactionsList)
        else:
            return Result(
                'Couldn\'t get a list of transactions for fuel cards')

    def getListTransactionsBySiteAPI(self,
                            numberCard: str,
                            periodStart: str = '',
                            periodEnd: str = '') -> Result:

        transactions = []

        dataGetting = False
        for i in range(1, 10):
            if dataGetting:
                break
            if i != 1:
                time.sleep(0.3)

            try:
                cardID = id_card('tatneft', self.siteLogin, numberCard)
                if not cardID:
                    continue

                dateStart = (
                    datetime.
                    strptime(periodStart, '%d.%m.%Y').
                    strftime('%Y-%m-%d')
                )
                dateEnd = (
                    datetime.
                    strptime(periodEnd, '%d.%m.%Y').
                    strftime('%Y-%m-%d')
                )

                response = self.send_request(
                    'api/util/loadForm/tnp.customerCard')
                if not response.status_code == 200:
                    continue

                response = self.send_request(
                    'api/data/cardTxnList/tnp.customerCard/$all',
                    json.dumps(
                        {
                            'cardNumber': numberCard,
                            'pager': {
                                'page': 1,
                                'pageSize': 10000
                            },
                            'txnDateFrom': dateStart,
                            'txnDateTo': dateEnd
                        }
                    )
                )

                if not response.status_code == 200:
                    continue

                dataTransaction = json_to_structure(response.text)
                if not 'data' in dataTransaction:
                    continue
                
                dataGetting = True
                for data in dataTransaction['data']:

                    response = self.send_request('api/util/loadForm/tnp.txn')
                    if not response.status_code == 200:
                        dataGetting = False
                        break

                    response = self.send_request(
                        'api/data/txnLineItemList/tnp.txn/$all',
                        json.dumps(
                            {
                                'docId': ''.join([
                                        cardID,
                                        ';',
                                        convert_to_numeric_str(data['id'])
                                    ]),
                                'pager': {
                                    'page': 1,
                                    'pageSize': 10
                                }
                            }
                        )
                    )
                    if not response.status_code == 200:
                        dataGetting = False
                        break

                    dataItems = json_to_structure(response.text)
                    if not 'data' in dataItems:
                        dataGetting = False
                        break

                    items = []
                    for item in dataItems['data']: 
                        items.append({
                            'id': convert_to_numeric_str(item['id']),
                            'category': parsing.code_category(self, item['goodsCategory']),
                            'categoryDescription': item['goodsCategoryDescription'],
                            'group': item['goodsGroup'],
                            'groupDescription': item['goodsGroupDescription'],
                            'item': item['goodsItem'],
                            'itemDescription': item['goodsItemDescription'],
                            'quantity': convert_to_numeric_str(item['quantity']),
                            'price': convert_to_numeric_str(item['price']),
                            'priceWithDiscount': convert_to_numeric_str(item['priceWithDiscount']),
                            'amount': convert_to_numeric_str(item['amount']),
                            'amountWithDiscount': convert_to_numeric_str(item['amount']),
                        })

                    transactions.append({
                        'id': convert_to_numeric_str(data['id']),
                        'dateTime': data['transactionDate'].strip(),
                        'cardNumber': convert_to_numeric_str(data['cardNumber']),
                        'type': parsing.code_type_transaction(self, data['requestCategory']),
                        'details': data['transactionDetails'].strip(),
                        'amount': convert_to_numeric_str(data['amount']),
                        'discount': convert_to_numeric_str(data['discount']),
                        'items': items
                    })
                    dataGetting = True

                self.send_request('api/util/loadData/tnp.mainData')
            except:
                continue

        if dataGetting:
            return Result('Successful', True, transactions)
        else:
            return Result(
                'Couldn\'t get a data for fuel cards')

    def getListTransactionsByReportHTML(self, periodStart: str, periodEnd: str) -> Result:

        if not self.tempDir:
            return Result('The download file storage directory is not set')

        formatReport = 'html'
        nameReport = 'ТранзакцииПоКартамКонтракта'.lower()

        resultDownload = self.downloadReportIsExist(nameReport, formatReport, periodStart, periodEnd, 30, 5)

        if not resultDownload:
            
            if self.orderReport(nameReport, formatReport, periodStart, periodEnd):
                resultDownload = self.downloadReportIsExist(nameReport, formatReport, periodStart, periodEnd, 4)

        if not resultDownload:
            return Result('Failed to load transaction report file')

        downloadingFile = None
        for i in range(1, 10):
            time.sleep(1.5)
            files = os.listdir(self.tempDir)
            files = [os.path.join(self.tempDir, file) for file in files]
            files = [file for file in files if os.path.isfile(file)]
            if len(files) > 0:
                downloadingFile = max(files, key=os.path.getctime)
                if downloadingFile:
                    break

        if not downloadingFile:
            return Result('Failed to load transaction report file')

        with open(downloadingFile, 'r', encoding='utf-8') as readFile:

            card = ''
            item = ''
            listTransactions = []

            soup = bs4(readFile.read(), 'html5lib')
            tables = soup.find_all('table', attrs={'class': 'jrPage'})
            for table in tables:
                trs = table.find_all('tr', attrs={'style': 'height:555px'})
                if len(trs) == 0:
                    continue
                baseTR = trs[0]
                div = baseTR.find_all('div', attrs={
                                      'style': 'position: relative; width: 100%; height: 100%; pointer-events: none; '})[0]
                rows = div.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')

                    if len(cells) == 1:
                        continue

                    if len(cells) == 3:
                        findSpans = row.find_all('span')
                        if not findSpans:
                            continue
                        findText = findSpans[0].text.strip()
                        if findText.isdigit():
                            card = findText
                        else:
                            item = findText

                    if len(cells) == 9:
                        if cells[1].text.strip().lower() == 'дата':
                            continue

                        group = re.search(r'(\w+)', item).group(1)
                        item = item.partition('(')[0].strip()
                        
                        amount = float(convert_to_numeric_str(cells[4].text))
                        quantity = float(convert_to_numeric_str(cells[2].text))
                        if amount >= 0:
                            typeTransaction = 'return'
                        else:
                            amount = amount * -1
                            typeTransaction = 'sale'
                            
                        items = []

                        items.append({
                            'id': '',
                            'category': 'fuel',
                            'categoryDescription': 'Нефтепродукты',
                            'group': group,
                            'groupDescription': group,
                            'item': item,
                            'itemDescription': item,
                            'quantity': convert_to_numeric_str(quantity),
                            'price': convert_to_numeric_str(cells[3].text),
                            'priceWithDiscount': convert_to_numeric_str(0),
                            'amount': convert_to_numeric_str(amount),
                            'amountWithDiscount': convert_to_numeric_str(0),
                        })


                        listTransactions.append({
                            'id': '',
                            'dateTime': datetime.strptime(
                                cells[1].text.strip(),
                                '%d.%m.%Y %H:%M:%S').
                                strftime('%Y-%m-%dT%H:%M:%S'),
                            'cardNumber': convert_to_numeric_str(card),
                            'type': typeTransaction, # - sale; + return
                            'details': cells[6].text.strip(),
                            'amount': convert_to_numeric_str(amount),
                            'discount': convert_to_numeric_str(0),
                            'items': items
                        })

        return Result('Successful', True, listTransactions)

    def getListTransactionsByReportXLS(self, periodStart: str, periodEnd: str) -> Result:

        if not self.tempDir:
            return Result('The download file storage directory is not set')

        formatReport = 'xlsx'
        nameReport = 'ТранзакцииЗаОтчётныйПериод(КакВРассылке)'.lower()
        
        resultDownload = self.downloadReportIsExist(nameReport, formatReport, periodStart, periodEnd, 60, 5)

        if not resultDownload:
            
            if self.orderReport(nameReport, formatReport, periodStart, periodEnd):
                resultDownload = self.downloadReportIsExist(nameReport, formatReport, periodStart, periodEnd, 4)

        if not resultDownload:
            return Result('Failed to load transaction report file')

        downloadingFile = None
        for i in range(1, 10):
            time.sleep(1.5)
            files = os.listdir(self.tempDir)
            files = [os.path.join(self.tempDir, file) for file in files]
            files = [file for file in files if os.path.isfile(file)]
            if len(files) > 0:
                downloadingFile = max(files, key=os.path.getctime)
                if downloadingFile:
                    break

        if not downloadingFile:
            return Result('Failed to load transaction report file')

        listTransactions = []
        woorkbook = openpyxl.load_workbook(downloadingFile)
        worksheet = woorkbook.active

        for row in worksheet.values:
    
            dataRow=tuple(row)

            type = dataRow[20]

            if type != 'покупка' and type != 'возврат':
                continue

            amount = float(dataRow[14])
            amountWhithDiscont = float(dataRow[16])
            amountDiscont = amount - amountWhithDiscont
            price=dataRow[13]
            priceWhithDiscont=dataRow[15]
            quantity = float(dataRow[11])
            address = ''
            category = 'fuel'
            categoryDescription = 'Нефтепродукты'

            if isinstance(dataRow[5], str) and isinstance(dataRow[7], str) and isinstance(dataRow[8], str) and isinstance(dataRow[9], str):
                address = ', '.join([dataRow[5], dataRow[7], dataRow[8], dataRow[9]])
            
            item=dataRow[10]
            group=''
            id=dataRow[22]
            items = []

            if amount >= 0:
                typeTransaction = 'return'
            else:
                amount = amount * -1
                typeTransaction = 'sale'

            items.append({
                'id': '',
                'category': category,
                'categoryDescription': categoryDescription,
                'group': group,
                'groupDescription': group,
                'item': item,
                'itemDescription': item,
                'quantity': convert_to_numeric_str(quantity),
                'price': convert_to_numeric_str(price),
                'priceWithDiscount': convert_to_numeric_str(priceWhithDiscont),
                'amount': convert_to_numeric_str(amount),
                'amountWithDiscount': convert_to_numeric_str(amountWhithDiscont),
            })

            listTransactions.append({
                'id': id,
                'dateTime': dataRow[0].strftime('%Y-%m-%dT%H:%M:%S'),
                'cardNumber': dataRow[1],
                'type': typeTransaction,
                'details': address,
                'amount': convert_to_numeric_str(amount),
                'discount': convert_to_numeric_str(amountDiscont),
                'items': items
            })

        return Result('Successful', True, listTransactions)

    def getDataCards(self, cards: list) -> Result:

        limitsCards = []
        for cardData in cards:
            result = self.getDataCard(cardData['number'])
            if result:
                limitsCards.append(result.data)
            else:
                break

        if limitsCards and result:
            return Result('Successful', True, limitsCards)
        else:
            return Result(
                'Couldn\'t get a list of limits for fuel cards')

    def getDataCard(self, numberCard: str) -> Result:
        functions = {
            'function1': self.getDataCardBySiteAPI,
            'function2': self.getDataCardBySelenium
        }
        for function in functions:
            result = functions[function](numberCard)
            if result: break
        return result

    def getDataCardBySiteAPI(self, numberCard: str) -> Result:

        dataCard = {
            'number': numberCard,
            'status': '',
            'limits': []
        }

        dataGetting = False
        for i in range(1, 5):
            if dataGetting:
                break
            if i != 1:
                time.sleep(1.5)

            try:
                cardID = id_card('tatneft', self.siteLogin, numberCard)
                if not cardID:
                    continue

                response = self.send_request(
                    'api/util/loadForm/tnp.customerCard')
                if not response.status_code == 200:
                    continue

                uri = ''.join([
                    'api/util/loadData/tnp.customerCard?id=',
                    cardID,
                    '&clientId=',
                    self.clientId
                ])
                response = self.send_request(uri)
                if not response.status_code == 200:
                    continue

                jsonData = json_to_structure(response.text)
                if not 'data' in jsonData:
                    continue

                dataCard['status'] = parsing.code_status(
                    self,
                    jsonData['data'].get('status', '')
                )

                response = self.send_request(
                    'api/data/cardLimitList/tnp.customerCard/$all',
                    json.dumps(
                        {
                            'contractId': cardID,
                            'pager': {
                                'page': 1,
                                'pageSize': 9
                            }
                        }
                    )
                )
                if not response.status_code == 200:
                    continue

                jsonData = json_to_structure(response.text)
                if not 'data' in jsonData:
                    continue

                for dataLimit in jsonData['data']:

                    if dataLimit['goodsCategoryDescription']:
                        categoryDescription = dataLimit['goodsCategoryDescription'].strip(
                        )
                    else:
                        categoryDescription = ''

                    if dataLimit['goodsGroupDescription']:
                        groupDescription = dataLimit['goodsGroupDescription'].strip(
                        )
                    else:
                        groupDescription = ''

                    if dataLimit['goodsItemDescription']:
                        itemDescription = dataLimit['goodsItemDescription'].strip(
                        )
                    else:
                        itemDescription = ''

                    dataCard['limits'].append(
                        {
                            'id': str(dataLimit['id']),
                            'code': str(dataLimit['templateCode']),
                            'category': parsing.code_category(self, dataLimit['goodsCategory']),
                            'categoryDescription': categoryDescription,
                            'group': convert_to_lower_simple_chars(dataLimit['goodsGroup']),
                            'groupDescription': groupDescription,
                            'item': convert_to_lower_simple_chars(dataLimit['goodsItem']),
                            'itemDescription': itemDescription,
                            'currency': parsing.code_currency(self, dataLimit['globalControlCode']),
                            'period': parsing.code_period(self, dataLimit['periodUnit']),
                            'value': convert_to_numeric_str(dataLimit['maxAmount']),
                            'balance': convert_to_numeric_str(dataLimit['usedAmount'])
                        }
                    )

                self.send_request('api/util/loadData/tnp.mainData')
                dataGetting = True

            except:
                continue

        if dataCard and dataGetting:
            return Result('Successful', True, dataCard)
        else:
            return Result(
                'Couldn\'t get a data for fuel cards')

    def getDataCardBySelenium(self, numberCard: str) -> Result:

        dataCard = {
            'number': numberCard,
            'status': '',
            'limits': []
        }

        dataGetting = False
        for i in range(1, 50):
            if i != 1:
                time.sleep(0.3)

            if dataGetting:
                break

            result = parsing.open_section_card_data(self, numberCard)
            if not result:
                continue

            idCard = id_card('tatneft', self.siteLogin, numberCard)

            uri = ''.join([
                'api/util/loadData/tnp.customerCard?id=',
                idCard,
                '&clientId=',
                self.clientId
            ])

            entries = None
            for x in range(1, 20):
                if x != 1:
                    time.sleep(0.3)

                entries = parsing.find_requests(
                    self,
                    uri=uri
                )
                if not entries:
                    continue
                else:
                    break

            if not entries:
                continue

            try:
                strJSON = entries[0]['response']['content']['text']
                jsonData = json_to_structure(strJSON)

                if not jsonData:
                    continue

                dataCard['status'] = parsing.code_status(self,
                                                         jsonData['data'].get('status', ''))
            except:
                continue

            result = self.get_limits_from_proxy_log()
            if result:
                dataCard['limits'].append(result.data)
                dataGetting = True

        if dataCard and dataGetting:
            return Result('Successful', True, dataCard)
        else:
            return Result(
                'Couldn\'t get a data for fuel cards')


# ======================== Auxiliary functions =========================

    def get_limits_from_proxy_log(self) -> Result:

        limits = []

        entries = None
        for x in range(1, 20):
            if x != 1:
                time.sleep(0.3)
            entries = parsing.find_requests(
                self,
                uri='api/data/cardLimitList/tnp.customerCard/$all'
            )
            if not entries:
                continue
            else:
                break

        if not entries:
            return Result('Successful', True, limits)

        try:
            strJSON = entries[0]['response']['content']['text']
            jsonData = json_to_structure(strJSON)

            if not jsonData:
                return Result('Error')

            for dataLimit in jsonData['data']:

                if dataLimit['goodsCategoryDescription']:
                    categoryDescription = dataLimit['goodsCategoryDescription'].strip(
                    )
                else:
                    categoryDescription = ''

                if dataLimit['goodsGroupDescription']:
                    groupDescription = dataLimit['goodsGroupDescription'].strip(
                    )
                else:
                    groupDescription = ''

                if dataLimit['goodsItemDescription']:
                    itemDescription = dataLimit['goodsItemDescription'].strip()
                else:
                    itemDescription = ''

                limits.append(
                    {
                        'id': str(dataLimit['id']),
                        'category': parsing.code_category(self, dataLimit['goodsCategory']),
                        'categoryDescription': categoryDescription,
                        'group': convert_to_lower_simple_chars(dataLimit['goodsGroup']),
                        'groupDescription': groupDescription,
                        'item': convert_to_lower_simple_chars(dataLimit['goodsItem']),
                        'itemDescription': itemDescription,
                        'currency': parsing.code_currency(self, dataLimit['globalControlCode']),
                        'period': parsing.code_period(self, dataLimit['periodUnit']),
                        'value': convert_to_numeric_str(dataLimit['maxAmount']),
                        'balance': convert_to_numeric_str(dataLimit['usedAmount'])
                    }
                )
        except:
            return Result('Error')

        return Result('Successful', True, limits)

    def predefined_ID(self, elementName: str = None) -> dict or str:

        if not isinstance(elementName, type('')) or not elementName:
            return self.predefinedIDs

        searchKey = elementName.strip().lower().replace(' ', '')
        return self.predefinedIDs.get(searchKey, '')

    def get_modal_form(self) -> Result:

        form = None
        for i in range(1, 5):
            if i != 1:
                time.sleep(1)

            try:
                foundForm = self.webBrowser.find_element(
                    By.TAG_NAME, 'mat-dialog-container')
                if foundForm:
                    form = foundForm
                    break
            except:
                pass

            if not form:
                continue

        if form:
            return Result('Ok', True, form)
        else:
            return Result('Not found form Limit')

    def set_value_in_list(self, label: str, value) -> Result:

        result = self.get_modal_form()
        if not result:
            return ('Not found form Limit')
        else:
            form = result.data

        for i in range(1, 5):
            if i != 1:
                time.sleep(0.5)

            field = None
            try:
                for elementGroup in form.find_elements(By.CLASS_NAME, 'group__row'):
                    elementsGroup = elementGroup.find_elements(
                        By.CLASS_NAME, 'group__dynamic-element')
                    if elementsGroup:
                        dataField = elementsGroup[0].text.split('\n')
                        if dataField:
                            if convert_to_lower_simple_chars(dataField[0]) == convert_to_lower_simple_chars(label):
                                field = elementsGroup[0]
                                break
                        else:
                            continue
                    else:
                        continue
            except:
                continue

            if not field:
                return Result(''.join([
                    'Couldn\'t find the "',
                    label,
                    '" field'
                ]))

            return parsing.select_value_from_list(
                self, field, 'mat-option', value)

    def convert_headers_to_dict(self, headers: object) -> dict:
        result = {}
        try:
            if isinstance(headers, list):
                for entry in headers:
                    result[entry['name']] = entry['value']
            elif isinstance(headers, str):
                listHeaders = json_to_structure(headers)
                if listHeaders:
                    result = self.convert_headers_to_dict(listHeaders)
            else:
                for entry in headers:
                    result[entry] = headers[entry]
        except:
            result = {}
        return result

    def get_token_from_headers(self, headers) -> str:
        result = ''
        if not isinstance(headers, dict):
            return result
        return self.get_value_from_cookie(headers, 'XSRF-TOKEN')

    def get_value_from_cookie(self, headers: dict, key: str) -> str:
        
        result = ''
        
        if 'Cookie' in headers:
            cookie = headers.get('Cookie', '')
        elif 'Set-Cookie' in headers:
            cookie = headers.get('Set-Cookie', '')
        else:
            return result
        
        if cookie:

            entriesCookie = cookie.split(';')
            for entry in entriesCookie:
                
                splitEntry = entry.split('=')
                if not len(splitEntry) == 2:
                    continue

                keys = splitEntry[0].replace(' ', '').split(',')
                if key in keys:
                    if splitEntry[1]:
                        result = splitEntry[1].strip()
        return result

    def replace_value_in_cookie(self, headers: dict,
                                key: str, value: str) -> dict:
        
        result = headers
        
        if 'Cookie' in headers:
            nameCookie = 'Cookie'
        elif 'Set-Cookie' in headers:
            nameCookie = 'Set-Cookie'
        else:
            return result
        
        cookie = headers.get(nameCookie, '')
        newCookie = ''
        
        if cookie:

            entriesCookie = cookie.split(';')
            for entry in entriesCookie:

                splitEntry = entry.split('=')
                if not len(splitEntry) == 2:
                    continue
                if not splitEntry[1]:
                    continue

                keys = splitEntry[0].replace(' ', '').split(',')
                if key in keys:
                    newCookie += ''.join([key, '=', value, ';'])
                else:
                    newCookie += ''.join([splitEntry[0],
                                          '=', splitEntry[1], ';'])
        result[nameCookie] = newCookie
        return result

    def set_one_value_in_cookie(self, headers: dict,
                                key: str, value: str) -> dict:
        result = headers
        
        if 'Cookie' in headers:
            nameCookie = 'Cookie'
        elif 'Set-Cookie' in headers:
            nameCookie = 'Set-Cookie'
        else:
            return result
        
        newCookie = ''.join([key, '=', value])
        result[nameCookie] = newCookie
        
        return result

    def send_request(self, uri: str, data=None) -> requests.Response:

        url = ''.join([self.url, '/', uri])
        headers = self.basicHeaders
        
        if not isinstance(headers, dict):
            headers = self.convert_headers_to_dict(headers)
        if headers.get('Set-Cookie'):
            del headers['Set-Cookie']
            headers['Cookie'] = ''

        headers = self.set_one_value_in_cookie(
            headers,
            'XSRF-TOKEN',
            self.token
        )

        if data:
            result = self.sessionRequest.post(
                url, headers=headers, data=data)
        else:
            result = self.sessionRequest.get(url, headers=headers)
        
        if not result.status_code == 200:
            return result
        
        newToken = self.get_value_from_cookie(
            self.convert_headers_to_dict(result.headers),
            'XSRF-TOKEN'
        )

        self.token = newToken if newToken else self.token

        return result

    def downloadReportIsExist(self, nameReport: str, formatReport: str, periodStart: str, periodEnd: str, inaccuracyMinuts: int, numberAttempts=7):

        result = False
        timeOrderReport = datetime.now()

        if not parsing.open_main_section(self, 'Отчетность'):
            return result

        for i in range(1, 5):

            if i != 1:
                time.sleep(2)
            
            existSorts = False

            for element in (self.webBrowser.find_elements(By.TAG_NAME, 'td-svg-icon')):

                attrs = parsing.get_element_attributes(self, element)

                if attrs:
                    if (attrs.data.get('icon') and attrs.data.get('icon') == 'down-arrow'):
                        existSorts = True
                        break

            if existSorts:
                parsing.click_element(self, element)
            else:
                break

        for i in range(1, numberAttempts):

            if result:
                break
            if i != 1:
                time.sleep(1.5)

            try:

                inputsDate = self.webBrowser.find_elements(By.CLASS_NAME, 'field-date__input-field')
                dateStart = timeOrderReport
                dateEnd = timeOrderReport + timedelta(days=1)
                parsing.set_value_to_input(self, inputsDate[0], dateStart.strftime('%d.%m.%Y'))
                parsing.set_value_to_input(self, inputsDate[1], dateEnd.strftime('%d.%m.%Y'))

                divSearchButton = self.webBrowser.find_element(By.CLASS_NAME, 'field-action-button--applyFilter')
                svgSearchButton = divSearchButton.find_element(By.TAG_NAME, 'svg')

                if svgSearchButton:
                    if not parsing.click_element(self, svgSearchButton):
                        continue
                else:
                    continue
                
            except:
                pass

            time.sleep(2)

            try:
                for row in self.webBrowser.find_elements(By.TAG_NAME, 'mat-row'):

                    if result:
                        break

                    minTime = timeOrderReport - timedelta(minutes=inaccuracyMinuts)
                    maxTime = timeOrderReport + timedelta(minutes=inaccuracyMinuts)
                    cells = row.find_elements(By.TAG_NAME, 'mat-cell')
                    nameReportInTable = cells[0].text.strip().lower().replace(' ', '')

                    if (nameReportInTable == nameReport and
                        cells[1].text.strip().lower() == formatReport and
                        cells[2].text.strip() == periodStart and
                        cells[3].text.strip() == periodEnd and
                        cells[4].text.strip() != '' and
                        (datetime.strptime(cells[4].text.strip(), '%d.%m.%Y %H:%M') >= minTime and
                         datetime.strptime(cells[4].text.strip(), '%d.%m.%Y %H:%M') <= maxTime)):

                        elementSVG = row.find_elements(By.TAG_NAME, 'svg')[1]
                        if elementSVG:
                            resultClick = parsing.click_element(
                                self, elementSVG)
                            result = resultClick.status
            except:
                pass

        return result

    def orderReport(self, nameReport: str, formatReport: str, periodStart: str, periodEnd: str):
        
        result = False

        if not parsing.open_main_section(self, 'Отчетность'):
            return result

        resultFind = parsing.find_element_by_tag_and_text(self.webBrowser, 'button', 'ЗаказатьОтчет')
        if resultFind:
            if not parsing.click_element(self, resultFind.data):
                return result
        else:
            return result

        formOrderReport = self.webBrowser.find_element(By.TAG_NAME, 'mat-dialog-container')

        elementList = formOrderReport.find_elements(By.CLASS_NAME, 'field-md-dropdown-select')[1]
        if not parsing.select_value_from_list(self, elementList, 'mat-option', formatReport):
            return result

        elementList = formOrderReport.find_elements(By.CLASS_NAME, 'field-md-dropdown-select')[0]
        if not parsing.select_value_from_list(self, elementList, 'mat-option', nameReport):
            return result

        elementsInput = formOrderReport.find_elements(By.CLASS_NAME, 'field-date__input-field')
        elementStartPeriod = elementsInput[0]
        elementEndPeriod = elementsInput[1]

        if not parsing.set_value_to_input(self, elementStartPeriod, periodStart):
            return result
        
        if not parsing.set_value_to_input(self, elementEndPeriod, periodEnd):
            return result

        resultFind = parsing.find_element_by_tag_and_text(formOrderReport, 'button', 'Сохранить')
        
        if resultFind:
            if parsing.click_element(self, resultFind.data):
                time.sleep(1)
                result = True

        return result