import re
import base64
import os
import json
from bs4 import BeautifulSoup
import glob
from tqdm import tqdm

def extract_information(html_content, file_name):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Найти intent и overall_difficulty из первого pre блока
    intent = None
    overall_difficulty = None
    first_pre = soup.find('pre')
    if first_pre:
        pre_text = first_pre.get_text()
        intent_match = re.search(r'intent: (.+)', pre_text)
        if intent_match:
            intent = intent_match.group(1)
        
        # Извлечь overall_difficulty
        difficulty_match = re.search(r'overall_difficulty: (\w+)', pre_text)
        if difficulty_match:
            overall_difficulty = difficulty_match.group(1)
    
    # Найти все страницы (New Page blocks)
    pages = soup.find_all('h2', string='New Page')
    
    results = []
    
    for i, page in enumerate(pages):
        page_div = page.find_next('div')
        if not page_div:
            continue
        
        # Найти предварительно отформатированный текст (bbox descriptions)
        pre_element = page_div.find('pre')
        bbox_description = pre_element.get_text() if pre_element else None
        
        # Найти изображение и сохранить его
        img_tag = page_div.find('img')
        image_data = None
        image_filename = None
        
        if img_tag and 'src' in img_tag.attrs:
            src = img_tag['src']
            if src.startswith('data:image/png;base64,'):
                # Извлечь base64 данные
                base64_data = src.replace('data:image/png;base64, ', '').replace('data:image/png;base64,', '')
                
                # Проверка на валидные данные base64
                if base64_data and not base64_data.startswith('строка изображения'):
                    try:
                        image_data = base64.b64decode(base64_data)
                        image_filename = f"page_{i+1}.png"  # Базовое имя файла без папки (добавим позже)
                    except Exception as e:
                        print(f"Error decoding image: {e}")
        
        # Найти блок с предыдущим и текущим действием
        action_div = page_div.find('div', recursive=False)
        previous_action = None
        current_action_thinking = None
        current_action_prediction = None
        
        if action_div:
            # Предыдущее действие
            prev_action_div = action_div.find('div')
            if prev_action_div:
                previous_action = prev_action_div.get_text()
            
            # Текущие действия модели
            action_divs = action_div.find_all('div', recursive=False)
            if len(action_divs) >= 2:
                # Мысли (thinking) текущего действия
                thinking_div = action_divs[1].find('pre')
                if thinking_div:
                    current_action_thinking = thinking_div.get_text()
                
                # Предполагаемое (prediction) текущее действие
                if len(action_divs) >= 3:
                    prediction_div = action_divs[2].find('pre')
                    if prediction_div:
                        current_action_prediction = prediction_div.get_text()
        
        # Собрать информацию для текущей страницы
        page_data = {
            'page_number': i + 1,
            'bbox_description': bbox_description,
            'image_filename': image_filename,  # Базовое имя без папки (полное имя добавим при сохранении)
            'previous_action': previous_action,
            'current_action_thinking': current_action_thinking,
            'current_action_prediction': current_action_prediction
        }
        
        # Если есть данные изображения, сохраняем их отдельно
        if image_data and image_filename:
            page_data['image_data'] = image_data
        
        results.append(page_data)
    
    return {
        'intent': intent,
        'overall_difficulty': overall_difficulty,  # Добавляем информацию о сложности
        'pages': results
    }

def process_directory(directory_path, output_dir="processed_data"):
    # Создать базовую выходную директорию
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Создать папку для изображений
    images_dir = os.path.join(output_dir, "images")
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)
    
    # Получить все папки в указанной директории
    subdirs = [d for d in os.listdir(directory_path) if os.path.isdir(os.path.join(directory_path, d))]
    
    # Список всех данных о страницах для итогового JSON
    all_pages_data = []
    
    # Создаем общий трекер прогресса для всех папок
    total_html_files = sum(len(glob.glob(os.path.join(directory_path, subdir, "*.html"))) for subdir in subdirs)
    overall_progress = tqdm(total=total_html_files, desc="Overall progress", position=0)
    
    for subdir_idx, folder in enumerate(subdirs):
        print(f"\nProcessing directory ({subdir_idx+1}/{len(subdirs)}): {folder}")
        
        folder_path = os.path.join(directory_path, folder)
        
        # Получить все HTML файлы в текущей папке
        html_files = glob.glob(os.path.join(folder_path, "*.html"))
        
        # Создаем трекер прогресса для текущей папки
        with tqdm(total=len(html_files), desc=f"Files in {folder}", position=1, leave=False) as folder_progress:
            for html_file in html_files:
                try:
                    # Базовое имя HTML файла без расширения
                    base_filename = os.path.splitext(os.path.basename(html_file))[0]
                    
                    # Обрабатываем HTML файл
                    with open(html_file, 'r', encoding='utf-8') as file:
                        html_content = file.read()
                    
                    # Извлекаем информацию из HTML
                    result = extract_information(html_content, base_filename)
                    intent = result['intent']
                    overall_difficulty = result['overall_difficulty']  # Получаем сложность
                    
                    # Обрабатываем страницы и сохраняем изображения
                    for page in result['pages']:
                        if 'image_data' in page and page['image_filename']:
                            # Создаем уникальное имя файла с префиксом папки и именем HTML файла
                            image_filename = f"{folder}_{base_filename}_{page['image_filename']}"
                            
                            # Обновляем имя файла в результате
                            page['image_filename'] = image_filename
                            
                            # Сохраняем изображение
                            img_path = os.path.join(images_dir, image_filename)
                            with open(img_path, 'wb') as f:
                                f.write(page['image_data'])
                            
                            # Удаляем бинарные данные
                            del page['image_data']
                        
                        # Добавляем информацию к данным страницы
                        page_info = {
                            'intent': intent,
                            'overall_difficulty': overall_difficulty,  # Добавляем сложность
                            'folder': folder,
                            'file_name': base_filename,
                            'page_number': page['page_number'],
                            'bbox_description': page['bbox_description'],
                            'image_filename': page.get('image_filename', None),
                            'previous_action': page['previous_action'],
                            'current_action_thinking': page['current_action_thinking'],
                            'current_action_prediction': page['current_action_prediction']
                        }
                        
                        # Добавляем в общий список
                        all_pages_data.append(page_info)
                    
                    folder_progress.update(1)
                    overall_progress.update(1)
                    
                except Exception as e:
                    print(f"\n  Error processing {html_file}: {e}")
                    folder_progress.update(1)
                    overall_progress.update(1)
    
    # Закрываем общий трекер прогресса
    overall_progress.close()
    
    # Сохраняем общий JSON файл со всеми данными
    output_json = os.path.join(output_dir, "all_data.json")
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_pages_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nProcessing complete. Created single JSON file with {len(all_pages_data)} pages.")
    print(f"JSON data saved to: {output_json}")
    print(f"Images saved to: {images_dir}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if os.path.isdir(sys.argv[1]):
            # Обработка директории
            output_dir = sys.argv[2] if len(sys.argv) > 2 else "processed_data"
            process_directory(sys.argv[1], output_dir)
        else:
            print("This script processes directories to create a single JSON with all data.")
            print("Usage: python script.py <directory_with_subfolders> [output_directory]")
    else:
        print("Usage: python script.py <directory_with_subfolders> [output_directory]")