from datetime import datetime

import requests


url = "http://127.0.0.1:5090/webhook/ticket"
body = {
  "chat_id": "398039301",
  "username": "sam_tvls",
  "question": "Цена проживания?",
  "ai_confident": False,
  "external_id": "",
  "date": int(datetime.now().timestamp() * 1000)
}


if __name__ == "__main__":
    res = requests.post(url=url, json=body)
    print(res)

