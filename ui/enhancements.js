// RFSN UI Enhancements - Advanced Features
// Theme toggle, charts, export, drag-drop, keyboard shortcuts, and more

class UIEnhancements {
    constructor(app) {
        this.app = app;
        this.theme = localStorage.getItem('rfsn_theme') || 'dark';
        this.charts = {};
        this.notifications = [];
        this.taskHistory = JSON.parse(localStorage.getItem('rfsn_history') || '[]');
        
        this.init();
    }
    
    init() {
        this.setupThemeToggle();
        this.setupCharts();
        this.setupExport();
        this.setupDragDrop();
        this.setupKeyboardShortcuts();
        this.setupNotifications();
        this.setupSearch();
        this.setupSettings();
        this.setupProgressPersistence();
        this.applyTheme();
        this.loadHistory();
    }
    
    // ==================== THEME TOGGLE ====================
    setupThemeToggle() {
        const toggle = document.createElement('button');
        toggle.className = 'theme-toggle';
        toggle.innerHTML = this.theme === 'dark' ? '☀️' : '🌙';
        toggle.title = 'Toggle theme';
        toggle.onclick = () => this.toggleTheme();
        
        document.querySelector('.header-content').appendChild(toggle);
    }
    
    toggleTheme() {
        this.theme = this.theme === 'dark' ? 'light' : 'dark';
        localStorage.setItem('rfsn_theme', this.theme);
        this.applyTheme();
        
        const toggle = document.querySelector('.theme-toggle');
        toggle.innerHTML = this.theme === 'dark' ? '☀️' : '🌙';
        toggle.style.animation = 'spin 0.5s';
        setTimeout(() => toggle.style.animation = '', 500);
    }
    
    applyTheme() {
        const root = document.documentElement;
        
        if (this.theme === 'light') {
            root.style.setProperty('--bg', '#f0f4f8');
            root.style.setProperty('--bg-secondary', '#ffffff');
            root.style.setProperty('--text', '#1a202c');
            root.style.setProperty('--text-secondary', '#4a5568');
            root.style.setProperty('--border', '#e2e8f0');
        } else {
            root.style.setProperty('--bg', '#0f172a');
            root.style.setProperty('--bg-secondary', '#1e293b');
            root.style.setProperty('--text', '#f1f5f9');
            root.style.setProperty('--text-secondary', '#94a3b8');
            root.style.setProperty('--border', '#334155');
        }
    }
    
    // ==================== CHARTS & VISUALIZATION ====================
    setupCharts() {
        // Add chart canvas elements to results tab
        const resultsContent = document.getElementById('resultsContent');
        
        const chartsContainer = document.createElement('div');
        chartsContainer.className = 'charts-container';
        chartsContainer.innerHTML = `
            <div class="chart-card">
                <h3>Success Rate Over Time</h3>
                <canvas id="successChart" width="400" height="200"></canvas>
            </div>
            <div class="chart-card">
                <h3>Phase Duration</h3>
                <canvas id="phaseChart" width="400" height="200"></canvas>
            </div>
            <div class="chart-card">
                <h3>Patch Strategies</h3>
                <canvas id="strategyChart" width="400" height="200"></canvas>
            </div>
        `;
        
        if (resultsContent.querySelector('.empty-state')) {
            resultsContent.innerHTML = '';
        }
        resultsContent.insertBefore(chartsContainer, resultsContent.firstChild);
        
        this.initCharts();
    }
    
    initCharts() {
        // Simple canvas-based charts (no external library needed)
        this.renderSuccessChart();
        this.renderPhaseChart();
        this.renderStrategyChart();
    }
    
