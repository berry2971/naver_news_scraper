# get article urls
import requests
import time
import re
import os
import sqlite3
from pprint import pprint
from bs4 import BeautifulSoup as bs
from datetime import date
from datetime import timedelta
from selenium import webdriver

ABS_PATH = os.path.dirname(os.path.abspath(__file__))
HEADLINE_CONTENT_TYPE = [{'tag': 'h3', 'attr': 'id', 'name': 'articleTitle'}]
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}

##### create massmedias
main_html = requests.get('https://news.naver.com/main/list.nhn?mode=LPOD&mid=sec&oid=032').text
main_soup = bs(main_html, 'html.parser')
nav_li = main_soup.find('ul', {'class': 'nav'}).find_all('a')

massmedias = dict() # {'중앙일보': {'oid': '011', 'category': '종합', 'url': 'https://...'}, ...}
for nav in nav_li:
    category = nav.text.strip()
    if re.search('선택됨', category):
        category = re.sub('선택됨', '', category).strip()
    nav_html = requests.get('https://news.naver.com'+nav.attrs['href'], headers=headers).text
    nav_soup = bs(nav_html, 'html.parser')
    massmedia_a = nav_soup.find('ul', {'class': 'massmedia'}).find_all('a')
    for massmedia in massmedia_a:
        massmedia_url = 'https://news.naver.com'+massmedia.attrs['href']
        massmedia_oid = re.search('[0-9]+', massmedia_url).group()
        massmedia_name = massmedia.text
        massmedia_category = category
        massmedias.update({massmedia_name: {'oid': massmedia_oid, 'category': massmedia_category, 'url': massmedia_url}})

##### user configuration
selected_massmedias = []
# date
print('=====시작 날짜 및 종료 날짜 입력... YYYYMMDD')
DATE_START = input('시작 날짜: ')
DATE_END = input('종료 날짜: ')
DATE_START = date(int(DATE_START[:4]), int(DATE_START[4:6]), int(DATE_START[6:]))
DATE_END = date(int(DATE_END[:4]), int(DATE_END[4:6]), int(DATE_END[6:]))
print()

# category
print('=====카테고리 목록... 빈칸으로 입력 중단')
category_list = set()
for i in massmedias:
    category_list.add(massmedias[i]['category'])
for i in category_list:
    print(i, end='\t')
print()
while True:
    c = input('카테고리 추가: ')
    for i in massmedias:
        if massmedias[i]['category'] == c: selected_massmedias.append(i)
    if c == '': break
print()

# massmedia
print('=====언론사 목록... 빈칸으로 입력 중단')
for i in massmedias.keys():
    print(i, end='\t')
print()
while True:
    m = input('언론사 추가: ')
    for massmedia in massmedias:
        if massmedia == m: selected_massmedias.append(i)
    if m == '': break
print()

# page
while True:
    MAX_PAGE = int(input('한 언론사당 최대 페이지: '))
    if isinstance(MAX_PAGE, int) and 0<MAX_PAGE<100: break
    else: print('0<n<100 숫자를 입력하세요')

selected_massmedias = list(set(selected_massmedias)) # remove redundancy of selected_massmedias
URLS = [] # [{'url': 'https://...', 'media': '중앙일보'}, ...]
for m in selected_massmedias:
    date_current = DATE_START
    while True:
        if date_current > DATE_END: break
        date = date_current.strftime('%Y%m%d')
        oid = massmedias[m]['oid']
        for page in range(1, MAX_PAGE+1):
            headline_main = 'https://news.naver.com/main/list.nhn?mode=LPOD&mid=sec&oid={oid}&date={date}&page={page}'.format(oid=oid, date=date, page=page)
            headline_html = requests.get(headline_main).text
            headline_soup = bs(headline_html, 'html.parser')

            # check if last page
            displayed_page = int(headline_soup.find('div', {'class': 'paging'}).find('strong').text)
            if page != displayed_page: break

            # scrape headlines
            headline_type1 = []
            headline_type2 = []
            try:
                headline_type1 = [dt for dt in headline_soup.find('ul', {'class': 'type06_headline'}).find_all('dt') if dt.get('class')==None]
            except:
                pass
            try:
                headline_type2 = [dt for dt in headline_soup.find('ul', {'class': 'type06'}).find_all('dt') if dt.get('class')==None]
            except:
                pass
            print(len(headline_type1))
            print(len(headline_type2))

            if headline_type1 != []:
                headline_type1_url = [dt.find('a').attrs['href'] for dt in headline_type1]
                for i in headline_type1_url:
                    URLS.append({'url': i, 'media': m})
            if headline_type2 != []:
                headline_type2_url = [dt.find('a').attrs['href'] for dt in headline_type2]
                for i in headline_type2_url:
                    URLS.append({'url': i, 'media': m})
        date_current += timedelta(days=1)

