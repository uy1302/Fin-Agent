/**
 * Các hàm tạo biểu đồ tròn sử dụng Chart.js
 */

// Tạo biểu đồ tròn (Pie Chart)
function createPieChart(containerId, data, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Không tìm thấy container với id ${containerId}`);
        return null;
    }

    // Xóa nội dung cũ
    container.innerHTML = '';

    // Tạo canvas cho biểu đồ
    const canvas = document.createElement('canvas');
    canvas.id = `${containerId}-canvas`;
    container.appendChild(canvas);

    // Chuẩn bị dữ liệu
    const labels = data.map(item => item.category);
    const values = data.map(item => item.value);

    // Tạo màu ngẫu nhiên cho các phần
    const colors = [
        'rgba(54, 162, 235, 0.8)',
        'rgba(255, 99, 132, 0.8)',
        'rgba(255, 206, 86, 0.8)',
        'rgba(75, 192, 192, 0.8)',
        'rgba(153, 102, 255, 0.8)',
        'rgba(255, 159, 64, 0.8)',
        'rgba(199, 199, 199, 0.8)',
        'rgba(83, 102, 255, 0.8)',
        'rgba(40, 159, 64, 0.8)',
        'rgba(210, 199, 199, 0.8)',
    ];

    // Tạo biểu đồ tròn
    const chart = new Chart(canvas, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, values.length),
                borderColor: colors.slice(0, values.length).map(color => color.replace('0.8', '1')),
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        font: {
                            family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                            size: 12
                        },
                        color: '#333'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            return `${label}: ${value}%`;
                        }
                    }
                },
                title: {
                    display: options.title ? true : false,
                    text: options.title || '',
                    font: {
                        family: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
                        size: 16,
                        weight: 'bold'
                    },
                    color: '#333',
                    padding: {
                        top: 10,
                        bottom: 10
                    }
                }
            },
            ...options.chartOptions
        }
    });

    // Xử lý sự kiện resize
    const resizeObserver = new ResizeObserver(entries => {
        if (entries.length === 0 || entries[0].target !== container) {
            return;
        }
        chart.resize();
    });

    resizeObserver.observe(container);

    // Trả về đối tượng biểu đồ để có thể cập nhật sau này
    return {
        chart,
        cleanup: () => {
            resizeObserver.disconnect();
            chart.destroy();
        }
    };
}

// Tải dữ liệu và tạo biểu đồ tròn cho cơ cấu cổ đông
async function loadShareholdersPieChart(containerId, symbol, options = {}) {
    try {
        // Hiển thị loading
        showLoading(containerId);

        // Lấy dữ liệu từ API
        const data = await fetchStockData('stock/shareholders', {
            symbol
        });

        // Kiểm tra dữ liệu
        if (!data || !data.shareholders || data.shareholders.length === 0) {
            showError(containerId, `Không có dữ liệu cổ đông cho cổ phiếu ${symbol}`);
            return null;
        }

        // Tạo biểu đồ tròn
        return createPieChart(containerId, data.shareholders, {
            title: `Cơ cấu cổ đông ${symbol}`,
            ...options
        });
    } catch (error) {
        console.error('Lỗi khi tải dữ liệu biểu đồ cổ đông:', error);
        showError(containerId, `Lỗi khi tải dữ liệu: ${error.message}`);
        return null;
    }
}

// Khởi tạo biểu đồ tròn cổ đông
function initShareholdersPieChart(containerId, symbol, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Không tìm thấy container với id ${containerId}`);
        return;
    }
    
    // Tạo container cho biểu đồ
    const chartDiv = document.createElement('div');
    chartDiv.id = `${containerId}-chart`;
    chartDiv.style.height = options.height || '400px';
    
    // Thêm vào container
    container.appendChild(chartDiv);
    
    // Khởi tạo biểu đồ
    let chartObj = null;
    
    // Tải biểu đồ ban đầu
    loadShareholdersPieChart(chartDiv.id, symbol)
        .then(obj => {
            chartObj = obj;
        });
    
    return {
        updateSymbol: async (newSymbol) => {
            symbol = newSymbol;
            
            if (chartObj) {
                // Dọn dẹp biểu đồ cũ
                chartObj.cleanup();
            }
            
            // Tạo biểu đồ mới với symbol mới
            chartObj = await loadShareholdersPieChart(chartDiv.id, symbol);
        }
    };
}
