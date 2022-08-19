#!/usr/bin/env bash

set -eu
#set -x

####################################### IMPORT FILES ######################################
# shellcheck source=/dev/null
source functions.sh
# shellcheck source=/dev/null
source install_service.cfg

#################################### SERVICE FUNCTIONS ####################################
function systemUpdatePackages() {

    local question_title="Обновить систему?"
    local question_text="Произвести автоматическое обновление установленных пакетов?"

    answer=$(askQuestion "${question_title}" "${question_text}")

    if [ "${answer}" == "${TRUE}" ]; then

        echo "$ROOT_PASS" | sudo -S apt-get -y install -f &> /dev/null
        echo "$ROOT_PASS" | sudo -S apt-get -y update &> /dev/null
        echo "$ROOT_PASS" | sudo -S apt-get -y upgrade &> /dev/null
        echo "$ROOT_PASS" | sudo -S apt-get -y autoremove &> /dev/null
        echo "$ROOT_PASS" | sudo -S apt-get -y clean &> /dev/null
        echo "$ROOT_PASS" | sudo -S apt-get -y autoclean &> /dev/null

    fi

}

function systemInstallPackages() {

    local packages="python3-pip python3-dev build-essential libssl-dev \
        libffi-dev python3-setuptools python3-venv nginx"

    for name_package in ${packages}; do
        installPackage "${name_package}"
    done

}

function serviceMakeTreeDir() {

    for currentDir in ${SERVICE_DIR_TREE}; do

        if [ -d "${currentDir}" ]; then
            rm -rf "${currentDir}"
        fi

        mkdir -p "${currentDir}"

        echo "$ROOT_PASS" | sudo -S mkdir -p "${currentDir}"
        echo "$ROOT_PASS" | sudo -S chown -R "${SERVICE_USER}:${SERVICE_GROUP}" "${currentDir}"
        echo "$ROOT_PASS" | sudo -S chmod -R 644 "${currentDir}"

    done

}

function serviceCreateEnv() {

    cd "${SERVICE_DIR}" || exit
    local dirEnv="${SERVICE_DIR}/env"

    if [ -d "${dirEnv}" ]; then
        rm -rf "${dirEnv}"
    fi

    python3 -m venv "${dirEnv}"

    # shellcheck source=/dev/null
    source "${dirEnv}/bin/activate"

    packagesPython="wheel requests selenium selenium-wire beautifulsoup4 \
        html5lib fake-useragent uwsgi flask"

    for namePackage in ${packagesPython}; do
        installPython3Package "${namePackage}"
    done

    deactivate

}

