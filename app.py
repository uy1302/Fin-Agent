from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
import pymongo
from datetime import datetime, timedelta
from langchain.prompts import PromptTemplate
from langchain_google_vertexai import ChatVertexAI
from langchain.schema import HumanMessage
import os
import re
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import seaborn as sns
import json
import base64
from io import BytesIO
from functools import lru_cache
import threading
from flask_caching import Cache
import requests
from bs4 import BeautifulSoup
import time

load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")
app = Flask(__name__)

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

client = pymongo.MongoClient(MONGODB_URI,
                             maxPoolSize=10,
                             connectTimeoutMS=5000,
                             serverSelectionTimeoutMS=5000)
db = client["Soni_Agent"]

news_collections = {
    "cafef": db["cafef_vn"],
    "vnexpress": db["vnexpress_net"],
    "tinnhanhchungkhoan": db["www_tinnhanhchungkhoan_vn"]
}

llm_lock = threading.Lock()
llm = ChatVertexAI(model="gemini-2.0-flash", temperature=0.0, max_tokens=1000)

sentiment_cache = {}
content_cache = {}
insight_cache = {}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8',
}

def fetch_article_content(url):
    """Fetch article content from URL with caching"""
    if url in content_cache:
        return content_cache[url]
    
    try:
        time.sleep(0.5)
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        
        article_content = ""
        
        if "cafef.vn" in url:
            content_div = soup.select_one('.detail-content, .contentdetail')
            if content_div:
                paragraphs = content_div.find_all('p')
                article_content = ' '.join([p.get_text().strip() for p in paragraphs])
        elif "vnexpress.net" in url:
            content_div = soup.select_one('.fck_detail, .article-content')
            if content_div:
                paragraphs = content_div.find_all('p')
                article_content = ' '.join([p.get_text().strip() for p in paragraphs])
        elif "tinnhanhchungkhoan.vn" in url:
            content_div = soup.select_one('.detail-content, .article-body')
            if content_div:
                paragraphs = content_div.find_all('p')
                article_content = ' '.join([p.get_text().strip() for p in paragraphs])
        else:

            for selector in ['.article-content', '.post-content', '.entry-content', '.content', 'article', '.detail-content']:
                content_div = soup.select_one(selector)
                if content_div:
                    paragraphs = content_div.find_all('p')
                    article_content = ' '.join([p.get_text().strip() for p in paragraphs])
                    break
        
        if not article_content:
            main_content = soup.select_one('main, #main, .main, .content, #content, .container')
            if main_content:
                paragraphs = main_content.find_all('p')
                article_content = ' '.join([p.get_text().strip() for p in paragraphs])
            else:
                paragraphs = soup.find_all('p')
                article_content = ' '.join([p.get_text().strip() for p in paragraphs])
        
        # Clean up the content
        article_content = re.sub(r'\s+', ' ', article_content).strip()
        
        # Cache the result
        content_cache[url] = article_content
        return article_content
    except Exception as e:
        print(f"Error fetching article content from {url}: {str(e)}")
        return ""

@lru_cache(maxsize=1000)
def analyze_sentiment(text):
    """Analyze sentiment of text as positive, neutral, or negative with caching"""
    # Check cache first
    if text in sentiment_cache:
        return sentiment_cache[text]
    
    # Truncate very long texts to save tokens
    text_to_analyze = text[:1000] if len(text) > 1000 else text
    
    prompt = PromptTemplate(
        input_variables=["text"],
        template="Phân loại nội dung sau thành các tín hiệu: tích cực (positive), trung bình (neutral), và tiêu cực (negative). Chỉ trả về 'positive', 'neutral', hoặc 'negative'.\n\nText: {text}\n\nSignal:"
    )
    message = HumanMessage(content=prompt.format(text=text_to_analyze))
    try:
        with llm_lock:  # Use lock to prevent concurrent API calls
            classification = llm.invoke([message]).content.strip().lower()
        
        # Parse response
        if "tích cực" in classification or "positive" in classification:
            result = "positive"
        elif "tiêu cực" in classification or "negative" in classification:
            result = "negative"
        else:
            result = "neutral"
        
        # Cache the result
        sentiment_cache[text] = result
        return result
    except Exception as e:
        print(f"Error analyzing sentiment: {str(e)}")
        return "neutral"

