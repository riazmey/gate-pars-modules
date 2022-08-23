# gate-pars-modules
Модули входящие в службу gate_pars.

Принимающий модуль - `app.py`. Принимает запрос от Вэб-сервиса и производит запрос/ы в процессинговый центры топливной компании. 

Может обрабатывать запросы:
- Запрос остатка средств на лицевом счете - `getBalance` (GET запрос);
- Запрос списка топливных карт - `getListCards` (GET запрос);
- Блокировка топливной карты - `setStatusCard` (POST запрос);
- Разблокировка топливной карты - `setStatusCard` (POST запрос);
- Запрос списка лимитов по всем топливным картам - `getDataCards` (GET запрос);
- Запрос списка лимитов на топливной карте - `getDataCard` (GET запрос);
- Запрос списка транзакций за период - `getListTransactions` (GET запрос);
- Создать лимит на топливной карте - `setLimitCard` (POST запрос);
- Удалить лимит на топливной карте - `delLimitCard` (POST запрос);
- Изменить лимит на топливной карте - `editLimitCard` (POST запрос).

Поддерживаемые процеццинговые центры:
- РН-Карт - `rosneft`;
- ТАТ-Нефть - `tatneft`;
- ППР (Передовые платежные решения) - `petrolplus`.

#### Примеры запросов:
```
/api/getBalance?&site=tatneft&login=user&password=pass
/api/getListCards?&site=rosneft&login=user&password=pass
/api/delLimitCard?&site=petrolplus&api_key=keyapibysite&numberCard=9998887766&limitID=0
/api/setLimitCard?&site=petrolplus&api_key=keyapibysite&numberCard=9998887766&value=9999.99&category=FUEL&period=nonrenewable&currency=RUB 
/api/getListTransactions?&site=rosneft&login=user&password=pass&contract=numbercontract&periodStart=01.08.2022&periodEnd=30.08.2022
```
## Зависимости:
#### Системные пакеты:
```
apt-get install python3-pip python3-dev build-essential libssl-dev libffi-dev python3-setuptools python3-venv nginx
```
#### Python:
```
pip3 install requests selenium selenium-wire beautifulsoup4 html5lib fake-useragent uwsgi flask
```