function nginxConfig() {

    function readConfig() {

        local currentAreaHttp="${FALSE}"
        local excludesStringsInAreaHttp="# { }"

        while read -r string; do

            if [[ $string == *"http {"* ]]; then
                currentAreaHttp="${TRUE}"
                echo "httpAreaInsertionLocation" >> "${NGINX_CONF_FILE_TEMPLATE}"
            fi

            if [ "${currentAreaHttp}" == "${TRUE}" ]; then

                thisExcludedPhrase="${FALSE}"

                for phrase in ${excludesStringsInAreaHttp}; do

                    if [[ $string == *"${phrase}"* ]]; then
                        thisExcludedPhrase="${TRUE}"
                        break
                    fi

                done

                if [[ "${thisExcludedPhrase}" == "${FALSE}" && -n ${string} ]]; then
                    parametr=$(echo "$string" | awk '{print $1}' )
                    value=$(echo "$string" | awk '{print $2}' | sed 's/;//')
                    parametrsHttp+=( "${parametr} ${value}" )
                fi

            else
                echo "${string}" >> "${NGINX_CONF_FILE_TEMPLATE}"
            fi

            if [[ "${currentAreaHttp}" == "${TRUE}" && $string == *"}"* ]]; then
                currentAreaHttp="${FALSE}"
            fi

        done < "${NGINX_CONF_FILE}"

    }

    function setParametrs() {

        function setParametr() {

            if [ "$1" == "include" ]; then
                return 0
            fi

            local indexForSet="${FALSE}"
            local lengthSetParametr=${#parametrsHttp[@]}

            for (( indexSetParametr=0; $(( indexSetParametr < lengthSetParametr )); indexSetParametr++ )); do

                parametr=$(echo "${parametrsHttp[$indexSetParametr]}" | awk '{print $1}')

                if [ "${parametr}" == "$1" ]; then
                    indexForSet=${indexSetParametr}
                    break
                fi

            done

            if [ "${indexForSet}" == "${FALSE}" ]; then
                parametrsHttp+=( "$1 $2" )
            else
                parametrsHttp[indexForSet]="$1 $2"
            fi

        }

        local length=${#NGINX_CONF_PARAMS_FOR_SET[@]}
        for (( index=0; $(( index < length )); index++ )); do

            parametr=$(echo "${NGINX_CONF_PARAMS_FOR_SET[$index]}" | awk '{print $1}')
            value=$(echo "${NGINX_CONF_PARAMS_FOR_SET[$index]}" | awk '{print $2}')

            setParametr "${parametr}" "${value}"

        done

    }

    function writeConfigTemp() {

        local level=0

        while read -r string; do

            if [[ $string == *"}"* ]]; then
                level=$(( level-1 ))
            fi

            if [ "${string}" == "httpAreaInsertionLocation" ]; then

                echo "http {" >> "${NGINX_CONF_FILE_TMP}"

                local length=${#parametrsHttp[@]}
                for (( index=0; $(( index < length )); index++ )); do
                    echo "${NGINX_CONF_PARAMS_RETREAT}${parametrsHttp[$index]};" >> "${NGINX_CONF_FILE_TMP}"
                done

                echo "}" >> "${NGINX_CONF_FILE_TMP}"

            else

                local retreats=""
                for (( counterLevel=1; $(( counterLevel <= level )); counterLevel++ )); do
                    retreats="${NGINX_CONF_PARAMS_RETREAT}${retreats}"
                done

                local firstSymbol="${string:0:1}"
                if [[ "${firstSymbol}" == "#" ]]; then
                    echo "${string}" >> "${NGINX_CONF_FILE_TMP}"
                else
                    echo "${retreats}${string}" >> "${NGINX_CONF_FILE_TMP}"
                fi

            fi

            if [[ $string == *"{"* ]]; then
                level=$(( level+1 ))
            fi

        done < "${NGINX_CONF_FILE_TEMPLATE}"

    }

    function writeConfig() {

        local nginxConfigFileOld="${NGINX_CONF_FILE}.old"

        if [ -f "${nginxConfigFileOld}" ]; then
            echo "$ROOT_PASS" | sudo -S rm -rf "${nginxConfigFileOld}"
        fi

        echo "$ROOT_PASS" | sudo -S cp "${NGINX_CONF_FILE}" "${nginxConfigFileOld}"
        echo "$ROOT_PASS" | sudo -S bash -c "cat ${NGINX_CONF_FILE_TMP} | tee ${NGINX_CONF_FILE} > /dev/null"
    }

    if [ -f "${NGINX_CONF_FILE_TMP}" ]; then
        echo "$ROOT_PASS" | sudo -S rm -rf "${NGINX_CONF_FILE_TMP}"
    fi

    if [ -f "${NGINX_CONF_FILE_TEMPLATE}" ]; then
        echo "$ROOT_PASS" | sudo -S rm -rf "${NGINX_CONF_FILE_TEMPLATE}"
    fi

    local parametrsHttp=()

    readConfig
    setParametrs
    writeConfigTemp
    writeConfig

    echo "$ROOT_PASS" | sudo -S systemctl daemon-reload
    echo "$ROOT_PASS" | sudo -S systemctl stop nginx
    echo "$ROOT_PASS" | sudo -S systemctl enable nginx
    echo "$ROOT_PASS" | sudo -S systemctl start nginx

}

function nginxConfigSites() {

    local fileSiteAvailableService="${NGINX_CONF_DIR_SITES_AVAILABLE}/${SERVICE_NAME}"
    local fileSiteEnabledService="${NGINX_CONF_DIR_SITES_ENABLED}/${SERVICE_NAME}"
    local fileTmpSiteAvailableService="/tmp/nginx-sites-available-${SERVICE_NAME}"

    if [ -f "${fileSiteAvailableService}" ]; then
        echo "$ROOT_PASS" | sudo -S rm -rf "${fileSiteAvailableService}"
    fi

    if [ -f "${fileSiteEnabledService}" ]; then
        echo "$ROOT_PASS" | sudo -S rm -rf "${fileSiteEnabledService}"
    fi

    if [ -f "${fileTmpSiteAvailableService}" ]; then
        echo "$ROOT_PASS" | sudo -S rm -rf "${fileTmpSiteAvailableService}"
    fi

    ipAdresses=$(ip a | grep inet | grep -v inet6 | grep -v '127.0.0.1' | awk '{print $2}' | sed 's/^\(.*\)\/.*$/\1/')
    ipAdress=$(echo "${ipAdresses}" | awk '{ print $1}')

    echo "
upstream gate_pars_upstream {
	server unix:/tmp/${SERVICE_NAME}.sock;
}

server {
	listen 80;
	server_tokens off;
	server_name ${ipAdress};
	fastcgi_read_timeout 900s;

	location / {
		include uwsgi_params;
		uwsgi_pass unix:${SERVICE_DIR}/${SERVICE_NAME}.sock;
	}
    	
	location /static {
		root ${SERVICE_DIR};
	}
}" > "${fileTmpSiteAvailableService}"

    echo "$ROOT_PASS" | sudo -S bash -c "cat ${fileTmpSiteAvailableService} | tee ${fileSiteAvailableService} > /dev/null"
    echo "$ROOT_PASS" | sudo -S sudo ln -s "${fileSiteAvailableService}" "${NGINX_CONF_DIR_SITES_ENABLED}"

}

function serviceCreatUnit() {

    local fileService="/etc/systemd/system/${SERVICE_NAME}.service"
    local fileTmpService="/tmp/${SERVICE_NAME}.service"

    if [ -f "${fileService}" ]; then
        echo "$ROOT_PASS" | sudo -S rm -rf "${fileService}"
    fi

    if [ -f "${fileTmpService}" ]; then
        echo "$ROOT_PASS" | sudo -S rm -rf "${fileTmpService}"
    fi

    echo "
[Unit]
Description=uWSGI instance to serve ${SERVICE_NAME} project
After=network.target

[Service]
User=${SERVICE_USER}
Group=www-data
WorkingDirectory=${SERVICE_DIR}
ExecStart=${SERVICE_DIR}/venv/bin/uwsgi --ini ${SERVICE_NAME}.ini

[Install]
WantedBy=multi-user.target" > "${fileTmpService}"

    echo "$ROOT_PASS" | sudo -S bash -c "cat ${fileTmpService} | tee ${fileService} > /dev/null"

    echo "$ROOT_PASS" | sudo -S systemctl daemon-reload
    echo "$ROOT_PASS" | sudo -S systemctl stop "${SERVICE_NAME}"
    echo "$ROOT_PASS" | sudo -S systemctl enable "${SERVICE_NAME}"
    echo "$ROOT_PASS" | sudo -S systemctl start "${SERVICE_NAME}"

}

########################################## MAIN ###########################################
if [ "${USER}" == "root" ]; then
    whiptail --title " Уведомление " --clear --msgbox "Запрещено производить установку от пользователя root!" 7 60 3>&1 1>&2 2>&3
    exit 0
fi

sudo -k
if [ "$(requestPasswordSU)" == "${FALSE}" ]; then
    exit 0
fi

systemUpdatePackages
systemInstallPackages
nginxConfig
nginxConfigSites
serviceCreatUnit
#serviceMakeTreeDir
#serviceCreateEnv

echo 'Done'