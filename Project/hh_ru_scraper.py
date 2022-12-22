""" Scraping вакансий из hh.ru.
Сохраняем результаты в базе данных sqlite.
"""

import datetime
import random
import sqlite3
import sys
import time
import requests
import tqdm
from bs4 import BeautifulSoup

PAGES_BATCH_SIZE = 20
PER_PAGE = 100
FETCH_FOR_DAYS = 365
DB_NAME = "descriptions2.db"

def scrape(phrase_to_search, con):

    cur = con.cursor()
    try:
        cur.execute("DROP TABLE hh_descriptions")
    except Exception as e:
        pass
    cur.execute("CREATE TABLE hh_descriptions(hhid, title, description, skills, url)")

    ses = requests.Session()

    date_to = datetime.datetime.now().replace(microsecond=0)
    date_from = date_to - datetime.timedelta(days=FETCH_FOR_DAYS)
    params = {
        'text': phrase_to_search,
        'per_page': PER_PAGE,
        'order_by': 'publication_time',
        'date_from': date_from.isoformat(),
        'date_to': date_to.isoformat(),
    }
    URL = f'https://api.hh.ru/vacancies'
    vacancies_ids = set()
    pages_scraped = 0
    done = False
    
    # Получение списка всех ids вакансий
    while not done:
        for page_num in range(PAGES_BATCH_SIZE):
            time.sleep(0.5)
            print(f'\rscraping page {pages_scraped + page_num}', end='')
            params['page'] = page_num
            res = ses.get(URL, params=params).json()
            if not res['items']:
                done = True
                break
            last_vacancy = res['items'][-1]
            vacancies_ids.update([item['id'] for item in res['items']])
        if done:
            break
        pages_scraped += PAGES_BATCH_SIZE
        params['date_to'] = last_vacancy['published_at']
    print('\nVacation number: ', len(vacancies_ids))

    # Парсинг вакансий
    for vac_id in tqdm.tqdm(vacancies_ids):
        try:
            vac_res = ses.get(f'https://api.hh.ru/vacancies/{vac_id}')
            title = BeautifulSoup(vac_res.json()['name'], "html.parser").get_text().replace('"','')
            description = BeautifulSoup(vac_res.json()['description'], "html.parser").get_text().replace('"','')
            skills = vac_res.json()['key_skills']
            skills_list = [i['name'].replace('"','') for i in skills]
            vac_url = vac_res.json()['alternate_url']
            cur.execute(f"""INSERT INTO hh_descriptions VALUES ("{vac_id}", "{title}", "{description}", "{repr(skills_list)}", "{vac_url}")""")
            con.commit()
        except Exception as e:
            print('Error on:', vac_id)
            print("Error message:", e)
            print(title)
            print(description)
            print(skills_list)

        time.sleep(random.random())


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: ./scrapers/hh_ru_scraper.py "python"')
    else:
        phrase_to_search = sys.argv[1]
        try:
            con = sqlite3.connect(DB_NAME)
            descriptions = scrape(phrase_to_search, con)

            res = con.cursor().execute("SELECT * FROM hh_descriptions LIMIT 5")
            print(type(res.fetchall()))
            res = con.cursor().execute("SELECT COUNT(*) FROM hh_descriptions")
            print(type(res.fetchall()))
        finally:
            con.close()
        
