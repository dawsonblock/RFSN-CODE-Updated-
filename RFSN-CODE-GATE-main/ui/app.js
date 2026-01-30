// RFSN SWE-Bench Killer - UI Application Logic

class RFSNApp {
    constructor() {
        this.config = {};
        this.isRunning = false;
        this.startTime = null;
        this.timerInterval = null;
        this.websocket = null;
        
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.loadSavedConfig();
        this.updateTemperatureDisplay();
    }
    
    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => this.switchTab(e.target.closest('.tab')));
        });
        
        // Configuration buttons
        document.getElementById('saveConfigBtn').addEventListener('click', () => this.saveConfig());
        document.getElementById('startBtn').addEventListener('click', () => this.startAgent());
        
        // Process control buttons
        document.getElementById('stopBtn').addEventListener('click', () => this.stopAgent());
        document.getElementById('pauseBtn').addEventListener('click', () => this.pauseAgent());
        document.getElementById('clearLogBtn').addEventListener('click', () => this.clearLog());
        
        // Temperature slider
        document.getElementById('temperature').addEventListener('input', (e) => {
            document.getElementById('tempValue').textContent = e.target.value;
        });
        
        // Auto-save config on change
        const configInputs = ['repoUrl', 'repoBranch', 'githubToken', 'githubUsername', 'llmApiKey', 'llmModel'];
        configInputs.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('change', () => this.autoSaveConfig());
            }
        });
    }
    
    switchTab(tab) {
        // Remove active class from all tabs and contents
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        // Add active class to clicked tab
        tab.classList.add('active');
        
        // Show corresponding content
        const tabName = tab.dataset.tab;
        document.getElementById(tabName).classList.add('active');
    }
    
    updateTemperatureDisplay() {
        const temp = document.getElementById('temperature').value;
        document.getElementById('tempValue').textContent = temp;
    }
    
    gatherConfig() {
        const config = {
            // Repository
            repoUrl: document.getElementById('repoUrl').value,
            repoBranch: document.getElementById('repoBranch').value,
            problemStatement: document.getElementById('problemStatement').value,
            
            // GitHub credentials
            githubToken: document.getElementById('githubToken').value,
            githubUsername: document.getElementById('githubUsername').value,
            createPR: document.getElementById('createPR').checked,
            commitChanges: document.getElementById('commitChanges').checked,
            
            // LLM API
            llmProvider: document.getElementById('llmProvider').value,
            llmApiKey: document.getElementById('llmApiKey').value,
            llmModel: document.getElementById('llmModel').value,
            temperature: parseFloat(document.getElementById('temperature').value),
            
            // Execution settings
            profile: document.getElementById('profile').value,
            maxSteps: parseInt(document.getElementById('maxSteps').value),
            maxTime: parseInt(document.getElementById('maxTime').value),
            
            // Localization layers
            useTrace: document.getElementById('useTrace').checked,
            useRipgrep: document.getElementById('useRipgrep').checked,
            useSymbols: document.getElementById('useSymbols').checked,
            useEmbeddings: document.getElementById('useEmbeddings').checked,
            
            // Patch strategies
            strategyDirect: document.getElementById('strategyDirect').checked,
            strategyTestDriven: document.getElementById('strategyTestDriven').checked,
            strategyEnsemble: document.getElementById('strategyEnsemble').checked,
        };
        
        return config;
    }
    
    saveConfig() {
        this.config = this.gatherConfig();
        localStorage.setItem('rfsn_config', JSON.stringify(this.config));
        this.addLog('info', 'Configuration saved successfully');
        this.showNotification('✅ Configuration saved!', 'success');
    }
    
    autoSaveConfig() {
        this.config = this.gatherConfig();
        localStorage.setItem('rfsn_config', JSON.stringify(this.config));
    }
    
    loadSavedConfig() {
        const saved = localStorage.getItem('rfsn_config');
        if (saved) {
            try {
                this.config = JSON.parse(saved);
                this.applyConfig(this.config);
                this.addLog('info', 'Previous configuration loaded');
            } catch (e) {
                console.error('Failed to load config:', e);
            }
        }
    }
    
    applyConfig(config) {
        // Apply saved config to form fields
        const fields = {
            repoUrl: 'value',
            repoBranch: 'value',
            problemStatement: 'value',
            githubToken: 'value',
            githubUsername: 'value',
            createPR: 'checked',
            commitChanges: 'checked',
            llmProvider: 'value',
            llmApiKey: 'value',
            llmModel: 'value',
            temperature: 'value',
            profile: 'value',
            maxSteps: 'value',
            maxTime: 'value',
            useTrace: 'checked',
            useRipgrep: 'checked',
            useSymbols: 'checked',
            useEmbeddings: 'checked',
            strategyDirect: 'checked',
            strategyTestDriven: 'checked',
            strategyEnsemble: 'checked',
        };
        
        Object.entries(fields).forEach(([id, prop]) => {
            const element = document.getElementById(id);
            if (element && config[id] !== undefined) {
                element[prop] = config[id];
            }
        });
        
        this.updateTemperatureDisplay();
    }
    
    validateConfig() {
        const config = this.gatherConfig();
        const errors = [];
        
        if (!config.repoUrl) errors.push('Repository URL is required');
        if (!config.problemStatement) errors.push('Problem statement is required');
        if (!config.llmApiKey) errors.push('LLM API key is required');
        
        if (errors.length > 0) {
            errors.forEach(err => this.addLog('error', err));
            this.showNotification('❌ Configuration errors. Check log.', 'error');
            return false;
        }
        
        return true;
    }
    
    async startAgent() {
        if (!this.validateConfig()) return;
        
        if (this.isRunning) {
            this.showNotification('⚠️ Agent is already running', 'warning');
            return;
        }
        
        this.config = this.gatherConfig();
        this.isRunning = true;
        this.startTime = Date.now();
        
        // Update UI
        document.getElementById('startBtn').disabled = true;
        document.getElementById('stopBtn').disabled = false;
        document.getElementById('pauseBtn').disabled = false;
        this.updateStatus('running', 'Running');
        
        // Switch to process tab
        document.querySelector('[data-tab="process"]').click();
        
        // Clear previous logs
        this.clearLog();
        this.addLog('info', 'Starting RFSN Agent...');
        this.addLog('info', `Repository: ${this.config.repoUrl}`);
        this.addLog('info', `Profile: ${this.config.profile}`);
        this.addLog('info', `Max Steps: ${this.config.maxSteps}, Max Time: ${this.config.maxTime} minutes`);
        
        // Start timer
        this.startTimer();
        
        // Send start request to backend
        try {
            const response = await fetch('http://localhost:8000/api/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.config),
            });
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}`);
            }
            
            const data = await response.json();
            this.addLog('success', `Agent started successfully. Task ID: ${data.task_id}`);
            
            // Connect WebSocket for live updates
            this.connectWebSocket(data.task_id);
            
        } catch (error) {
            this.addLog('error', `Failed to start agent: ${error.message}`);
            this.addLog('warning', 'Running in simulation mode (backend not available)');
            
            // Run simulation for demo purposes
            this.runSimulation();
        }
    }
    
    async stopAgent() {
        if (!this.isRunning) return;
        
        this.addLog('warning', 'Stopping agent...');
        
        try {
            await fetch('http://localhost:8000/api/stop', {
                method: 'POST',
            });
            this.addLog('info', 'Stop signal sent to agent');
        } catch (error) {
            this.addLog('warning', 'Could not reach backend, stopping locally');
        }
        
        this.cleanupAfterRun();
    }
    
    pauseAgent() {
        this.addLog('info', 'Pause requested (feature coming soon)');
        this.showNotification('⏸️ Pause feature coming soon', 'info');
    }
    
    cleanupAfterRun() {
        this.isRunning = false;
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
        
        document.getElementById('startBtn').disabled = false;
        document.getElementById('stopBtn').disabled = true;
        document.getElementById('pauseBtn').disabled = true;
        this.updateStatus('idle', 'Ready');
        
        this.addLog('info', 'Agent stopped');
    }
    
    connectWebSocket(taskId) {
        try {
            this.websocket = new WebSocket(`ws://localhost:8000/ws/${taskId}`);
            
            this.websocket.onopen = () => {
                this.addLog('success', 'Connected to live updates');
            };
            
            this.websocket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(data);
            };
            
            this.websocket.onerror = (error) => {
                this.addLog('error', 'WebSocket error, falling back to polling');
                this.websocket = null;
            };
            
            this.websocket.onclose = () => {
                this.addLog('info', 'Live updates disconnected');
            };
        } catch (error) {
            this.addLog('warning', 'Could not connect WebSocket, using simulation');
        }
    }
    
    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'phase':
                this.updatePhase(data.phase);
                this.addLog('info', `Phase: ${data.phase}`);
                break;
            case 'log':
                this.addLog(data.level, data.message);
                break;
            case 'progress':
                this.updateProgress(data);
                break;
            case 'complete':
                this.handleTaskComplete(data);
                break;
            case 'error':
                this.addLog('error', data.message);
                break;
        }
    }
    
    updatePhase(phase) {
        document.getElementById('currentPhase').textContent = phase;
    }
    
    updateProgress(data) {
        if (data.steps !== undefined) {
            document.getElementById('stepsCompleted').textContent = 
                `${data.current_step} / ${data.total_steps}`;
        }
        if (data.patches !== undefined) {
            document.getElementById('patchesTried').textContent = data.patches;
        }
        if (data.progress !== undefined) {
            document.getElementById('progressFill').style.width = `${data.progress}%`;
        }
    }
    
    handleTaskComplete(data) {
        this.addLog('success', '✅ Task completed!');
        this.addLog('info', `Success: ${data.success}`);
        this.addLog('info', `Time: ${data.time_taken}s`);
        
        this.cleanupAfterRun();
        this.showNotification('✅ Task completed!', 'success');
        
        // Switch to results tab
        document.querySelector('[data-tab="results"]').click();
    }
    
    startTimer() {
        this.timerInterval = setInterval(() => {
            if (this.startTime) {
                const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
                const minutes = Math.floor(elapsed / 60);
                const seconds = elapsed % 60;
                document.getElementById('elapsedTime').textContent = 
                    `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }
    
    updateStatus(status, text) {
        const dot = document.getElementById('statusDot');
        const textEl = document.getElementById('statusText');
        
        dot.style.background = {
            'idle': 'var(--success)',
            'running': 'var(--primary)',
            'error': 'var(--danger)',
            'paused': 'var(--warning)',
        }[status] || 'var(--success)';
        
        textEl.textContent = text;
    }
    
    addLog(level, message) {
        const container = document.getElementById('logContainer');
        const entry = document.createElement('div');
        entry.className = `log-entry log-${level}`;
        
        const time = new Date().toLocaleTimeString();
        entry.innerHTML = `
            <span class="log-time">${time}</span>
            <span class="log-message">${this.escapeHtml(message)}</span>
        `;
        
        container.appendChild(entry);
        container.scrollTop = container.scrollHeight;
        
        // Keep only last 100 entries
        while (container.children.length > 100) {
            container.removeChild(container.firstChild);
        }
    }
    
    clearLog() {
        document.getElementById('logContainer').innerHTML = '';
        this.addLog('info', 'Log cleared');
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    showNotification(message, type) {
        // Simple notification (could be enhanced with a library)
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 1rem 1.5rem;
            background: var(--${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'});
            color: white;
            border-radius: var(--radius-md);
            box-shadow: var(--shadow-xl);
            z-index: 1000;
            animation: slideIn 0.3s;
        `;
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    // Simulation mode for demo without backend
    runSimulation() {
        const phases = ['INGEST', 'LOCALIZE', 'PLAN', 'PATCH', 'TEST', 'DIAGNOSE', 'FINALIZE'];
        let phaseIndex = 0;
        let step = 0;
        
        const simulationInterval = setInterval(() => {
            if (!this.isRunning) {
                clearInterval(simulationInterval);
                return;
            }
            
            // Update phase
            if (step % 3 === 0 && phaseIndex < phases.length) {
                this.updatePhase(phases[phaseIndex]);
                this.addLog('info', `Entering phase: ${phases[phaseIndex]}`);
                phaseIndex++;
            }
            
            // Update progress
            step++;
            const progress = Math.min((step / 30) * 100, 100);
            this.updateProgress({
                current_step: step,
                total_steps: 30,
                patches: Math.floor(step / 5),
                progress: progress,
            });
            
            // Random log messages
            const messages = [
                'Analyzing repository structure...',
                'Running localization layers...',
                'Found 5 potential bug locations',
                'Generating patch candidates...',
                'Testing patch #1...',
                'Patch validation successful',
                'Running test suite...',
            ];
            if (step % 2 === 0) {
                this.addLog('info', messages[Math.floor(Math.random() * messages.length)]);
            }
            
            // Complete after 30 steps
            if (step >= 30) {
                clearInterval(simulationInterval);
                this.handleTaskComplete({
                    success: true,
                    time_taken: Math.floor((Date.now() - this.startTime) / 1000),
                });
            }
        }, 1000);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.rfsn = new RFSNApp();
});

// Add animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);
