/**
 * Các hàm tiện ích cho biểu đồ
 */

// Định dạng số thành chuỗi có dấu phân cách hàng nghìn
function formatNumber(number, decimals = 0) {
    return new Intl.NumberFormat('vi-VN', {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    }).format(number);
}

// Định dạng giá trị tiền tệ VND
function formatCurrency(number) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'currency',
        currency: 'VND',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(number);
}

// Định dạng phần trăm
function formatPercent(number) {
    return new Intl.NumberFormat('vi-VN', {
        style: 'percent',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(number);
}

// Định dạng ngày tháng
function formatDate(dateString) {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('vi-VN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
    }).format(date);
}

// Lấy màu dựa trên giá trị (dùng cho biểu đồ nhiệt)
function getHeatmapColor(value) {
    if (value > 0.05) return 'rgb(0, 128, 0)';     // Xanh lá đậm (tăng mạnh)
    if (value > 0.02) return 'rgb(144, 238, 144)'; // Xanh lá nhạt (tăng)
    if (value > -0.02) return 'rgb(255, 255, 224)'; // Vàng nhạt (đi ngang)
    if (value > -0.05) return 'rgb(255, 182, 193)'; // Hồng nhạt (giảm)
    return 'rgb(255, 0, 0)';                       // Đỏ (giảm mạnh)
}

// Lấy màu cho nến dựa trên giá mở cửa và đóng cửa
function getCandleColor(open, close) {
    return close >= open ? 'rgb(0, 150, 136)' : 'rgb(255, 82, 82)';
}

// Lấy màu cho khối lượng dựa trên giá mở cửa và đóng cửa
function getVolumeColor(open, close) {
    return close >= open ? 'rgba(0, 150, 136, 0.8)' : 'rgba(255, 82, 82, 0.8)';
}

// Tạo tooltip tùy chỉnh cho biểu đồ
function createTooltip(id) {
    const tooltip = document.createElement('div');
    tooltip.className = 'lightweight-charts-tooltip';
    tooltip.id = id;
    tooltip.style.position = 'absolute';
    tooltip.style.display = 'none';
    tooltip.style.padding = '8px';
    tooltip.style.boxShadow = '0 2px 5px rgba(0, 0, 0, 0.2)';
    tooltip.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
    tooltip.style.color = '#333';
    tooltip.style.borderRadius = '4px';
    tooltip.style.fontSize = '12px';
    tooltip.style.pointerEvents = 'none';
    tooltip.style.zIndex = '1000';
    tooltip.style.whiteSpace = 'nowrap';
    document.body.appendChild(tooltip);
    return tooltip;
}

// Cập nhật vị trí tooltip
function updateTooltipPosition(tooltip, x, y) {
    tooltip.style.left = `${x + 15}px`;
    tooltip.style.top = `${y + 15}px`;
}

// Hiển thị tooltip
function showTooltip(tooltip) {
    tooltip.style.display = 'block';
}

// Ẩn tooltip
function hideTooltip(tooltip) {
    tooltip.style.display = 'none';
}

// Lấy dữ liệu cổ phiếu từ API
async function fetchStockData(endpoint, params = {}) {
    try {
        const url = new URL(`/api/${endpoint}`, window.location.origin);
        
        // Thêm các tham số vào URL
        Object.keys(params).forEach(key => {
            if (params[key] !== null && params[key] !== undefined) {
                url.searchParams.append(key, params[key]);
            }
        });
        
        const response = await fetch(url.toString());
        
        if (!response.ok) {
            throw new Error(`Lỗi HTTP: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error);
        }
        
        return data;
    } catch (error) {
        console.error(`Lỗi khi lấy dữ liệu từ API ${endpoint}:`, error);
        throw error;
    }
}

// Hiển thị thông báo lỗi
function showError(containerId, message) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = `
        <div class="chart-error">
            <i class="fas fa-exclamation-circle"></i>
            <p>${message}</p>
        </div>
    `;
}

// Hiển thị loading
function showLoading(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = `
        <div class="chart-loading">
            <div class="spinner"></div>
            <p>Đang tải dữ liệu...</p>
        </div>
    `;
}

// Thêm CSS cho biểu đồ
function addChartStyles() {
    if (document.getElementById('chart-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'chart-styles';
    style.textContent = `
        .chart-container {
            position: relative;
            height: 100%;
            width: 100%;
        }
        
        .chart-error {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: #e74c3c;
            text-align: center;
            padding: 20px;
        }
        
        .chart-error i {
            font-size: 32px;
            margin-bottom: 10px;
        }
        
        .chart-loading {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            text-align: center;
            padding: 20px;
        }
        
        .spinner {
            border: 4px solid rgba(0, 0, 0, 0.1);
            border-radius: 50%;
            border-top: 4px solid #3498db;
            width: 30px;
            height: 30px;
            animation: spin 1s linear infinite;
            margin-bottom: 10px;
        }
        
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        
        .lightweight-charts-tooltip {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.5;
        }
        
        .chart-controls {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        
        .chart-controls .btn-group {
            display: flex;
        }
        
        .chart-legend {
            display: flex;
            flex-wrap: wrap;
            font-size: 12px;
            padding: 5px;
            background-color: rgba(255, 255, 255, 0.7);
            border-radius: 4px;
            position: absolute;
            top: 5px;
            left: 5px;
            z-index: 100;
        }
        
        .legend-item {
            display: flex;
            align-items: center;
            margin-right: 10px;
        }
        
        .legend-color {
            width: 10px;
            height: 10px;
            margin-right: 5px;
            border-radius: 50%;
        }
    `;
    
    document.head.appendChild(style);
}

// Khởi tạo các styles khi trang được tải
document.addEventListener('DOMContentLoaded', addChartStyles);