@lru_cache(maxsize=500)
def generate_stock_insights(article_content, ticker):
    """Generate insights from article content related to a specific ticker"""
    # Check cache first
    cache_key = f"{ticker}_{hash(article_content[:1000])}"
    if cache_key in insight_cache:
        return insight_cache[cache_key]
    
    # Truncate very long texts to save tokens but keep more content for better analysis
    text_to_analyze = article_content[:3000] if len(article_content) > 3000 else article_content
    
    if len(text_to_analyze) < 100:
        return None
    
    # Enhanced prompt for better stock insights
    insight_prompt = PromptTemplate.from_template(
        """Bạn là một chuyên gia phân tích tài chính với kinh nghiệm phân tích cổ phiếu Việt Nam. Hãy phân tích nội dung bài báo sau đây về mã cổ phiếu {ticker} và đưa ra nhận định chuyên sâu.

Nội dung bài báo:
{content}

Hãy phân tích các yếu tố sau (nếu có trong bài báo):
1. Kết quả kinh doanh gần đây hoặc dự kiến
2. Chiến lược phát triển của công ty
3. Các thay đổi về quản trị, nhân sự cấp cao
4. Các dự án, sản phẩm, dịch vụ mới
5. Tình hình thị trường và đối thủ cạnh tranh
6. Các yếu tố vĩ mô ảnh hưởng đến công ty
7. Các rủi ro tiềm ẩn hoặc cơ hội đầu tư

Đưa ra nhận định ngắn gọn trong 2-3 câu, tập trung vào thông tin quan trọng nhất liên quan đến mã {ticker} và ý nghĩa đối với nhà đầu tư. Nếu bài báo không có thông tin đủ để phân tích, hãy trả về "Không đủ thông tin để phân tích".

Nhận định:"""
    )
    
    try:
        with llm_lock:  # Use lock to prevent concurrent API calls
            chain = insight_prompt | llm
            response = chain.invoke({"ticker": ticker, "content": text_to_analyze})
        
        insight = response.content.strip()
        
        # Check if the insight is meaningful
        if "không đủ thông tin" in insight.lower() or "không có thông tin" in insight.lower():
            insight = None
        
        # Cache the result
        insight_cache[cache_key] = insight
        return insight
    except Exception as e:
        print(f"Error generating insights: {str(e)}")
        return None

@lru_cache(maxsize=500)
def generate_investment_recommendation(article_content, ticker):
    """Generate investment recommendation based on article content"""
    # Only generate recommendation if we have substantial content
    if not article_content or len(article_content) < 300:
        return None
    
    # Truncate very long texts to save tokens
    text_to_analyze = article_content[:3500] if len(article_content) > 3500 else article_content
    
    recommendation_prompt = PromptTemplate.from_template(
        """Bạn là một chuyên gia phân tích tài chính với kinh nghiệm phân tích cổ phiếu Việt Nam. Dựa trên nội dung bài báo sau đây về mã cổ phiếu {ticker}, hãy đưa ra khuyến nghị đầu tư.

Nội dung bài báo:
{content}

Hãy đánh giá các yếu tố sau (nếu có trong bài báo):
1. Triển vọng tăng trưởng ngắn hạn và dài hạn
2. Định giá hiện tại (P/E, P/B, EV/EBITDA...)
3. Các yếu tố cơ bản của doanh nghiệp
4. Các yếu tố kỹ thuật và xu hướng giá
5. Các rủi ro tiềm ẩn

Đưa ra một trong các khuyến nghị sau kèm lý do ngắn gọn (1-2 câu):
- MUA: Nếu có triển vọng tích cực rõ ràng
- NẮM GIỮ: Nếu triển vọng ổn định hoặc chưa rõ ràng
- BÁN: Nếu có triển vọng tiêu cực rõ ràng
- THEO DÕI: Nếu cần thêm thông tin để đánh giá

Nếu bài báo không có đủ thông tin để đưa ra khuyến nghị, hãy trả về "Không đủ thông tin để đưa ra khuyến nghị".

Khuyến nghị:"""
    )
    
    try:
        with llm_lock:  # Use lock to prevent concurrent API calls
            chain = recommendation_prompt | llm
            response = chain.invoke({"ticker": ticker, "content": text_to_analyze})
        
        recommendation = response.content.strip()
        
        # Check if the recommendation is meaningful
        if "không đủ thông tin" in recommendation.lower():
            return None
        
        return recommendation
    except Exception as e:
        print(f"Error generating recommendation: {str(e)}")
        return None

