#!/bin/bash

DIR_BASIC=$(dirname $(pwd))
DIR_BIN="${DIR_BASIC}/bin"
DIR_TMP="/tmp"

chrome_version=$(google-chrome --version | awk '{print $3}')

rm -f "${DIR_TMP}/chromedriver"
rm -f "${DIR_TMP}/chromedriver_linux64.zip"

cd /tmp
wget "https://chromedriver.storage.googleapis.com/${chrome_version}/chromedriver_linux64.zip"

if [ -f "${DIR_TMP}/chromedriver_linux64.zip" ]; then

    unzip chromedriver_linux64.zip

    if [ -f "${DIR_TMP}/chromedriver" ]; then
        rm -f "${DIR_BIN}/chromedriver"
        mv "${DIR_TMP}/chromedriver" "${DIR_BIN}/chromedriver" 
        chmod +x "${DIR_BIN}/chromedriver"
    fi

fi
