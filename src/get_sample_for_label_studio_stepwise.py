import os
import json
import random
import shutil
import argparse
from pathlib import Path

def select_easy_images(processed_data_dir, output_dir, num_images=100, seed=None):
    """
    Выбирает случайные изображения с overall_difficulty = 'easy' и создает JSON в формате Label Studio
    со всеми требуемыми полями.
    
    Args:
        processed_data_dir: Путь к папке с обработанными данными
        output_dir: Путь к папке, куда сохранить выбранные изображения и конфиг
        num_images: Количество изображений для выбора
        seed: Зерно для генератора случайных чисел (для воспроизводимости)
    """
    # Устанавливаем seed для воспроизводимости
    if seed is not None:
        random.seed(seed)
    
    # Пути к файлам
    all_data_path = os.path.join(processed_data_dir, "all_data.json")
    images_dir = os.path.join(processed_data_dir, "images")
    
    # Создаем выходную директорию
    os.makedirs(output_dir, exist_ok=True)
    
    # Создаем директорию для изображений
    output_images_dir = os.path.join(output_dir, "images")
    os.makedirs(output_images_dir, exist_ok=True)
    
    # Проверяем наличие файла с данными
    if not os.path.exists(all_data_path):
        print(f"Ошибка: Файл данных не найден: {all_data_path}")
        return
    
    # Загружаем данные
    try:
        with open(all_data_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        print(f"Загружено {len(all_data)} записей из {all_data_path}")
    except Exception as e:
        print(f"Ошибка при загрузке данных: {e}")
        return
    
    # Фильтруем записи: только с overall_difficulty = 'easy' и имеющие изображения
    easy_pages_with_images = []
    for page in all_data:
        # Проверяем, что overall_difficulty == 'easy' и есть изображение
        if (page.get('overall_difficulty') == 'easy' and 
            page.get('image_filename') and 
            os.path.exists(os.path.join(images_dir, page['image_filename']))):
            easy_pages_with_images.append(page)
    
    print(f"Найдено {len(easy_pages_with_images)} страниц с уровнем сложности 'easy' и с изображениями")
    
    # Проверяем достаточно ли изображений
    if len(easy_pages_with_images) < num_images:
        print(f"Внимание: запрошено {num_images} изображений, но доступно только {len(easy_pages_with_images)} с уровнем сложности 'easy'.")
        num_images = len(easy_pages_with_images)
    
    # Выбираем случайные страницы
    selected_pages = random.sample(easy_pages_with_images, num_images)
    
    # Получаем абсолютный путь к папке с изображениями
    abs_output_images_dir = os.path.abspath(output_images_dir)
    
    # Готовим данные в формате Label Studio
    label_studio_items = []
    
    # Копируем изображения и создаем записи
    for i, page in enumerate(selected_pages, 1):
        src_image = os.path.join(images_dir, page['image_filename'])
        new_image_name = f"{i}.jpg"  # Простые имена файлов 1.jpg, 2.jpg и т.д.
        dst_image = os.path.join(output_images_dir, new_image_name)
        
        try:
            # Копируем изображение
            shutil.copy2(src_image, dst_image)
            
            # Используем абсолютный путь к изображению
            abs_image_path = os.path.join(abs_output_images_dir, new_image_name)
            
            # Заменяем None значения на пустые строки
            intent = page.get('intent', '') or ''
            overall_difficulty = page.get('overall_difficulty', '') or ''
            folder = page.get('folder', '') or ''
            file_name = page.get('file_name', '') or ''
            page_number = page.get('page_number', '') or ''
            previous_action = page.get('previous_action', '') or ''
            current_action_thinking = page.get('current_action_thinking', '') or ''
            current_action_prediction = page.get('current_action_prediction', '') or ''
            original_filename = page.get('image_filename', '') or ''
            
            # Создаем запись в требуемом формате
            label_studio_item = {
                "id": i,
                "data": {
                    "image": f"file://{abs_image_path}",
                    "intent": intent,
                    "overall_difficulty": overall_difficulty,
                    "folder": folder,
                    "file_name": file_name,
                    "page_number": page_number,
                    "previous_action": previous_action,
                    "current_action_thinking": current_action_thinking,
                    "current_action_prediction": current_action_prediction,
                    "original_filename": original_filename
                }
            }
            
            label_studio_items.append(label_studio_item)
            print(f"Обработано изображение {i}/{num_images}: {new_image_name}")
            
        except Exception as e:
            print(f"Ошибка при обработке изображения {src_image}: {e}")
    
    # Сохраняем JSON для Label Studio
    json_path = os.path.join(output_dir, "tasks.json")
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(label_studio_items, f, ensure_ascii=False, indent=2)
        print(f"JSON для Label Studio сохранен: {json_path}")
    except Exception as e:
        print(f"Ошибка при сохранении JSON: {e}")

    label_config_path = os.path.join(output_dir, "label_config.xml")

    with open(label_config_path, 'w', encoding='utf-8') as f:
        f.write("""<View>
<Image name="image" value="$image" maxWidth="100%"/>

<Header value="Intent и сложность"/>
<Text name="intent" value="Intent: $intent"/>
<Text name="difficulty" value="Сложность: $overall_difficulty"/>

<Header value="Исходная информация"/>
<Text name="folder" value="Папка: $folder"/>
<Text name="file_name" value="Файл: $file_name"/>
<Text name="page_number" value="Страница: $page_number"/>

<Header value="Предыдущее действие"/>
<Text name="previous_action" value="$previous_action"/>

<Header value="Мысли модели"/>
<Text name="current_action_thinking" value="$current_action_thinking"/>

<Header value="Предсказание модели"/>
<Text name="current_action_prediction" value="$current_action_prediction"/>

<Header value="Оценка пользователя"/>
<Choices name="correctness" toName="image" choice="single" showInline="true">
<Choice value="correct" background="success"/>
<Choice value="incorrect" background="error"/>
</Choices>

<TextArea name="comments" toName="image" placeholder="Комментарии к оценке..."/>
</View>""")
    

    summary_path = os.path.join(output_dir, "selection_summary.json")
    try:
        summary_info = {
            "total_records": len(all_data),
            "easy_records_with_images": len(easy_pages_with_images),
            "selected_images": num_images,
            "selected_files": [page['image_filename'] for page in selected_pages]
        }
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary_info, f, ensure_ascii=False, indent=2)
        print(f"Сводная информация сохранена: {summary_path}")
    except Exception as e:
        print(f"Ошибка при сохранении сводной информации: {e}")
    
    print(f"\nОбработка завершена. Выбрано {len(label_studio_items)} изображений с уровнем сложности 'easy'.")
    print(f"Выходная директория: {output_dir}")
    print(f"Для запуска Label Studio используйте команду: ./run_label_studio.sh")
    print(f"Или: label-studio start --data-dir \"{os.path.abspath(output_dir)}\" -c \"{os.path.abspath(config_path)}\"")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Выбор случайных изображений с уровнем сложности 'easy' для Label Studio")
    parser.add_argument("--input", required=True, help="Путь к папке с обработанными данными")
    parser.add_argument("--output", required=True, help="Путь к папке для сохранения результатов")
    parser.add_argument("--count", type=int, default=100, help="Количество изображений для выбора (по умолчанию: 100)")
    parser.add_argument("--seed", type=int, help="Seed для воспроизводимости")
    
    args = parser.parse_args()
    
    select_easy_images(
        processed_data_dir=args.input,
        output_dir=args.output,
        num_images=args.count,
        seed=args.seed
    )