@lru_cache(maxsize=500)
def extract_key_metrics(article_content, ticker):
    """Extract key financial metrics mentioned in the article"""
    if not article_content or len(article_content) < 200:
        return None
    
    # Truncate very long texts to save tokens
    text_to_analyze = article_content[:3000] if len(article_content) > 3000 else article_content
    
    metrics_prompt = PromptTemplate.from_template(
        """Trích xuất các chỉ số tài chính và con số quan trọng từ bài báo sau về mã cổ phiếu {ticker}.

Nội dung bài báo:
{content}

Hãy trích xuất các thông tin sau (nếu có trong bài báo):
1. Doanh thu (quý/năm)
2. Lợi nhuận (quý/năm)
3. Biên lợi nhuận
4. EPS (thu nhập trên mỗi cổ phiếu)
5. P/E (hệ số giá trên thu nhập)
6. Cổ tức
7. Giá mục tiêu
8. Tăng trưởng (%)
9. Các chỉ số tài chính khác

Trả về dưới dạng danh sách các chỉ số với giá trị và thời kỳ tương ứng. Nếu không tìm thấy thông tin, hãy trả về "Không tìm thấy chỉ số tài chính trong bài báo".

Các chỉ số:"""
    )
    
    try:
        with llm_lock:  # Use lock to prevent concurrent API calls
            chain = metrics_prompt | llm
            response = chain.invoke({"ticker": ticker, "content": text_to_analyze})
        
        metrics = response.content.strip()
        
        # Check if any metrics were found
        if "không tìm thấy" in metrics.lower():
            return None
        
        return metrics
    except Exception as e:
        print(f"Error extracting metrics: {str(e)}")
        return None

@lru_cache(maxsize=500)
def summarize_text(text):
    """Summarize text in one sentence with caching"""
    # Truncate very long texts to save tokens
    text_to_summarize = text[:1500] if len(text) > 1500 else text
    
    summarize_prompt = PromptTemplate.from_template(
        """Summarize the following text in one short sentence in Vietnamese.
         Text: {text}
         Summary:"""
    )
    try:
        with llm_lock:  # Use lock to prevent concurrent API calls
            chain = summarize_prompt | llm
            response = chain.invoke({"text": text_to_summarize})
        return response.content
    except Exception as e:
        print(f"Error summarizing text: {str(e)}")
        return "Không thể tóm tắt văn bản."

def query_all_collections(query, projection=None, limit=None):
    """Query all news collections and combine results with optimization"""
    all_results = []
    threads = []
    
    # Use thread-local results
    results_by_source = {}
    
    def query_collection(name, collection):
        try:
            results = list(collection.find(query, projection).limit(limit * 3 if limit else 1000))
            for result in results:
                result['source'] = name
            results_by_source[name] = results
        except Exception as e:
            print(f"Error querying {name}: {str(e)}")
            results_by_source[name] = []
    
    # Create threads for each collection query
    for collection_name, collection in news_collections.items():
        thread = threading.Thread(target=query_collection, args=(collection_name, collection))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Combine results from all collections
    for results in results_by_source.values():
        all_results.extend(results)
    
    # Sort by post_time
    all_results.sort(key=lambda x: x.get('post_time', 0), reverse=True)
    
    if limit:
        all_results = all_results[:limit]
        
    return all_results

