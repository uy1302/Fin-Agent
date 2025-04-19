from flask import render_template, make_response, jsonify, request
from datetime import datetime, timedelta
import io
import logging
import traceback
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import matplotlib.pyplot as plt
import base64
from visualizations.stock_plots import (
    get_stock_data,
    get_internal_reports
)
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  

logger = logging.getLogger(__name__)

def plot_to_image_bytes(fig):
    """Convert matplotlib figure to bytes for embedding in ReportLab PDF"""
    img_buffer = io.BytesIO()
    fig.savefig(img_buffer, format='png', dpi=100, bbox_inches='tight')
    img_buffer.seek(0)
    return img_buffer.getvalue()

def create_line_chart(stock_df, symbol):
    """Create a line chart of closing prices"""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(stock_df.index, stock_df['close'], label='Closing Price')
    ax.set_title(f'{symbol} Price History')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    ax.legend()
    ax.grid(True)
    return fig

def create_volume_chart(stock_df, symbol):
    """Create a volume chart"""
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(stock_df.index, stock_df['volume'], label='Volume')
    ax.set_title(f'{symbol} Trading Volume')
    ax.set_xlabel('Date')
    ax.set_ylabel('Volume')
    ax.legend()
    ax.grid(True)
    return fig

def create_candlestick_chart(stock_df, symbol):
    """Create a candlestick chart"""
    fig, ax = plt.subplots(figsize=(8, 4))
    
    width = 0.6
    
    up = stock_df['close'] > stock_df['open']
    down = stock_df['close'] <= stock_df['open']
    
    ax.bar(stock_df.index[up], stock_df['close'][up] - stock_df['open'][up],
           bottom=stock_df['open'][up], width=width, color='green')
    ax.bar(stock_df.index[up], stock_df['high'][up] - stock_df['close'][up],
           bottom=stock_df['close'][up], width=0.1, color='green')
    ax.bar(stock_df.index[up], stock_df['open'][up] - stock_df['low'][up],
           bottom=stock_df['low'][up], width=0.1, color='green')
    
    ax.bar(stock_df.index[down], stock_df['open'][down] - stock_df['close'][down],
           bottom=stock_df['close'][down], width=width, color='red')
    ax.bar(stock_df.index[down], stock_df['high'][down] - stock_df['open'][down],
           bottom=stock_df['open'][down], width=0.1, color='red')
    ax.bar(stock_df.index[down], stock_df['close'][down] - stock_df['low'][down],
           bottom=stock_df['low'][down], width=0.1, color='red')
    
    ax.set_title(f'{symbol} Candlestick Chart')
    ax.set_xlabel('Date')
    ax.set_ylabel('Price')
    ax.grid(True)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

