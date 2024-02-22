
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
import csv
import re
import time
import requests
from logger import logger
import math

COUNTRIES = {
    # 'Germany': {
    #     'bottom_left': [47.271, 5.865],
    #     'top_right': [],
    # },
    'Italy': {
        'bottom_left': [37.196154, 6.891502],
        'top_right': [47.216118, 13.583875],
    }
}

SEARCH_KEY='Negozio di moda sposa'
ZOOM = 14
SEARCH_AREA_RADIUS_IN_KM = 30
FILE_PATH = 'bridal_stores_contact_information_raw_italy.csv'
CLASS_NAME_SHOP_NAME = "DUwDvf"
CLASS_NAME_GOOGLE_MAPS_LINK = "hfpxzc"
CLASS_NAME_INFORMATION_DIV = "Io6YTe"
IRRELEVANT_INFORMATION = ['Send to your phone',
                          'Identifies as women-owned', 'Claim this business', 'LGBTQ+ friendly', 'LGBT friendly']

cookies_accepted = False
prev_result = []


def accept_cookies(driver):
    time.sleep(5)
    accept_button = driver.find_element(
        By.XPATH, '/html/body/c-wiz/div/div/div/div[2]/div[1]/div[3]/div[1]/div[1]/form[2]/div/div/button')
    accept_button.click()
    time.sleep(5)


def is_valid_website(url):
    pattern = r'^(http|https)://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if re.match(pattern, url):
        return True
    else:
        return False


def extract_emails_from_website(url):
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        emails = re.findall(email_pattern, soup.get_text())

        return list(set(emails))

    except Exception as e:
        print(f"Error processing {url}: {e}")
        return []


def extract_contact_information(driver, url, country_bridal_stores_information, csv_writer):
    driver.get(url)
    html_page = driver.page_source
    soup = BeautifulSoup(html_page, 'html.parser')
    shop_name_tag = soup.find(
        'h1', attrs={"class": CLASS_NAME_SHOP_NAME})
    shop_information = [shop_name_tag.get_text() if shop_name_tag else None]
    shop_raw_information = soup.find_all(
        'div', attrs={"class": CLASS_NAME_INFORMATION_DIV})

    for information_tag in shop_raw_information:
        information = information_tag.get_text() if information_tag else None
        if information not in IRRELEVANT_INFORMATION:
            shop_information.append(information)
            if is_valid_website('https://' + information):
                shop_website_emails = extract_emails_from_website(
                    'https://' + information)
                shop_information.extend(shop_website_emails)
    is_unique = True
    if is_unique:
        if shop_information.__len__():

            return shop_information
        else:
            return False
    else:
        return False


def generate_url(keyword, lat, long, zoom, radius):
    return '''https://www.google.com/maps/search/{}/@{},{},{}z?hl=en&radius={}km'''.format('+'.join(key for key in keyword.split(' ')), lat, long, zoom, radius)


def calculate_lon_step(distance_km, latitude):
    latitude_rad = math.radians(latitude)
    lon_step = distance_km / (111 * math.cos(latitude_rad))
    return lon_step


def scrap_url(driver, url, country_bridal_stores_information, csv_writer):
    global cookies_accepted, prev_result
    driver.get(url)
    if not cookies_accepted:
        accept_cookies(driver)
        cookies_accepted = True
    html_page = driver.page_source
    soup = BeautifulSoup(html_page, 'html.parser')
    google_pages = soup.find_all(
        'a', attrs={"class": CLASS_NAME_GOOGLE_MAPS_LINK})
    stores = []
    for google_page in google_pages:
        if 'mara' not in google_page:
            link = google_page['href']
            if link not in prev_result:
                res = extract_contact_information(
                    driver, link, country_bridal_stores_information, csv_writer)
                prev_result.append(link)
                if res:
                    stores.append(res)
    return stores


def generate_positions(start, end, lat_step, lon_step_func):
    positions = []
    current_lat = start[0]
    while current_lat <= end[0]:
        current_lon = start[1]
        lon_step = lon_step_func(current_lat)
        while current_lon <= end[1]:
            positions.append([current_lat, current_lon])
            current_lon += lon_step
        current_lat += lat_step
    return positions


for country, country_coordinates in COUNTRIES.items():
    distance_for_scan = 2
    lat_step = distance_for_scan / 111
    positions = generate_positions(
        country_coordinates['bottom_left'], 
        country_coordinates['top_right'],
        lat_step,
        lambda lat: calculate_lon_step(distance_for_scan, lat)
    )
    results = []
    NO_OF_POSITIONS = positions.__len__()
    last_pos_index = 0
    while True:
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            driver = webdriver.Chrome(options=options)
            threshold_mem = 100
            positions_index = 0
            with open(FILE_PATH, 'a', encoding='utf-8', newline='') as csv_writer:
                csv_temp_w = csv.writer(csv_writer)
                country_bridal_stores_information = []
                for index, position in enumerate(positions[last_pos_index:]):
                    url = generate_url(
                        SEARCH_KEY, position[0], position[1], ZOOM, SEARCH_AREA_RADIUS_IN_KM)
                    res = scrap_url(
                        driver, url, country_bridal_stores_information, csv_writer)
                    if res:
                        results.append(res)
                    if (index % 2 == 0):
                        prev_result = []
                    last_pos_index += 1
                    print('CURRENT POSITION INDEX:', last_pos_index,
                          'POSITIONS:', NO_OF_POSITIONS)
                    print('CURRENT SESSION POSITION INDEX:', positions_index)
                    if positions_index > threshold_mem:
                        driver.quit()
                        cookies_accepted = False
                        driver = webdriver.Chrome(options=options)
                        positions_index = 0
                        logger.debug('-----------------------------')
                        logger.debug(
                            'SCRAPER MEMORY LIMIT REACHED, RESTARTING THE PROCESS FROM LAST INDEX')
                        print(
                            'SCRAPER MEMORY LIMIT REACHED, RESTARTING THE PROCESS FROM LAST INDEX')
                        for res in results:
                            csv_temp_w.writerows(res)
                        results = []
                    positions_index += 1
            driver.quit()
            logger.info('SCRAPER FINISHED THE JOB')
            print('Job finished!')
            break
        except Exception as error:
            print(error)
            logger.debug('-----------------------------')
            logger.error(
                f'SCRAPER ERROR AT POSITION {last_pos_index} of {positions.__len__()}.')
            logger.error(str(error))
            logger.debug('-----------------------------')
            cookies_accepted = False