@cache.memoize(timeout=3600)  # Cache for one hour
def analyze_news_sentiment(ticker, date=None):
    """Analyze sentiment for a specific ticker and date using stored data from all collections"""
    query = {"tickers": ticker}
    
    if date:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            start_timestamp = int(dt.timestamp())
            end_timestamp = int((dt + timedelta(days=1)).timestamp())
            query["post_time"] = {"$gte": start_timestamp, "$lt": end_timestamp}
        except ValueError:
            pass
    
    projection = {
        "_id": 1,
        "title": 1,
        "full_url": 1,
        "description": 1,
        "post_time": 1,
        "tickers": 1
    }
    
    # Limit the initial query to save resources
    news_items = query_all_collections(query, projection, limit=30)
    
    results = []
    
    # Process results in batches to prevent API overload
    batch_size = 3
    for i in range(0, len(news_items), batch_size):
        batch = news_items[i:i+batch_size]
        
        for news in batch:
            title = news.get("title", "")
            description = news.get("description", "")
            url = news.get("full_url", "#")
            text = title + " " + description
            
            if len(text) < 10:
                continue
            
            # Fetch article content from URL
            article_content = fetch_article_content(url)
            
            # Analyze sentiment based on title and description
            sentiment = analyze_sentiment(text)
            
            # Generate insights from article content
            insight = None
            recommendation = None
            key_metrics = None
            
            if article_content:
                insight = generate_stock_insights(article_content, ticker)
                
                # Only generate recommendation and extract metrics for articles with insights
                if insight:
                    recommendation = generate_investment_recommendation(article_content, ticker)
                    key_metrics = extract_key_metrics(article_content, ticker)
            
            # Only summarize if absolutely necessary
            if description:
                summary = description
            else:
                summary = summarize_text(title) if len(title) > 10 else "Không có mô tả."
            
            timestamp = news.get("post_time", 0)
            date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M") if timestamp else "Unknown"
            
            source = news.get("source", "Unknown")
            
            results.append({
                "title": title,
                "url": url,
                "date": date,
                "sentiment": sentiment,
                "summary": summary,
                "insight": insight,
                "recommendation": recommendation,
                "key_metrics": key_metrics,
                "tickers": news.get("tickers", []),
                "source": source
            })
    
    return results

