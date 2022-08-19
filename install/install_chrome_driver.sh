#!/bin/bash

####################################### IMPORT FILES ######################################
source functions.sh
source install_service.cfg

######################################## VARIABLES ########################################
SERVICE_DIR_BIN="${SERVICE_DIR}/bin"
DIR_TMP="/tmp"

########################################### MAIN ##########################################

if [ ! -d "${SERVICE_DIR_BIN}" ]; then
    mkdir -p "${SERVICE_DIR_BIN}"
fi

chrome_version=$(google-chrome --version | awk '{print $3}')

rm -f "${DIR_TMP}/chromedriver"
rm -f "${DIR_TMP}/chromedriver_linux64.zip"

cd "${DIR_TMP}" || exit
wget "https://chromedriver.storage.googleapis.com/${chrome_version}/chromedriver_linux64.zip"

if [ -f "${DIR_TMP}/chromedriver_linux64.zip" ]; then

    installPackage "unzip"
    unzip chromedriver_linux64.zip

    if [ -f "${DIR_TMP}/chromedriver" ]; then
        rm -f "${SERVICE_DIR_BIN}/chromedriver"
        mv "${DIR_TMP}/chromedriver" "${DIRSERVICE_DIR_BIN_BIN}/chromedriver" 
        chmod +x "${SERVICE_DIR_BIN}/chromedriver"
    fi

fi
