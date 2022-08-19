#!/usr/bin/python3

from lib.common.general import Result
import os.path
import subprocess
from sys import platform as nameOS
import time
import hashlib
from seleniumwire import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.remote.webelement import WebElement as TypeWebElement
from selenium.webdriver.chrome.webdriver import WebDriver as TypeWebDriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup as bs4
from lib.common.general import convert_to_lower_simple_chars
from lib.common.general import convert_to_numeric_str
from lib.common.general import id_card
from lib.common.general import json_to_structure
from selenium.webdriver.common.keys import Keys
from fake_useragent import UserAgent


def login(site: object,
          userName: str,
          password: str,
          driverWebBrowser: str = None) -> Result:

    if not site.webBrowser:

        if not driverWebBrowser:
            filesDriver = []
            if nameOS == "linux" or nameOS == "linux2":

                resultShell = subprocess.run(
                    'find /usr -type f -name chromedriver 2>/dev/null',
                    shell=True,
                    executable='/bin/bash',
                    stdout=subprocess.PIPE,
                    text=True
                )

                if isinstance(resultShell, subprocess.CompletedProcess):
                    filesDriver = (resultShell.
                                   stdout.
                                   strip().
                                   split('\\n'))

            elif nameOS == "win32":
                filesDriver = []
            else:
                return Result(''.join([
                    'Invalid operating system type: ',
                    nameOS]))
        else:
            if not isinstance(driverWebBrowser, type('')):
                return Result('The "driverWebBrowser" parameter is '
                              'not passed correctly to the "login"'
                              ' function')

            else:
                filesDriver = [driverWebBrowser]

        for fileDriver in filesDriver:
            if os.path.exists(fileDriver):
                driverWebBrowser = fileDriver
                break

        if not driverWebBrowser:
            return Result('Web browser driver not found')

        chrome_options = webdriver.ChromeOptions()
        #chrome_options.add_argument('headless')
        chrome_options.add_argument("start-maximized")
        chrome_options.add_argument("disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument(''.join([
            'user-agent=',
            UserAgent().chrome]))
        
        if site.tempDir:
            chrome_options.add_experimental_option(
                "prefs",
                {"download.default_directory": site.tempDir}
            )
        try:
            site.webBrowser = webdriver.Chrome(
                executable_path=driverWebBrowser,
                chrome_options=chrome_options,
                seleniumwire_options={'enable_har': True})
        except:
            return Result('Failed to create the "WEB Browser" object')

        site.webBrowser.implicitly_wait(40)

    time.sleep(0.5)
    authExist = False
    urns = site.urns.mainMenu()
    for nameURN in urns:
        url = ''.join([site.url, urns[nameURN]])
        if site.webBrowser.current_url == url:
            authExist = True
            break

    if not authExist:
        url = ''.join([site.url, site.urns.login])
        if site.webBrowser.current_url != url:
            site.webBrowser.get(url)

    elementUsername = (site.
                       webBrowser.
                       find_element(By.ID, site.predefined_ID('userName')))
    elementPassword = (site.
                       webBrowser.
                       find_element(By.ID, site.predefined_ID('password')))

    result = set_value_to_input(site, elementUsername, userName)
    if not result:
        return result

    result = set_value_to_input(site, elementPassword, password)
    if not result:
        return result

    resultFind = find_element_by_tag_and_text(site.webBrowser,
                                              'button',
                                              'Вход')

    del site.webBrowser.requests
    if resultFind:
        return click_element(site, resultFind.data, True)
    else:
        return resultFind


def findErrors(site: object) -> Result:

    for classError in site.classErrors:

        soup = bs4(site.webBrowser.page_source, 'html5lib')
        elements = soup.find_all('div', attrs={'class': classError})
        if elements:
            return Result(elements[0].text.strip(), True)

    return Result('Not errors', False)


def find_element_by_tag_and_text(webBrowser: (TypeWebElement or
                                              TypeWebDriver),
                                 tagName: str,
                                 text: str) -> Result:

    if (not isinstance(webBrowser, TypeWebElement) and
            not isinstance(webBrowser, TypeWebDriver)):
        return Result('The "webBrowser" parameter is not passed '
                      'correctly to the "find_element_by_tag_and_text"'
                      ' function')

    if not isinstance(tagName, type('')) or not tagName:
        return Result('The "tagName" parameter is not passed '
                      'correctly to the "find_element_by_tag_and_text"'
                      ' function')

    if not isinstance(text, type('')) or not text:
        return Result('The "text" parameter is not passed '
                      'correctly to the "find_element_by_tag_and_text"'
                      ' function')

    foundElements = webBrowser.find_elements(By.TAG_NAME, tagName)
    searchText = text.strip().lower().replace(' ', '')
    for element in foundElements:
        if not isinstance(element, TypeWebElement):
            continue

        elementText = element.text.strip().lower().replace(' ', '')
        if elementText == searchText:
            return Result('Successful', True, element)

    return Result(''.join(['Couldn\'t find an element with tag "',
                           tagName,
                           '" and text "',
                           searchText,
                           '"']))