@cache.memoize(timeout=7200)  # Cache for two hours
def generate_sentiment_chart(ticker, date_range=30):
    """Generate sentiment chart for a ticker with caching"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=date_range)
    
    query = {
        "tickers": ticker,
        "post_time": {
            "$gte": int(start_date.timestamp()),
            "$lte": int(end_date.timestamp())
        }
    }
    
    projection = {
        "title": 1,
        "description": 1,
        "post_time": 1
    }
    
    news_items = query_all_collections(query, projection, limit=100)
    
    if not news_items:
        return None, "No data available for the specified ticker and date range."
    
    # Process in smaller batches
    dates = []
    sentiments = []
    sources = []
    
    batch_size = 10
    for i in range(0, len(news_items), batch_size):
        batch = news_items[i:i+batch_size]
        
        for news in batch:
            title = news.get("title", "")
            description = news.get("description", "")
            text = title + " " + description
            
            if len(text) < 10:
                continue
                
            sentiment = analyze_sentiment(text)
            timestamp = news.get("post_time", 0)
            date = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
            source = news.get("source", "Unknown")
            
            dates.append(date)
            sources.append(source)
            if sentiment == "positive":
                sentiments.append(1)
            elif sentiment == "negative":
                sentiments.append(-1)
            else:
                sentiments.append(0)
    
    if not dates:
        return None, "No valid news found for sentiment analysis."
    
    df = pd.DataFrame({'date': dates, 'sentiment': sentiments, 'source': sources})
    
    df_grouped = df.groupby('date').agg(
        sentiment_avg=('sentiment', 'mean'),
        sentiment_count=('sentiment', 'count')
    ).reset_index()
    
    df_grouped = df_grouped.sort_values('date')
    
    # Optimize matplotlib rendering
    plt.figure(figsize=(12, 6), dpi=80)  # Lower DPI
    
    colors = df_grouped['sentiment_avg'].apply(
        lambda x: 'green' if x > 0.2 else ('red' if x < -0.2 else 'yellow')
    )
    
    plt.bar(df_grouped['date'], df_grouped['sentiment_avg'], color=colors)
    plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
    plt.title(f'Sentiment Analysis for {ticker} over the Last {date_range} Days')
    plt.xlabel('Date')
    plt.ylabel('Average Sentiment (Positive = 1, Neutral = 0, Negative = -1)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Optimize image saving - removed the invalid 'optimize' parameter
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight', dpi=80)
    buffer.seek(0)
    chart_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close()
    
    return chart_data, None

@cache.memoize(timeout=7200)  # Cache for two hours
def generate_daily_sentiment_analysis(ticker, date_range=30):
    """Generate daily sentiment analysis summaries for a ticker with caching"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=date_range)
    
    query = {
        "tickers": ticker,
        "post_time": {
            "$gte": int(start_date.timestamp()),
            "$lte": int(end_date.timestamp())
        }
    }
    
    projection = {
        "title": 1,
        "description": 1,
        "post_time": 1,
        "full_url": 1
    }
    
    news_items = query_all_collections(query, projection, limit=100)
    
    if not news_items:
        return None, "Không có dữ liệu cho mã chứng khoán này trong khoảng thời gian đã chọn."
    
    # Group news by date
    news_by_date = {}
    
    for news in news_items:
        title = news.get("title", "")
        description = news.get("description", "")
        url = news.get("full_url", "#")
        text = title + " " + description
        
        if len(text) < 10:
            continue
            
        timestamp = news.get("post_time", 0)
        date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
        
        if date_str not in news_by_date:
            news_by_date[date_str] = []
        
        # Fetch article content for insights
        article_content = fetch_article_content(url)
        insight = None
        recommendation = None
        
        if article_content:
            insight = generate_stock_insights(article_content, ticker)
            if insight:
                recommendation = generate_investment_recommendation(article_content, ticker)
            
        sentiment = analyze_sentiment(text)
        
        news_by_date[date_str].append({
            "title": title,
            "description": description,
            "sentiment": sentiment,
            "url": url,
            "insight": insight,
            "recommendation": recommendation
        })
    
    if not news_by_date:
        return None, "Không có tin tức hợp lệ để phân tích."
    
    # Generate summaries for each date
    daily_summaries = []
    
    for date_str, news_list in sorted(news_by_date.items(), reverse=True):
        positive_count = sum(1 for n in news_list if n["sentiment"] == "positive")
        negative_count = sum(1 for n in news_list if n["sentiment"] == "negative")
        neutral_count = sum(1 for n in news_list if n["sentiment"] == "neutral")
        total_count = len(news_list)
        
        if total_count == 0:
            continue
            
        sentiment_score = (positive_count - negative_count) / total_count
        
        # Determine overall sentiment
        if sentiment_score > 0.3:
            overall = "Tích cực"
            sentiment_class = "positive"
        elif sentiment_score < -0.3:
            overall = "Tiêu cực"
            sentiment_class = "negative"
        else:
            overall = "Trung lập"
            sentiment_class = "neutral"
        
        # Find articles with insights for summary
        articles_with_insights = [n for n in news_list if n.get("insight")]
        
        # Generate summary using LLM based on insights if available
        summary_text = ""
        if articles_with_insights:
            # Use insights from articles for summary
            insights_text = "\n".join([n["insight"] for n in articles_with_insights if n["insight"]])
            summary_prompt = PromptTemplate.from_template(
                """Dựa trên các nhận định sau đây về mã chứng khoán {ticker}, hãy tóm tắt ngắn gọn trong một câu về tình hình và ý nghĩa đối với nhà đầu tư:
                {insights}
                
                Tóm tắt:"""
            )
            try:
                with llm_lock:
                    chain = summary_prompt | llm
                    response = chain.invoke({"ticker": ticker, "insights": insights_text})
                summary_text = response.content
            except Exception as e:
                print(f"Error generating summary: {str(e)}")
                summary_text = "Không thể tạo tóm tắt."
        elif total_count >= 3:
            # Fall back to title-based summary if no insights available
            all_titles = "\n".join([n["title"] for n in news_list])
            summary_prompt = PromptTemplate.from_template(
                """Dựa trên các tiêu đề tin tức sau đây về mã chứng khoán, hãy tóm tắt ngắn gọn trong một câu về tình hình và ý nghĩa đối với nhà đầu tư:
                {titles}
                
                Tóm tắt:"""
            )
            try:
                with llm_lock:
                    chain = summary_prompt | llm
                    response = chain.invoke({"titles": all_titles})
                summary_text = response.content
            except Exception as e:
                print(f"Error generating summary: {str(e)}")
                summary_text = "Không thể tạo tóm tắt."
        else:
            # For days with few news, use the most significant news title
            if positive_count > negative_count:
                for n in news_list:
                    if n["sentiment"] == "positive":
                        summary_text = n["title"]
                        break
            elif negative_count > 0:
                for n in news_list:
                    if n["sentiment"] == "negative":
                        summary_text = n["title"]
                        break
            else:
                summary_text = news_list[0]["title"]
        
        # Get most important news by sentiment and insights
        top_news = []
        
        # First try to get news with insights
        if articles_with_insights:
            for sentiment_type in ["positive", "negative", "neutral"]:
                top_article = next((n for n in articles_with_insights if n["sentiment"] == sentiment_type), None)
                if top_article:
                    top_news.append({
                        "title": top_article["title"],
                        "sentiment": sentiment_type,
                        "url": top_article["url"],
                        "insight": top_article["insight"],
                        "recommendation": top_article.get("recommendation")
                    })
                    if len(top_news) >= 2:  # Limit to 2 top news
                        break
        
        # If we don't have enough, add more without insights
        if len(top_news) < 2:
            for sentiment_type in ["positive", "negative"]:
                if not any(n["sentiment"] == sentiment_type for n in top_news):
                    top_article = next((n for n in news_list if n["sentiment"] == sentiment_type), None)
                    if top_article:
                        top_news.append({
                            "title": top_article["title"],
                            "sentiment": sentiment_type,
                            "url": top_article["url"],
                            "insight": top_article.get("insight"),
                            "recommendation": top_article.get("recommendation")
                        })
        
        daily_summaries.append({
            "date": date_str,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "total_count": total_count,
            "sentiment_score": round(sentiment_score, 2),
            "overall_sentiment": overall,
            "sentiment_class": sentiment_class,
            "summary": summary_text,
            "top_news": top_news
        })
    
    # Sort by date, most recent first
    daily_summaries.sort(key=lambda x: x["date"], reverse=True)
    
    return daily_summaries, None

