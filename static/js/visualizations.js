// Tệp JavaScript cho các thành phần trực quan hóa dữ liệu
// Được sử dụng bởi các template để hiển thị biểu đồ và trực quan hóa

document.addEventListener('DOMContentLoaded', function() {
    // Khởi tạo tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });

    // Tạo biểu đồ phân phối cảm xúc nếu có phần tử canvas
    const sentimentDistributionChart = document.getElementById('sentimentDistributionChart');
    if (sentimentDistributionChart) {
        const sentimentData = JSON.parse(sentimentDistributionChart.getAttribute('data-sentiment'));
        
        new Chart(sentimentDistributionChart, {
            type: 'doughnut',
            data: {
                labels: ['Tích cực', 'Trung lập', 'Tiêu cực'],
                datasets: [{
                    data: [
                        sentimentData.positive, 
                        sentimentData.neutral, 
                        sentimentData.negative
                    ],
                    backgroundColor: [
                        '#27ae60', // Tích cực - xanh lá
                        '#f39c12', // Trung lập - vàng
                        '#e74c3c'  // Tiêu cực - đỏ
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'bottom',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                return `${label}: ${value}%`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Tạo biểu đồ xu hướng cảm xúc theo thời gian nếu có phần tử canvas
    const sentimentTrendChart = document.getElementById('sentimentTrendChart');
    if (sentimentTrendChart) {
        const chartData = JSON.parse(sentimentTrendChart.getAttribute('data-trend'));
        
        new Chart(sentimentTrendChart, {
            type: 'line',
            data: {
                labels: chartData.dates,
                datasets: [{
                    label: 'Điểm Cảm Xúc',
                    data: chartData.scores,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: false,
                        suggestedMin: -1,
                        suggestedMax: 1,
                        ticks: {
                            callback: function(value) {
                                if (value === 1) return 'Tích cực';
                                if (value === 0) return 'Trung lập';
                                if (value === -1) return 'Tiêu cực';
                                return '';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const score = context.raw;
                                let sentiment = 'Trung lập';
                                if (score > 0.3) sentiment = 'Tích cực';
                                if (score < -0.3) sentiment = 'Tiêu cực';
                                return `Cảm xúc: ${sentiment} (${score.toFixed(2)})`;
                            }
                        }
                    }
                }
            }
        });
    }

    // Tạo biểu đồ nguồn tin nếu có phần tử canvas
    const sourceStatsChart = document.getElementById('sourceStatsChart');
    if (sourceStatsChart) {
        const sourceData = JSON.parse(sourceStatsChart.getAttribute('data-sources'));
        const sources = Object.keys(sourceData);
        const counts = sources.map(source => sourceData[source]);
        
        new Chart(sourceStatsChart, {
            type: 'bar',
            data: {
                labels: sources.map(source => {
                    if (source === 'cafef') return 'CafeF';
                    if (source === 'vnexpress') return 'VnExpress';
                    if (source === 'tinnhanhchungkhoan') return 'TNCK';
                    return source;
                }),
                datasets: [{
                    label: 'Số lượng bài báo',
                    data: counts,
                    backgroundColor: [
                        '#3498db',
                        '#2ecc71',
                        '#e74c3c',
                        '#f39c12',
                        '#9b59b6'
                    ],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    // Hiệu ứng hiển thị cho các phần tử khi cuộn trang
    const animateOnScroll = function() {
        const elements = document.querySelectorAll('.animate-on-scroll');
        
        elements.forEach(element => {
            const elementPosition = element.getBoundingClientRect().top;
            const windowHeight = window.innerHeight;
            
            if (elementPosition < windowHeight - 50) {
                element.classList.add('animated');
            }
        });
    };

    // Thêm lớp animate-on-scroll cho các phần tử cần hiệu ứng
    document.querySelectorAll('.card, .daily-summary').forEach(element => {
        element.classList.add('animate-on-scroll');
    });

    // Gọi hàm animateOnScroll khi trang tải và khi cuộn
    window.addEventListener('scroll', animateOnScroll);
    animateOnScroll(); // Gọi ngay khi trang tải

    // Xử lý sự kiện khi người dùng thay đổi khoảng thời gian
    const dateRangeSelector = document.getElementById('dateRangeSelector');
    if (dateRangeSelector) {
        dateRangeSelector.addEventListener('change', function() {
            const ticker = this.getAttribute('data-ticker');
            const days = this.value;
            window.location.href = `/analyze?ticker=${ticker}&days=${days}`;
        });
    }

    // Tạo hiệu ứng loading khi chuyển trang
    const searchForm = document.querySelector('form[action="/analyze"]');
    if (searchForm) {
        searchForm.addEventListener('submit', function() {
            document.body.classList.add('loading');
        });
    }
});

// Thêm CSS cho hiệu ứng animation
document.head.insertAdjacentHTML('beforeend', `
<style>
    .animate-on-scroll {
        opacity: 0;
        transform: translateY(20px);
        transition: opacity 0.5s ease, transform 0.5s ease;
    }
    
    .animate-on-scroll.animated {
        opacity: 1;
        transform: translateY(0);
    }
    
    body.loading::after {
        content: '';
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(255, 255, 255, 0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 9999;
    }
    
    body.loading::before {
        content: '';
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 50px;
        height: 50px;
        border: 5px solid #f3f3f3;
        border-top: 5px solid #3498db;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        z-index: 10000;
    }
</style>
`);
