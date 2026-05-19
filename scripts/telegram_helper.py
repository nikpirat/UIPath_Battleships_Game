import requests
import json

BOT_TOKEN = ""
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    r = requests.post(url, json=payload)
    return str(r.status_code)

def get_latest_message(offset):
    url = f"{BASE_URL}/getUpdates"
    payload = {"offset": int(offset), "timeout": 5, "limit": 1}
    r = requests.post(url, json=payload)
    data = r.json()
    if data.get("result"):
        item = data["result"][0]
        update_id = item["update_id"]
        chat_id   = str(item["message"]["chat"]["id"])
        text      = item["message"].get("text", "").strip().upper()
        return json.dumps({
            "update_id": update_id,
            "chat_id":   chat_id,
            "text":      text,
            "found":     True
        })
    return json.dumps({
        "found":     False,
        "update_id": int(offset)
    })

def wait_for_start(offset):
    """
    Reads one pending update.
    Returns matched=True if the message text is /START or READY.
    Always returns the latest update_id so caller can advance offset.
    Does NOT require knowing chat_id in advance.
    """
    url = f"{BASE_URL}/getUpdates"
    payload = {"offset": int(offset), "timeout": 5, "limit": 1}
    r = requests.post(url, json=payload)
    data = r.json()
    if data.get("result"):
        item      = data["result"][0]
        update_id = item["update_id"]
        chat_id   = str(item["message"]["chat"]["id"])
        text      = item["message"].get("text", "").strip().upper()
        matched   = text in ["/START", "READY", "START"]
        return json.dumps({
            "update_id": update_id,
            "chat_id":   chat_id,
            "text":      text,
            "matched":   matched,
            "found":     True
        })
    return json.dumps({
        "found":     False,
        "matched":   False,
        "update_id": int(offset)
    })

def clear_pending_updates():
    """
    Call once at startup to flush any old messages sitting in the queue.
    Gets the latest offset so stale /start messages are ignored.
    """
    url = f"{BASE_URL}/getUpdates"
    payload = {"offset": -1, "limit": 1}
    r = requests.post(url, json=payload)
    data = r.json()
    if data.get("result"):
        return str(data["result"][-1]["update_id"] + 1)
    return "0"