@cache.memoize(timeout=3600)  # Cache for one hour
def get_related_tickers(ticker, limit=5):
    """Find related tickers with caching"""
    related_tickers = {}
    threads = []
    results_by_source = {}
    
    def process_collection(name, collection):
        try:
            pipeline = [
                {"$match": {"tickers": ticker}},
                {"$unwind": "$tickers"},
                {"$match": {"tickers": {"$ne": ticker}}},
                {"$group": {"_id": "$tickers", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit * 2}  # Get more for combining
            ]
            
            results = list(collection.aggregate(pipeline))
            results_by_source[name] = results
        except Exception as e:
            print(f"Error processing {name}: {str(e)}")
            results_by_source[name] = []
    
    # Create threads for parallel processing
    for collection_name, collection in news_collections.items():
        thread = threading.Thread(target=process_collection, args=(collection_name, collection))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Combine results
    for results in results_by_source.values():
        for result in results:
            ticker_id = result["_id"]
            count = result["count"]
            
            if ticker_id in related_tickers:
                related_tickers[ticker_id] += count
            else:
                related_tickers[ticker_id] = count
    
    result_list = [{"ticker": k, "count": v} for k, v in related_tickers.items()]
    result_list.sort(key=lambda x: x["count"], reverse=True)
    
    return result_list[:limit]

@cache.memoize(timeout=3600)  # Cache for one hour
def get_trending_tickers(days=7, limit=10):
    """Get trending tickers with caching"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    trending_tickers = {}
    threads = []
    results_by_source = {}
    
    def process_collection(name, collection):
        try:
            pipeline = [
                {"$match": {"post_time": {"$gte": int(start_date.timestamp())}}},
                {"$unwind": "$tickers"},
                {"$group": {"_id": "$tickers", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": limit * 2}  # Get more for combining
            ]
            
            results = list(collection.aggregate(pipeline))
            results_by_source[name] = results
        except Exception as e:
            print(f"Error processing {name}: {str(e)}")
            results_by_source[name] = []
    
    # Create threads for parallel processing
    for collection_name, collection in news_collections.items():
        thread = threading.Thread(target=process_collection, args=(collection_name, collection))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Combine results
    for results in results_by_source.values():
        for result in results:
            ticker_id = result["_id"]
            count = result["count"]
            
            if ticker_id in trending_tickers:
                trending_tickers[ticker_id] += count
            else:
                trending_tickers[ticker_id] = count
    
    result_list = [{"ticker": k, "count": v} for k, v in trending_tickers.items()]
    result_list.sort(key=lambda x: x["count"], reverse=True)
    
    return result_list[:limit]

@cache.memoize(timeout=3600)  # Cache for one hour
def get_sentiment_distribution(ticker, date_range=30):
    """Get sentiment distribution with caching"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=date_range)
    
    query = {
        "tickers": ticker,
        "post_time": {
            "$gte": int(start_date.timestamp()),
            "$lte": int(end_date.timestamp())
        }
    }
    
    projection = {
        "title": 1,
        "description": 1,
        "source": 1
    }
    
    # Limit query size
    news_items = query_all_collections(query, projection, limit=100)
    
    if not news_items:
        return None
    
    sentiments = {"positive": 0, "neutral": 0, "negative": 0}
    source_stats = {}
    
    # Process in batches
    batch_size = 10
    for i in range(0, len(news_items), batch_size):
        batch = news_items[i:i+batch_size]
        
        for news in batch:
            title = news.get("title", "")
            description = news.get("description", "")
            text = title + " " + description
            source = news.get("source", "unknown")
            
            if len(text) < 10:
                continue
                
            sentiment = analyze_sentiment(text)
            sentiments[sentiment] += 1
            
            if source not in source_stats:
                source_stats[source] = {"positive": 0, "neutral": 0, "negative": 0, "total": 0}
            
            source_stats[source][sentiment] += 1
            source_stats[source]["total"] += 1
    
    total = sum(sentiments.values())
    if total == 0:
        return None
    
    sentiment_percentages = {
        "positive": round(sentiments["positive"] / total * 100, 2),
        "neutral": round(sentiments["neutral"] / total * 100, 2),
        "negative": round(sentiments["negative"] / total * 100, 2),
        "total_count": total,
        "by_source": source_stats
    }
    
    return sentiment_percentages

@cache.memoize(timeout=3600)  # Cache for one hour
def get_sources_stats(ticker=None, date_range=30):
    """Get statistics on news sources with caching"""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=date_range)
    
    query = {
        "post_time": {
            "$gte": int(start_date.timestamp()),
            "$lte": int(end_date.timestamp())
        }
    }
    
    if ticker:
        query["tickers"] = ticker
    
    source_stats = {}
    threads = []
    results = {}
    
    def count_documents(name, collection):
        try:
            count = collection.count_documents(query)
            results[name] = count
        except Exception as e:
            print(f"Error counting documents for {name}: {str(e)}")
            results[name] = 0
    
    # Create threads for parallel processing
    for source_name, collection in news_collections.items():
        thread = threading.Thread(target=count_documents, args=(source_name, collection))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    return results

