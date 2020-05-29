import requests

while True:
    task_sample = requests.get("https://ssc.k2consult.ru/api/newtask",
                               params={'serviceid': 298,
                                       'tasktypeid': 1011},
                               auth=("k2-telegram-bot", "4BaQuH5GU5U8r6ynaqo1"))
    print(task_sample.status_code)