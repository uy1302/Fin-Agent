import os
from flask import Flask, render_template, request, jsonify, make_response
import pandas as pd
import pymongo
from datetime import datetime, timedelta
import markdown
from markupsafe import Markup
import matplotlib
matplotlib.use('Agg')
import logging
from functools import lru_cache
import threading
from flask_caching import Cache
import requests
from bs4 import BeautifulSoup
import time
import random
import tenacity
from tenacity import wait_exponential, wait_random
from collections import deque
from dotenv import load_dotenv
import traceback

from visualizations.stock_plots import (
    get_stock_data,
    plot_volume_chart,
    plot_line_chart,
    plot_candlestick,
    plot_volume_and_closed_price,
    plot_shareholders_piechart,
    plot_monthly_returns_heatmap,
    get_internal_reports
)
from models.report_generator import (
    create_reportlab_pdf,
    generate_stock_report_data,
    get_stock_summary,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


load_dotenv()
print(f"MONGODB_URI: {os.getenv('MONGODB_URI')}") 
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

MONGO_URI = os.getenv("MONGODB_URI")
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')


cache = Cache(app, config={'CACHE_TYPE': 'simple'})


client = pymongo.MongoClient(MONGO_URI,
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


retry_config = {
    'wait_min': 2,
    'wait_max': 60,  
    'max_attempts': 5,  
    'jitter_factor': 0.25 
}


api_call_timestamps = deque(maxlen=100)
MAX_CALLS_PER_MINUTE = 10
RATE_LIMIT_WINDOW = 60  


DAILY_TOKEN_BUDGET = 100000
tokens_used_today = 0
token_usage_reset_time = datetime.now()


api_priority_queue = []
PRIORITY_HIGH = 0
PRIORITY_MEDIUM = 1
PRIORITY_LOW = 2

try:
    from langchain_google_vertexai import ChatVertexAI
    llm = ChatVertexAI(
        model="gemini-2.0-flash",
        temperature=0.0,
        max_tokens=1000,
        max_retries=3,
        retry_min_seconds=2,
        retry_max_seconds=30
    )
except Exception as e:
    logger.error(f"Error initializing LLM: {str(e)}")
    llm = None

def is_rate_limited():
    now = time.time()
    while api_call_timestamps and api_call_timestamps[0] < now - RATE_LIMIT_WINDOW:
        api_call_timestamps.popleft()
    return len(api_call_timestamps) >= MAX_CALLS_PER_MINUTE

def is_token_budget_exceeded():
    global tokens_used_today, token_usage_reset_time
    if (datetime.now() - token_usage_reset_time).days > 0:
        tokens_used_today = 0
        token_usage_reset_time = datetime.now()
    return tokens_used_today >= DAILY_TOKEN_BUDGET

def is_rate_limit_error(exception):
    error_msg = str(exception).lower()
    return any(term in error_msg for term in ['rate limit', 'quota', 'resource exhausted', '429'])

def llm_retry_decorator(func):
    wait_strategy = wait_exponential(
        multiplier=retry_config['wait_min'],
        max=retry_config['wait_max'],
        exp_base=2
    ) + wait_random(0, retry_config['jitter_factor'] * retry_config['wait_max'])
    
    @tenacity.retry(
        retry=tenacity.retry_if_exception(is_rate_limit_error),
        wait=wait_strategy,
        stop=tenacity.stop_after_attempt(retry_config['max_attempts']),
        before_sleep=lambda retry_state: logger.warning(f"Rate limit hit, retrying in {retry_state.next_action.sleep} seconds...")
    )
    def wrapper(*args, **kwargs):
        if is_rate_limited():
            delay = random.uniform(1, 5)
            logger.info(f"Rate limit approaching, adding delay of {delay:.2f}s")
            time.sleep(delay)
        
        if is_token_budget_exceeded():
            logger.warning("Token budget exceeded, using fallback method")
            raise Exception("Token budget exceeded")
        
        api_call_timestamps.append(time.time())
        
        return func(*args, **kwargs)
    
    return wrapper

@app.template_filter('markdown')
def markdown_filter(text):
    if isinstance(text, pd.DataFrame):
        if text.empty:
            return Markup("<p>No data available</p>")
        text = text.to_markdown()
    if not text:
        return ""
    return Markup(markdown.markdown(text))

@app.route('/')
def index():
    trending_stocks = get_trending_stocks()
    
    recent_news = get_recent_news(limit=10)
    
    sources_stats = get_sources_stats()
    
    return render_template('index.html', 
                          trending_stocks=trending_stocks,
                          recent_news=recent_news,
                          sources_stats=sources_stats)

@app.route('/analyze')
def analyze():
    ticker = request.args.get('ticker', '').upper()
    if not ticker:
        return render_template('index.html', error="Vui lòng nhập mã cổ phiếu")
    
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    
    try:
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if start_dt > end_dt:
            return render_template('index.html', error="Ngày bắt đầu phải trước ngày kết thúc")
    except ValueError:
        return render_template('index.html', error="Định dạng ngày không hợp lệ")
    
    stock_summary = get_stock_summary(ticker, start_date, end_date)
    if stock_summary is None:
        stock_summary = "Không có dữ liệu cho mã cổ phiếu này."
    
    line_chart, _ = plot_line_chart(ticker, start_date, end_date) or ("Không có dữ liệu", None)
    volume_chart, _ = plot_volume_chart(ticker, start_date, end_date) or ("Không có dữ liệu", None)
    candlestick_chart, _ = plot_candlestick(ticker, start_date, end_date) or ("Không có dữ liệu", None)
    volume_price_chart, _ = plot_volume_and_closed_price(ticker, start_date, end_date) or ("Không có dữ liệu", None)
    shareholders_chart, _ = plot_shareholders_piechart(ticker) or ("Không có dữ liệu", None)
    returns_heatmap, _ = plot_monthly_returns_heatmap(ticker, start_date, end_date) or ("Không có dữ liệu", None)
    
    internal_reports, _ = get_internal_reports(ticker)
    if isinstance(internal_reports, pd.DataFrame):
        internal_reports = internal_reports.to_dict(orient='records') if not internal_reports.empty else []
    
    sentiment_data = get_sentiment_analysis(ticker, start_date, end_date)
    
    template_data = {
        'ticker': ticker,
        'start_date': start_date,
        'end_date': end_date,
        'stock_summary': stock_summary,
        'line_chart': line_chart,
        'volume_chart': volume_chart,
        'candlestick_chart': candlestick_chart,
        'volume_price_chart': volume_price_chart,
        'shareholders_chart': shareholders_chart,
        'returns_heatmap': returns_heatmap,
        'internal_reports': internal_reports
    }
    
    if sentiment_data:
        template_data.update(sentiment_data)
    
    return render_template('analyze.html', **template_data)

# @app.route('/generate_report')
# def generate_report():
#     try:
#         ticker = request.args.get('ticker', '').upper()
#         if not ticker:
#             return jsonify({"error": "Vui lòng nhập mã cổ phiếu"}), 400
            
#         end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
#         start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        
#         include_plots = request.args.getlist('include_plots')
#         if not include_plots:
#             include_plots = ['line', 'volume', 'candlestick', 'volume_price', 'shareholders', 'heatmap']
        
#         include_sentiment = request.args.get('include_sentiment') == 'true'
        
#         sentiment_data = None
#         if include_sentiment:
#             sentiment_data = get_sentiment_analysis(ticker, start_date, end_date)
        
#         logger.info(f"Generating report for {ticker} from {start_date} to {end_date}")
#         report_data = generate_stock_report(
#             ticker,
#             start_date,
#             end_date,
#             include_plots=include_plots,
#             sentiment_data=sentiment_data
#         )
        
#         pdf_result = generate_pdf_report(report_data, 'report_template.html')
        
#         if pdf_result is None:
#             logger.error("PDF generation returned None")
#             return jsonify({"error": "Không thể tạo báo cáo PDF - Kết quả trống"}), 500
            
#         if isinstance(pdf_result, dict) and 'error' in pdf_result:
#             logger.error(f"PDF generation error: {pdf_result['error']}")
#             return jsonify(pdf_result), 500
            
#         response = make_response(pdf_result)
#         response.headers['Content-Type'] = 'application/pdf'
#         response.headers['Content-Disposition'] = f'attachment; filename={ticker}_report_{datetime.now().strftime("%Y%m%d")}.pdf'
#         return response
        
#     except Exception as e:
#         logger.error(f"Unexpected error in generate_report: {str(e)}")
#         logger.error(traceback.format_exc())
#         return jsonify({"error": f"Lỗi hệ thống: {str(e)}"}), 500

@app.route('/generate_report')
def generate_report():
    try:
        ticker = request.args.get('ticker', '').upper()
        if not ticker:
            return jsonify({"error": "Vui lòng nhập mã cổ phiếu"}), 400
            
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        start_date = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
        
        include_plots = request.args.getlist('include_plots')
        if not include_plots:
            include_plots = ['line', 'volume', 'candlestick', 'volume_price', 'shareholders', 'heatmap']
            
        include_sentiment = request.args.get('include_sentiment') == 'true'
        
        sentiment_data = None
        if include_sentiment:
            sentiment_data = get_sentiment_analysis(ticker, start_date, end_date)
            
        logger.info(f"Generating report for {ticker} from {start_date} to {end_date}")
        
        report_data = generate_stock_report_data(
            ticker,
            start_date,
            end_date,
            include_plots=include_plots,
            sentiment_data=sentiment_data
        )
        
        pdf_result = create_reportlab_pdf(report_data)
        
        if pdf_result is None:
            logger.error("PDF generation returned None")
            return jsonify({"error": "Không thể tạo báo cáo PDF - Kết quả trống"}), 500
            
        response = make_response(pdf_result)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={ticker}_report_{datetime.now().strftime("%Y%m%d")}.pdf'
        
        return response
        
    except Exception as e:
        logger.error(f"Unexpected error in generate_report_new: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({"error": f"Lỗi hệ thống: {str(e)}"}), 500


@app.route('/health')
def health_check():
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "llm_available": llm is not None,
        "api_calls_last_minute": len(api_call_timestamps),
        "token_budget_remaining": DAILY_TOKEN_BUDGET - tokens_used_today
    }
    return jsonify(status)

def get_trending_stocks(limit=10):
    """Get trending stocks based on news frequency"""
    try:
        pipeline = [
            {"$match": {"tickers": {"$exists": True, "$ne": None}}},
            {"$unwind": "$tickers"},  
            {"$group": {"_id": "$tickers", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        results = []
        for collection_name, collection in news_collections.items():
            collection_results = list(collection.aggregate(pipeline))
            results.extend(collection_results)
        
        ticker_counts = {}
        for result in results:
            ticker = result["_id"]
            if ticker in ticker_counts:
                ticker_counts[ticker] += result["count"]
            else:
                ticker_counts[ticker] = result["count"]
        
        trending = [{"ticker": ticker, "count": count} for ticker, count in ticker_counts.items()]
        trending.sort(key=lambda x: x["count"], reverse=True)
        
        return trending[:limit]
    except Exception as e:
        logger.error(f"Error getting trending stocks: {str(e)}")
        return []

def get_recent_news(limit=20):
    """Get recent news from all collections"""
    try:
        all_news = []
        for collection_name, collection in news_collections.items():
            news = list(collection.find(
                {"post_time": {"$exists": True}},
                {"_id": 0, "title": 1, "post_time": 1, "full_url": 1, "tickers": 1, "description": 1}
            ).sort("post_time", -1).limit(limit))
            
            for item in news:
                item["url"] = item.get("full_url", "")
                item["source"] = collection_name
                if "tickers" in item and item["tickers"]:
                    item["ticker"] = item["tickers"][0]
                if "post_time" in item:
                    item["date"] = datetime.fromtimestamp(item["post_time"]).strftime('%Y-%m-%d')
            
            all_news.extend(news)
        
        all_news.sort(key=lambda x: x.get("post_time", 0), reverse=True)
        
        return all_news[:limit]
    except Exception as e:
        logger.error(f"Error getting recent news: {str(e)}")
        return []

def get_sources_stats():
    """Get statistics about news sources"""
    try:
        stats = {}
        for source, collection in news_collections.items():
            count = collection.count_documents({})
            stats[source] = count
        
        return stats
    except Exception as e:
        logger.error(f"Error getting source stats: {str(e)}")
        return {}

@lru_cache(maxsize=100)
def fetch_article_content(url):
    """Fetch and extract content from a news article URL"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        content = ""
        
        if "cafef.vn" in url:
            article_body = soup.select_one('.detail-content')
            if article_body:
                content = article_body.get_text(separator='\n', strip=True)
        
        elif "vnexpress.net" in url:
            article_body = soup.select_one('.fck_detail')
            if article_body:
                content = article_body.get_text(separator='\n', strip=True)
        
        elif "tinnhanhchungkhoan.vn" in url:
            article_body = soup.select_one('.detail-content')
            if article_body:
                content = article_body.get_text(separator='\n', strip=True)
        
        else:
            for selector in ['.article-content', '.post-content', '.entry-content', 'article', '.content', '#content']:
                article_body = soup.select_one(selector)
                if article_body:
                    content = article_body.get_text(separator='\n', strip=True)
                    break
        
        if not content:
            paragraphs = soup.find_all('p')
            content = '\n'.join([p.get_text(strip=True) for p in paragraphs])
        
        return content
    except Exception as e:
        logger.error(f"Error fetching article content from {url}: {str(e)}")
        return ""

@llm_retry_decorator
def get_sentiment_analysis(ticker, start_date, end_date):
    """Get sentiment analysis for a stock in a date range using LLM with full article content analysis"""
    try:
        start_timestamp = datetime.strptime(start_date, '%Y-%m-%d').timestamp()
        end_timestamp = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).timestamp()  
        
        content_cache = {}
        sentiment_cache = {}
        
        all_news = []
        for collection_name, collection in news_collections.items():
            query = {
                "tickers": ticker,
                "post_time": {
                    "$gte": start_timestamp,
                    "$lte": end_timestamp
                }
            }
            
            news = list(collection.find(
                query,
                {"_id": 0, "title": 1, "post_time": 1, "full_url": 1, "description": 1}
            ))
            
            for item in news:
                item["url"] = item.get("full_url", "")
                item["source"] = collection_name
                if "post_time" in item:
                    timestamp = item["post_time"]
                    item["date"] = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
            
            all_news.extend(news)
        
        if not all_news:
            return None
        
        with llm_lock:
            for news in all_news:
                full_content = ""
                if news.get("url"):
                    url = news["url"]
                    if url in content_cache:
                        full_content = content_cache[url]
                    else:
                        full_content = fetch_article_content(url)
                        content_cache[url] = full_content
                
                title = news.get('title', '')
                description = news.get('description', '')
                
                if full_content:
                    content = f"{title} {description} {full_content}"
                else:
                    content = f"{title} {description}"
                
                if not content.strip():
                    news["sentiment"] = "neutral"
                    continue
                
                try:
                    cache_key = hash(content[:1000])
                    if cache_key in sentiment_cache:
                        news["sentiment"] = sentiment_cache[cache_key]
                        continue
                    
                    prompt = f"""
                    Phân tích tình cảm (sentiment) của tin tức tài chính này về cổ phiếu {ticker}:
                    ---
                    {content[:3000]}  # Using more content for better analysis but limit length
                    ---
                    Phân loại sentient thành một trong các loại: positive (tích cực), neutral (trung lập), negative (tiêu cực).
                    Chỉ trả về một từ duy nhất: positive, neutral, hoặc negative.
                    """
                    
                    if llm:
                        response = llm.invoke(prompt).content.strip().lower()
                        if "positive" in response or "tích cực" in response:
                            news["sentiment"] = "positive"
                        elif "negative" in response or "tiêu cực" in response:
                            news["sentiment"] = "negative"
                        else:
                            news["sentiment"] = "neutral"
                        
                        if full_content and len(full_content) > 100:
                            insight_prompt = f"""
                            Bạn là một chuyên gia phân tích tài chính với kinh nghiệm phân tích cổ phiếu Việt Nam. 
                            Hãy phân tích nội dung bài báo sau đây về mã cổ phiếu {ticker} và đưa ra nhận định chuyên sâu.

                            Nội dung bài báo:
                            {full_content[:2000]}

                            Hãy phân tích các yếu tố sau (nếu có trong bài báo):
                            1. Kết quả kinh doanh gần đây hoặc dự kiến
                            2. Chiến lược phát triển của công ty
                            3. Các thay đổi về quản trị, nhân sự cấp cao
                            4. Các dự án, sản phẩm, dịch vụ mới
                            5. Tình hình thị trường và đối thủ cạnh tranh

                            Đưa ra nhận định ngắn gọn trong 2-3 câu, tập trung vào thông tin quan trọng nhất.
                            """
                            try:
                                insight_response = llm.invoke(insight_prompt).content.strip()
                                if not ("không đủ thông tin" in insight_response.lower() or 
                                        "không có thông tin" in insight_response.lower()):
                                    news["insight"] = insight_response
                            except Exception as e:
                                logger.error(f"Error generating insights: {str(e)}")
                        
                        sentiment_cache[cache_key] = news["sentiment"]
                    else:
                        news["sentiment"] = "neutral"
                except Exception as e:
                    logger.error(f"Error in sentiment analysis: {str(e)}")
                    news["sentiment"] = "neutral"
                
                time.sleep(0.2)
        
        sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0, "total_count": len(all_news)}
        for news in all_news:
            sentiment = news.get("sentiment", "neutral")
            if sentiment in ["positive", "neutral", "negative"]:
                sentiment_counts[sentiment] += 1
        
        total = sentiment_counts["total_count"]
        if total > 0:
            positive_exact = (sentiment_counts["positive"] / total) * 100 
            neutral_exact = (sentiment_counts["neutral"] / total) * 100 
            negative_exact = (sentiment_counts["negative"] / total) * 100 
            
            sentiment_counts["positive_pct"] = round(positive_exact)
            sentiment_counts["neutral_pct"] = round(neutral_exact)
            sentiment_counts["negative_pct"] = round(negative_exact)
            
            total_pct = sentiment_counts["positive_pct"] + sentiment_counts["neutral_pct"] + sentiment_counts["negative_pct"]
            
            if total_pct != 100:
                errors = [
                    ("positive", abs(positive_exact - sentiment_counts["positive_pct"])),
                    ("neutral", abs(neutral_exact - sentiment_counts["neutral_pct"])),
                    ("negative", abs(negative_exact - sentiment_counts["negative_pct"]))
                ]
                
                errors.sort(key=lambda x: x[1])
                
                adjustment = 100 - total_pct
                sentiment_counts[f"{errors[0][0]}_pct"] += adjustment
        else:
            sentiment_counts["positive_pct"] = 0
            sentiment_counts["neutral_pct"] = 0
            sentiment_counts["negative_pct"] = 0
        
        news_by_date = {}
        for news in all_news:
            date_str = news.get("date", "")
            if not date_str:
                continue
            
            if date_str not in news_by_date:
                news_by_date[date_str] = []
            
            news_by_date[date_str].append(news)
        
        daily_sentiment = []
        for date_str, news_list in sorted(news_by_date.items(), reverse=True):
            day_sentiments = {"positive": 0, "neutral": 0, "negative": 0}
            for news in news_list:
                sentiment = news.get("sentiment", "neutral")
                if sentiment in day_sentiments:
                    day_sentiments[sentiment] += 1
            
            max_sentiment = max(day_sentiments.items(), key=lambda x: x[1])
            overall_sentiment = max_sentiment[0]
            
            sentiment_display = {
                "positive": "Tích cực",
                "neutral": "Trung lập",
                "negative": "Tiêu cực"
            }
            
            sentiment_class = {
                "positive": "success",
                "neutral": "warning text-dark",
                "negative": "danger"
            }
            
            def news_sort_key(news_item):
                has_insight = 0 if "insight" in news_item else 1
                sentiment_priority = {
                    "positive": 1, 
                    "negative": 2, 
                    "neutral": 3
                }.get(news_item.get("sentiment", "neutral"), 3)
                return (has_insight, sentiment_priority)
            
            top_news = sorted(news_list, key=news_sort_key)[:5]
            
            summary = f"Có {len(news_list)} tin tức về {ticker} trong ngày này. "
            summary += f"Tổng quan: {day_sentiments['positive']} tin tích cực, {day_sentiments['neutral']} tin trung lập, và {day_sentiments['negative']} tin tiêu cực."
            
            daily_sentiment.append({
                "date": date_str,
                "overall_sentiment": sentiment_display[overall_sentiment],
                "sentiment_class": sentiment_class[overall_sentiment],
                "summary": summary,
                "top_news": top_news
            })
        
        return {
            "sentiment_distribution": sentiment_counts,
            "daily_sentiment": daily_sentiment
        }
    except Exception as e:
        logger.error(f"Error getting sentiment analysis: {str(e)}")
        return None

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
