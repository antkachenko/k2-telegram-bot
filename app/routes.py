from app import app
from flask import request
from flask import jsonify
from collections import defaultdict
import requests
import json
from requests.adapters import HTTPAdapter
from urllib3.util import Retry


START, SELECT_PROBLEM, DESCRIPTION, BLOCKING, TEAMVIEWER, PHONE, SCREENSHOT, BRAND, ADDRESS = range(9)
USER_STATE = defaultdict(lambda: [START, ''])


def requests_retry_session(retries=3, backoff_factor=0.3, status_forcelist=(500, 502, 504), session=None,):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def get_state(chat_id):
    return USER_STATE[chat_id][0]


def update_state(chat_id, state, task_sample):
    USER_STATE[chat_id] = [state, task_sample]


def write_json(data, filename="answer.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def write_my_data(data, filename="my_data.json"):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def send_message(chat_id, text, keyboard=False, buttons=('Отмена создания заявки',), request_contact=False):
    url = app.config['TELEGRAM_API_URL']+"sendMessage"
    answer = {'chat_id': chat_id, 'text': text}
    if keyboard:
        reply_keyboard_markup = {"keyboard": [[{"text": b}] for b in buttons],  # "request_contact": True
                                 "resize_keyboard": True, 'one_time_keyboard': True}
        if request_contact:
            reply_keyboard_markup["keyboard"][0][0]["request_contact"] = True
        answer['reply_markup'] = reply_keyboard_markup
    r = requests.post(url, json=answer)
    return r.json()


@app.route(f'/{app.config["TELEGRAM_TOKEN"]}', methods=['POST'])
def handler():
    r = request.get_json()
    chat_id = r['message']['chat']['id']
    text = r['message']['text'] if 'text' in r['message'] else None
    screenshot = r['message']['photo'] if 'photo' in r['message'] else None
    phone = r["message"]["contact"]["phone_number"] if "contact" in r['message'] else None

    if text == 'Отмена создания заявки':
        send_message(chat_id, "Создание заявки прекращено.",
                     keyboard=True, buttons=["Создать заявку"])

    elif text == 'Пропустить этот шаг' and USER_STATE[chat_id][0] in (4, 6,):
        # DONE настроить отправку сообщения для след фразы
        if USER_STATE[chat_id][0] is TEAMVIEWER:
            send_message(chat_id, "Оставьте свой номер для обратной связи", keyboard=True,
                         buttons=['Добавить номер телефона', 'Отмена создания заявки'], request_contact=True)
        else:
            send_message(chat_id, "К какому бренду вы относитесь?",
                         keyboard=True, buttons=app.config['BRANDS'])
        USER_STATE[chat_id][0] += 1

    elif text == '/start':
        send_message(chat_id,
                     text="Я готов зарегистрировать вашу новую заявку в техническую поддержку."
                          "Для этого потребуется 9 шагов. Начните создание заявки, нажав кнопку внизу.",
                     keyboard=True, buttons=["Создать заявку"])

    elif text == "Создать заявку":
        service_buttons = [k for k in app.config['SERVICES']]
        service_buttons.append('Отмена создания заявки')
        send_message(chat_id, "Выберите тип обращения", keyboard=True, buttons=service_buttons)
        update_state(chat_id, SELECT_PROBLEM, "")

    elif text in app.config['SERVICES']:
        s = requests.Session()
        s.auth = (app.config['SD_API_LOGIN'], app.config['SD_API_PASSWORD'])

        task_sample = requests_retry_session(session=s).get(app.config['SD_API_URL']+"/api/newtask",
                                                              params={'serviceid': app.config['SERVICES'][text][0],
                                                                      'tasktypeid': app.config['SERVICES'][text][1]},)
        task_sample = task_sample.json()
        task_sample = task_sample["Task"]
        task_sample["Name"] = f'{text}'
        username = f'@{r["message"]["from"]["username"]}' if "username" in r['message']["from"] \
            else r["message"]["from"]["first_name"]
        task_sample["Field216"] = username
        # DONE добавить ФИО Заявителя(Field216) в поле "Description" шаблона таска
        if task_sample["ServiceId"] == 536:
            send_message(chat_id, "Укажите номер ККМ (номер с наклейки в нижней части аппарата диной 14 знаков)")
        else:
            send_message(chat_id, "Опишите проблему подробно")
        update_state(chat_id, DESCRIPTION, task_sample)

    elif text and (get_state(chat_id) == DESCRIPTION):
        # DONE описание проблемы в поле "Description" шаблона таска
        task_sample = USER_STATE[chat_id][1]
        task_sample["Description"] = f'{text}\n'
        if task_sample["ServiceId"] == 536:
            task_sample["Field1070"] = f'{text}'
        send_message(chat_id, "Блокируются ли продажи?",
                     keyboard=True, buttons=['Да, блокируются', 'Нет, не блокируются', 'Отмена создания заявки'])
        update_state(chat_id, BLOCKING, task_sample)

    elif text in ['Да, блокируются', 'Нет, не блокируются']:
        # DONE изменить критичность таска в шаблоне таска
        task_sample = USER_STATE[chat_id][1]
        if text == 'Да, блокируются':
            task_sample["PriorityId"] = 12
            task_sample["PriorityName"] = "критичный"
        send_message(chat_id, "Пожалуйста укажите номер id и пароль программы TeamViewer",
                     keyboard=True, buttons=['Пропустить этот шаг', 'Отмена создания заявки'])
        update_state(chat_id, TEAMVIEWER, task_sample)

    elif text and (get_state(chat_id) is TEAMVIEWER):
        # DONE добавить инфу c id и паролем TeamViewer в шаблон таска
        task_sample = USER_STATE[chat_id][1]
        if text != 'Пропустить этот шаг':
            task_sample["Description"] = task_sample["Description"] + f'TeamViewer: {text}\n'
        send_message(chat_id, "Оставьте свой номер для обратной связи", keyboard=True,
                     buttons=['Добавить номер телефона', 'Отмена создания заявки'], request_contact=True)
        update_state(chat_id, PHONE, task_sample)

    elif phone:
        # DONE получить номер телефона (Field217) и занести его в шаблон таска
        # DONE создать заявку в SD и получить ответ с её id
        task_sample = USER_STATE[chat_id][1]
        task_sample["Description"] = task_sample["Description"] + f'{r["message"]["contact"]["phone_number"]}'
        task_sample["Field217"] = f'{r["message"]["contact"]["phone_number"]}'

        send_message(chat_id, "Прикрепите скриншот/фотографию",
                     keyboard=True, buttons=['Пропустить этот шаг', 'Отмена создания заявки'])
        update_state(chat_id, SCREENSHOT, task_sample)

    elif screenshot and get_state(chat_id) == SCREENSHOT:
        # DONE добавить скриншот в таск если он был загружен
        # DONE пофиксить спам сообщениями после загрузки каждого изображения
        task_sample = USER_STATE[chat_id][1]
        # Скачиваем картинку из телеги

        file_path = requests_retry_session().get(app.config["TELEGRAM_API_URL"] + "getFile",
                                 params={'file_id': screenshot[-1]["file_id"]})
        file_path = file_path.json()["result"]["file_path"]
        photo = requests_retry_session().get(f'https://api.telegram.org/file/bot{app.config["TELEGRAM_TOKEN"]}/{file_path}')
        # photo = requests.get(f'https://api.telegram.org/file/bot{app.config["TELEGRAM_TOKEN"]}/{file_path}')
        file = {'file': (f'screenshot_{screenshot[-1]["file_id"]}.png', photo.content, 'image/png')}

        upload_photo = requests_retry_session().post(app.config['SD_API_URL'] + '/api/TaskFile', files=file,
                                     auth=(app.config['SD_API_LOGIN'], app.config['SD_API_PASSWORD']))

        if task_sample.get('FileTokens', False):
            task_sample['FileTokens'] += f",{upload_photo.json()['FileTokens']}"
        else:
            task_sample['FileTokens'] = f"{upload_photo.json()['FileTokens']}"

        if get_state(chat_id) == SCREENSHOT:
            buttons = [i for i in app.config['BRANDS']]
            buttons.append('Отмена создания заявки')
            send_message(chat_id, "К какому бренду вы относитесь?",
                         keyboard=True, buttons=buttons)
            update_state(chat_id, BRAND, task_sample)
    elif text in app.config['BRANDS']:
        # DONE добавить инфу о бренде инициатора в шаблон таска
        task_sample = USER_STATE[chat_id][1]
        task_sample["Name"] = task_sample["Name"] + f' {text}'
        task_sample["Description"] = task_sample["Description"] + f' {text}'
        send_message(chat_id, "Укажите полное название магазина/ТЦ",
                     keyboard=True, buttons=['Отмена создания заявки'])
        update_state(chat_id, ADDRESS, task_sample)
    elif text and (get_state(chat_id) == ADDRESS):
        # DONE имя магазина/ТЦ занести в "Name" и "Description"
        task_sample = USER_STATE[chat_id][1]
        task_sample["Name"] = task_sample["Name"] + f' в {text}'
        task_sample["Description"] = task_sample["Description"] + f' в {text}\n'

        s = requests.Session()
        s.auth = (app.config['SD_API_LOGIN'], app.config['SD_API_PASSWORD'])

        task = requests_retry_session(session=s).post(app.config['SD_API_URL']+"/api/task", json=task_sample)
        task = task.json()
        send_message(chat_id, f"Спасибо, заявка создана, ее номер {task['Task']['Id']}",
                     keyboard=True, buttons=["Создать заявку"])
        update_state(chat_id, START, '')
    return jsonify(r)
