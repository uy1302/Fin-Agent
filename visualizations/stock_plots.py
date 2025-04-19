import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import pandas as pd
import seaborn as sns
import base64
from io import BytesIO
from vnstock import Vnstock

def get_stock_data(symbol, start_date, end_date, interval='1D'):
    """Fetches historical stock data."""
    try:
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        df = stock.quote.history(start=start_date, end=end_date, interval=interval)
        return df
    except Exception as e:
        print(f"Error fetching stock data: {str(e)}")
        return None

def plot_volume_chart(symbol, start_date, end_date, interval='1D', save_path=None):
    """Plots the volume chart for a given stock symbol."""
    df = get_stock_data(symbol, start_date, end_date, interval)
    if df is None or df.empty:
        return None, "Không thể lấy dữ liệu cổ phiếu"
    
    plt.figure(figsize=(10, 5))
    plt.bar(df['time'], df['volume'], color='g', alpha=0.7)
    plt.title(f'Biểu đồ khối lượng giao dịch - {symbol}')
    plt.xlabel('Ngày')
    plt.ylabel('Khối lượng')
    plt.grid(alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
        return save_path, None
    else:
        img = BytesIO()
        plt.savefig(img, format='png')
        plt.close()
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf-8')
        return plot_url, None

def plot_line_chart(symbol, start_date, end_date, interval='1D', save_path=None):
    """Plots the line chart for a given stock symbol."""
    df = get_stock_data(symbol, start_date, end_date, interval)
    if df is None or df.empty:
        return None, "Không thể lấy dữ liệu cổ phiếu"
    
    plt.figure(figsize=(10, 5))
    plt.plot(df['time'], df['close'], label=symbol, color='b')
    plt.title(f'Biểu đồ giá đóng cửa - {symbol}')
    plt.xlabel('Ngày')
    plt.ylabel('Giá đóng cửa')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
        return save_path, None
    else:
        img = BytesIO()
        plt.savefig(img, format='png')
        plt.close()
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf-8')
        return plot_url, None

def plot_candlestick(symbol, start_date, end_date, interval='1D', save_path=None):
    """Plots the candlestick chart for a given stock symbol using matplotlib."""
    df = get_stock_data(symbol, start_date, end_date, interval)
    if df is None or df.empty:
        return None, "Không thể lấy dữ liệu cổ phiếu"
    
    df['time'] = pd.to_datetime(df['time'])
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    width = 0.6
    width2 = 0.1
    
    up_color = 'green'
    down_color = 'red'
    
    for i, (idx, row) in enumerate(df.iterrows()):
        if row['close'] >= row['open']:
            color = up_color
            bottom = row['open']
            height = row['close'] - row['open']
        else:
            color = down_color
            bottom = row['close']
            height = row['open'] - row['close']
        
        rect = plt.Rectangle((i-width/2, bottom), width, height, 
                             fill=True, color=color, alpha=0.8)
        ax.add_patch(rect)
        
        plt.plot([i, i], [row['low'], row['high']], color='black', alpha=0.7)
    
    plt.xticks(range(0, len(df)), [d.strftime('%Y-%m-%d') for d in df['time']], rotation=45)
    plt.xlim(-1, len(df))
    
    plt.title(f'Biểu đồ nến - {symbol}')
    plt.xlabel('Ngày')
    plt.ylabel('Giá')
    plt.grid(alpha=0.3)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
        return save_path, None
    else:
        img = BytesIO()
        plt.savefig(img, format='png')
        plt.close()
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf-8')
        return plot_url, None

def plot_volume_and_closed_price(symbol, start_date, end_date, interval='1D', save_path=None):
    """Plots a combo chart with volume as bars and close price as a line using matplotlib."""
    df = get_stock_data(symbol, start_date, end_date, interval)
    if df is None or df.empty:
        return None, "Không thể lấy dữ liệu cổ phiếu"
    
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    ax1.bar(df['time'], df['volume'], color='blue', alpha=0.5, label='Khối lượng')
    ax1.set_xlabel('Ngày')
    ax1.set_ylabel('Khối lượng giao dịch', color='blue')
    ax1.tick_params(axis='y', labelcolor='blue')
    
    ax2 = ax1.twinx()
    ax2.plot(df['time'], df['close'], color='red', linewidth=2, label='Giá đóng cửa')
    ax2.set_ylabel('Giá đóng cửa', color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    
    plt.title(f'Giá đóng cửa và khối lượng giao dịch - {symbol}')
    plt.xticks(rotation=45)
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
    
    plt.grid(alpha=0.3)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path)
        plt.close()
        return save_path, None
    else:
        img = BytesIO()
        plt.savefig(img, format='png')
        plt.close()
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode('utf-8')
        return plot_url, None

def plot_shareholders_piechart(symbol, save_path=None):
    """Plots a pie chart of shareholders for a given stock symbol."""
    try:
        company = Vnstock().stock(symbol=symbol, source="VCI").company
        shareholders_df = company.shareholders()
        
        if shareholders_df is None or shareholders_df.empty:
            return None, "Không thể lấy dữ liệu cổ đông"
        
        threshold = 0.03  
        
        total_quantity = shareholders_df['quantity'].sum()
        shareholders_df['share_own_percent'] = shareholders_df['quantity'] / total_quantity
        
        major_shareholders = shareholders_df[shareholders_df['share_own_percent'] >= threshold].copy()
        
        other_share = shareholders_df[shareholders_df['share_own_percent'] < threshold]['quantity'].sum()
        
        if other_share > 0 and not major_shareholders.empty:
            other_row = pd.DataFrame({'share_holder': ['Khác'], 'quantity': [other_share]})
            major_shareholders = pd.concat([major_shareholders, other_row], ignore_index=True)
        elif major_shareholders.empty:
            major_shareholders = shareholders_df.copy()
        
        major_shareholders['share_own_percent'] = (major_shareholders['quantity'] / major_shareholders['quantity'].sum()) * 100
        
        fig, ax = plt.subplots(figsize=(10, 6))
        explode = [0.1 if label == 'Khác' else 0 for label in major_shareholders['share_holder']]
        
        ax.pie(
            major_shareholders['share_own_percent'],
            labels=major_shareholders['share_holder'],
            autopct='%1.1f%%',
            colors=plt.cm.Paired.colors,
            startangle=140,
            pctdistance=0.8,
            labeldistance=1.1,
            explode=explode
        )
        
        ax.set_title(f"Cổ đông lớn {symbol}")
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
            return save_path, None
        else:
            img = BytesIO()
            plt.savefig(img, format='png')
            plt.close()
            img.seek(0)
            plot_url = base64.b64encode(img.getvalue()).decode('utf-8')
            return plot_url, None
    except Exception as e:
        return None, f"Lỗi khi tạo biểu đồ cổ đông: {str(e)}"

def plot_monthly_returns_heatmap(symbol, start_date, end_date, interval='1D', save_path=None):
    """Creates a heatmap of monthly average returns for a given stock symbol."""
    df = get_stock_data(symbol, start_date, end_date, interval)
    if df is None or df.empty:
        return None, "Không thể lấy dữ liệu cổ phiếu"
    
    try:
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        df['returns'] = df['close'].pct_change() * 100
        
        return_pivot = pd.pivot_table(
            df, 
            index=df.index.year, 
            columns=df.index.month, 
            values='returns', 
            aggfunc='mean'
        )
        
        month_names = {
            1: 'Tháng 1', 2: 'Tháng 2', 3: 'Tháng 3', 4: 'Tháng 4',
            5: 'Tháng 5', 6: 'Tháng 6', 7: 'Tháng 7', 8: 'Tháng 8',
            9: 'Tháng 9', 10: 'Tháng 10', 11: 'Tháng 11', 12: 'Tháng 12'
        }
        return_pivot.columns = [month_names.get(col, col) for col in return_pivot.columns]
        
        plt.figure(figsize=(12, 8))
        
        sns.heatmap(
            return_pivot, 
            annot=True, 
            cmap='RdYlGn', 
            center=0, 
            fmt='.2f'
        )
        
        plt.title(f'Lợi nhuận trung bình hàng tháng - {symbol} ({start_date} đến {end_date})', fontsize=15)
        plt.xlabel('Tháng', fontsize=12)
        plt.ylabel('Năm', fontsize=12)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path)
            plt.close()
            return save_path, None
        else:
            img = BytesIO()
            plt.savefig(img, format='png')
            plt.close()
            img.seek(0)
            plot_url = base64.b64encode(img.getvalue()).decode('utf-8')
            return plot_url, None
    except Exception as e:
        return None, f"Lỗi khi tạo biểu đồ heatmap: {str(e)}"

def get_internal_reports(symbol):
    """Fetches internal reports for a given stock symbol."""
    try:
        from vnstock.explorer.vci import Company
        company = Company(symbol)
        data_report = company.reports()
        return data_report, None
    except Exception as e:
        return None, f"Lỗi khi lấy báo cáo nội bộ: {str(e)}"
