/**
 * Các hàm tạo biểu đồ nhiệt sử dụng D3.js
 */

// Tạo biểu đồ nhiệt (Heatmap)
function createHeatmapChart(containerId, data, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) {
        console.error(`Không tìm thấy container với id ${containerId}`);
        return null;
    }

    // Xóa nội dung cũ
    container.innerHTML = '';

    // Kiểm tra dữ liệu
    if (!data || !data.heatmap || data.heatmap.length === 0) {
        showError(containerId, 'Không có dữ liệu cho biểu đồ nhiệt');
        return null;
    }

    // Lấy danh sách các năm và tháng
    const years = data.years || [];
    const months = data.months || [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
    const monthNames = data.month_names || [
        'Tháng 1', 'Tháng 2', 'Tháng 3', 'Tháng 4', 'Tháng 5', 'Tháng 6',
        'Tháng 7', 'Tháng 8', 'Tháng 9', 'Tháng 10', 'Tháng 11', 'Tháng 12'
    ];

    // Kích thước và margin
    const margin = { top: 50, right: 25, bottom: 30, left: 50 };
    const width = container.clientWidth - margin.left - margin.right;
    const height = Math.max(300, years.length * 30) - margin.top - margin.bottom;

    // Tạo SVG container
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width + margin.left + margin.right)
        .attr('height', height + margin.top + margin.bottom)
        .append('g')
        .attr('transform', `translate(${margin.left},${margin.top})`);

    // Tạo scales
    const x = d3.scaleBand()
        .domain(months)
        .range([0, width])
        .padding(0.05);

    const y = d3.scaleBand()
        .domain(years)
        .range([0, height])
        .padding(0.05);

    // Tạo color scale
    const colorScale = d3.scaleSequential()
        .interpolator(d3.interpolateRdYlGn)
        .domain([-0.1, 0.1]); // Từ -10% đến 10%

    // Thêm tiêu đề
    if (options.title) {
        svg.append('text')
            .attr('x', width / 2)
            .attr('y', -margin.top / 2)
            .attr('text-anchor', 'middle')
            .style('font-size', '16px')
            .style('font-weight', 'bold')
            .style('font-family', "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif")
            .text(options.title);
    }

    // Thêm trục x (tháng)
    svg.append('g')
        .style('font-size', '12px')
        .style('font-family', "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif")
        .attr('transform', `translate(0,${height})`)
        .call(d3.axisBottom(x).tickFormat(d => monthNames[d-1].substring(0, 3)))
        .select('.domain').remove();

    // Thêm trục y (năm)
    svg.append('g')
        .style('font-size', '12px')
        .style('font-family', "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif")
        .call(d3.axisLeft(y))
        .select('.domain').remove();

    // Tạo tooltip
    const tooltip = d3.select('body')
        .append('div')
        .style('position', 'absolute')
        .style('display', 'none')
        .style('background-color', 'rgba(255, 255, 255, 0.95)')
        .style('border', '1px solid #ddd')
        .style('padding', '8px')
        .style('border-radius', '4px')
        .style('font-size', '12px')
        .style('font-family', "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif")
        .style('pointer-events', 'none')
        .style('z-index', '1000');

    // Thêm các ô nhiệt
    svg.selectAll()
        .data(data.heatmap)
        .enter()
        .append('rect')
        .attr('x', d => x(d.x))
        .attr('y', d => y(d.y))
        .attr('width', x.bandwidth())
        .attr('height', y.bandwidth())
        .style('fill', d => colorScale(d.value))
        .style('stroke', 'white')
        .style('stroke-width', 1)
        .on('mouseover', function(event, d) {
            d3.select(this)
                .style('stroke', 'black')
                .style('stroke-width', 2);
            
            tooltip.style('display', 'block')
                .html(`
                    <div>Năm: <strong>${d.y}</strong></div>
                    <div>Tháng: <strong>${monthNames[d.x-1]}</strong></div>
                    <div>Lợi nhuận: <strong>${d.formattedValue}</strong></div>
                `);
        })
        .on('mousemove', function(event) {
            tooltip.style('left', (event.pageX + 15) + 'px')
                .style('top', (event.pageY + 15) + 'px');
        })
        .on('mouseout', function() {
            d3.select(this)
                .style('stroke', 'white')
                .style('stroke-width', 1);
            
            tooltip.style('display', 'none');
        });

    // Thêm giá trị vào các ô
    svg.selectAll()
        .data(data.heatmap)
        .enter()
        .append('text')
        .attr('x', d => x(d.x) + x.bandwidth() / 2)
        .attr('y', d => y(d.y) + y.bandwidth() / 2)
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'middle')
        .style('font-size', '10px')
        .style('font-family', "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif")
        .style('fill', d => Math.abs(d.value) > 0.05 ? 'white' : 'black')
        .text(d => d.formattedValue);

    // Thêm chú thích màu
    const legendWidth = 200;
    const legendHeight = 20;
    
    const legendX = d3.scaleLinear()
        .domain([-0.1, 0.1])
        .range([0, legendWidth]);
    
    const legendXAxis = d3.axisBottom(legendX)
        .tickFormat(d => formatPercent(d));
    
    const legend = svg.append('g')
        .attr('transform', `translate(${(width - legendWidth) / 2},${height + margin.bottom - 5})`);
    
    // Gradient cho legend
    const defs = svg.append('defs');
    const linearGradient = defs.append('linearGradient')
        .attr('id', 'linear-gradient');
    
    linearGradient.selectAll('stop')
        .data([
            {offset: '0%', color: colorScale(-0.1)},
            {offset: '50%', color: colorScale(0)},
            {offset: '100%', color: colorScale(0.1)}
        ])
        .enter().append('stop')
        .attr('offset', d => d.offset)
        .attr('stop-color', d => d.color);
    
    legend.append('rect')
        .attr('width', legendWidth)
        .attr('height', legendHeight)
        .style('fill', 'url(#linear-gradient)');
    
    legend.append('g')
        .attr('transform', `translate(0,${legendHeight})`)
        .call(legendXAxis);
    
    // Xử lý sự kiện resize
    const resizeFunction = () => {
        const newWidth = container.clientWidth - margin.left - margin.right;
        svg.attr('width', newWidth + margin.left + margin.right);
        x.range([0, newWidth]);
        
        // Cập nhật vị trí của các phần tử
        svg.selectAll('rect')
            .attr('x', d => x(d.x))
            .attr('width', x.bandwidth());
        
        svg.selectAll('text')
            .filter((d, i, nodes) => d && d.x) // Chỉ cập nhật text trong các ô
            .attr('x', d => x(d.x) + x.bandwidth() / 2);
        
        // Cập nhật trục x
        svg.select('.x-axis')
            .call(d3.axisBottom(x).tickFormat(d => monthNames[d-1].substring(0, 3)));
        
        // Cập nhật legend
        legend.attr('transform', `translate(${(newWidth - legendWidth) / 2},${height + margin.bottom - 5})`);
    };
    
    const resizeObserver = new ResizeObserver(() => {
        resizeFunction();
    });
    
    resizeObserver.observe(container);

    // Trả về đối tượng để có thể cập nhật sau này
    return {
        svg,
        cleanup: () => {
            resizeObserver.disconnect();
            tooltip.remove();
        }
    };
}