##############################

def find_elem(driver, tag, attr, name):
    if attr == 'class':
        try: elem = driver.find_element_by_class_name(name).text
        except: elem = None
    elif attr == 'id':
        try: elem = driver.find_element_by_id(name).text
        except: elem = None
    return elem

import random
def sleep_rand():
    sleep_time = random.random() * 3
    time.sleep(sleep_time)

# run selenium
import warnings
warnings.filterwarnings('ignore')

options = webdriver.ChromeOptions()
options.add_argument("headless")
options.add_argument("disable-gpu")
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36")
options.add_argument("--use-fake-ui-for-media-stream")
options.add_experimental_option('excludeSwitches', ['enable-logging'])
options.add_argument('--log-level=3')

# create database
try:
    result_dir = ABS_PATH + r'\result'
    if os.path.exists(result_dir):
        print('result folder exist... OK')
    else:
        os.mkdir(result_dir)
        print('result folder not exists...\nmake it... OK')

    file_name = time.strftime('%Y%m%d%H%M%S')
    con = sqlite3.connect(result_dir + r'\result-{}.db'.format(file_name))
    con.execute('CREATE TABLE news (url TEXT, category TEXT, massmedia TEXT, headline TEXT, content TEXT)')
except Exception as e:
    print('database exception 발생... 내용:')
    print(e)

class ArticleInside:
    tag = None
    attr = None
    text = None

    def __init__(self, tag, attr, text):
        self.tag = tag
        self.attr = attr
        self.text = text
    def get_tag(self):
        return self.tag
    def get_attr(self):
        return self.attr
    def get_text(self):
        return self.text

class Article:
    headline = None
    content = None

    def __init__(self, headline, content):
        self.headline = headline
        self.content = content
    def get_headline(self):
        return self.headline
    def get_content(self):
        return self.content

article_types = [Article(ArticleInside('h3', 'id', 'articleTitle'), ArticleInside('div', 'id', 'articleBodyContents')),
                 Article(ArticleInside('h2', 'class', 'end_tit'), ArticleInside('div', 'id', 'articeBody')),
                 Article(ArticleInside('h4', 'class', 'title'), ArticleInside('div', 'id', 'newsEndContents'))]

try:
    try:
        driver = webdriver.Chrome(ABS_PATH + r'\84.exe', chrome_options=options)
        driver.get('https://www.naver.com')
    except Exception as e:
        print(e)
        try:
            driver = webdriver.Chrome(ABS_PATH + r'\83.exe', chrome_options=options)
            driver.get('https://www.naver.com')
        except Exception as e:
            print(e)
            try:
                driver = webdriver.Chrome(ABS_PATH + r'\81.exe', chrome_options=options)    ``````````````
                driver.get('https://www.naver.com')
            except Exception as e:
                print(e)
                try:
                    driver = webdriver.Chrome(ABS_PATH + r'\80.exe', chrome_options=options)
                    driver.get('https://www.naver.com')
                except Exception as e:
                    print(e)
                    try:
                        driver = webdriver.Chrome(ABS_PATH + r'\chromedriver.exe', chrome_options=options)
                        driver.get('https://www.naver.com')
                    except:
                        print('''ERROR OCCURED...\n크롬>설정>크롬 정보에서 버전을 확인하고,
                        구글에서 chromedriver를 검색하여 자신의 버전에 맞는 파일을 다운받고,
                        그 후에 다시 실행하여 해결. 파일명은 chromedriver.exe 그대로 두면 됩니다.''')
    total = len(URLS)
    count = 0

    for url in URLS:
        media = url['media']
        category = massmedias[media]['category']

        sleep_rand()

        count += 1
        print('{count}/{total}'.format(count=count, total=total))

        driver.get(url['url'])
        html = driver.execute_script('return document.documentElement.innerHTML;')
        soup = bs(html, 'html.parser')

        headline = ''
        content = ''
        #def find_elem(driver, tag, attr, name):
        for article in article_types:
            headline = find_elem(driver, article.get_headline().get_tag, article.get_headline().get_attr(), article.get_headline().get_text())
            content = find_elem(driver, article.get_content().get_tag, article.get_content().get_attr(), article.get_content().get_text())
            if headline != None and content != None: break

        insert_sql = 'INSERT INTO news (url, category, massmedia, headline, content) VALUES (?, ?, ?, ?, ?)'
        con.execute(insert_sql, (url['url'], category, media, headline, content))
        if count % 10 == 0: con.commit()
except Exception as e:
    print('exception 발생... 내용:')
    print(e)
finally:
    con.close()
    driver.close()
    print('완료. 프로그램 종료.')