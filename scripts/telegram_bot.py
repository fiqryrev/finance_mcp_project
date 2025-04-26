import requests
def sendMessage(pesan, chat_id, reply_id=None, TOKEN=None):
    url = f'https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&parse_mode=MarkdownV2&text={pesan}'+ (f'&reply_to_message_id={reply_id}' if reply_id else '')
    response = requests.get(url)
    sending_message = response.json()
    return sending_message

def inbox(TOKEN):
    url = f'https://api.telegram.org/bot{TOKEN}/getUpdates'
    response = requests.get(url)
    all_message = response.json()
    return all_message