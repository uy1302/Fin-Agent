/**
 * Các hàm tạo biểu đồ khối lượng sử dụng TradingView lightweight-charts
 */

// Tạo biểu đồ khối lượng (Volume Chart)
function createVolumeChart(containerId, data, options = {}) {
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
        height: container.clientHeight || 300,
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

    // Tạo series histogram cho khối lượng
    const volumeSeries = chart.addHistogramSeries({
        color: 'rgba(76, 175, 80, 0.5)',
        priceFormat: {
            type: 'volume',
        },
        priceScaleId: '',
        scaleMargins: {
            top: 0.1,
            bottom: 0.1,
        },
        ...options.volumeOptions
    });

    // Thêm dữ liệu
    volumeSeries.setData(data);

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
            const data = param.seriesData.get(volumeSeries);
            if (data) {
                const dateStr = formatDate(new Date(param.time * 1000).toISOString().split('T')[0]);
                const volume = formatNumber(data.value, 0);
                tooltip.innerHTML = `
                    <div>Ngày: <strong>${dateStr}</strong></div>
                    <div>Khối lượng: <strong>${volume}</strong></div>
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
        series: volumeSeries,
        cleanup: () => {
            chart.unsubscribeCrosshairMove();
            resizeObserver.disconnect();
            document.body.removeChild(tooltip);
        }
    };
}

// Tải dữ liệu và tạo biểu đồ khối lượng
async function loadVolumeChart(containerId, symbol, startDate = null, endDate = null) {
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
        if (!data || (data.volume && data.volume.length === 0)) {
            showError(containerId, `Không có dữ liệu khối lượng cho cổ phiếu ${symbol}`);
            return null;
        }

        // Tạo biểu đồ khối lượng
        return createVolumeChart(containerId, data.volume);
    } catch (error) {
        console.error('Lỗi khi tải dữ liệu biểu đồ khối lượng:', error);
        showError(containerId, `Lỗi khi tải dữ liệu: ${error.message}`);
        return null;
    }
}

// Khởi tạo biểu đồ khối lượng với các nút điều khiển
function initVolumeChartWithControls(containerId, symbol, options = {}) {
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
    chartDiv.style.height = options.height || '300px';
    
    // Thêm vào container
    container.appendChild(controlsContainer);
    container.appendChild(chartDiv);
    
    // Khởi tạo biểu đồ
    let timeRange = '1y';
    let chartObj = null;
    
    // Tải biểu đồ ban đầu
    loadVolumeChart(chartDiv.id, symbol, calculateStartDate(timeRange))
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
            chartObj = await loadVolumeChart(
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
            chartObj = await loadVolumeChart(
                chartDiv.id, 
                symbol, 
                calculateStartDate(timeRange)
            );
        }
    };
}