def create_volume_price_chart(stock_df, symbol):
    """Create a combined volume and price chart"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 6), sharex=True, gridspec_kw={'height_ratios': [3, 1]})
    
    ax1.plot(stock_df.index, stock_df['close'], label='Closing Price')
    ax1.set_title(f'{symbol} Price and Volume')
    ax1.set_ylabel('Price')
    ax1.grid(True)
    ax1.legend()
    
    ax2.bar(stock_df.index, stock_df['volume'], label='Volume')
    ax2.set_xlabel('Date')
    ax2.set_ylabel('Volume')
    ax2.grid(True)
    
    plt.tight_layout()
    return fig

def create_mock_shareholders_chart(symbol):
    """Create a mock shareholders chart"""
    fig, ax = plt.subplots(figsize=(6, 6))
    
    shareholders = {
        'Institutional': 45,
        'Retail': 30,
        'Insiders': 15,
        'Other': 10
    }
    
    ax.pie(shareholders.values(), labels=shareholders.keys(), autopct='%1.1f%%',
           shadow=True, startangle=90)
    ax.set_title(f'{symbol} Shareholder Distribution')
    ax.axis('equal')  
    
    return fig

def create_monthly_returns_heatmap(stock_df, symbol):
    """Create a monthly returns heatmap"""
    if not stock_df.empty and len(stock_df) > 30: 
        if not isinstance(stock_df.index, pd.DatetimeIndex):
            stock_df.index = pd.to_datetime(stock_df.index)
            
        stock_df['returns'] = stock_df['close'].pct_change()
        
        monthly_returns = stock_df['returns'].groupby([stock_df.index.year, stock_df.index.month]).mean() * 100
        
        years = sorted(set(stock_df.index.year))
        months = range(1, 13)
        
        heatmap_data = np.full((len(years), 12), np.nan)
        
        for i, year in enumerate(years):
            for j, month in enumerate(months):
                if (year, month) in monthly_returns.index:
                    heatmap_data[i, j] = monthly_returns[(year, month)]
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        cmap = plt.cm.RdYlGn
        
        im = ax.imshow(heatmap_data, cmap=cmap)
        
        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.ax.set_ylabel('Monthly Returns (%)', rotation=-90, va="bottom")
        
        ax.set_xticks(np.arange(len(months)))
        ax.set_yticks(np.arange(len(years)))
        ax.set_xticklabels(['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])
        ax.set_yticklabels(years)
        
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        ax.set_title(f"{symbol} Monthly Returns (%)")
        fig.tight_layout()
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, 'Not enough data for heatmap', 
                horizontalalignment='center', verticalalignment='center',
                transform=ax.transAxes, fontsize=14)
        ax.axis('off')
        return fig

def generate_stock_report_data(symbol, start_date, end_date, include_plots=None, sentiment_data=None):
    """
    Generate stock report data with selected visualizations.
    
    Args:
        symbol: Stock ticker symbol
        start_date: Start date for analysis
        end_date: End date for analysis
        include_plots: List of plot types to include
        sentiment_data: Optional sentiment analysis data
        
    Returns:
        Dictionary with report data
    """
    if include_plots is None:
        include_plots = ['line', 'volume', 'candlestick', 'volume_price', 'shareholders', 'heatmap']
    
    report_data = {
        'symbol': symbol,
        'start_date': start_date,
        'end_date': end_date,
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'stock_data': None,
        'plots': {},
        'internal_reports': None,
        'sentiment_data': sentiment_data,
        'errors': []
    }
    
    try:
        stock_df = get_stock_data(symbol, start_date, end_date)
        
        if stock_df is not None and not stock_df.empty:
            if not isinstance(stock_df.index, pd.DatetimeIndex):
                stock_df.index = pd.to_datetime(stock_df['date']) if 'date' in stock_df.columns else pd.to_datetime(stock_df.index)
            
            report_data['stock_data'] = {
                'latest_price': stock_df['close'].iloc[-1],
                'price_change': stock_df['close'].iloc[-1] - stock_df['close'].iloc[0],
                'price_change_pct': ((stock_df['close'].iloc[-1] / stock_df['close'].iloc[0]) - 1) * 100,
                'highest_price': stock_df['high'].max(),
                'lowest_price': stock_df['low'].min(),
                'avg_volume': stock_df['volume'].mean(),
                'summary_stats': stock_df.describe().to_dict()
            }
            
            if 'line' in include_plots:
                fig = create_line_chart(stock_df, symbol)
                report_data['plots']['line_chart'] = plot_to_image_bytes(fig)
                plt.close(fig)
            
            if 'volume' in include_plots:
                fig = create_volume_chart(stock_df, symbol)
                report_data['plots']['volume_chart'] = plot_to_image_bytes(fig)
                plt.close(fig)
                
            if 'candlestick' in include_plots:
                fig = create_candlestick_chart(stock_df, symbol)
                report_data['plots']['candlestick_chart'] = plot_to_image_bytes(fig)
                plt.close(fig)
                
            if 'volume_price' in include_plots:
                fig = create_volume_price_chart(stock_df, symbol)
                report_data['plots']['volume_price_chart'] = plot_to_image_bytes(fig)
                plt.close(fig)
                
            if 'shareholders' in include_plots:
                fig = create_mock_shareholders_chart(symbol)
                report_data['plots']['shareholders_chart'] = plot_to_image_bytes(fig)
                plt.close(fig)
                
            if 'heatmap' in include_plots:
                fig = create_monthly_returns_heatmap(stock_df, symbol)
                report_data['plots']['returns_heatmap'] = plot_to_image_bytes(fig)
                plt.close(fig)
        else:
            report_data['errors'].append(f"No stock data found for {symbol} in the specified date range")
            
    except Exception as e:
        logger.error(f"Error processing stock data for {symbol}: {str(e)}")
        report_data['errors'].append(f"Error processing stock data: {str(e)}")
    
    try:
        internal_reports, error = get_internal_reports(symbol)
        if internal_reports is not None and not error:
            report_data['internal_reports'] = internal_reports
        elif error:
            report_data['errors'].append(f"Error fetching internal reports: {error}")
    except Exception as e:
        logger.error(f"Error fetching internal reports for {symbol}: {str(e)}")
        report_data['errors'].append(f"Error fetching internal reports: {str(e)}")
    
    return report_data

def create_reportlab_pdf(report_data):
    """
    Generate a PDF report using ReportLab.
    
    Args:
        report_data: Dictionary with report data
        
    Returns:
        PDF content as bytes
    """
    buffer = io.BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    header1_style = ParagraphStyle(
        name='ReportHeader1',
        fontName='Helvetica-Bold',
        fontSize=16,
        spaceAfter=12
    )
    
    header2_style = ParagraphStyle(
        name='ReportHeader2',
        fontName='Helvetica-Bold',
        fontSize=14,
        spaceAfter=10
    )
    
    normal_style = styles['Normal']
    normal_style.spaceAfter = 8
    
    content = []
    
    title = Paragraph(f"Stock Analysis Report: {report_data['symbol']}", header1_style)
    content.append(title)
    content.append(Spacer(1, 12))
    
    report_date = Paragraph(f"Report generated on: {report_data['generated_at']}", normal_style)
    content.append(report_date)
    content.append(Paragraph(f"Analysis period: {report_data['start_date']} to {report_data['end_date']}", normal_style))
    content.append(Spacer(1, 12))
    
    if report_data.get('stock_data') is not None:
        stock_data = report_data['stock_data']
        content.append(Paragraph("Price Summary", header2_style))
        
        data = [
            ["Metric", "Value"],
            ["Latest Price", f"${stock_data['latest_price']:.2f}"],
            ["Price Change", f"${stock_data['price_change']:.2f}"],
            ["Percentage Change", f"{stock_data['price_change_pct']:.2f}%"],
            ["Highest Price", f"${stock_data['highest_price']:.2f}"],
            ["Lowest Price", f"${stock_data['lowest_price']:.2f}"],
            ["Average Volume", f"{stock_data['avg_volume']:.0f}"]
        ]
        
        table = Table(data, colWidths=[200, 200])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('BACKGROUND', (0, 1), (1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        content.append(table)
        content.append(Spacer(1, 24))
    
    if report_data.get('plots') is not None:
        content.append(Paragraph("Technical Analysis Charts", header2_style))
        content.append(Spacer(1, 12))
        
        for plot_name, plot_data in report_data['plots'].items():
            if plot_data is not None:
                plot_title = ' '.join(word.capitalize() for word in plot_name.replace('_chart', '').split('_'))
                content.append(Paragraph(plot_title, header2_style))
                
                img = Image(io.BytesIO(plot_data))
                img.drawHeight = 300
                img.drawWidth = 450
                content.append(img)
                content.append(Spacer(1, 24))
    
    if report_data.get('sentiment_data') is not None:
        content.append(Paragraph("Market Sentiment Analysis", header2_style))
        sentiment_data = report_data['sentiment_data']
        
        if 'sentiment_distribution' in sentiment_data:
            dist = sentiment_data['sentiment_distribution']
            data = [
                ["Sentiment", "Percentage"],
                ["Positive", f"{dist.get('positive', 0):.1f}%"],
                ["Neutral", f"{dist.get('neutral', 0):.1f}%"],
                ["Negative", f"{dist.get('negative', 0):.1f}%"]
            ]
            
            table = Table(data, colWidths=[200, 200])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (1, 0), 12),
                ('BACKGROUND', (0, 1), (1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            
            content.append(table)
            content.append(Spacer(1, 24))
    

    if report_data.get('internal_reports') is not None:
        content.append(Paragraph("Internal Analysis Reports", header2_style))
        internal_reports = report_data['internal_reports']
        
        if hasattr(internal_reports, 'iterrows'): 
            for _, report_row in internal_reports.iterrows():
                report = report_row.to_dict()
                content.append(Paragraph(report.get('title', 'Untitled Report'), header2_style))
                content.append(Paragraph(f"Author: {report.get('author', 'Unknown Author')}", normal_style))
                content.append(Paragraph(f"Date: {report.get('date', 'Unknown Date')}", normal_style))
                content.append(Paragraph(report.get('summary', 'No summary available.'), normal_style))
                content.append(Spacer(1, 12))
        elif isinstance(internal_reports, list):
            for report in internal_reports:
                content.append(Paragraph(report.get('title', 'Untitled Report'), header2_style))
                content.append(Paragraph(f"Author: {report.get('author', 'Unknown Author')}", normal_style))
                content.append(Paragraph(f"Date: {report.get('date', 'Unknown Date')}", normal_style))
                content.append(Paragraph(report.get('summary', 'No summary available.'), normal_style))
                content.append(Spacer(1, 12))
    
    if report_data.get('errors') is not None and len(report_data.get('errors', [])) > 0:
        content.append(Paragraph("Processing Errors", header2_style))
        for error in report_data['errors']:
            content.append(Paragraph(f"• {error}", normal_style))
        content.append(Spacer(1, 12))
    
    doc.build(content)
    buffer.seek(0)
    return buffer.getvalue()

def get_sentiment_analysis(symbol, start_date, end_date):
    import random
    
    positive = random.uniform(20, 60)
    negative = random.uniform(10, 40)
    neutral = 100 - positive - negative
    
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    daily_sentiment = []
    current_date = start
    
    while current_date <= end:
        sentiment_score = random.uniform(-1, 1)
        
        if sentiment_score > 0.3:
            overall = "positive"
        elif sentiment_score < -0.3:
            overall = "negative"
        else:
            overall = "neutral"
            
        daily_sentiment.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'sentiment_score': sentiment_score,
            'overall_sentiment': overall
        })
        
        current_date += timedelta(days=1)
    
    return {
        'sentiment_distribution': {
            'positive': positive,
            'neutral': neutral,
            'negative': negative,
            'total_count': random.randint(50, 500)
        },
        'daily_sentiment': daily_sentiment
    }

def get_stock_summary(symbol, start_date, end_date, interval='1D'):
    """
    Generate a summary of stock performance.
    
    Args:
        symbol: Stock ticker symbol
        start_date: Start date for analysis
        end_date: End date for analysis
        interval: Data interval
        
    Returns:
        Dictionary with summary data
    """
    stock_df = get_stock_data(symbol, start_date, end_date, interval)
    if stock_df is None or stock_df.empty:
        return None
    
    latest_price = stock_df['close'].iloc[-1]
    start_price = stock_df['close'].iloc[0]
    price_change = latest_price - start_price
    price_change_pct = (price_change / start_price) * 100
    
    stock_df['MA20'] = stock_df['close'].rolling(window=20).mean()
    stock_df['MA50'] = stock_df['close'].rolling(window=50).mean()
    
    if len(stock_df) >= 20:
        current_ma20 = stock_df['MA20'].iloc[-1]
        trend = "Tăng" if latest_price > current_ma20 else "Giảm"
    else:
        trend = "Không xác định (không đủ dữ liệu)"
    
    returns = stock_df['close'].pct_change().dropna()
    volatility = returns.std() * 100
    
    summary = {
        'symbol': symbol,
        'latest_price': latest_price,
        'price_change': price_change,
        'price_change_pct': price_change_pct,
        'highest_price': stock_df['high'].max(),
        'lowest_price': stock_df['low'].min(),
        'avg_volume': stock_df['volume'].mean(),
        'trend': trend,
        'volatility': volatility,
        'start_date': start_date,
        'end_date': end_date
    }
    
    return summary