// frappe_gantt_init.js
// 用於初始化 Frappe Gantt，介面全部繁體中文
// 載入 MES 排程資料並顯示在甘特圖

// 取得資料（可根據實際 API 調整）
fetch('/scheduling/api/schedule/')
  .then(res => res.json())
  .then(data => {
    // 將資料轉換成 Frappe Gantt 格式
    var tasks = (data.tasks || []).map(function(item) {
      return {
        id: item.id || item.pk || item.task_id || Math.random().toString(36).slice(2,10),
        name: item.text || item.name || '未命名',
        start: item.start_date || item.start || '',
        end: item.end_date || item.end || '',
        progress: item.progress || 0,
        custom_class: item.status ? 'status-' + item.status : ''
      };
    });
    // 初始化 Frappe Gantt
    var gantt = new Gantt("#gantt", tasks, {
      language: 'zh', // 月份自動繁體中文
      view_mode: 'Day',
      custom_popup_html: function(task) {
        // 自訂彈窗內容（全部繁體中文）
        return `
          <div class="details-container">
            <h5>任務名稱：${task.name}</h5>
            <p>開始：${task.start}</p>
            <p>結束：${task.end}</p>
            <p>進度：${task.progress}%</p>
          </div>
        `;
      }
    });
  })
  .catch(function(error) {
    document.getElementById('gantt-warning').textContent = '載入資料失敗，請檢查網路連線';
    document.getElementById('gantt-warning').classList.remove('d-none');
  });

// 若要自訂顏色，可在 frappe-gantt.css 加上 .status-xxx 樣式 