@app.route('/')
@cache.cached(timeout=600)  # Cache for 10 minutes
def index():
    trending_tickers = get_trending_tickers()
    sources_stats = get_sources_stats()
    return render_template('index.html', trending_tickers=trending_tickers, sources_stats=sources_stats)

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    if request.method == 'POST':
        ticker = request.form.get('ticker', '').upper()
        date = request.form.get('date', '')
    else:
        ticker = request.args.get('ticker', '').upper()
        date = request.args.get('date', '')
    
    if not ticker:
        return render_template('analyze.html', error="Please enter a ticker symbol")
    
    # Use a cache key based on ticker and date
    cache_key = f"{ticker}_{date}"
    
    # Implement progressive loading for heavy computation parts
    news_results = analyze_news_sentiment(ticker, date)
    
    chart_data, chart_error = generate_sentiment_chart(ticker)
    
    # Replace wordcloud with daily sentiment analysis
    daily_sentiment, daily_error = generate_daily_sentiment_analysis(ticker)
    
    related_tickers = get_related_tickers(ticker)
    
    sentiment_distribution = get_sentiment_distribution(ticker)
    
    sources_stats = get_sources_stats(ticker)
    
    return render_template(
        'analyze.html', 
        ticker=ticker, 
        date=date,
        news_results=news_results,
        chart_data=chart_data,
        chart_error=chart_error,
        daily_sentiment=daily_sentiment,
        daily_error=daily_error,
        related_tickers=related_tickers,
        sentiment_distribution=sentiment_distribution,
        sources_stats=sources_stats
    )