def find_element_by_tag_and_class(webBrowser: (TypeWebElement or
                                               TypeWebDriver),
                                  tagName: str,
                                  className: str) -> Result:

    if (not isinstance(webBrowser, TypeWebElement) and
            not isinstance(webBrowser, TypeWebDriver)):
        return Result('The "webBrowser" parameter is not passed '
                      'correctly to the "find_element_by_tag_and_class"'
                      ' function')

    if not isinstance(tagName, type('')) or not tagName:
        return Result('The "tagName" parameter is not passed '
                      'correctly to the "find_element_by_tag_and_class"'
                      ' function')

    if not isinstance(className, type('')) or not className:
        return Result('The "className" parameter is not passed '
                      'correctly to the "find_element_by_tag_and_class"'
                      ' function')

    for element in (webBrowser.
                    find_elements(By.CLASS_NAME, className)):
        if element.tag_name == tagName:
            return Result('Successful', True, element)

    return Result(''.join(['Couldn\'t find an element with tag "',
                           tagName,
                           '" and class "',
                           className,
                           '"']))


def find_element_by_class_and_text(webBrowser: (TypeWebElement or
                                                TypeWebDriver),
                                   className: str,
                                   text: str) -> Result:

    if (not isinstance(webBrowser, TypeWebElement) and
            not isinstance(webBrowser, TypeWebDriver)):
        return Result('The "text" parameter is not passed correctly '
                      'to the "find_element_by_class_and_text" '
                      'function')

    if not isinstance(className, type('')) or not className:
        return Result('The "text" parameter is not passed correctly '
                      'to the "find_element_by_class_and_text" '
                      'function')

    if not isinstance(text, type('')) or not text:
        return Result('The "text" parameter is not passed correctly '
                      'to the "find_element_by_class_and_text" '
                      'function')

    searchText = text.strip().lower().replace(' ', '')
    for element in webBrowser.find_elements(By.CLASS_NAME, className):
        if not isinstance(element, TypeWebElement):
            continue

        elementText = element.text.strip().lower().replace(' ', '')
        if elementText == searchText:
            return Result('Successful', True, element)

    return Result(''.join(['Couldn\'t find an element with class "',
                           className,
                           '" and text "',
                           searchText,
                           '"']))


def click_element(site: object,
                  webElement: TypeWebElement,
                  checkErrors: bool = False) -> Result:

    if not isinstance(webElement, TypeWebElement):
        return Result('The "webElement" parameter is not passed '
                      'correctly to the "click_element" '
                      'function')

    try:
        textWebElement = webElement.text.strip()
    except:
        return Result('The element button is not find')
    
    del site.webBrowser.requests
    hashBefore = hashlib.md5((site.
                              webBrowser.
                              page_source.
                              encode('utf-8')))
    counter = 1
    successClick = False
    while counter <= 3 and not successClick:
        try:
            (
                ActionChains(site.webBrowser).
                move_to_element(webElement).
                click(webElement).
                perform()
            )
            successClick = True
        except:
            pass
        counter += 1

    if not successClick:
        return Result(''.join([
            'All attempts to click on the "',
            textWebElement,
            '" button ended in errors']))

    time.sleep(1)

    if checkErrors:
        resultFind = findErrors(site)
    else:
        resultFind = False

    if not resultFind:
        if hashBefore == hashlib.md5((site.
                                      webBrowser.
                                      page_source.encode('utf-8'))):
            return Result(''.join([
                'After click on the "',
                textWebElement,
                '", the content of the web page has not changed']))
        else:
            return Result('Successful', True)
    else:
        resultFind.status = False
        return resultFind


