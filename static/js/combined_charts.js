/**
 * Các hàm tạo biểu đồ kết hợp sử dụng TradingView lightweight-charts
 */

// Tạo biểu đồ kết hợp (Combined Chart) - Nến và Khối lượng
function createCombinedChart(containerId, candleData, volumeData, options = {}) {
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
        height: container.clientHeight || 500,
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
                bottom: 0.3, // Để lại không gian cho biểu đồ khối lượng
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

    // Thêm dữ liệu nến
    candlestickSeries.setData(candleData);

    // Tạo series histogram cho khối lượng với trục giá riêng
    const volumeSeries = chart.addHistogramSeries({
        color: 'rgba(76, 175, 80, 0.5)',
        priceFormat: {
            type: 'volume',
        },
        priceScaleId: 'volume',
        scaleMargins: {
            top: 0.8, // Đặt ở phần dưới của biểu đồ
            bottom: 0,
        },
        ...options.volumeOptions
    });

    // Thêm dữ liệu khối lượng
    volumeSeries.setData(volumeData);

    // Tạo tooltip
    const toolTipId = `tooltip-${containerId}`;
    const tooltip = createTooltip(toolTipId);

    // Tạo legend
    const legendContainer = document.createElement('div');
    legendContainer.className = 'chart-legend';
    legendContainer.innerHTML = `
        <div class="legend-item">
            <div class="legend-color" style="background-color: rgb(0, 150, 136);"></div>
            <span>Tăng</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: rgb(255, 82, 82);"></div>
            <span>Giảm</span>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background-color: rgba(76, 175, 80, 0.5);"></div>
            <span>Khối lượng</span>
        </div>
    `;
    chartContainer.appendChild(legendContainer);

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
            const candleData = param.seriesData.get(candlestickSeries);
            const volumeData = param.seriesData.get(volumeSeries);
            
            if (candleData) {
                const dateStr = formatDate(new Date(param.time * 1000).toISOString().split('T')[0]);
                let tooltipContent = `
                    <div>Ngày: <strong>${dateStr}</strong></div>
                    <div>Mở: <strong>${formatNumber(candleData.open, 2)}</strong></div>
                    <div>Cao: <strong>${formatNumber(candleData.high, 2)}</strong></div>
                    <div>Thấp: <strong>${formatNumber(candleData.low, 2)}</strong></div>
                    <div>Đóng: <strong>${formatNumber(candleData.close, 2)}</strong></div>
                `;
                
                if (volumeData) {
                    tooltipContent += `<div>Khối lượng: <strong>${formatNumber(volumeData.value, 0)}</strong></div>`;
                }
                
                tooltip.innerHTML = tooltipContent;
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
        candleSeries: candlestickSeries,
        volumeSeries: volumeSeries,
        cleanup: () => {
            chart.unsubscribeCrosshairMove();
            resizeObserver.disconnect();
            document.body.removeChild(tooltip);
        }
    };
}

// Tải dữ liệu và tạo biểu đồ kết hợp
async function loadCombinedChart(containerId, symbol, startDate = null, endDate = null) {
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
        if (!data || !data.candle || data.candle.length === 0) {
            showError(containerId, `Không có dữ liệu cho cổ phiếu ${symbol}`);
            return null;
        }

        // Tạo biểu đồ kết hợp
        return createCombinedChart(containerId, data.candle, data.volume);
    } catch (error) {
        console.error('Lỗi khi tải dữ liệu biểu đồ kết hợp:', error);
        showError(containerId, `Lỗi khi tải dữ liệu: ${error.message}`);
        return null;
    }
}

// Khởi tạo biểu đồ kết hợp với các nút điều khiển
function initCombinedChartWithControls(containerId, symbol, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Không tìm thấy container với id ${containerId}`);
        return;
    }

    // Tạo các nút điều khiển
    const controlsContainer = document.createElement('div');
    controlsContainer.className = 'chart-controls';
    controlsContainer.innerHTML = `
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
    chartDiv.style.height = options.height || '500px';
    
    // Thêm vào container
    container.appendChild(controlsContainer);
    container.appendChild(chartDiv);
    
    // Khởi tạo biểu đồ
    let timeRange = '1y';
    let chartObj = null;
    
    // Tải biểu đồ ban đầu
    loadCombinedChart(chartDiv.id, symbol, calculateStartDate(timeRange))
        .then(obj => {
            chartObj = obj;
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
            
            if (chartObj) {
                // Dọn dẹp biểu đồ cũ
                chartObj.cleanup();
            }
            
            // Tạo biểu đồ mới với khoảng thời gian mới
            chartObj = await loadCombinedChart(
                chartDiv.id, 
                symbol, 
                calculateStartDate(timeRange)
            );
        });
    });
    
    return {
        updateSymbol: async (newSymbol) => {
            symbol = newSymbol;
            
            if (chartObj) {
                // Dọn dẹp biểu đồ cũ
                chartObj.cleanup();
            }
            
            // Tạo biểu đồ mới với symbol mới
            chartObj = await loadCombinedChart(
                chartDiv.id, 
                symbol, 
                calculateStartDate(timeRange)
            );
        }
    };
}
