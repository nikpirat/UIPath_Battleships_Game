import requests
import json

BASE_URL_TEMPLATE = "https://api.telegram.org/bot{token}"


def _base_url(bot_token):
    return BASE_URL_TEMPLATE.format(token=bot_token)


def send_message(bot_token, chat_id, text):
    """Send a text message to `chat_id`."""
    url = f"{_base_url(bot_token)}/sendMessage"
    r = requests.post(url, json={"chat_id": chat_id, "text": text})
										
    return str(r.status_code)


def get_latest_message(bot_token, offset):
    """
    Poll for one update at `offset`.
    Returns JSON: { found, update_id, chat_id, text }
    """
    url = f"{_base_url(bot_token)}/getUpdates"
    r = requests.post(url, json={"offset": int(offset), "timeout": 5, "limit": 1})
										
    data = r.json()
    if data.get("result"):
        item = data["result"][0]
									 
													  
																   
        return json.dumps({
            "found":     True,
            "update_id": item["update_id"],
            "chat_id":   str(item["message"]["chat"]["id"]),
            "text":      item["message"].get("text", "").strip().upper(),
							 
        })
					   
						   
    return json.dumps({"found": False, "update_id": int(offset)})
	  


def wait_for_start(bot_token, offset):
    """
    Poll once and check whether the incoming message is a /start or READY.
    Returns JSON: { found, matched, update_id, chat_id, text }
																	 
												
    """
    url = f"{_base_url(bot_token)}/getUpdates"
    r = requests.post(url, json={"offset": int(offset), "timeout": 5, "limit": 1})
										
    data = r.json()
    if data.get("result"):
        item    = data["result"][0]
									 
													  
        text    = item["message"].get("text", "").strip().upper()
        matched = text in ("/START", "READY", "START")
        return json.dumps({
            "found":     True,
								 
							  
            "matched":   matched,
            "update_id": item["update_id"],
            "chat_id":   str(item["message"]["chat"]["id"]),
            "text":      text,
        })
    return json.dumps({
        "found":     False,
        "matched":   False,
        "update_id": int(offset),
    })


def clear_pending_updates(bot_token):
    """
    Flush stale messages at startup.
    Returns the next offset to use as a string (UiPath converts via CInt).
    """
    url = f"{_base_url(bot_token)}/getUpdates"
    r = requests.post(url, json={"offset": -1, "limit": 1})
										
    data = r.json()
    if data.get("result"):
        return str(data["result"][-1]["update_id"] + 1)
    return "0"
