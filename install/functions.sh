#!/usr/bin/env bash

###########################################################################################
#################################### DEFAULT FUNCTIONS ####################################
###########################################################################################

# Функция запрашивает для текущего пользователя $USER пароль, использую текстовый интерфейс.
# В дальнейшем данный парольль будет использован для команды sudo
# Входящие параметры:
#   отсутствуют
# Глобальные переменные:
#   ROOT_PASS - пароль для sudo
# Возвращаемое значение:
#   Булево
function requestPasswordSU() {

  result="${FALSE}"
  ROOT_PASS=$(whiptail --title " Пароль SUPER USER " --ok-button "OK" --cancel-button "Отменить" \
    --clear --passwordbox "Введите пароль суперпользователя для $USER:" 10 60 3>&1 1>&2 2>&3)

  case $? in

    0)
      passCorrect=$(echo "${ROOT_PASS}" | sudo -S /bin/true && echo "${TRUE}")

      if [ "${passCorrect}" == "${TRUE}" ]; then
        result="${TRUE}"
      else
        whiptail --title " Уведомление " --clear --msgbox \
          "Пароль суперпользователя $USER введен неправильно. УСТАНОВКА ПРЕРВАНА!" 7 60 3>&1 1>&2 2>&3
      fi
      ;;

    1)
      whiptail --title " Уведомление " --ok-button "OK" --clear --msgbox \
        "УCТАНОВКА ПРЕРВАНА ПОЛЬЗОВАТЕЛЕМ!" 7 60 3>&1 1>&2 2>&3
      ;;

    255)
      whiptail --title " Уведомление " --ok-button "OK" --clear --msgbox \
        "УCТАНОВКА ПРЕРВАНА ПОЛЬЗОВАТЕЛЕМ!" 7 60 3>&1 1>&2 2>&3
      ;;

  esac

  echo "${result}"

}

# Задает пользователю вопрос, использую текстовый интерфейс.
# Входящие параметры:
#   $1 - Заголовок вопроса
#   $2 - Текст вопроса
# Возвращаемое значение:
#   Булево
function askQuestion() {

  whiptail --title " $1 " --clear --yesno --yes-button "Да" --no-button "Нет" "$2" 9 60 3>&1 1>&2 2>&3

  case $? in

    0)
      echo "${TRUE}"
      ;;

    1)
      echo "${FALSE}"
      ;;

    255)
      echo "${FALSE}"
      ;;

  esac

}

# Производит установку пакета, при условии что он не установлен.
# Входящие параметры:
#   $1 - Имя пакета
# Возвращаемое значение:
#   отсутствует
function installPackage() {

  installed=$(packageIsInstalled "$1")

  if [ "${installed}" == "${FALSE}" ]; then
    echo "$ROOT_PASS" | sudo -S apt-get -y --force-yes install "$1" &> /dev/null
  fi

}

# Проверяет установлен ли пакет в системе.
# Входящие параметры:
#   $1 - Имя пакета
# Возвращаемое значение:
#   Булево
function packageIsInstalled () {

  resultFind=$(dpkg -l | awk '{print $2}' | grep "$1" | sed 's/\:[^:]*$//' | grep ^"$1"$)

  if [ "${resultFind}" == "$1" ]; then
    echo "${TRUE}"
  else
    echo "${FALSE}"
  fi

}

# Производит установку пакета для Python3, при условии что он не установлен.
# Входящие параметры:
#   $1 - Имя пакета
# Возвращаемое значение:
#   отсутствует
function installPython3Package() {

  installed=$(packagePython3IsInstalled "$1")

  if [ "${installed}" == "${FALSE}" ]; then
    pip3 install "$1" &> /dev/null
  fi

}

# Проверяет установлен ли пакет для Python3 в системе.
# Входящие параметры:
#   $1 - Имя пакета
# Возвращаемое значение:
#   Булево
function packagePython3IsInstalled () {

  resultFind=$(pip3 list | grep -F "$1" | awk '{print $1}')

  if [ "${resultFind}" == "$1" ]; then
    echo "${TRUE}"
  else
    echo "${FALSE}"
  fi

}

# Определяет имя дистрибутива. Если доступные значения: ubuntu, fedora, centos
# Входящие параметры:
#   отсутствует
# Возвращаемое значение:
#   имя дистрибутива
function nameOS () {

  local distribs="ubuntu fedora centos"

  for nameDistrib in ${distribs}; do

    thisDistrib=$(cat /etc/*release* | grep -i "${nameDistrib}")

    if [[ -n "${thisDistrib}" ]]; then
      echo "${nameDistrib}"
      break
    fi

  done

}