def set_value_to_input(site: object,
                       webElement: TypeWebElement,
                       value: str) -> Result:

    if not isinstance(webElement, TypeWebElement):
        return Result('The "webElement" parameter is not passed '
                      'correctly to the "set_value_to_input" '
                      'function')

    if not isinstance(value, type('')) or not value:
        return Result('The "value" parameter is not passed '
                      'correctly to the "set_value_to_input" '
                      'function')

    hashBefore = hashlib.md5((site.
                              webBrowser.
                              page_source.encode('utf-8')))

    result = False
    for i in range(1, 10):

        if result:
            break
        if i != 1:
            time.sleep(0.5)
        
        try:
            (
                ActionChains(site.webBrowser).
                move_to_element(webElement).
                click(webElement).
                perform()
            )
            webElement.send_keys(Keys.END)
            currentValue = webElement.get_attribute('value')
            for x in range(len(currentValue)):
                webElement.send_keys(Keys.BACKSPACE)

            webElement.send_keys(value)

            if (convert_to_numeric_str(webElement.get_attribute('value')) ==
                convert_to_numeric_str(value)):
                result = True
        except:
            pass

    if result:
        if hashBefore == hashlib.md5((site.
                                      webBrowser.
                                      page_source.encode('utf-8'))):
            return Result('After setting the value, the content of '
                          'the web page has not changed')
        else:
            return Result('Successful', True)
    else:
        return Result('Failed to set value')


def select_value_from_list(site: object,
                           webElement: TypeWebElement,
                           nameClassElements: str,
                           lookingNameField: str) -> Result:

    if not isinstance(webElement, TypeWebElement):
        return Result('The "webElement" parameter is not passed '
                      'correctly to the "select_value_from_list" '
                      'function')

    if (not isinstance(nameClassElements, type('')) or
            not nameClassElements):
        return Result('The "nameClassElements" parameter is not passed '
                      'correctly to the "select_value_from_list" '
                      'function')

    if (not isinstance(lookingNameField, type('')) or
            not lookingNameField):
        return Result('The "lookingNameField" parameter is not passed '
                      'correctly to the "select_value_from_list" '
                      'function')

    findID = None
    resultNotFindElement = Result('Could not find the item in the '
                                  'list of values')

    try:
        webElement.click()
        time.sleep(0.2)

        resultFind = find_element_by_class_and_text(site.webBrowser,
                                                    nameClassElements,
                                                    lookingNameField)
        if resultFind:
            resultGetAttributes = get_element_attributes(site,
                                                         resultFind.data)
            if resultGetAttributes.status:
                findID = resultGetAttributes.data['id']
            else:
                return resultNotFindElement
        else:
            return resultNotFindElement

    except:
        return resultNotFindElement

    if findID:
        try:
            site.webBrowser.find_element(By.ID, findID).click()
            if webElement.text.strip().lower().replace(' ', ''):
                return Result('Successful', True)
        except:
            return Result('Failed to set an item in the list of values')
    else:
        return resultNotFindElement


def get_element_attributes(site: object,
                           webElement: TypeWebElement) -> Result:

    result = {}

    if not isinstance(site.webBrowser, TypeWebDriver):
        return result

    if not isinstance(webElement, TypeWebElement):
        return result

    try:
        data = site.webBrowser.execute_script(
            '''
                let attr = arguments[0].attributes;
                let items = {};
                for (let i = 0; i < attr.length; i++) {
                    items[attr[i].name] = attr[i].value;
                }
                return items;
            ''',
            webElement
        )

        return Result('Successful', True, data)
    except:
        pass

    return result


def open_main_section(site: object, nameSection: str) -> Result:

    if not site.loginOn:
        return Result('Error when executing the "open_main_section" '
                      'function: authorization failed')

    if not isinstance(nameSection, type('')):
        return Result('The "nameSection" parameter is not passed '
                      'correctly to the "open_main_section" function')

    resultSectionNotFound = Result(''.join(['The "',
                                            nameSection,
                                            '" section was not found"']))

    searchLinkText = nameSection.strip().lower().replace(' ', '')
    urnMainMenu = site.urns.mainMenu(searchLinkText)
    if not urnMainMenu:
        return resultSectionNotFound

    url = ''.join([site.url, '/form', urnMainMenu])

    if site.webBrowser.current_url == url:
        return Result('Successful', True)

    foundElement = None
    for element in (site.webBrowser.
                    find_element(By.CLASS_NAME, 'nav-links-group').
                    find_elements(By.TAG_NAME, 'a')):

        if (element.text.strip().
                lower().replace(' ', '')) == searchLinkText:
            foundElement = element
            break

    if foundElement:
        del site.webBrowser.requests
        resultClick = click_element(site, foundElement)
        if resultClick.status:
            time.sleep(0.5)
        return resultClick
    else:
        return resultSectionNotFound


