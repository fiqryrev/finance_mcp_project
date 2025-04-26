import os
import pyautogui
import time
def open_new_tab(url):
    os.system(f'start chrome {url}')

def change_url(url):
    # Memberikan sedikit waktu untuk memastikan Chrome terbuka
    time.sleep(2)

    # Menekan Ctrl+L untuk fokus ke address bar
    pyautogui.hotkey('ctrl', 'l')

    # Mengetikkan URL di address bar
    pyautogui.write(url)

    # Menekan Enter untuk membuka URL
    pyautogui.press('enter')