    renderSuccessChart() {
        const canvas = document.getElementById('successChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.getSuccessRateData();
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Draw axes
        ctx.strokeStyle = '#475569';
        ctx.beginPath();
        ctx.moveTo(40, 10);
        ctx.lineTo(40, 180);
        ctx.lineTo(380, 180);
        ctx.stroke();
        
        // Draw data line
        if (data.length > 0) {
            const maxVal = Math.max(...data.map(d => d.value));
            const stepX = 340 / (data.length - 1 || 1);
            
            ctx.strokeStyle = '#6366f1';
            ctx.lineWidth = 3;
            ctx.beginPath();
            
            data.forEach((point, i) => {
                const x = 40 + (i * stepX);
                const y = 180 - (point.value / maxVal * 170);
                
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
                
                // Draw point
                ctx.fillStyle = '#6366f1';
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fill();
            });
            
            ctx.stroke();
            
            // Draw labels
            ctx.fillStyle = '#94a3b8';
            ctx.font = '12px Inter';
            ctx.textAlign = 'center';
            data.forEach((point, i) => {
                const x = 40 + (i * stepX);
                ctx.fillText(point.label, x, 195);
            });
        }
        
        // Y-axis labels
        ctx.fillStyle = '#94a3b8';
        ctx.font = '12px Inter';
        ctx.textAlign = 'right';
        ctx.fillText('100%', 35, 15);
        ctx.fillText('50%', 35, 95);
        ctx.fillText('0%', 35, 185);
    }
    
    renderPhaseChart() {
        const canvas = document.getElementById('phaseChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.getPhaseDurationData();
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Bar chart
        const barWidth = 40;
        const spacing = 10;
        const startX = 50;
        const maxDuration = Math.max(...data.map(d => d.duration), 1);
        
        data.forEach((phase, i) => {
            const x = startX + (i * (barWidth + spacing));
            const height = (phase.duration / maxDuration) * 150;
            const y = 170 - height;
            
            // Draw bar
            const gradient = ctx.createLinearGradient(x, y, x, 170);
            gradient.addColorStop(0, '#ec4899');
            gradient.addColorStop(1, '#f472b6');
            
            ctx.fillStyle = gradient;
            ctx.fillRect(x, y, barWidth, height);
            
            // Draw value
            ctx.fillStyle = '#f1f5f9';
            ctx.font = '12px Inter';
            ctx.textAlign = 'center';
            ctx.fillText(`${phase.duration}s`, x + barWidth/2, y - 5);
            
            // Draw label
            ctx.save();
            ctx.translate(x + barWidth/2, 185);
            ctx.rotate(-Math.PI / 4);
            ctx.fillStyle = '#94a3b8';
            ctx.font = '11px Inter';
            ctx.textAlign = 'right';
            ctx.fillText(phase.name, 0, 0);
            ctx.restore();
        });
    }
    
    renderStrategyChart() {
        const canvas = document.getElementById('strategyChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        const data = this.getStrategyData();
        
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        
        // Pie chart
        const centerX = 200;
        const centerY = 100;
        const radius = 80;
        
        let startAngle = -Math.PI / 2;
        const total = data.reduce((sum, d) => sum + d.count, 0);
        
        const colors = ['#6366f1', '#ec4899', '#14b8a6', '#f59e0b', '#8b5cf6'];
        
        data.forEach((strategy, i) => {
            const sliceAngle = (strategy.count / total) * Math.PI * 2;
            const endAngle = startAngle + sliceAngle;
            
            // Draw slice
            ctx.fillStyle = colors[i % colors.length];
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.arc(centerX, centerY, radius, startAngle, endAngle);
            ctx.closePath();
            ctx.fill();
            
            // Draw label
            const labelAngle = startAngle + sliceAngle / 2;
            const labelX = centerX + Math.cos(labelAngle) * (radius + 30);
            const labelY = centerY + Math.sin(labelAngle) * (radius + 30);
            
            ctx.fillStyle = '#f1f5f9';
            ctx.font = '12px Inter';
            ctx.textAlign = labelX > centerX ? 'left' : 'right';
            ctx.fillText(`${strategy.name} (${strategy.count})`, labelX, labelY);
            
            startAngle = endAngle;
        });
    }
    
    // Mock data generators
    getSuccessRateData() {
        return this.taskHistory.slice(-10).map((task, i) => ({
            label: `T${i+1}`,
            value: task.success ? 100 : 0
        }));
    }
    
    getPhaseDurationData() {
        return [
            { name: 'LOCALIZE', duration: 15 },
            { name: 'PLAN', duration: 8 },
            { name: 'PATCH', duration: 25 },
            { name: 'TEST', duration: 30 },
            { name: 'VERIFY', duration: 12 }
        ];
    }
    
    getStrategyData() {
        return [
            { name: 'Direct', count: 12 },
            { name: 'Test-Driven', count: 8 },
            { name: 'Hypothesis', count: 5 },
            { name: 'Incremental', count: 6 },
            { name: 'Ensemble', count: 3 }
        ];
    }
    
    // ==================== EXPORT FUNCTIONALITY ====================
    setupExport() {
        const exportBar = document.createElement('div');
        exportBar.className = 'export-bar';
        exportBar.innerHTML = `
            <button class="btn btn-sm btn-secondary" onclick="window.enhancements.exportJSON()">
                <span class="btn-icon">📄</span> Export JSON
            </button>
            <button class="btn btn-sm btn-secondary" onclick="window.enhancements.exportCSV()">
                <span class="btn-icon">📊</span> Export CSV
            </button>
            <button class="btn btn-sm btn-secondary" onclick="window.enhancements.exportReport()">
                <span class="btn-icon">📑</span> Generate Report
            </button>
        `;
        
        const resultsTab = document.getElementById('results');
        resultsTab.insertBefore(exportBar, resultsTab.firstChild);
    }
    
    exportJSON() {
        const data = {
            config: this.app.config,
            history: this.taskHistory,
            exportDate: new Date().toISOString()
        };
        
        this.downloadFile(
            JSON.stringify(data, null, 2),
            `rfsn-export-${Date.now()}.json`,
            'application/json'
        );
        
        this.showToast('✅ JSON export complete', 'success');
    }
    
    exportCSV() {
        const headers = ['Date', 'Success', 'Time (s)', 'Patches', 'Strategy'];
        const rows = this.taskHistory.map(task => [
            new Date(task.timestamp).toLocaleString(),
            task.success ? 'Yes' : 'No',
            task.duration || 0,
            task.patchesTried || 0,
            task.strategy || 'N/A'
        ]);
        
        const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
        
        this.downloadFile(
            csv,
            `rfsn-history-${Date.now()}.csv`,
            'text/csv'
        );
        
        this.showToast('✅ CSV export complete', 'success');
    }
    
    exportReport() {
        const html = this.generateHTMLReport();
        
        this.downloadFile(
            html,
            `rfsn-report-${Date.now()}.html`,
            'text/html'
        );
        
        this.showToast('✅ Report generated', 'success');
    }
    
    generateHTMLReport() {
        const totalTasks = this.taskHistory.length;
        const successful = this.taskHistory.filter(t => t.success).length;
        const successRate = totalTasks > 0 ? (successful / totalTasks * 100).toFixed(1) : 0;
        
        return `<!DOCTYPE html>
<html>
<head>
    <title>RFSN Report</title>
    <style>
        body { font-family: Inter, sans-serif; padding: 2rem; background: #f0f4f8; }
        .container { max-width: 900px; margin: 0 auto; background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1 { color: #6366f1; }
        .stat { display: inline-block; margin: 1rem; padding: 1rem; background: #f0f4f8; border-radius: 8px; }
        .stat-value { font-size: 2rem; font-weight: bold; color: #6366f1; }
        table { width: 100%; border-collapse: collapse; margin-top: 2rem; }
        th, td { padding: 0.75rem; text-align: left; border-bottom: 1px solid #e2e8f0; }
        th { background: #f8fafc; font-weight: 600; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 RFSN SWE-Bench Report</h1>
        <p>Generated: ${new Date().toLocaleString()}</p>
        
        <h2>Summary</h2>
        <div class="stat">
            <div class="stat-value">${totalTasks}</div>
            <div>Total Tasks</div>
        </div>
        <div class="stat">
            <div class="stat-value">${successRate}%</div>
            <div>Success Rate</div>
        </div>
        <div class="stat">
            <div class="stat-value">${successful}</div>
            <div>Successful</div>
        </div>
        
        <h2>Task History</h2>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Patches</th>
                </tr>
            </thead>
            <tbody>
                ${this.taskHistory.map(task => `
                    <tr>
                        <td>${new Date(task.timestamp).toLocaleString()}</td>
                        <td>${task.success ? '✅ Success' : '❌ Failed'}</td>
                        <td>${task.duration || 0}s</td>
                        <td>${task.patchesTried || 0}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    </div>
</body>
</html>`;
    }
    
    downloadFile(content, filename, type) {
        const blob = new Blob([content], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    // ==================== DRAG & DROP ====================
    setupDragDrop() {
        const dropZone = document.querySelector('.card-primary');
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.add('drag-over');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('drag-over');
            });
        });
        
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.handleFileUpload(files[0]);
            }
        });
        
        // Add visual indicator
        const indicator = document.createElement('div');
        indicator.className = 'drop-indicator';
        indicator.textContent = '📁 Drop config file here';
        dropZone.appendChild(indicator);
    }
    
    handleFileUpload(file) {
        if (file.type === 'application/json') {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const config = JSON.parse(e.target.result);
                    this.app.applyConfig(config);
                    this.showToast('✅ Configuration loaded', 'success');
                } catch (err) {
                    this.showToast('❌ Invalid config file', 'error');
                }
            };
            reader.readAsText(file);
        } else {
            this.showToast('⚠️ Only JSON files supported', 'warning');
        }
    }
    
    // ==================== KEYBOARD SHORTCUTS ====================
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K: Focus search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                document.getElementById('historySearch')?.focus();
            }
            
            // Ctrl/Cmd + S: Save config
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.app.saveConfig();
            }
            
            // Ctrl/Cmd + Enter: Start agent
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                if (!this.app.isRunning) {
                    this.app.startAgent();
                }
            }
            
            // Ctrl/Cmd + E: Export JSON
            if ((e.ctrlKey || e.metaKey) && e.key === 'e') {
                e.preventDefault();
                this.exportJSON();
            }
            
            // Ctrl/Cmd + T: Toggle theme
            if ((e.ctrlKey || e.metaKey) && e.key === 't') {
                e.preventDefault();
                this.toggleTheme();
            }
            
            // Escape: Stop agent
            if (e.key === 'Escape' && this.app.isRunning) {
                this.app.stopAgent();
            }
        });
        
        // Add shortcuts help
        this.addShortcutsHelp();
    }
    
    addShortcutsHelp() {
        const help = document.createElement('div');
        help.className = 'shortcuts-help';
        help.innerHTML = `
            <button class="btn-icon-only" onclick="this.parentElement.classList.toggle('expanded')">
                ⌨️
            </button>
            <div class="shortcuts-list">
                <h4>Keyboard Shortcuts</h4>
                <div class="shortcut"><kbd>Ctrl+S</kbd> Save Config</div>
                <div class="shortcut"><kbd>Ctrl+Enter</kbd> Start Agent</div>
                <div class="shortcut"><kbd>Ctrl+E</kbd> Export JSON</div>
                <div class="shortcut"><kbd>Ctrl+T</kbd> Toggle Theme</div>
                <div class="shortcut"><kbd>Ctrl+K</kbd> Focus Search</div>
                <div class="shortcut"><kbd>Esc</kbd> Stop Agent</div>
            </div>
        `;
        
        document.body.appendChild(help);
    }
    
    // ==================== NOTIFICATIONS ====================
    setupNotifications() {
        const container = document.createElement('div');
        container.id = 'notification-container';
        container.className = 'notification-container';
        document.body.appendChild(container);
    }
    
    showToast(message, type = 'info') {
        const container = document.getElementById('notification-container');
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span class="toast-icon">${this.getToastIcon(type)}</span>
            <span class="toast-message">${message}</span>
            <button class="toast-close" onclick="this.parentElement.remove()">×</button>
        `;
        
        container.appendChild(toast);
        
        // Auto-remove after 4 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }
    
    getToastIcon(type) {
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        return icons[type] || icons.info;
    }
    
    // ==================== SEARCH & FILTER ====================
    setupSearch() {
        const historyTab = document.getElementById('history');
        
        const searchBar = document.createElement('div');
        searchBar.className = 'search-bar';
        searchBar.innerHTML = `
            <input 
                type="text" 
                id="historySearch" 
                class="input search-input" 
                placeholder="🔍 Search history... (Ctrl+K)">
            <select id="filterStatus" class="select filter-select">
                <option value="all">All Status</option>
                <option value="success">Success</option>
                <option value="failed">Failed</option>
            </select>
            <button class="btn btn-sm" onclick="window.enhancements.sortHistory()">
                <span class="btn-icon">🔄</span> Sort
            </button>
        `;
        
        historyTab.insertBefore(searchBar, historyTab.firstChild);
        
        document.getElementById('historySearch').addEventListener('input', (e) => {
            this.filterHistory(e.target.value);
        });
        
        document.getElementById('filterStatus').addEventListener('change', (e) => {
            this.filterHistoryByStatus(e.target.value);
        });
    }
    
    filterHistory(query) {
        const filtered = this.taskHistory.filter(task => 
            JSON.stringify(task).toLowerCase().includes(query.toLowerCase())
        );
        this.renderHistory(filtered);
    }
    
    filterHistoryByStatus(status) {
        if (status === 'all') {
            this.renderHistory(this.taskHistory);
        } else {
            const filtered = this.taskHistory.filter(task => 
                task.success === (status === 'success')
            );
            this.renderHistory(filtered);
        }
    }
    
    sortHistory() {
        this.taskHistory.sort((a, b) => b.timestamp - a.timestamp);
        this.renderHistory(this.taskHistory);
        this.showToast('📊 History sorted', 'info');
    }
    
    // ==================== SETTINGS PANEL ====================
    setupSettings() {
        const settingsBtn = document.createElement('button');
        settingsBtn.className = 'settings-btn btn-icon-only';
        settingsBtn.innerHTML = '⚙️';
        settingsBtn.title = 'Settings';
        settingsBtn.onclick = () => this.openSettings();
        
        document.querySelector('.header-content').appendChild(settingsBtn);
    }
    
    openSettings() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>⚙️ Settings</h2>
                    <button class="btn-icon-only" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="settingAutoSave" ${localStorage.getItem('rfsn_autoSave') !== 'false' ? 'checked' : ''}>
                            Auto-save configuration
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="settingNotifications" ${localStorage.getItem('rfsn_notifications') !== 'false' ? 'checked' : ''}>
                            Show notifications
                        </label>
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="settingPersistence" ${localStorage.getItem('rfsn_persistence') !== 'false' ? 'checked' : ''}>
                            Persist progress across reloads
                        </label>
                    </div>
                    <div class="form-group">
                        <label>History retention (days)</label>
                        <input type="number" id="settingRetention" class="input" value="${localStorage.getItem('rfsn_retention') || 30}" min="1" max="365">
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">Cancel</button>
                    <button class="btn btn-primary" onclick="window.enhancements.saveSettings()">Save</button>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Close on outside click
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.remove();
        });
    }
    
    saveSettings() {
        localStorage.setItem('rfsn_autoSave', document.getElementById('settingAutoSave').checked);
        localStorage.setItem('rfsn_notifications', document.getElementById('settingNotifications').checked);
        localStorage.setItem('rfsn_persistence', document.getElementById('settingPersistence').checked);
        localStorage.setItem('rfsn_retention', document.getElementById('settingRetention').value);
        
        document.querySelector('.modal').remove();
        this.showToast('✅ Settings saved', 'success');
    }
    
    // ==================== PROGRESS PERSISTENCE ====================
    setupProgressPersistence() {
        // Save progress periodically
        setInterval(() => {
            if (this.app.isRunning && localStorage.getItem('rfsn_persistence') !== 'false') {
                this.saveProgress();
            }
        }, 5000);
        
        // Restore progress on load
        this.restoreProgress();
    }
    
    saveProgress() {
        const progress = {
            config: this.app.config,
            startTime: this.app.startTime,
            phase: document.getElementById('currentPhase').textContent,
            logs: Array.from(document.querySelectorAll('.log-entry')).map(el => ({
                time: el.querySelector('.log-time').textContent,
                message: el.querySelector('.log-message').textContent,
                level: Array.from(el.classList).find(c => c.startsWith('log-'))
            }))
        };
        
        localStorage.setItem('rfsn_progress', JSON.stringify(progress));
    }
    
    restoreProgress() {
        const saved = localStorage.getItem('rfsn_progress');
        if (saved) {
            try {
                const progress = JSON.parse(saved);
                
                // Ask user if they want to restore
                const restore = confirm('Found previous session. Restore progress?');
                if (restore) {
                    this.app.applyConfig(progress.config);
                    document.getElementById('currentPhase').textContent = progress.phase;
                    
                    progress.logs.forEach(log => {
                        this.app.addLog(log.level.replace('log-', ''), log.message);
                    });
                    
                    this.showToast('📂 Progress restored', 'success');
                }
            } catch (err) {
                console.error('Failed to restore progress:', err);
            }
        }
    }
    
    // ==================== HISTORY MANAGEMENT ====================
    loadHistory() {
        this.renderHistory(this.taskHistory);
    }
    
    renderHistory(tasks) {
        const container = document.getElementById('historyContent');
        
        if (tasks.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📭</span>
                    <p>No history yet. Completed tasks will appear here.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = tasks.map(task => `
            <div class="history-item ${task.success ? 'success' : 'failed'}">
                <div class="history-header">
                    <span class="history-status">${task.success ? '✅' : '❌'}</span>
                    <span class="history-date">${new Date(task.timestamp).toLocaleString()}</span>
                </div>
                <div class="history-details">
                    <div class="history-stat">
                        <strong>Duration:</strong> ${task.duration || 0}s
                    </div>
                    <div class="history-stat">
                        <strong>Patches:</strong> ${task.patchesTried || 0}
                    </div>
                    <div class="history-stat">
                        <strong>Strategy:</strong> ${task.strategy || 'N/A'}
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    addToHistory(task) {
        task.timestamp = Date.now();
        this.taskHistory.unshift(task);
        
        // Limit history size
        const retention = parseInt(localStorage.getItem('rfsn_retention') || 30);
        const cutoff = Date.now() - (retention * 24 * 60 * 60 * 1000);
        this.taskHistory = this.taskHistory.filter(t => t.timestamp > cutoff);
        
        localStorage.setItem('rfsn_history', JSON.stringify(this.taskHistory));
        this.loadHistory();
    }
}

// Initialize enhancements when app is ready
document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        window.enhancements = new UIEnhancements(window.rfsn);
    }, 100);
});
