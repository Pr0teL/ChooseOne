import requests
import json
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp
import os
import base64
import schedule
import time
from instagrapi import Client
from instagrapi.types import Usertag

# Замените на свой API ключ
OPENAI_API_KEY = ""
Kandinsky_API_KEY = ""
Kandinsky_API_SECRET = ""



def generate_question_and_descriptions():
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "Generate a 'Choose one' question and 6 short descriptions for images."
            },
            {
                "role": "user",
                "content": "Create a 'Choose one' question and 6 short image descriptions."
            }
        ],
        "temperature": 0.7,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_data",
                    "description": "Create a 'Choose one' question and 6 short image descriptions. With fish",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "'Choose one' question",
                            },
                            "desc_img_1": {
                                "type": "string",
                                "description": "1 short image descriptions",
                            },
                            "desc_img_2": {
                                "type": "string",
                                "description": "2 short image descriptions",
                            },
                            "desc_img_3": {
                                "type": "string",
                                "description": "3 short image descriptions",
                            },
                            "desc_img_4": {
                                "type": "string",
                                "description": "4 short image descriptions",
                            },
                            "desc_img_5": {
                                "type": "string",
                                "description": "5 short image descriptions",
                            },
                            "desc_img_6": {
                                "type": "string",
                                "description": "6 short image descriptions",
                            },
                        },
                        "required": ["question", "desc_img_1", "desc_img_2","desc_img_3","desc_img_4","desc_img_5","desc_img_6"],
                        "additionalProperties": False,
                    },
                }
            }
        ]
    }

    response = requests.post(url, headers=headers, json=data)
    content = json.loads(response.content)

    # Извлечение результата из вызова функции
    function_call = content['choices'][0]['message']['tool_calls'][0]['function']
    if function_call['name'] == "get_data":
        result = json.loads(function_call['arguments'])
        return result
    else:
        raise ValueError("Unexpected function call")


def generate_image(description):
    url = "https://api-key.fusionbrain.ai/key/api/v1/text2image/run"
    headers = {
        "X-Key": f"Key {Kandinsky_API_KEY}",
        "X-Secret": f"Secret {Kandinsky_API_SECRET}"
    }
    params = {
        "type": "GENERATE",
        "numImages": 1,
        "width": 576,  # Соотношение 9:16
        "height": 1024,
        "generateParams": {
            "query": description
        }
    }

    def get_model():
        response = requests.get('https://api-key.fusionbrain.ai/' + 'key/api/v1/models', headers= {
        "X-Key": f"Key EAA11767A130FA0864E1211211149808",
        "X-Secret": f"Secret AC86240CA57048D1E0E3A06491288A31"
    })
        data = response.json()
        print(data)
        return data[0]['id']

    data = {
        'model_id': (None, get_model()),  # Убедитесь, что у вас правильный ID модели
        'params': (None, json.dumps(params), 'application/json')
    }
    response = requests.post(url, headers=headers, files=data)

    response_data = response.json()

    # Проверяем наличие ключа 'uuid'
    if 'uuid' not in response_data:
        raise KeyError(f"'uuid' not found in the response: {response_data}")

    request_id = response_data['uuid']

    # Проверка статуса генерации
    status_url = f"https://api-key.fusionbrain.ai/key/api/v1/text2image/status/{request_id}"
    while True:
        status_response = requests.get(status_url, headers=headers)
        status_data = status_response.json()

        if status_response.status_code != 200:
            raise Exception(f"Error checking status: {status_response.status_code}, {status_response.text}")

        if status_data['status'] == 'DONE':
            image_base64 = status_data['images'][0]  # Получаем изображение в base64 формате
            break

    # Сохранение изображения
    img_name = f"image_{description[:10]}.png"
    with open(img_name, 'wb') as f:
        f.write(base64.b64decode(image_base64))

    return img_name


def create_text_image(text):
    print(f"Генерация изображения с текстом: {text}")
    img = Image.new('RGBA', (1080, 1920), color=(0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 70)

    # Разбиваем текст на строки
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        line = ' '.join(current_line + [word])
        bbox = d.textbbox((0, 0), line, font=font)
        if bbox[2] - bbox[0] <= 1000:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    lines.append(' '.join(current_line))

    # Рисуем текст
    total_height = sum(
        d.textbbox((0, 0), line, font=font)[3] - d.textbbox((0, 0), line, font=font)[1] for line in lines)
    y = (1920 - total_height) // 2
    for line in lines:
        bbox = d.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        x = (1080 - line_width) // 2
        d.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y += line_height

    img_name = "question.png"
    img.save(img_name)
    return img_name


def add_number_to_image(image_path, number):
    img = Image.open(image_path)
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype("arial.ttf", 90)
    text = str(number)

    # Определение положения текста
    x = 50  # Отступ слева
    y = 50  # Отступ сверху

    # Добавляем текст
    d.text((x, y), text, font=font, fill=(255, 255, 255, 255))  # Белый цвет

    img.save(image_path)


def create_video(question_img, image_files, durations):
    # Загружаем фоновое видео и аудио
    background = mp.VideoFileClip("Assets/first_bg.mp4")
    background = background.without_audio()  # Убираем аудио из фонового видео
    audio = mp.AudioFileClip("Assets/audio.mp3")

    # Создаем клип с вопросом
    question_clip = mp.ImageClip(question_img).set_duration(durations[0])
    question_clip = question_clip.set_position(("center", "center"))
    question_clip = question_clip.resize(newsize=(background.size[0], background.size[1]))  # Растягиваем на весь экран
    first_clip = mp.CompositeVideoClip([background, question_clip]).set_duration(durations[0])

    # Создаем клипы с изображениями
    image_clips = []
    for img, duration in zip(image_files, durations[1:]):
        clip = mp.ImageClip(img).set_duration(duration)
        clip = clip.resize(newsize=(background.size[0], background.size[1]))  # Растягиваем на весь экран
        image_clips.append(clip)

    # Собираем все клипы вместе
    final_clip = mp.concatenate_videoclips([first_clip] + image_clips)

    # Обрезаем аудио до длительности видео
    audio_duration = min(audio.duration, final_clip.duration)
    audio = audio.subclip(0, audio_duration)

    # Добавляем аудио
    final_clip = final_clip.set_audio(audio)

    # Записываем итоговое видео
    final_clip.write_videofile("choose_one_video.mp4", fps=24)


def main(durations=[4, 3, 3, 3, 3, 3, 3]):
    data = generate_question_and_descriptions()
    question_img = create_text_image(data['question'])

    image_files = []
    for i in range(1, 7):
        img_file = generate_image(data[f'desc_img_{i}'])
        add_number_to_image(img_file, i)
        image_files.append(img_file)

    create_video(question_img, image_files, durations)

    # Очистка временных файлов
    os.remove(question_img)
    for img in image_files:
        os.remove(img)


if __name__ == "__main__":
    main()