def open_section_card_data(site: object, numberCard: str) -> Result:

    from lib.sites.tatneft import TATNeft
    from lib.sites.rosneft import RNCart
    from lib.sites.petrolplus import PetrolPlus

    if not site.loginOn:
        return Result('Error when executing the "open_section_card_data" '
                      'function: authorization failed')

    if not isinstance(numberCard, type('')) or not numberCard:
        return Result('The "numberCard" parameter is not passed '
                      'correctly to the "open_main_section" function')

    nameSite = ''
    if isinstance(site, TATNeft):
        nameSite = 'tatneft'
    elif isinstance(site, RNCart):
        nameSite = 'rosneft'
    elif isinstance(site, PetrolPlus):
        nameSite = 'petrolplus'
    
    idCard = id_card(nameSite, site.siteLogin, numberCard)
    if idCard:

        result = Result('Couldn\'t find fuel card')
        for i in range(1, 5):
            if i != 1:
                time.sleep(2)

            try:
                url = ''.join([
                    site.url,
                    '/',
                    'form/tnp.customerCard?id=',
                    idCard,
                    '&clientId=',
                    site.clientId
                ])

                del site.webBrowser.requests
                site.webBrowser.get(url)
                time.sleep(1)

                result = Result('Successful', True)
                break
            except:
                pass
        
        return result

    else:
        resultOpenSection = open_main_section(site, 'Карты')
        if not resultOpenSection:
            return resultOpenSection

        elementInput = None
        for element in site.webBrowser.find_elements(By.TAG_NAME, 'input'):
            attributes = get_element_attributes(site, element)
            if not attributes:
                continue
            if (convert_to_lower_simple_chars(attributes.data['placeholder']
                                    ) == 'номеркарты' and attributes.data['type'] == 'text'):
                elementInput = element
                break

        if not elementInput:
            return Result('Couldn\'t find the "Карта" search field')

        resultSetInput = set_value_to_input(site, elementInput, numberCard)
        if not resultSetInput:
            return resultSetInput

        elementSVG = (
            site.webBrowser.
            find_element(By.CLASS_NAME, 'params-filter-content.ng-star-inserted').
            find_elements(By.TAG_NAME, 'svg')[1]
        )

        for i in range(1, 5):
            if i != 1:
                time.sleep(2)

            resultClick = click_element(site, elementSVG)
            if not resultClick:
                return resultClick
            else:
                rowsTable = (
                    site.webBrowser.find_element(By.TAG_NAME,  'mat-table').
                    find_elements(By.TAG_NAME, 'mat-row')
                )
                if len(rowsTable) != 1:
                    continue
                else:
                    break

        resultClick = Result('Couldn\'t find fuel card')
        for i in range(1, 5):
            if i != 1:
                time.sleep(2)

            try:
                rowsTable = (
                    site.webBrowser.find_element(By.TAG_NAME,  'mat-table').
                    find_elements(By.TAG_NAME, 'mat-row')
                )

                if len(rowsTable) != 1:
                    continue

                cellsRow = rowsTable[0].find_elements(By.TAG_NAME, 'mat-cell')
                if len(cellsRow) != 6:
                    continue
                
                del site.webBrowser.requests
                resultClick = click_element(
                    site,
                    cellsRow[0].find_elements(By.TAG_NAME, 'a')[0]
                )

                if resultClick:
                    break
            except:
                pass

        if not resultClick:
            return Result('When trying to open the fuel card data window, '
                        'an error occurred')
        else:
            return Result('Successful', True)


def code_category(site: object, value:str) -> str:

    from lib.sites.tatneft import TATNeft
    from lib.sites.rosneft import RNCart

    result = ''
    if isinstance(site, TATNeft):
        values = {
            '01': 'fuel',
            '02': 'gas',
            '03': 'goods',
            '04': 'service'
        }
        result = values.get(value, '')

    elif isinstance(site, RNCart):
        values = {
            'FUEL': 'fuel',
            'GOODS': 'goods',
            'SERVICE': 'service'
        }
        result = values.get(value, '')

    return result


def code_currency(site: object, value:str) -> str:

    from lib.sites.tatneft import TATNeft
    from lib.sites.rosneft import RNCart
    from lib.sites.petrolplus import PetrolPlus

    result = ''

    if not isinstance(value, str):
        value = str(value)

    if isinstance(site, PetrolPlus):
        values = {
            '4': 'rub',
            '1': 'litre'
        }
        result = values.get(value, '')

    elif isinstance(site, TATNeft):
        values = {
            'RLI_CURR': 'rub',
            'RLI_ITEM': 'litre'
        }
        result = values.get(value, '')

    elif isinstance(site, RNCart):
        values = {
            'C': 'rub',
            'V': 'litre'
        }
        result = values.get(value, '')

    return result


