/**
 * Các hàm tạo biểu đồ cổ phiếu sử dụng TradingView lightweight-charts
 */

// Tạo biểu đồ đường (Line Chart)
function createLineChart(containerId, data, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Không tìm thấy container với id ${containerId}`);
        return null;
    }

    // Xóa nội dung cũ
    container.innerHTML = '';

    // Tạo div cho biểu đồ
    const chartContainer = document.createElement('div');
    chartContainer.className = 'chart-container';
    container.appendChild(chartContainer);

    // Tạo biểu đồ
    const chart = LightweightCharts.createChart(chartContainer, {
        width: container.clientWidth,
        height: container.clientHeight || 400,
        layout: {
            background: { type: 'solid', color: 'white' },
            textColor: '#333',
            fontSize: 12,
            fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        },
        grid: {
            vertLines: { color: 'rgba(197, 203, 206, 0.5)' },
            horzLines: { color: 'rgba(197, 203, 206, 0.5)' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
            vertLine: {
                width: 1,
                color: 'rgba(32, 38, 46, 0.1)',
                style: LightweightCharts.LineStyle.Dashed,
            },
            horzLine: {
                width: 1,
                color: 'rgba(32, 38, 46, 0.1)',
                style: LightweightCharts.LineStyle.Dashed,
            },
        },
        timeScale: {
            borderColor: 'rgba(197, 203, 206, 0.8)',
            timeVisible: true,
            secondsVisible: false,
            tickMarkFormatter: (time) => {
                const date = new Date(time * 1000);
                return date.getDate().toString().padStart(2, '0') + '/' + 
                       (date.getMonth() + 1).toString().padStart(2, '0');
            },
        },
        rightPriceScale: {
            borderColor: 'rgba(197, 203, 206, 0.8)',
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
        },
        handleScroll: { mouseWheel: true, pressedMouseMove: true },
        handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
        ...options
    });

    // Tạo series đường
    const lineSeries = chart.addLineSeries({
        color: '#2962FF',
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
        crosshairMarkerBorderColor: '#2962FF',
        crosshairMarkerBackgroundColor: 'white',
        lastValueVisible: true,
        priceLineVisible: true,
        priceLineWidth: 1,
        priceLineColor: '#2962FF',
        priceLineStyle: LightweightCharts.LineStyle.Dashed,
        ...options.lineOptions
    });

    // Thêm dữ liệu
    lineSeries.setData(data);

    // Tạo tooltip
    const toolTipId = `tooltip-${containerId}`;
    const tooltip = createTooltip(toolTipId);

    // Xử lý sự kiện crosshair move
    chart.subscribeCrosshairMove((param) => {
        if (
            param.point === undefined ||
            !param.time ||
            param.point.x < 0 ||
            param.point.x > container.clientWidth ||
            param.point.y < 0 ||
            param.point.y > container.clientHeight
        ) {
            hideTooltip(tooltip);
        } else {
            const data = param.seriesData.get(lineSeries);
            if (data) {
                const dateStr = formatDate(new Date(param.time * 1000).toISOString().split('T')[0]);
                const price = formatNumber(data.value, 2);
                tooltip.innerHTML = `
                    <div>Ngày: <strong>${dateStr}</strong></div>
                    <div>Giá: <strong>${price}</strong></div>
                `;
                showTooltip(tooltip);
                updateTooltipPosition(tooltip, param.point.x, param.point.y);
            } else {
                hideTooltip(tooltip);
            }
        }
    });

    // Xử lý sự kiện resize
    const resizeObserver = new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) {
            return;
        }
        const newRect = entries[0].contentRect;
        chart.applyOptions({ width: newRect.width, height: newRect.height });
    });

    resizeObserver.observe(container);

    // Trả về đối tượng biểu đồ và series để có thể cập nhật sau này
    return {
        chart,
        series: lineSeries,
        cleanup: () => {
            chart.unsubscribeCrosshairMove();
            resizeObserver.disconnect();
            document.body.removeChild(tooltip);
        }
    };
}

// Tạo biểu đồ nến (Candlestick Chart)
function createCandlestickChart(containerId, data, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Không tìm thấy container với id ${containerId}`);
        return null;
    }

    // Xóa nội dung cũ
    container.innerHTML = '';

    // Tạo div cho biểu đồ
    const chartContainer = document.createElement('div');
    chartContainer.className = 'chart-container';
    container.appendChild(chartContainer);

    // Tạo biểu đồ
    const chart = LightweightCharts.createChart(chartContainer, {
        width: container.clientWidth,
        height: container.clientHeight || 400,
        layout: {
            background: { type: 'solid', color: 'white' },
            textColor: '#333',
            fontSize: 12,
            fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
        },
        grid: {
            vertLines: { color: 'rgba(197, 203, 206, 0.5)' },
            horzLines: { color: 'rgba(197, 203, 206, 0.5)' },
        },
        crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
        },
        timeScale: {
            borderColor: 'rgba(197, 203, 206, 0.8)',
            timeVisible: true,
            secondsVisible: false,
            tickMarkFormatter: (time) => {
                const date = new Date(time * 1000);
                return date.getDate().toString().padStart(2, '0') + '/' + 
                       (date.getMonth() + 1).toString().padStart(2, '0');
            },
        },
        rightPriceScale: {
            borderColor: 'rgba(197, 203, 206, 0.8)',
            scaleMargins: {
                top: 0.1,
                bottom: 0.1,
            },
        },
        handleScroll: { mouseWheel: true, pressedMouseMove: true },
        handleScale: { mouseWheel: true, pinch: true, axisPressedMouseMove: true },
        ...options
    });

    // Tạo series nến
    const candlestickSeries = chart.addCandlestickSeries({
        upColor: 'rgb(0, 150, 136)',
        downColor: 'rgb(255, 82, 82)',
        borderVisible: false,
        wickUpColor: 'rgb(0, 150, 136)',
        wickDownColor: 'rgb(255, 82, 82)',
        ...options.candlestickOptions
    });

    // Thêm dữ liệu
    candlestickSeries.setData(data);

    // Tạo tooltip
    const toolTipId = `tooltip-${containerId}`;
    const tooltip = createTooltip(toolTipId);

    // Xử lý sự kiện crosshair move
    chart.subscribeCrosshairMove((param) => {
        if (
            param.point === undefined ||
            !param.time ||
            param.point.x < 0 ||
            param.point.x > container.clientWidth ||
            param.point.y < 0 ||
            param.point.y > container.clientHeight
        ) {
            hideTooltip(tooltip);
        } else {
            const data = param.seriesData.get(candlestickSeries);
            if (data) {
                const dateStr = formatDate(new Date(param.time * 1000).toISOString().split('T')[0]);
                tooltip.innerHTML = `
                    <div>Ngày: <strong>${dateStr}</strong></div>
                    <div>Mở: <strong>${formatNumber(data.open, 2)}</strong></div>
                    <div>Cao: <strong>${formatNumber(data.high, 2)}</strong></div>
                    <div>Thấp: <strong>${formatNumber(data.low, 2)}</strong></div>
                    <div>Đóng: <strong>${formatNumber(data.close, 2)}</strong></div>
                `;
                showTooltip(tooltip);
                updateTooltipPosition(tooltip, param.point.x, param.point.y);
            } else {
                hideTooltip(tooltip);
            }
        }
    });

    // Xử lý sự kiện resize
    const resizeObserver = new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) {
            return;
        }
        const newRect = entries[0].contentRect;
        chart.applyOptions({ width: newRect.width, height: newRect.height });
    });

    resizeObserver.observe(container);

    // Trả về đối tượng biểu đồ và series để có thể cập nhật sau này
    return {
        chart,
        series: candlestickSeries,
        cleanup: () => {
            chart.unsubscribeCrosshairMove();
            resizeObserver.disconnect();
            document.body.removeChild(tooltip);
        }
    };
}

