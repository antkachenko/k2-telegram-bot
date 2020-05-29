import os


class Config(object):
    MY_URL = os.environ.get("MY_URL") or "http://localhost:5000"
    TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") or "1039885023:AAEGi0W0l1lI0R7xtf0ewZgDqrjCThkxQWM"
    TELEGRAM_METHOD = "setWebhook"
    TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
    SD_API_LOGIN = os.environ.get("SD_API_LOGIN") or "k2-telegram-bot"
    SD_API_PASSWORD = os.environ.get("SD_API_PASSWORD") or "4BaQuH5GU5U8r6ynaqo1"
    SD_API_URL = os.environ.get("SD_URL") or "https://ssc.k2consult.ru"
    BRANDS = ('re:Store', 'LEGO', 'Sony', 'Samsung',
              'Nike', 'UNOde50', 'Street Beat')
    SERVICES = {'Не работает интернет или телефония': [26, 1],
                'Неисправность ККМ': [536, 1009],
                'Проблемы связанные с 1С': [595, 1],
                'Заказ клиента OMNI': [421, 1],
                'Проблемы с Закрытием смены': [19, 1],
                'Оргтехника (сканеры/принтеры и т.п.)': [127, 30],
                'Не запускается ПК': [589, 1003],
                }
    LOG_TO_STDOUT = os.environ.get('LOG_TO_STDOUT')
