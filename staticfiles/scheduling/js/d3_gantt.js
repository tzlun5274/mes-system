// d3_gantt.js - D3.js 甘特圖主程式（全部繁體中文說明）

// 建立 tooltip
const tooltip = document.createElement('div');
tooltip.className = 'd3-gantt-tooltip';
document.body.appendChild(tooltip);

// 載入 MES 排程資料
fetch('/scheduling/api/schedule/')
  .then(res => res.json())
  .then(data => {
    // 轉換資料格式
    const tasks = (data.tasks || []).map(item => ({
      id: item.id || item.pk || item.task_id || Math.random().toString(36).slice(2,10),
      name: item.text || item.name || '未命名',
      start: new Date(item.start_date || item.start),
      end: new Date(item.end_date || item.end),
      progress: item.progress || 0,
      status: item.status || ''
    }));
    drawGantt(tasks);
  })
  .catch(() => {
    document.getElementById('gantt-warning').textContent = '載入資料失敗，請檢查網路連線';
    document.getElementById('gantt-warning').classList.remove('d-none');
  });

function drawGantt(tasks) {
  // 設定寬高與邊界
  const margin = {top: 40, right: 40, bottom: 40, left: 160};
  const width = document.getElementById('gantt-d3').clientWidth - margin.left - margin.right;
  const height = Math.max(tasks.length * 40, 300);

  // 計算時間範圍
  const minDate = d3.min(tasks, d => d.start);
  const maxDate = d3.max(tasks, d => d.end);

  // 建立 SVG
  d3.select('#gantt-d3').selectAll('*').remove();
  const svg = d3.select('#gantt-d3')
    .append('svg')
    .attr('width', width + margin.left + margin.right)
    .attr('height', height + margin.top + margin.bottom);

  // X 軸（時間）
  const x = d3.scaleTime()
    .domain([minDate, maxDate])
    .range([0, width]);

  // Y 軸（任務）
  const y = d3.scaleBand()
    .domain(tasks.map(d => d.name))
    .range([0, height])
    .padding(0.2);

  // 畫 X 軸
  svg.append('g')
    .attr('class', 'd3-gantt-axis')
    .attr('transform', `translate(${margin.left},${margin.top})`)
    .call(d3.axisTop(x).ticks(10).tickFormat(d => {
      // 日期格式：2025年6月27日
      const dt = new Date(d);
      return `${dt.getFullYear()}年${dt.getMonth()+1}月${dt.getDate()}日`;
    }));

  // 畫 Y 軸
  svg.append('g')
    .attr('class', 'd3-gantt-axis')
    .attr('transform', `translate(${margin.left},${margin.top})`)
    .call(d3.axisLeft(y));

  // 畫任務條
  svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)
    .selectAll('.d3-gantt-bar')
    .data(tasks)
    .enter()
    .append('rect')
    .attr('class', 'd3-gantt-bar')
    .attr('x', d => x(d.start))
    .attr('y', d => y(d.name))
    .attr('width', d => x(d.end) - x(d.start))
    .attr('height', y.bandwidth())
    .on('mouseover', function(event, d) {
      tooltip.style.display = 'block';
      tooltip.innerHTML = `<b>任務：</b>${d.name}<br><b>開始：</b>${formatDate(d.start)}<br><b>結束：</b>${formatDate(d.end)}<br><b>進度：</b>${d.progress}%`;
      d3.select(this).attr('opacity', 1);
    })
    .on('mousemove', function(event) {
      tooltip.style.left = (event.pageX + 15) + 'px';
      tooltip.style.top = (event.pageY - 20) + 'px';
    })
    .on('mouseout', function() {
      tooltip.style.display = 'none';
      d3.select(this).attr('opacity', 0.85);
    });

  // 在條上顯示進度百分比
  svg.append('g')
    .attr('transform', `translate(${margin.left},${margin.top})`)
    .selectAll('.d3-gantt-label')
    .data(tasks)
    .enter()
    .append('text')
    .attr('class', 'd3-gantt-label')
    .attr('x', d => x(d.start) + 8)
    .attr('y', d => y(d.name) + y.bandwidth()/2 + 5)
    .text(d => d.progress ? `${d.progress}%` : '')
    .attr('fill', '#fff');
}

function formatDate(date) {
  if (!date) return '';
  const d = new Date(date);
  return `${d.getFullYear()}年${d.getMonth()+1}月${d.getDate()}日`;
} 