// Tải dữ liệu và tạo biểu đồ cổ phiếu
async function loadStockChart(containerId, symbol, chartType = 'line', startDate = null, endDate = null) {
    try {
        // Hiển thị loading
        showLoading(containerId);

        // Nếu không có ngày bắt đầu, lấy 1 năm trước
        if (!startDate) {
            const date = new Date();
            date.setFullYear(date.getFullYear() - 1);
            startDate = date.toISOString().split('T')[0];
        }

        // Lấy dữ liệu từ API
        const data = await fetchStockData('stock/history', {
            symbol,
            start_date: startDate,
            end_date: endDate
        });

        // Kiểm tra dữ liệu
        if (!data || (data.line && data.line.length === 0)) {
            showError(containerId, `Không có dữ liệu cho cổ phiếu ${symbol}`);
            return null;
        }

        // Tạo biểu đồ dựa trên loại
        let chartObj = null;
        switch (chartType) {
            case 'line':
                chartObj = createLineChart(containerId, data.line);
                break;
            case 'candle':
                chartObj = createCandlestickChart(containerId, data.candle);
                break;
            default:
                chartObj = createLineChart(containerId, data.line);
        }

        return chartObj;
    } catch (error) {
        console.error('Lỗi khi tải dữ liệu biểu đồ:', error);
        showError(containerId, `Lỗi khi tải dữ liệu: ${error.message}`);
        return null;
    }
}

