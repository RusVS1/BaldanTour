import time
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException
from bs4 import BeautifulSoup
import json
import csv


def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-popup-blocking')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver


def click_show_more_until_gone(driver, max_clicks=100, wait_time=2):
    click_count = 0
    last_height = driver.execute_script("return document.body.scrollHeight")
    
    while click_count < max_clicks:
        try:
            buttons = driver.find_elements(By.XPATH, "//button[contains(., 'показать ещё') or contains(., 'Показать ещё')]")
            if not buttons:
                buttons = driver.find_elements(By.CSS_SELECTOR, "button.button-text-white.bg-white")
            if not buttons:
                buttons = driver.find_elements(By.CSS_SELECTOR, "div.shadow-light.mx-auto.mt-16 button")
            
            if not buttons:
                print("Кнопка 'Показать ещё' не найдена. Все туры загружены.")
                break
            
            button = buttons[0]
            if button.is_displayed() and button.is_enabled():
                driver.execute_script(
                    "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center', inline: 'center'});", 
                    button
                )
                time.sleep(1)
                try:
                    button.click()
                except ElementClickInterceptedException:
                    try:
                        driver.execute_script("arguments[0].click();", button)
                    except Exception as e:
                        print(f"Не удалось кликнуть по кнопке: {e}")
                        break
                
                click_count += 1
                print(f"Клик #{click_count}: Загружена новая порция туров")
                time.sleep(wait_time)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    print("Высота страницы не изменилась. Возможно, туры закончились.")
                    time.sleep(3)
                    new_height2 = driver.execute_script("return document.body.scrollHeight")
                    if new_height2 == last_height:
                        break
                last_height = new_height
            else:
                print("Кнопка не видима или не активна")
                break
                
        except TimeoutException:
            print("Время ожидания кнопки истекло. Все туры загружены.")
            break
        except Exception as e:
            print(f"Ошибка при клике на кнопку: {e}")
            break
    
    print(f"Всего выполнено кликов: {click_count}")
    return click_count


def parse_tour_card(card_soup):
    data = {}
    
    try:
        link_tag = card_soup.find('a', href=True)
        if link_tag and link_tag.get('href'):
            href = link_tag['href']
            data['link'] = 'https://anextour.ru' + href if href.startswith('/') else href
        name_tag = card_soup.find('span', class_='truncate')
        if name_tag:
            data['hotel_name'] = name_tag.get_text(strip=True)
        stars_tag = card_soup.find('div', class_='whitespace-nowrap ml-4 flex-shrink-0')
        if stars_tag:
            stars_text = stars_tag.get_text(strip=True)
            stars_match = re.search(r'\d+', stars_text)
            if stars_match:
                data['stars'] = stars_match.group()
        location_tag = card_soup.find('p', class_='text-14 font-regular break-all max-lines-1')
        if location_tag:
            data['location'] = location_tag.get_text(strip=True)
        dist_buttons = card_soup.find_all('button', {'data-testid': re.compile(r'tooltip\d+')})
        for button in dist_buttons:
            div_text = button.find('div', class_='text-14 font-regular whitespace-nowrap')
            if div_text:
                text = div_text.get_text(strip=True)
                if 'м' in text and 'км' not in text:
                    data['sea_distance'] = text
                elif 'км' in text:
                    if 'airport_distance' not in data:
                        data['airport_distance'] = text
        fav_button = card_soup.find('button', {'data-testid': re.compile(r'sbButtonFavorite-\d+')})
        if fav_button:
            testid = fav_button.get('data-testid', '')
            hotel_id_match = re.search(r'sbButtonFavorite-(\d+)', testid)
            if hotel_id_match:
                data['hotel_id'] = hotel_id_match.group(1)
        date_spans = card_soup.find_all('span', class_='text-14 ml-8 flex items-center truncate lg:w-356 md:w-240 sm:w-216')
        for span in date_spans:
            text = span.get_text(strip=True)
            date_match = re.search(r'\d{2}\.\d{2}\.\d{4}\s*-\s*\d{2}\.\d{2}\.\d{4}', text)
            nights_match = re.search(r'(\d+)\s+ноч', text)
            if date_match:
                data['dates'] = date_match.group()
            if nights_match:
                data['nights'] = nights_match.group(1)
        detail_spans = card_soup.find_all('span', class_='text-14 ml-8 flex items-center truncate lg:w-356 md:w-240 sm:w-216')
        for span in detail_spans:
            text = span.get_text(strip=True)
            svg = span.find_previous_sibling('svg')
            if svg:
                if any(room_type in text.lower() for room_type in ['standard', 'economy', 'suite', 'deluxe', 'room']):
                    data['room_type'] = text
                elif text in ['AI', 'UAI', 'BB', 'HB', 'RO']:
                    data['meal'] = text
        rating_tag = card_soup.find('span', class_='rounded-3 mr-6 px-4 py-2 text-white bg-yellow-dark')
        if rating_tag:
            data['rating'] = rating_tag.get_text(strip=True)
        reviews_tag = card_soup.find('a', href=True, string=re.compile(r'отзыв'))
        if reviews_tag:
            reviews_text = reviews_tag.get_text(strip=True)
            reviews_match = re.search(r'(\d+)', reviews_text)
            if reviews_match:
                data['reviews_count'] = reviews_match.group(1)
        amenities = []
        amenity_tags = card_soup.find_all('li', class_='bg-fog rounded text-12 font-regular px-8 py-4 mt-4 mr-4 whitespace-nowrap h-22 sm:mt-0')
        for tag in amenity_tags:
            amenity_text = tag.get_text(strip=True)
            if amenity_text and not amenity_text.startswith('+'):
                amenities.append(amenity_text)
        hidden_amenities = card_soup.find_all('button', {'data-testid': re.compile(r'tooltip\d+')})
        for btn in hidden_amenities:
            btn_text = btn.get_text(strip=True)
            if btn_text and btn_text.startswith('+'):
                amenities.append(f"Ещё {btn_text}")
        
        if amenities:
            data['amenities'] = amenities
        price_candidates = card_soup.find_all('span', string=re.compile(r'\d+[\d\s]*₽'))
        for price_tag in price_candidates:
            parent = price_tag.parent
            if parent and 'font-bold' in parent.get('class', []):
                data['price'] = price_tag.get_text(strip=True)
                break
        instant_confirm = card_soup.find('span', string='Мгновенное подтверждение')
        if instant_confirm:
            data['instant_confirm'] = True
        special_tag = card_soup.find('span', class_='flex h-20 min-w-fit rounded px-8 font-medium leading-20 absolute -top-10 left-16 bg-red-light text-12 text-white md:left-8')
        if special_tag:
            data['special'] = special_tag.get_text(strip=True)
        hotel_type_tag = card_soup.find('div', class_='whitespace-nowrap ml-4 flex-shrink-0 text-carbon font-medium text-12 -mb-4 first-letter:uppercase lg:text-14 sm:-mb-3')
        if hotel_type_tag:
            hotel_type = hotel_type_tag.get_text(strip=True)
            if hotel_type and not hotel_type.isdigit():
                data['hotel_type'] = hotel_type
        
    except Exception as e:
        print(f"Ошибка при парсинге карточки: {e}")
    
    return data