// Tải dữ liệu và tạo biểu đồ nhiệt cho lợi nhuận hàng tháng
async function loadMonthlyReturnsHeatmap(containerId, symbol, startDate = null, endDate = null) {
    try {
        // Hiển thị loading
        showLoading(containerId);

        // Nếu không có ngày bắt đầu, lấy 5 năm trước
        if (!startDate) {
            const date = new Date();
            date.setFullYear(date.getFullYear() - 5);
            startDate = date.toISOString().split('T')[0];
        }

        // Lấy dữ liệu từ API
        const data = await fetchStockData('stock/monthly_returns', {
            symbol,
            start_date: startDate,
            end_date: endDate
        });

        // Kiểm tra dữ liệu
        if (!data || !data.heatmap || data.heatmap.length === 0) {
            showError(containerId, `Không có dữ liệu lợi nhuận hàng tháng cho cổ phiếu ${symbol}`);
            return null;
        }

        // Tạo biểu đồ nhiệt
        return createHeatmapChart(containerId, data, {
            title: `Lợi nhuận hàng tháng ${symbol}`
        });
    } catch (error) {
        console.error('Lỗi khi tải dữ liệu biểu đồ lợi nhuận hàng tháng:', error);
        showError(containerId, `Lỗi khi tải dữ liệu: ${error.message}`);
        return null;
    }
}

// Khởi tạo biểu đồ nhiệt lợi nhuận hàng tháng
function initMonthlyReturnsHeatmap(containerId, symbol, options = {}) {
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
    loadMonthlyReturnsHeatmap(chartDiv.id, symbol)
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
            chartObj = await loadMonthlyReturnsHeatmap(chartDiv.id, symbol);
        }
    };
}