// Cập nhật loại biểu đồ
async function updateChartType(chartObj, containerId, symbol, newChartType, startDate = null, endDate = null) {
    if (chartObj) {
        // Dọn dẹp biểu đồ cũ
        chartObj.cleanup();
    }

    // Tạo biểu đồ mới
    return await loadStockChart(containerId, symbol, newChartType, startDate, endDate);
}

// Cập nhật khoảng thời gian
async function updateTimeRange(chartObj, containerId, symbol, chartType, newStartDate, newEndDate = null) {
    if (chartObj) {
        // Dọn dẹp biểu đồ cũ
        chartObj.cleanup();
    }

    // Tạo biểu đồ mới với khoảng thời gian mới
    return await loadStockChart(containerId, symbol, chartType, newStartDate, newEndDate);
}

// Tính toán ngày bắt đầu dựa trên khoảng thời gian
function calculateStartDate(range) {
    const date = new Date();
    
    switch (range) {
        case '1m':
            date.setMonth(date.getMonth() - 1);
            break;
        case '3m':
            date.setMonth(date.getMonth() - 3);
            break;
        case '6m':
            date.setMonth(date.getMonth() - 6);
            break;
        case '1y':
            date.setFullYear(date.getFullYear() - 1);
            break;
        case '3y':
            date.setFullYear(date.getFullYear() - 3);
            break;
        case '5y':
            date.setFullYear(date.getFullYear() - 5);
            break;
        case 'all':
            date.setFullYear(date.getFullYear() - 20); // Giả sử "tất cả" là 20 năm
            break;
        default:
            date.setFullYear(date.getFullYear() - 1); // Mặc định 1 năm
    }
    
    return date.toISOString().split('T')[0];
}

// Khởi tạo biểu đồ với các nút điều khiển
function initStockChartWithControls(containerId, symbol, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Không tìm thấy container với id ${containerId}`);
        return;
    }

    // Tạo các nút điều khiển
    const controlsContainer = document.createElement('div');
    controlsContainer.className = 'chart-controls';
    controlsContainer.innerHTML = `
        <div class="btn-group chart-type-controls">
            <button class="btn btn-sm btn-outline-primary chart-type-btn active" data-type="line">Đường</button>
            <button class="btn btn-sm btn-outline-primary chart-type-btn" data-type="candle">Nến</button>
        </div>
        <div class="btn-group time-range-controls">
            <button class="btn btn-sm btn-outline-secondary time-range-btn" data-range="1m">1T</button>
            <button class="btn btn-sm btn-outline-secondary time-range-btn" data-range="3m">3T</button>
            <button class="btn btn-sm btn-outline-secondary time-range-btn active" data-range="1y">1N</button>
            <button class="btn btn-sm btn-outline-secondary time-range-btn" data-range="3y">3N</button>
            <button class="btn btn-sm btn-outline-secondary time-range-btn" data-range="all">Tất cả</button>
        </div>
    `;
    
    // Tạo container cho biểu đồ
    const chartDiv = document.createElement('div');
    chartDiv.id = `${containerId}-chart`;
    chartDiv.style.height = options.height || '400px';
    
    // Thêm vào container
    container.appendChild(controlsContainer);
    container.appendChild(chartDiv);
    
    // Khởi tạo biểu đồ
    let chartType = 'line';
    let timeRange = '1y';
    let chartObj = null;
    
    // Tải biểu đồ ban đầu
    loadStockChart(chartDiv.id, symbol, chartType, calculateStartDate(timeRange))
        .then(obj => {
            chartObj = obj;
        });
    
    // Xử lý sự kiện khi click vào nút loại biểu đồ
    const chartTypeBtns = controlsContainer.querySelectorAll('.chart-type-btn');
    chartTypeBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            // Cập nhật trạng thái active
            chartTypeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Cập nhật biểu đồ
            chartType = btn.dataset.type;
            chartObj = await updateChartType(
                chartObj, 
                chartDiv.id, 
                symbol, 
                chartType, 
                calculateStartDate(timeRange)
            );
        });
    });
    
    // Xử lý sự kiện khi click vào nút khoảng thời gian
    const timeRangeBtns = controlsContainer.querySelectorAll('.time-range-btn');
    timeRangeBtns.forEach(btn => {
        btn.addEventListener('click', async () => {
            // Cập nhật trạng thái active
            timeRangeBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Cập nhật biểu đồ
            timeRange = btn.dataset.range;
            chartObj = await updateTimeRange(
                chartObj, 
                chartDiv.id, 
                symbol, 
                chartType, 
                calculateStartDate(timeRange)
            );
        });
    });
    
    return {
        updateSymbol: async (newSymbol) => {
            symbol = newSymbol;
            chartObj = await updateTimeRange(
                chartObj, 
                chartDiv.id, 
                symbol, 
                chartType, 
                calculateStartDate(timeRange)
            );
        }
    };
}