def parse_tours_from_page(driver):
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    tour_cards = soup.find_all('li', class_='sm:px-20')
    
    print(f"Найдено карточек туров: {len(tour_cards)}")
    
    tours = []
    for i, card in enumerate(tour_cards, 1):
        tour_data = parse_tour_card(card)
        if tour_data and tour_data.get('hotel_name'):
            tours.append(tour_data)
            if i % 10 == 0:
                print(f"Обработано {i} карточек...")
    
    return tours


def save_to_json(data, filename='anextour_tours.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Данные сохранены в {filename}")


def save_to_csv(data, filename='anextour_tours.csv'):
    if not data:
        print("Нет данных для сохранения в CSV")
        return
    
    fieldnames = set()
    for tour in data:
        fieldnames.update(tour.keys())
    fieldnames = sorted(list(fieldnames))
    
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for tour in data:
            tour_copy = tour.copy()
            if 'amenities' in tour_copy and isinstance(tour_copy['amenities'], list):
                tour_copy['amenities'] = '; '.join(tour_copy['amenities'])
            writer.writerow(tour_copy)
    
    print(f"Данные сохранены в {filename}")


def main():
    url = 'https://anextour.ru/search/tours'
    
    print("=" * 50)
    print("Запуск парсера ANEX Tour")
    print("=" * 50)
    
    driver = setup_driver()
    
    try:
        print(f"Загрузка страницы: {url}")
        driver.get(url)
        print("Ожидание загрузки первоначального контента...")
        time.sleep(5)
        try:
            cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Принять') or contains(text(), 'Согласен')]")
            if cookie_buttons:
                cookie_buttons[0].click()
                time.sleep(1)
                print("Закрыт cookie-баннер")
        except:
            pass
        print("Начинаем загрузку всех туров...")
        clicks = click_show_more_until_gone(driver, max_clicks=100, wait_time=3)
        
        if clicks == 0:
            print("Кнопка 'Показать ещё' не была нажата. Проверяем, может быть все туры уже загружены.")
        print("Ожидание окончательной загрузки...")
        time.sleep(5)
        print("Начинаем парсинг туров...")
        tours = parse_tours_from_page(driver)
        
        print("=" * 50)
        print(f"Всего спарсено туров: {len(tours)}")
        print("=" * 50)
        if tours:
            save_to_json(tours)
            save_to_csv(tours)
            hotels_with_stars = sum(1 for t in tours if 'stars' in t)
            hotels_with_price = sum(1 for t in tours if 'price' in t)
            print(f"\nСтатистика:")
            print(f"- Отелей со звёздами: {hotels_with_stars}")
            print(f"- Отелей с ценой: {hotels_with_price}")
            print("\nПримеры первых 3 туров:")
            for i, tour in enumerate(tours[:3], 1):
                print(f"\n--- Тур {i} ---")
                for key, value in tour.items():
                    if key == 'amenities' and isinstance(value, list):
                        print(f"{key}: {', '.join(value[:5])}{'...' if len(value) > 5 else ''}")
                    else:
                        print(f"{key}: {value}")
        else:
            print("Не удалось найти данные о турах. Проверьте структуру страницы.")
            
    except Exception as e:
        print(f"Ошибка в основном процессе: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("\nПарсер завершил работу")


if __name__ == '__main__':
    main()