def code_period(site: object, value:str) -> str:

    from lib.sites.tatneft import TATNeft
    from lib.sites.rosneft import RNCart
    from lib.sites.petrolplus import PetrolPlus

    result = ''

    if not isinstance(value, str):
        value = str(value)

    if isinstance(site, PetrolPlus):
        values = {
            '0': 'nonrenewable',
            '1': 'day',
            '3': 'month',
            '4': 'quarter'
        }
        result = values.get(value, '')
    
    elif isinstance(site, TATNeft):
        values = {
            'E': 'nonrenewable',
            'F': 'day',
            'M': 'month',
            'Q': 'quarter'
        }
        result = values.get(value, '')

    elif isinstance(site, RNCart):
        values = {
            'N': 'nonrenewable',
            'F': 'day',
            'M': 'month',
            'Q': 'quarter'
        }
        result = values.get(value, '')

    return result


def code_status(site: object, value: str) -> str:

    from lib.sites.tatneft import TATNeft
    from lib.sites.rosneft import RNCart
    from lib.sites.petrolplus import PetrolPlus

    result = ''

    if not isinstance(value, str):
        value = str(value)

    if isinstance(site, PetrolPlus):
        if value.strip().lower() == '4':
            result = 'active'
        else:
            result = 'block'

    if isinstance(site, TATNeft):
        if value.strip().lower() == 'c_00':
            result = 'active'
        else:
            result = 'block'
    
    elif isinstance(site, RNCart):
        if value.strip().lower() == '00':
            result = 'active'
        else:
            result = 'block'

    return result

def code_type_transaction(site: object, value: str) -> str:
    
    from lib.sites.tatneft import TATNeft
    from lib.sites.rosneft import RNCart
    from lib.sites.petrolplus import PetrolPlus

    if not isinstance(value, str):
        value = str(value)

    result = ''

    if isinstance(site, PetrolPlus):
        if value.strip().lower() == '2':
            result = 'return'
        elif value.strip().lower() == '1':
            result = 'sale'
    
    elif isinstance(site, TATNeft):
        if value.strip().lower() == 'j':
            result = 'return'
        elif value.strip().lower() == 'p':
            result = 'sale'
    
    elif isinstance(site, RNCart):
        if value.strip().lower() == '24':
            result = 'return'
        elif value.strip().lower() == '11':
            result = 'sale'
        elif value.strip().lower() == '4':
            result = 'accountDebiting'
        elif value.strip().lower() == '1':
            result = 'accountReplenish'

    return result

def repres_category(site: object, value:str) -> str:

    from lib.sites.tatneft import TATNeft
    from lib.sites.rosneft import RNCart

    result = ''
    strValue = str(value).strip().lower()
    if isinstance(site, TATNeft):
        values = {
            'fuel': 'Нефтепродукты',
            'gas': 'Газ',
            'goods': 'Непродовольственные товары',
            'service': 'Услуги',
        }
        result = values.get(strValue, '')

    elif isinstance(site, RNCart):
        values = {
            'fuel': 'Топливо',
            'goods': 'Товары',
            'service': 'Услуги',
        }
        result = values.get(strValue, '')

    return result

def repres_period(site: object, value:str) -> str:

    from lib.sites.tatneft import TATNeft
    from lib.sites.rosneft import RNCart

    result = ''
    strValue = str(value).strip().lower()
    if isinstance(site, TATNeft):
        values = {
            'nonrenewable': 'Навсегда',
            'day': 'Сутки',
            'month': 'Месяц',
            'quarter': 'Квартал',
        }
        result = values.get(strValue, '')

    elif isinstance(site, RNCart):
        values = {
            'nonrenewable': 'Навсегда',
            'day': 'Сутки',
            'month': 'Месяц',
            'quarter': 'Квартал',
        }
        result = values.get(strValue, '')

    return result

def repres_currency(site: object, value:str) -> str:

    from lib.sites.tatneft import TATNeft

    result = ''
    strValue = str(value).strip().lower()
    if isinstance(site, TATNeft):
        values = {
            'rub': 'Рублей',
            'litre': 'Литров'
        }
        result = values.get(strValue, '')
    
    elif isinstance(site, TATNeft):
        values = {
            'rub': 'Рублей',
            'litre': 'Литров'
        }
        result = values.get(strValue, '')        

    return result

def all_requests(site: object) -> list:
    try:
        return json_to_structure(site.webBrowser.har)['log']['entries']
    except:
        return []

def find_requests(site: object, **kwagrs) -> list:
    
    url = None
    if kwagrs.get('uri'):
        url = ''.join([
            site.url,
            '/',
            kwagrs.get('uri')
        ])

    result = []
    try:
        entries = all_requests(site)
        for entry in entries:
            match = False
            if url:
                if entry['request']['url'] == url:
                    match = True
            if match:
                result.append(entry)
    except:
        return []

    return result
