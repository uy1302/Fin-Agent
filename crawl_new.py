import os
import json
import re
import faiss
import requests
import time
import urllib.parse
import logging
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
from dateutil import parser
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def get_full_url(base_url, relative_url):
    return urllib.parse.urljoin(base_url, relative_url.lstrip("/")) if relative_url else ""

def parse_relative_time(relative_time):
    current_time = datetime.now()
    match = re.search(r"(\d+)\s*(giờ|phút) trước", relative_time)
    if match:
        amount, unit = int(match.group(1)), match.group(2)
        return (current_time - (timedelta(hours=amount) if unit=="giờ" else timedelta(minutes=amount))).timestamp()
    relative_time = re.sub(r"^.*?,\s*", "", relative_time)
    match_tz = re.search(r"\(GMT([+-]\d+)\)", relative_time)
    tz_offset = int(match_tz.group(1)) if match_tz else 0
    if match_tz:
        relative_time = re.sub(r"\s*\(GMT[+-]\d+\)", "", relative_time)
    try:
        absolute_time = datetime.strptime(relative_time.strip(), "%d/%m/%Y, %H:%M")
        absolute_time = absolute_time.replace(tzinfo=timezone(timedelta(hours=tz_offset)))
        return absolute_time.timestamp()
    except ValueError:
        return current_time.timestamp()

def clean_html(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    return soup.get_text(separator=" ", strip=True)

def extract_article_content(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    
    article_body = soup.find("div", class_="article__body cms-body") or soup.find("div", class_="w640 fr clear")
    if not article_body:
        return clean_html(html_content)  
    
    for ads in article_body.select("div.ads_middle"):
        ads.decompose()
    
    for script in article_body.find_all("script"):
        script.decompose()
    
    paragraphs = article_body.find_all("p")
    content = "\n\n".join([p.get_text(strip=True) for p in paragraphs])
    
    return content

def get_web_content(url):
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return extract_article_content(r.text)
    except Exception:
        return ""

def get_article_details(article_url, headers, model):
    try:
        r = requests.get(article_url, headers=headers)
        r.encoding = "utf-8"
        soup = BeautifulSoup(r.text, "html.parser")
        
        desc_tag = (soup.find("meta", {"name": "description"}) or 
                    soup.find("meta", {"property": "og:description"}))
        if desc_tag:
            description = desc_tag.get("content", "").strip()
        else:
            desc_tag = (soup.find("p", class_="sapo") or soup.find("div", class_="article__sapo") or 
                       soup.find("div", class_="sapo"))
            description = desc_tag.get_text(strip=True) if desc_tag else ""
            
        if not description:
            article_body = soup.find("div", class_="article__body cms-body")
            if article_body:
                first_p = article_body.find("p")
                if first_p:
                    description = first_p.get_text(strip=True)
                else:
                    full_content = extract_article_content(r.text)
                    description = full_content[:500] if full_content else "Không có mô tả"
            else:
                first_p = soup.select_one("div.detail-content p")
                if first_p:
                    description = first_p.get_text(strip=True)
                else:
                    description = "Không có mô tả"
        
        embedding = model.encode(description).tolist() if description else []
        
        time_tag = soup.find("span", class_="time") or soup.find("div", class_="time") or soup.find("span", class_="date")
        time_ago = soup.find("span", class_="time-ago")
        meta_time = soup.find("meta", {"property": "article:published_time"})
        if meta_time:
            post_time = parser.parse(meta_time.get("content", "").strip()).timestamp()
        elif time_ago:
            post_time = parse_relative_time(time_ago.get_text(strip=True))
        elif time_tag:
            post_time = parse_relative_time(time_tag.get_text(strip=True))
        else:
            post_time = time.time()
            
        article_content = extract_article_content(r.text)
        
        return description, post_time, embedding, article_content
    except Exception as e:
        logging.error(f"Error processing {article_url}: {e}")
        return "Không có mô tả", time.time(), [], ""

def extract_tickers(article_text):
    with open("vnstock.json", "r", encoding="utf-8") as f:
        ticker_dict = json.load(f)
    
    found = {t for t in ticker_dict if re.search(rf'\b{re.escape(t)}\b', article_text)}
    
    for t, name in ticker_dict.items():
        if name and name in article_text:
            found.add(t)
    
    return list(found) if found else []

def crawl_news_urls(sites, model, db, config_collection):
    headers = {"User-Agent": "Mozilla/5.0"}
    total_inserted = 0
    config_entry = config_collection.find_one({"config_name": "global"})
    last_update = config_entry["last_update_timestamp"] if config_entry else 0
    max_post = last_update
    for site in sites:
        try:
            r = requests.get(site["url"], headers=headers)
            r.encoding = "utf-8"
            soup = BeautifulSoup(r.text, "html.parser")
            domain = urllib.parse.urlparse(site["url"]).netloc.replace(".", "_")
            collection = db[domain]
            for selector in site["selectors"]:
                for link in soup.select(selector):
                    href = link.get("href", "").strip()
                    title = link.get_text(strip=True)
                    if not href or not title:
                        continue
                    full_url = get_full_url(site["url"], href)
                    description, post_time, embedding, article_content = get_article_details(full_url, headers, model)
                    if post_time <= last_update:
                        continue
                    
                    tickers_extracted = extract_tickers(article_content) if article_content else []
                    
                    news_data = {
                        "title": title,
                        "full_url": full_url,
                        "description": description,
                        "post_time": post_time,
                        "crawl_timestamp": time.time(),
                        "embedding": embedding,
                        "tickers": tickers_extracted
                    }
                    
                    if not collection.find_one({"full_url": news_data["full_url"]}):
                        collection.insert_one(news_data)
                        logging.info(f"Added: {news_data['title']} to {domain}")
                    max_post = max(max_post, post_time)
            total_inserted += collection.count_documents({"post_time": {"$gt": last_update}})
        except Exception as e:
            logging.error(f"Error crawling {site['url']}: {e}")
    if total_inserted > 0:
        config_collection.update_one({"config_name": "global"}, {"$set": {"last_update_timestamp": max_post}}, upsert=True)
    return total_inserted

def main():
    load_dotenv()
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    mongodb_url = os.getenv("MONGODB_URI")
    client = MongoClient(mongodb_url)
    db = client["Soni_Agent"]
    config_collection = db["configs"]
    sites = [
        {"url": "https://cafef.vn/thi-truong-chung-khoan.chn", "selectors": ["h3.title a", "div.box-category-item a", "article a"]},
        {"url": "https://vnexpress.net/kinh-doanh/chung-khoan", "selectors": ["h3.title-news a", "article a"]},
        {"url": "https://www.tinnhanhchungkhoan.vn/", "selectors": ["h2.title a", "h2 a"]}
    ]
    while True:
        total_news = crawl_news_urls(sites, model, db, config_collection)
        if total_news == 0:
            logging.info("No new articles found.")
        logging.info("Waiting 1 hour for next crawl...")
        time.sleep(3600)

if __name__ == "__main__":
    # main()
    d, p ,e, a = get_article_details("https://vnexpress.net/he-thong-giao-dich-chung-khoan-moi-du-kien-chay-tu-5-5-4869195.html", {}, SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2"))
    print(a)
    print(d)
    print(p)
    print(extract_tickers(a))