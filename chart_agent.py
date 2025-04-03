import matplotlib.pyplot as plt
from vnstock import Vnstock



def plot_line_charts(state: State):
    """Plots line charts for all stock symbols."""
    symbol_data_list = state.get("symbol_data_list", [])
    
    if not symbol_data_list:
        return {"errors": ["No stock data available to plot"]}
    
    chart_paths = []
    errors = []
    
    for symbol_data in symbol_data_list:
        parts = symbol_data.split('|')
        if len(parts) != 4:
            errors.append(f"Error: Invalid input format for {symbol_data}")
            continue
        
        symbol, start_date, end_date, interval = parts
        
        try:
            df = get_stock_data(symbol_data)
            
            if df.empty:
                errors.append(f"No data available for symbol: {symbol}")
                continue
                
            plt.figure(figsize=(10, 5))
            plt.plot(df['time'], df['close'], label=symbol, color='b')
            plt.title(f'Line Chart - {symbol}')
            plt.xlabel('Date')
            plt.ylabel('Close Price')
            plt.legend()
            plt.grid()
            
            chart_path = f"{symbol}_line_chart.png"
            plt.savefig(chart_path)
            plt.close()
            
            chart_paths.append(chart_path)
            
        except Exception as e:
            errors.append(f"Error generating chart for {symbol}: {str(e)}")
    
    return {"chart_paths": chart_paths, "errors": errors}

def get_stock_data(symbol_and_dates):
    """Fetches historical stock data."""
    parts = symbol_and_dates.split('|')
    if len(parts) != 4:
        raise ValueError("Invalid input format. Expected 'symbol|start_date|end_date|interval'")
    
    symbol, start_date, end_date, interval = parts
    
    try:
        stock = Vnstock().stock(symbol=symbol, source="VCI")
        df = stock.quote.history(start=start_date, end=end_date, interval=interval)
        return df
    except Exception as e:
        import pandas as pd
        return pd.DataFrame()