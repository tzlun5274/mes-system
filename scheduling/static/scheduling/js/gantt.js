// dhtmlxGantt v7.1.12 初始化與互動升級

// 設定日期格式
gantt.config.date_format = "%Y-%m-%d %H:%i";

// 設定時間軸
gantt.config.scales = [
  {unit: "day", step: 1, format: "%Y-%m-%d"},
  {unit: "hour", step: 1, format: "%H:%i"}
];

// 設定欄位
gantt.config.columns = [
  {name: "text", label: "任務", width: "*", tree: true},
  {name: "start_date", label: "開始", align: "center", width: 100},
  {name: "end_date", label: "結束", align: "center", width: 100},
  {name: "add", label: "", width: 44}
];

// 基本設定
gantt.config.order_branch = true;
gantt.config.order_branch_free = true;
gantt.config.drag_move = true;
gantt.config.drag_resize = true;
gantt.config.drag_links = true;
gantt.config.fit_tasks = true;

// 初始化甘特圖
gantt.init("gantt_here");

// 多層級檢視切換
function setScale(unit) {
  if(unit === 'day') {
    gantt.config.scales = [
      {unit: "day", step: 1, format: "%Y-%m-%d"},
      {unit: "hour", step: 1, format: "%H:%i"}
    ];
  } else if(unit === 'week') {
    gantt.config.scales = [
      {unit: "week", step: 1, format: "第%W週"},
      {unit: "day", step: 1, format: "%m-%d"}
    ];
  } else if(unit === 'month') {
    gantt.config.scales = [
      {unit: "month", step: 1, format: "%Y-%m"},
      {unit: "week", step: 1, format: "第%W週"}
    ];
  }
  gantt.render();
}

// 可加在頁面上自訂切換按鈕
// setScale('day'); setScale('week'); setScale('month');

// 載入資料
fetch('/scheduling/api/schedule/')
  .then(res => res.json())
  .then(data => gantt.parse({data: data.tasks, links: data.links}))
  .catch(error => {
    console.error('載入資料失敗:', error);
    document.getElementById('gantt-warning').textContent = '載入資料失敗，請檢查網路連線';
    document.getElementById('gantt-warning').classList.remove('d-none');
  });

// 任務更新事件
gantt.attachEvent("onAfterTaskUpdate", function(id, item){
  fetch('/scheduling/api/schedule/manual/', {
    method: 'POST',
    body: JSON.stringify(item),
    headers: {'Content-Type': 'application/json'}
  }).then(res => res.json()).then(resp => {
    if(resp.status !== 'success'){
      alert(resp.message);
      gantt.refreshData();
    }
  });
});

// 連結新增事件
gantt.attachEvent("onAfterLinkAdd", function(id, item){
  fetch('/scheduling/api/schedule/links/', {
    method: 'POST',
    body: JSON.stringify(item),
    headers: {'Content-Type': 'application/json'}
  });
});

// 即時資源衝突/超載警示（可根據後端回傳或本地驗證擴充） 

// dhtmlxGantt v7.1.12 介面繁體中文化
// 只保留 Save、Cancel、Delete 為英文，其餘全部中文
gantt.i18n = {
  date: {
    month_full: ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"],
    month_short: ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"],
    day_full: ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"],
    day_short: ["日", "一", "二", "三", "四", "五", "六"]
  },
  labels: {
    new_task: "新任務",
    dhx_cal_today_button: "今天",
    day_tab: "日",
    week_tab: "週",
    month_tab: "月",
    save_button: "Save",
    cancel_button: "Cancel", 
    delete_button: "Delete",
    confirm_closing: "您的更改將會遺失，確定關閉嗎？",
    confirm_deleting: "確定要刪除嗎？",
    invalid_date: "未定義或日期格式錯誤，請重新輸入！",
    invalid_link: "連結設定錯誤，請檢查！",
    undefined: "未定義或資料錯誤！",
    section_description: "描述",
    section_time: "時間區間",
    section_type: "類型",
    column_text: "任務",
    column_start_date: "開始",
    column_end_date: "結束",
    confirm_recurring: "您想要將任務設為重複嗎？",
    section_recurrence: "重複週期",
    section_priority: "優先順序",
    message_ok: "確定",
    message_cancel: "取消",
    minutes: "分鐘",
    hours: "小時",
    days: "天",
    time_period: "時間區間",
    delete_task: "刪除任務",
    save_task: "儲存任務",
    cancel: "取消",
    close: "關閉",
    time: "時間區間",
    description: "描述"
  }
};

// 設定語言
gantt.i18n.setLocale("zh");

// 自訂 lightbox 欄位標題（全部中文）
gantt.config.lightbox.sections = [
  {name: "description", height: 38, map_to: "text", type: "textarea", focus: true, title: "描述"},
  {name: "time", type: "time", map_to: "auto", title: "時間區間"}
];

// 自動將 lightbox 月份下拉選單轉為繁體中文
gantt.attachEvent("onLightbox", function() {
  setTimeout(function() {
    document.querySelectorAll(".gantt_cal_ltext select[name='month']").forEach(function(sel) {
      var monthNames = ["一月", "二月", "三月", "四月", "五月", "六月", "七月", "八月", "九月", "十月", "十一月", "十二月"];
      for (var i = 0; i < sel.options.length; i++) {
        sel.options[i].text = monthNames[i];
      }
    });
  }, 10);
}); 