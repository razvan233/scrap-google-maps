
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
import csv
import re
import time
import requests
from logger import logger
import math
import polyline
import sys


KEY_POINTS = {
    'Spain & Portugal': {
        'Mercat del Born, Plaça Comercial, 12, 08003 Barcelona, Spain': [41.38521240000001, 2.184336300000007],
        'Carrer de Súria, 23, 08242 Manresa, Barcelona, Spain': [41.7326672, 1.8281259000000105],
        'Vía sin nombre, 50191 Zaragoza, Spain': [41.709173799999995, 0.9295117999999913],
        'Errepide izengabea, 20570 Bergara, Gipuzkoa, Spain': [43.11742240000002, -2.400528599999997],
        'aux point spain': [43.27892105094156, -8.266279072921394],
        'Ctra. Vilar do Rei, 15898 Santiago de Compostela, A Coruña, Spain': [42.95785619999999, -8.583511500000009],
        'R. Taím 187, 4475-846 Silva Escura, Portugal': [41.24715299999999, -8.576944300000003],
        'Av. Infante Dom Henrique 14, 1100 Lisboa, Portugal': [38.71712019999999, -9.11741730000001],
    },
    'Morocco': {
        'Av. Infante Dom Henrique 14, 1100 Lisboa, Portugal': [38.71712019999999, -9.11741730000001],
        'HCMW+RPP, Casablanca 20250, Morocco': [33.5848256, -7.553130500000007],
    },
    'USA & Canada':{
        # 'Antarctica Way, Miami, FL 33132, USA': [25.770317900000013,-80.1682594],
        # 'Statue of Liberty National Monument, New York, NY, USA': [40.6927547,-74.05661390000002],
        # '1929 Robie St, Halifax, NS B3H 3G1, Canada': [44.64651449999999,-63.58849699999999],
        'aux point 1': [38.61791495897834, -90.16019920196777],
        'aux point 2': [32.55473618082868, -115.17169347127731],
        '8888 Balboa Ave, San Diego, CA 92123, USA': [32.83780807958699,-115.34722925067304],
        # 'Port of Seattle, Alaskan Way, Seattle, WA, USA': [47.6140775,-122.35431189999998],
    }
}
SEARCH_REGION = 'USA & Canada' # REPLACE WITH A REGION FROM KEY_POINTS, CASE SENSITIVE!
API_KEY = '5b3ce3597851110001cf624830da203f9eed48d4a3d07a2af39dcb42'
SEARCH_KEY = 'tourist information centre'
ZOOM = 14
STEP_IN_POSITIONS = 100
SEARCH_AREA_RADIUS_IN_KM = 50
FILE_PATH = f'tourist_information_centre_along_80edays_route_{SEARCH_REGION}_2.csv'
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


def generate_positions(coordinates):
    _coordinates = [[pos[1][1], pos[1][0]] for pos in coordinates.items()]
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    # uncomment these lines if you want to see the coordinates that are send to the api
    # test the coordinates on https://openrouteservice.org/dev/#/api-docs/v2/directions/{profile}/post
    # print(_coordinates)
    # sys.exit()
    params = {
        'coordinates': _coordinates
    }

    response = requests.post(url, json=params, headers={
        'Authorization': API_KEY
    })

    if response.status_code == 200:
        data = response.json()
        if "routes" in data and len(data["routes"]) > 0:
            route = data["routes"][0]
            coordinates = [coord[::-1]
                           for coord in polyline.decode(route["geometry"])]
            return coordinates
    else:
        print("Error:", response.status_code, response.text)


if __name__ == '__main__':
    distance_for_scan = 2
    lat_step = distance_for_scan / 111
    if SEARCH_REGION not in KEY_POINTS:
        print( 'SEARCH REGION IS NOT PRESENT IN KEY POINTS')
        sys.exit()
    positions = generate_positions(KEY_POINTS[SEARCH_REGION])
    results = []
    NO_OF_POSITIONS = positions.__len__()
    last_pos_index = 0
    while True:
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            driver = webdriver.Chrome(options=options)
            threshold_mem = 100 * STEP_IN_POSITIONS
            positions_index = 0
            with open(FILE_PATH, 'a', encoding='utf-8', newline='') as csv_writer:
                csv_temp_w = csv.writer(csv_writer)
                csv_temp_w.writerow(['Name','Address'])
                country_bridal_stores_information = []
                for index, position in enumerate(positions[last_pos_index::STEP_IN_POSITIONS]):
                    url = generate_url(
                        SEARCH_KEY, position[1], position[0], ZOOM, SEARCH_AREA_RADIUS_IN_KM)
                    res = scrap_url(
                        driver, url, country_bridal_stores_information, csv_writer)
                    if res:
                        results.append(res)
                    if (index % 2 == 0):
                        prev_result = []
                    last_pos_index += 1 * STEP_IN_POSITIONS
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
                    positions_index += 1 * STEP_IN_POSITIONS
                curr_index = index * STEP_IN_POSITIONS
                if (NO_OF_POSITIONS - curr_index) <= STEP_IN_POSITIONS:
                    print('LAST INDEX IN POSITION...RUNNING THROUGH')
                    url = generate_url(
                        SEARCH_KEY, position[1], position[0], ZOOM, SEARCH_AREA_RADIUS_IN_KM)
                    res = scrap_url(
                        driver, url, country_bridal_stores_information, csv_writer)
                    if res:
                        results.append(res)
                    for res in results:
                        csv_temp_w.writerows(res)
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
