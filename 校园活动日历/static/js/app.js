/**
 * 校园活动日历系统 - Vue 3 前端应用
 * 使用CDN方式引入Vue 3，通过组合式API管理状态
 */
const { createApp, ref, computed, onMounted, watch, nextTick } = Vue;

const API_BASE = '/api';

const app = createApp({
    setup() {
        // ==================== 响应式状态 ====================
        const currentTime = ref('');
        const isDark = ref(false);
        const loading = ref(false);
        const submitting = ref(false);

        // 当前年月
        const now = new Date();
        const currentYear = ref(now.getFullYear());
        const currentMonth = ref(now.getMonth() + 1);
        const monthPicker = ref(`${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}`);

        // 分类数据
        const categories = ref([]);
        const selectedCategories = ref([]);

        // 活动数据
        const monthSummary = ref({});
        const selectedDate = ref(null);
        const detailActivities = ref([]);
        const detailPagination = ref({ page: 1, page_size: 10, total: 0, total_pages: 1 });
        const keyword = ref('');
        const quickFilter = ref('all');

        // 倒计时数据
        const countdowns = ref({});
        let countdownTimer = null;

        // 模态框
        const showAddModal = ref(false);
        const showEditModal = ref(false);
        const editingId = ref(null);
        const form = ref({
            title: '', description: '', category_id: '',
            location: '', start_time: '', end_time: '', publisher: ''
        });

        // 饼图实例
        let chartInstance = null;

        // 星期标题
        const weekdays = ['日', '一', '二', '三', '四', '五', '六'];

        // ==================== 日历网格计算 ====================
        const calendarCells = computed(() => {
            const year = currentYear.value;
            const month = currentMonth.value;
            const cells = [];

            // 该月第一天是星期几（0=周日）
            const firstDay = new Date(year, month - 1, 1).getDay();
            // 该月总天数
            const daysInMonth = new Date(year, month, 0).getDate();
            // 上月总天数
            const daysInPrevMonth = new Date(year, month - 1, 0).getDate();

            const today = new Date();
            const todayStr = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;

            // 填充上月日期
            for (let i = firstDay - 1; i >= 0; i--) {
                const day = daysInPrevMonth - i;
                const m = month === 1 ? 12 : month - 1;
                const y = month === 1 ? year - 1 : year;
                cells.push({
                    day,
                    dateStr: `${y}-${String(m).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
                    isCurrentMonth: false,
                    isToday: false,
                    hasActivity: false,
                    activityCount: 0,
                    activityColors: [],
                });
            }

            // 填充当月日期
            for (let day = 1; day <= daysInMonth; day++) {
                const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const summary = monthSummary.value[day];
                cells.push({
                    day,
                    dateStr,
                    isCurrentMonth: true,
                    isToday: dateStr === todayStr,
                    hasActivity: summary ? summary.count > 0 : false,
                    activityCount: summary ? summary.count : 0,
                    activityColors: summary ? summary.categories : [],
                });
            }

            // 填充下月日期至42格
            const remaining = 42 - cells.length;
            for (let day = 1; day <= remaining; day++) {
                const m = month === 12 ? 1 : month + 1;
                const y = month === 12 ? year + 1 : year;
                cells.push({
                    day,
                    dateStr: `${y}-${String(m).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
                    isCurrentMonth: false,
                    isToday: false,
                    hasActivity: false,
                    activityCount: 0,
                    activityColors: [],
                });
            }

            return cells;
        });

        // ==================== API请求封装 ====================
        async function request(url, options = {}) {
            try {
                const res = await fetch(`${API_BASE}${url}`, {
                    headers: { 'Content-Type': 'application/json' },
                    ...options,
                });
                const json = await res.json();
                if (json.code !== 200) {
                    alert(json.msg || '请求失败');
                    return null;
                }
                return json.data;
            } catch (err) {
                console.error('请求错误:', err);
                alert('网络请求失败，请检查后端服务');
                return null;
            }
        }

        // ==================== 加载分类 ====================
        async function loadCategories() {
            const data = await request('/categories');
            if (data) {
                categories.value = data;
            }
        }

        // ==================== 加载月度活动概览 ====================
        async function loadMonthSummary() {
            const data = await request(`/activities/month?year=${currentYear.value}&month=${currentMonth.value}`);
            if (data) {
                monthSummary.value = data.day_summary || {};
                updateChart();
            }
        }

        // ==================== 加载活动列表 ====================
        async function loadActivities(page = 1) {
            loading.value = true;
            let url = `/activities?page=${page}&page_size=10`;

            // 分类筛选
            if (selectedCategories.value.length === 1) {
                url += `&category_id=${selectedCategories.value[0]}`;
            }

            // 关键词
            if (keyword.value.trim()) {
                url += `&keyword=${encodeURIComponent(keyword.value.trim())}`;
            }

            // 日期范围：当月
            const sd = `${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}-01`;
            const nextMonth = currentMonth.value === 12 ? 1 : currentMonth.value + 1;
            const nextYear = currentMonth.value === 12 ? currentYear.value + 1 : currentYear.value;
            const ed = `${nextYear}-${String(nextMonth).padStart(2, '0')}-01`;
            url += `&start_date=${sd}&end_date=${ed}`;

            const data = await request(url);
            loading.value = false;
            if (data) {
                detailActivities.value = data.items || [];
                detailPagination.value = {
                    page: data.page,
                    page_size: data.page_size,
                    total: data.total,
                    total_pages: data.total_pages,
                };
                loadCountdowns();
            }
        }

        // ==================== 加载单日活动 ====================
        async function loadDateActivities(page = 1) {
            if (!selectedDate.value) return;
            loading.value = true;
            const data = await request(`/activities/date?date=${selectedDate.value}&page=${page}&page_size=10`);
            loading.value = false;
            if (data) {
                detailActivities.value = data.items || [];
                detailPagination.value = {
                    page: data.page,
                    page_size: data.page_size,
                    total: data.total,
                    total_pages: data.total_pages,
                };
                loadCountdowns();
            }
        }

        // ==================== 选择日期 ====================
        function selectDate(cell) {
            if (!cell.isCurrentMonth) return;
            selectedDate.value = cell.dateStr;
            loadDateActivities(1);
        }

        // ==================== 月份切换 ====================
        function prevMonth() {
            if (currentMonth.value === 1) {
                currentMonth.value = 12;
                currentYear.value--;
            } else {
                currentMonth.value--;
            }
            monthPicker.value = `${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}`;
            selectedDate.value = null;
            detailActivities.value = [];
            loadMonthSummary();
            loadActivities();
        }

        function nextMonth() {
            if (currentMonth.value === 12) {
                currentMonth.value = 1;
                currentYear.value++;
            } else {
                currentMonth.value++;
            }
            monthPicker.value = `${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}`;
            selectedDate.value = null;
            detailActivities.value = [];
            loadMonthSummary();
            loadActivities();
        }

        function onMonthChange() {
            const [y, m] = monthPicker.value.split('-');
            currentYear.value = parseInt(y);
            currentMonth.value = parseInt(m);
            selectedDate.value = null;
            detailActivities.value = [];
            loadMonthSummary();
            loadActivities();
        }

        // ==================== 快捷筛选 ====================
        function filterToday() {
            quickFilter.value = 'today';
            const today = new Date();
            selectedDate.value = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
            loadDateActivities(1);
        }

        function filterWeek() {
            quickFilter.value = 'week';
            const today = new Date();
            const dayOfWeek = today.getDay();
            const start = new Date(today);
            start.setDate(today.getDate() - dayOfWeek);
            const end = new Date(today);
            end.setDate(today.getDate() + (6 - dayOfWeek));

            const sd = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, '0')}-${String(start.getDate()).padStart(2, '0')}`;
            const ed = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, '0')}-${String(end.getDate()).padStart(2, '0')}`;

            loading.value = true;
            request(`/activities?page=1&page_size=100&start_date=${sd}&end_date=${ed}`).then(data => {
                loading.value = false;
                if (data) {
                    detailActivities.value = data.items || [];
                    selectedDate.value = `${sd} ~ ${ed}`;
                    loadCountdowns();
                }
            });
        }

        // ==================== 倒计时 ====================
        async function loadCountdowns() {
            for (const act of detailActivities.value) {
                const data = await request(`/activities/${act.id}/countdown`);
                if (data) {
                    countdowns.value[act.id] = data;
                }
            }
        }

        function formatCountdown(seconds) {
            if (seconds <= 0) return '已开始';
            const d = Math.floor(seconds / 86400);
            const h = Math.floor((seconds % 86400) / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = seconds % 60;
            let result = '';
            if (d > 0) result += `${d}天`;
            if (h > 0) result += `${h}时`;
            if (m > 0) result += `${m}分`;
            result += `${s}秒`;
            return result;
        }

        // 每秒更新倒计时
        function startCountdownTimer() {
            countdownTimer = setInterval(() => {
                for (const id in countdowns.value) {
                    if (countdowns.value[id].seconds > 0) {
                        countdowns.value[id].seconds--;
                    }
                }
            }, 1000);
        }

        // ==================== 活动提交 ====================
        async function submitActivity() {
            if (!form.value.title || !form.value.category_id || !form.value.start_time || !form.value.end_time) {
                alert('请填写必填项');
                return;
            }
            submitting.value = true;

            const payload = {
                ...form.value,
                category_id: parseInt(form.value.category_id),
                start_time: new Date(form.value.start_time).toISOString(),
                end_time: new Date(form.value.end_time).toISOString(),
            };

            let data;
            if (showEditModal.value && editingId.value) {
                data = await request(`/activities/${editingId.value}`, {
                    method: 'PUT',
                    body: JSON.stringify(payload),
                });
            } else {
                data = await request('/activities', {
                    method: 'POST',
                    body: JSON.stringify(payload),
                });
            }

            submitting.value = false;
            if (data) {
                closeModal();
                loadMonthSummary();
                if (selectedDate.value) {
                    loadDateActivities();
                } else {
                    loadActivities();
                }
            }
        }

        function editActivity(act) {
            editingId.value = act.id;
            showEditModal.value = true;
            form.value = {
                title: act.title,
                description: act.description || '',
                category_id: act.category_id,
                location: act.location || '',
                start_time: act.start_time ? act.start_time.slice(0, 16) : '',
                end_time: act.end_time ? act.end_time.slice(0, 16) : '',
                publisher: act.publisher || '',
            };
        }

        async function cancelActivity(id) {
            if (!confirm('确定要取消该活动吗？')) return;
            await request(`/activities/${id}`, { method: 'DELETE' });
            loadMonthSummary();
            if (selectedDate.value) {
                loadDateActivities();
            } else {
                loadActivities();
            }
        }

        function closeModal() {
            showAddModal.value = false;
            showEditModal.value = false;
            editingId.value = null;
            form.value = { title: '', description: '', category_id: '', location: '', start_time: '', end_time: '', publisher: '' };
        }

        // ==================== 主题切换 ====================
        function toggleTheme() {
            isDark.value = !isDark.value;
            document.documentElement.setAttribute('data-theme', isDark.value ? 'dark' : '');
            localStorage.setItem('theme', isDark.value ? 'dark' : 'light');
        }

        // ==================== 时间显示 ====================
        function updateTime() {
            const now = new Date();
            currentTime.value = now.toLocaleString('zh-CN', {
                year: 'numeric', month: '2-digit', day: '2-digit',
                hour: '2-digit', minute: '2-digit', second: '2-digit',
            });
        }

        // ==================== 工具函数 ====================
        function formatTime(isoStr) {
            if (!isoStr) return '';
            const d = new Date(isoStr);
            return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
        }

        function highlightKeyword(text) {
            if (!keyword.value.trim() || !text) return text;
            const kw = keyword.value.trim();
            const regex = new RegExp(`(${kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            return text.replace(regex, '<span class="highlight">$1</span>');
        }

        // ==================== 饼图 ====================
        function updateChart() {
            const canvas = document.getElementById('categoryChart');
            if (!canvas) return;

            // 统计各分类活动数量
            const catCount = {};
            for (const day in monthSummary.value) {
                // 使用monthSummary中的分类颜色来反查不太准确，
                // 直接从detailActivities统计
            }

            // 从当前月活动统计
            const counts = {};
            categories.value.forEach(c => { counts[c.name] = 0; });

            // 使用monthSummary的颜色信息粗略统计
            // 更好的方式：直接请求月度活动列表统计
            request(`/activities?page=1&page_size=999&start_date=${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}-01&end_date=${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}-28`).then(data => {
                if (!data || !data.items) return;
                data.items.forEach(a => {
                    const name = a.category ? a.category.name : '其他';
                    counts[name] = (counts[name] || 0) + 1;
                });

                const labels = Object.keys(counts).filter(k => counts[k] > 0);
                const values = labels.map(k => counts[k]);
                const colors = labels.map(name => {
                    const cat = categories.value.find(c => c.name === name);
                    return cat ? cat.color : '#ccc';
                });

                if (chartInstance) chartInstance.destroy();
                chartInstance = new Chart(canvas, {
                    type: 'doughnut',
                    data: {
                        labels,
                        datasets: [{
                            data: values,
                            backgroundColor: colors,
                            borderWidth: 2,
                            borderColor: isDark.value ? '#16213e' : '#fff',
                        }],
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    color: isDark.value ? '#e0e0e0' : '#303133',
                                    font: { size: 11 },
                                    padding: 10,
                                },
                            },
                        },
                    },
                });
            });
        }

        // ==================== 导出功能 ====================
        function exportJSON() {
            const data = JSON.stringify(detailActivities.value, null, 2);
            const blob = new Blob([data], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `activities_${selectedDate.value || 'export'}.json`;
            a.click();
            URL.revokeObjectURL(url);
        }

        function exportICal() {
            let ical = 'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//CampusCalendar//CN\r\n';
            detailActivities.value.forEach(act => {
                const start = new Date(act.start_time);
                const end = new Date(act.end_time);
                const fmt = d => d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');
                ical += 'BEGIN:VEVENT\r\n';
                ical += `DTSTART:${fmt(start)}\r\n`;
                ical += `DTEND:${fmt(end)}\r\n`;
                ical += `SUMMARY:${act.title}\r\n`;
                ical += `DESCRIPTION:${act.description || ''}\r\n`;
                ical += `LOCATION:${act.location || ''}\r\n`;
                ical += `UID:${act.id}@campus-calendar\r\n`;
                ical += 'END:VEVENT\r\n';
            });
            ical += 'END:VCALENDAR';
            const blob = new Blob([ical], { type: 'text/calendar;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `activities_${selectedDate.value || 'export'}.ics`;
            a.click();
            URL.revokeObjectURL(url);
        }

        // ==================== 浏览器通知 ====================
        function checkNotifications() {
            if (!('Notification' in window)) return;
            if (Notification.permission === 'default') {
                Notification.requestPermission();
            }
            // 检查即将开始的活动（5分钟内）
            const now = new Date();
            detailActivities.value.forEach(act => {
                if (!act.start_time) return;
                const start = new Date(act.start_time);
                const diff = start - now;
                if (diff > 0 && diff <= 5 * 60 * 1000) {
                    if (Notification.permission === 'granted') {
                        new Notification('活动即将开始', {
                            body: `${act.title} 将在${Math.ceil(diff / 60000)}分钟后开始`,
                        });
                    }
                }
            });
        }

        // ==================== 初始化 ====================
        onMounted(async () => {
            // 加载主题
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'dark') {
                isDark.value = true;
                document.documentElement.setAttribute('data-theme', 'dark');
            }

            // 更新时间
            updateTime();
            setInterval(updateTime, 1000);

            // 加载数据
            await loadCategories();
            await loadMonthSummary();
            await loadActivities();
            startCountdownTimer();

            // 定期检查通知
            setInterval(checkNotifications, 60000);
        });

        return {
            currentTime, isDark, loading, submitting,
            currentYear, currentMonth, monthPicker,
            categories, selectedCategories,
            monthSummary, selectedDate, detailActivities, detailPagination,
            keyword, quickFilter, countdowns,
            showAddModal, showEditModal, form,
            weekdays, calendarCells,
            toggleTheme, onMonthChange, prevMonth, nextMonth,
            filterToday, filterWeek, loadActivities, loadDateActivities,
            selectDate, submitActivity, editActivity, cancelActivity, closeModal,
            formatTime, formatCountdown, highlightKeyword,
            exportJSON, exportICal,
        };
    }
});

app.mount('#app');
