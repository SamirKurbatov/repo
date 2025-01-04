import os
import json
import requests
import re
import time
import yt_dlp
import shutil

from datetime import datetime
from yt_dlp.utils import orderedSet
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

API_KEY = "AIzaSyDWzqzAusSuSA9U2e11juBlM1N1OQt_twU"
CHANNEL_ID = "UCvz84_Q0BbvZThy75mbd-Dg"
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

def create_folder_structure(parent_name_folder, name):
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    base_dir = os.path.join(desktop_path, parent_name_folder)
    data_str = datetime.now().strftime("%Y%m%d%H%M%S")
    folder_name = f"{name} [{data_str}]"
    full_path = os.path.join(base_dir, folder_name)
    os.makedirs(full_path, exist_ok=True)
    return full_path

def rename_file(downloads_folder, file_name):
    clean_name = re.sub(r"\[\d+\]", "", file_name)  # Заменяет все цифры в скобках
    clean_name = clean_name.replace("[English (auto-generated)]", "").replace("[DownSub.com]", "").strip()

    new_file_name = f'{clean_name}.txt'
    new_file_path = os.path.join(downloads_folder, new_file_name)

    if os.path.exists(os.path.join(downloads_folder, file_name)):
        os.rename(os.path.join(downloads_folder, file_name), new_file_path)
        return new_file_path
    else:
        print(f"Файл {file_name} не найден в {downloads_folder}")
        return None  # Возвращаем None, если файл не найден

def download_transcription(url, save_folder, download_title):
    driver.get("https://downsub.com/")
    input_box = driver.find_element(By.CSS_SELECTOR, 'input[name="url"]')
    input_box.send_keys(url)
    input_box.send_keys(Keys.ENTER)

    time.sleep(10)

    # Нажатие на кнопку для скачивания транскрипции
    download_button = driver.find_element(By.XPATH,
                                          '//button[contains(@class, "download-button")]//span[@class="v-btn__content" and text()="TXT"]')
    download_button.click()

    max_wait_time = 10
    elapsed_time = 0
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")

    # Проверка существования скачанного файла
    while elapsed_time < max_wait_time:
        time.sleep(1)
        elapsed_time += 1
        # Проверяем все файлы в папке загрузок
        files_in_downloads = os.listdir(downloads_folder)
        for file in files_in_downloads:
            if file.endswith('.txt'):  # Ищем текстовый файл
                download_file_path = os.path.join(downloads_folder, file)
                break
        else:
            download_file_path = None

        if download_file_path:
            break

    # Если файл найден, переименовываем его
    if download_file_path:
        print(f'Файл {download_file_path} найден в папке загрузок!')
        renamed_file = rename_file(downloads_folder, os.path.basename(download_file_path))

        if renamed_file:
            shutil.move(renamed_file, save_folder)
            print(f'Файл перемещен в папку {save_folder}')
        else:
            print(f'Ошибка при переименовании файла: {download_file_path}')
    else:
        print(f'Файл не был найден после {max_wait_time} секунд ожидания.')



def get_latest_short(api_key, channel_id):
    youtube = build("youtube", "v3", developerKey=api_key)
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=1,
        order="date",
        type="video",
        videoDuration="short"
    )
    response = request.execute()
    print(json.dumps(response, indent=4))
    if "items" in response and response["items"]:
        video_id = response["items"][0]["id"]["videoId"]
        title = response["items"][0]["snippet"]["title"]
        return f"https://youtube.com/watch?v={video_id}", title
    return None, None


def download_video(video_url, save_path):
    ydl_opts = {
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'format': 'mp4'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])

if __name__ == "__main__":
    video_url, title = get_latest_short(API_KEY, CHANNEL_ID)
    if video_url:
        print(f"Новейший шортс: {title}")

        video_folder = create_folder_structure('все видео', 'видео')
        transcription_folder = create_folder_structure('транскрибации', 'транскрибация')

        print('Скачиваем транскрибацию')
        download_transcription(video_url, transcription_folder, title)
        print(f'Транскрибации сохранены в папке {transcription_folder}')

        print('Скачиваем видео...')
        download_video(video_url, video_folder)
        print(f"Видео сохранено в папке {video_folder}")

    else:
        print('Не удалось получить новейший шортс')