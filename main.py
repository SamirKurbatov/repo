import json
import os
import re
import time
import shutil
import random
from datetime import datetime
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import yt_dlp

API_KEY = "AIzaSyDWzqzAusSuSA9U2e11juBlM1N1OQt_twU"
CHANNEL_ID = "UCvz84_Q0BbvZThy75mbd-Dg"
HISTORY_FILE = "processed_videos.json"

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))

def create_folder_structure(parent_name_folder, name):
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    base_dir = os.path.join(desktop_path, parent_name_folder)
    clean_name = re.sub(r'[<>:"/\\|?*]','', name)
    data_str = datetime.now().strftime('%d-%m-%Y')
    folder_name = f"{clean_name} [{data_str}]"
    full_path = os.path.join(base_dir, folder_name)
    os.makedirs(full_path, exist_ok=True)
    return full_path

def rename_file(downloads_folder, file_name):
    clean_name = re.sub(r"\[\d+\]", "", file_name)  # Удаление чисел в квадратных скобках
    clean_name = clean_name.replace("[English (auto-generated)]", "").replace("[DownSub.com]", "").strip()
    new_file_name = f"{clean_name}.txt"
    new_file_path = os.path.join(downloads_folder, new_file_name)

    if os.path.exists(os.path.join(downloads_folder, file_name)):
        os.rename(os.path.join(downloads_folder, file_name), new_file_path)
        return new_file_path
    else:
        print(f"Файл {file_name} не найден в {downloads_folder}")
        return None

def download_transcription(video_url, save_folder):
    driver.get("https://downsub.com/")
    input_box = driver.find_element(By.CSS_SELECTOR, 'input[name="url"]')
    input_box.send_keys(video_url)
    input_box.send_keys(Keys.ENTER)

    time.sleep(5)

    try:
        download_button = driver.find_element(By.XPATH,
                                              '//button[contains(@class, "download-button")]//span[@class="v-btn__content" and text()="TXT"]')
        download_button.click()
    except Exception as e:
        print(f"Ошибка при нажатии кнопки загрузки транскрипции: {e}")
        return

    max_wait_time = 10
    elapsed_time = 0
    downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")

    while elapsed_time < max_wait_time:
        time.sleep(1)
        elapsed_time += 1

        files_in_downloads = os.listdir(downloads_folder)
        for file in files_in_downloads:
            if file.endswith('.txt'):  # Ищем текстовый файл
                download_file_path = os.path.join(downloads_folder, file)
                renamed_file = rename_file(downloads_folder, os.path.basename(download_file_path))

                if renamed_file:
                    shutil.move(renamed_file, save_folder)
                    print(f'Транскрипция сохранена в {save_folder}')
                return
    print(f'Не удалось скачать транскрипцию для видео {video_url}')

def download_video(video_url, save_path):
    ydl_opts = {
        'outtmpl': os.path.join(save_path, '%(title)s.%(ext)s'),
        'format': 'bestvideo[height=1080][ext=mp4]',  # Только видео без аудио
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
        print(f"Видео скачано в папку {save_path}")
    except Exception as e:
        print(f"Ошибка при скачивании видео {video_url}: {e}")

def get_random_videos(api_key, channel_id,count=5):
    youtube = build("youtube", "v3", developerKey=api_key)
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=50,
        order="date",
        type="video",
        videoDuration="short"
    )
    response = request.execute()
    videos = [
        {
            "videoId": item["id"]["videoId"],
            "title": item["snippet"]["title"],
        }
        for item in response.get("items", [])
    ]
    processed_videos = load_processed_videos()
    unprocessed_videos = [
        video for video in videos
        if video["videoId"] not in processed_videos
    ]
    if (len(unprocessed_videos) < count):
        print('Недостаточно новых видео для обработки!')
        count = len(unprocessed_videos)
    selected_videos = random.sample(unprocessed_videos, count)
    processed_videos.extend(video["videoId"] for video in selected_videos)
    save_processed_videos(processed_videos)
    return selected_videos

def load_processed_videos():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as file:
            return json.load(file)
    return []

def save_processed_videos(processed_videos):
    with open(HISTORY_FILE, 'w') as file:
        json.dump(processed_videos, file, indent=4)


if __name__ == "__main__":
    random_videos = get_random_videos(API_KEY, CHANNEL_ID, count=5)

    for video in random_videos:
        video_url = f"https://www.youtube.com/watch?v={video['videoId']}"
        title = video["title"]

        print(f'Обрабатываем видео: {title}')
        video_folder = create_folder_structure('все видео', title)
        transcription_folder = create_folder_structure('транскрибации', title)
        print(f"Скачиваем транскрипцию для видео: {title}")
        download_transcription(video_url, transcription_folder)
        print(f"Скачиваем видео: {title}")
        download_video(video_url, video_folder)
        print("Обработка завершена!")