@app.route('/api/sentiment/<ticker>')
@cache.cached(timeout=1800)  # Cache for 30 minutes
def api_sentiment(ticker):
    date = request.args.get('date', '')
    results = analyze_news_sentiment(ticker.upper(), date)
    return jsonify(results)

@app.route('/api/daily/<ticker>')
@cache.cached(timeout=3600)  # Cache for one hour
def api_daily(ticker):
    days = int(request.args.get('days', 30))
    results, error = generate_daily_sentiment_analysis(ticker.upper(), days)
    if error:
        return jsonify({"error": error})
    return jsonify(results or [])

@app.route('/api/trending')
@cache.cached(timeout=3600)  # Cache for one hour
def api_trending():
    days = int(request.args.get('days', 7))
    limit = int(request.args.get('limit', 10))
    results = get_trending_tickers(days, limit)
    return jsonify(results)

@app.route('/api/related/<ticker>')
@cache.cached(timeout=3600)  # Cache for one hour
def api_related(ticker):
    limit = int(request.args.get('limit', 5))
    results = get_related_tickers(ticker.upper(), limit)
    return jsonify(results)

@app.route('/api/distribution/<ticker>')
@cache.cached(timeout=3600)  # Cache for one hour
def api_distribution(ticker):
    days = int(request.args.get('days', 30))
    results = get_sentiment_distribution(ticker.upper(), days)
    return jsonify(results or {})

@app.route('/api/sources')
@cache.cached(timeout=3600)  # Cache for one hour
def api_sources():
    ticker = request.args.get('ticker', None)
    days = int(request.args.get('days', 30))
    results = get_sources_stats(ticker, days)
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)
