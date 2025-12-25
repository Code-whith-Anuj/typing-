class TypingGame {
    constructor() {
        this.sessionId = null;
        this.userId = localStorage.getItem('typing_user_id'); // Restore login
        this.currentText = '';
        this.currentPosition = 0;
        this.lastKeystrokeTime = null;
        this.gameActive = false;
        this.startTime = null;
        this.isTypingMode = true; // true = learning mode, false = test mode
        this.focusChars = new Set(); // Characters to focus on
        
        // Initialize stats
        this.stats = {
            score: 0,
            streak: 0,
            maxStreak: 0,
            combo: 1.0,
            errors: 0,
            wpm: 0,
            accuracy: 100,
            totalChars: 0,
            correctChars: 0,
            sessionChars: 0,
            sessionCorrect: 0
        };
        
        this.initializeElements();
        this.bindEvents();
        this.startNewSession();
    }

    initializeElements() {
        // Text display
        this.textDisplay = document.getElementById('text-display');
        this.typingInput = document.getElementById('typing-input');
        this.progressFill = document.getElementById('progress-fill');
        
        // Stats elements
        this.scoreEl = document.getElementById('score');
        this.wpmEl = document.getElementById('wpm');
        this.accuracyEl = document.getElementById('accuracy');
        this.streakEl = document.getElementById('streak');
        this.comboEl = document.getElementById('combo');
        this.errorsEl = document.getElementById('errors');
        this.maxStreakEl = document.getElementById('max-streak');
        this.levelEl = document.getElementById('current-level');
        this.sessionIdEl = document.getElementById('session-id');
        
        // Analysis elements
        this.focusList = document.getElementById('focus-list');
        this.insightsList = document.getElementById('insights-list');
        
        // Modal elements
        this.modal = document.getElementById('analysis-modal');
        this.closeBtn = document.querySelector('.close-btn');
        this.tabBtns = document.querySelectorAll('.tab-btn');
        this.tabContents = document.querySelectorAll('.tab-content');
        
        // Buttons
        this.newTextBtn = document.getElementById('new-text-btn');
        this.analysisBtn = document.getElementById('analysis-btn');
        this.resetBtn = document.getElementById('reset-btn');
        
        // Create Save Button
        this.saveBtn = document.createElement('button');
        this.saveBtn.id = 'save-btn';
        this.saveBtn.className = 'btn';
        this.saveBtn.innerHTML = '<i class="fas fa-save"></i> Save';
        this.resetBtn.insertAdjacentElement('beforebegin', this.saveBtn);

        // Dynamically create and add logout button
        const controlsDiv = this.resetBtn.parentElement;
        if (controlsDiv) {
            this.logoutBtn = document.createElement('button');
            this.logoutBtn.id = 'logout-btn';
            this.logoutBtn.className = 'btn btn-danger';
            this.logoutBtn.innerHTML = '<i class="fas fa-sign-out-alt"></i> Logout';
            // Insert after reset button
            this.resetBtn.insertAdjacentElement('afterend', this.logoutBtn);
        }

        // Inject CSS for visible spaces
        const style = document.createElement('style');
        style.textContent = `
            .char.space {
                color: #9ca3af;
                opacity: 0.6;
                margin: 0 2px;
            }
            .char.space.current {
                background-color: rgba(59, 130, 246, 0.15);
                border-radius: 4px;
            }
        `;
        document.head.appendChild(style);
    }

    bindEvents() {
        // KEY-BASED EVENT HANDLING (Professional approach)
        document.addEventListener('keydown', (e) => this.handleKeyDown(e));
        
        // Button events
        this.newTextBtn.addEventListener('click', () => this.requestNewText());
        this.analysisBtn.addEventListener('click', () => this.showDetailedAnalysis());
        this.resetBtn.addEventListener('click', () => this.resetSession());
        this.saveBtn.addEventListener('click', () => this.saveProgress());
        
        // Logout button event
        if (this.logoutBtn) {
            this.logoutBtn.addEventListener('click', () => this.logout());
        }
        
        // Modal events
        this.closeBtn.addEventListener('click', () => this.hideModal());
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.hideModal();
        });
        
        // Tab events
        this.tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e));
        });
        
        // Focus handling
        this.textDisplay.addEventListener('click', () => {
            this.typingInput.focus();
        });
        
        // Blur input field to prevent virtual keyboard on mobile
        window.addEventListener('load', () => {
            this.typingInput.blur();
        });
    }

    handleKeyDown(e) {
        // Don't process if modal is open
        if (this.modal.style.display === 'flex') return;

        // Don't process if game isn't active
        if (!this.gameActive || this.currentPosition >= this.currentText.length) {
            return;
        }

        // Ignore modifier keys and special keys
        if (e.ctrlKey || e.altKey || e.metaKey) {
            return;
        }

        // Handle special keys
        switch (e.key) {
            case 'Shift':
            case 'Control':
            case 'Alt':
            case 'Meta':
            case 'CapsLock':
            case 'Tab':
            case 'Escape':
                return; // Ignore these keys
                
            case 'Backspace':
                // We don't allow corrections in this game mode
                e.preventDefault();
                return;
                
            case 'Enter':
                // Optionally allow Enter to request new text
                if (this.currentPosition >= this.currentText.length - 1) {
                    this.requestNewText();
                }
                e.preventDefault();
                return;
        }

        // Process the key press
        e.preventDefault();
        e.stopPropagation();
        
        const inputChar = e.key;
        this.processKeystroke(inputChar);
    }

    async processKeystroke(inputChar) {
        if (!this.gameActive || this.currentPosition >= this.currentText.length) {
            return;
        }

        const expectedChar = this.currentText[this.currentPosition];
        
        // Calculate timing
        const now = Date.now();
        const timeSinceLast = this.lastKeystrokeTime ? (now - this.lastKeystrokeTime) / 1000 : null;
        this.lastKeystrokeTime = now;
        
        // Send keystroke to server
        const result = await this.sendKeystroke(inputChar, timeSinceLast);
        
        if (result) {
            this.updateGameState(result, expectedChar, inputChar);
            this.updateStatsDisplay();
            this.renderText();
            
            // Check if text is complete
            if (result.is_complete) {
                this.onTextComplete(result.new_text);
            }
            
            // Update analysis periodically
            if (this.stats.sessionChars % 20 === 0) {
                await this.fetchAnalysis();
            }
        }
    }

    async sendKeystroke(key, timeSinceLast) {
        try {
            const response = await fetch('/api/keystroke', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    key: key,
                    timestamp: Date.now() / 1000
                })
            });
            
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Failed to send keystroke:', error);
            return {
                correct: false,
                position: this.currentPosition,
                streak: 0,
                score: 0,
                errors: this.stats.errors + 1,
                is_complete: false
            };
        }
        return null;
    }

    updateGameState(result, expectedChar, inputChar) {
        // Update stats based on correctness
        if (result.correct) {
            this.stats.correctChars++;
            this.stats.sessionCorrect++;
            
            // Update streak and combo
            this.stats.streak = result.streak;
            this.stats.maxStreak = Math.max(this.stats.maxStreak, result.streak);
            this.stats.combo = result.combo_multiplier;
            
            // Score update
            this.stats.score = result.score;
            
            // Visual feedback for correct key
            this.showFeedback('correct', expectedChar);
        } else {
            this.stats.errors = result.errors;
            this.stats.streak = 0;
            this.stats.combo = result.combo_multiplier;
            
            // Visual feedback for incorrect key
            this.showFeedback('incorrect', expectedChar);
            
        }
        
        // Sync position with backend (Single Source of Truth)
        this.currentPosition = result.position;
        
        // Update total characters
        this.stats.totalChars++;
        this.stats.sessionChars++;
        
        // Calculate WPM and accuracy
        const elapsedMinutes = (Date.now() - this.startTime) / 60000;
        this.stats.wpm = Math.max(0, Math.round((this.stats.sessionCorrect / 5) / elapsedMinutes));
        this.stats.accuracy = this.stats.sessionChars > 0 
            ? Math.round((this.stats.sessionCorrect / this.stats.sessionChars) * 100)
            : 100;
        
        // Update progress bar
        const progress = (this.currentPosition / this.currentText.length) * 100;
        this.progressFill.style.width = `${Math.min(100, progress)}%`;
    }

    showFeedback(type, char) {
        // Create visual feedback element
        const feedback = document.createElement('div');
        feedback.className = `feedback ${type}`;
        feedback.textContent = type === 'correct' ? '✓' : '✗';
        feedback.style.cssText = `
            position: fixed;
            font-size: 2rem;
            color: ${type === 'correct' ? '#10b981' : '#ef4444'};
            pointer-events: none;
            z-index: 1000;
            animation: floatUp 1s ease-out forwards;
            font-weight: bold;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        `;
        
        // Position feedback near the current character
        const cursorPos = this.getCursorPosition();
        feedback.style.left = `${cursorPos.x}px`;
        feedback.style.top = `${cursorPos.y - 50}px`;
        
        document.body.appendChild(feedback);
        
        // Remove after animation
        setTimeout(() => {
            feedback.remove();
        }, 1000);
    }

    getCursorPosition() {
        // Calculate approximate position of current character
        const displayRect = this.textDisplay.getBoundingClientRect();
        const charElements = this.textDisplay.querySelectorAll('.char');
        
        if (charElements.length > this.currentPosition) {
            const charEl = charElements[this.currentPosition];
            const charRect = charEl.getBoundingClientRect();
            return {
                x: charRect.left + charRect.width / 2,
                y: charRect.top + charRect.height / 2
            };
        }
        
        // Fallback position
        return {
            x: displayRect.left + displayRect.width / 2,
            y: displayRect.top + displayRect.height / 2
        };
    }

    renderText() {
        if (!this.currentText) return;
        
        this.textDisplay.innerHTML = '';
        
        for (let i = 0; i < this.currentText.length; i++) {
            const char = this.currentText[i];
            const span = document.createElement('span');
            span.className = 'char';
            
            if (char === ' ') {
                span.textContent = '·';
                span.classList.add('space');
            } else {
                span.textContent = char;
            }
            
            if (i < this.currentPosition) {
                // Character has been typed
                span.classList.add('correct');
            } else if (i === this.currentPosition) {
                // Current character
                span.classList.add('current');
                
                // Highlight focus characters
                if (this.focusChars.has(char.toLowerCase())) {
                    span.classList.add('focus-char');
                }
            }
            
            this.textDisplay.appendChild(span);
        }
    }

    updateStatsDisplay() {
        this.scoreEl.textContent = this.stats.score.toLocaleString();
        this.wpmEl.textContent = this.stats.wpm;
        this.accuracyEl.textContent = `${this.stats.accuracy}%`;
        this.streakEl.textContent = this.stats.streak;
        this.comboEl.textContent = `${this.stats.combo.toFixed(1)}x`;
        this.errorsEl.textContent = this.stats.errors;
        this.maxStreakEl.textContent = this.stats.maxStreak;
        
        // Update level based on score
        this.levelEl.textContent = Math.min(10, Math.floor(this.stats.score / 1000) + 1);
    }

    async startNewSession() {
        try {
            const response = await fetch('/api/start_session', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ user_id: this.userId })
            });
            
            if (response.ok) {
                const data = await response.json();
                this.sessionId = data.session_id;
                this.currentText = data.text;
                this.currentPosition = 0;
                this.sessionIdEl.textContent = this.sessionId.substring(0, 8) + '...';
                this.gameActive = true;
                this.startTime = Date.now();
                
                // Restore level if provided
                if (data.level) {
                    this.levelEl.textContent = data.level;
                }
                
                // Reset session stats
                this.stats.sessionChars = 0;
                this.stats.sessionCorrect = 0;
                
                this.renderText();
                this.updateStatsDisplay();
                this.fetchAnalysis();
                
                // Focus the hidden input (for mobile compatibility)
                this.typingInput.focus();
            }
        } catch (error) {
            console.error('Failed to start session:', error);
            // Fallback text if server is unavailable
            this.currentText = "The quick brown fox jumps over the lazy dog.";
            this.currentPosition = 0;
            this.gameActive = true;
            this.startTime = Date.now();
            this.renderText();
        }
    }

    async onTextComplete(nextText) {
        // Celebrate completion
        this.showCompletionEffect();
        
        // Brief pause before new text
        setTimeout(async () => {
            if (nextText) {
                this.currentText = nextText;
                this.currentPosition = 0;
                this.progressFill.style.width = '0%';
                this.lastKeystrokeTime = null;
                this.renderText();
                this.typingInput.focus();
            } else {
                await this.requestNewText();
            }
            await this.fetchAnalysis();
        }, 800);
    }

    showCompletionEffect() {
        // Add completion animation to text display
        this.textDisplay.classList.add('complete');
        
        // Create celebration particles
        for (let i = 0; i < 20; i++) {
            setTimeout(() => {
                const particle = document.createElement('div');
                particle.className = 'celebration-particle';
                particle.style.cssText = `
                    position: fixed;
                    width: ${8 + Math.random() * 8}px;
                    height: ${8 + Math.random() * 8}px;
                    background: ${['#3b82f6', '#10b981', '#f59e0b', '#ef4444'][Math.floor(Math.random() * 4)]};
                    border-radius: 50%;
                    top: ${window.innerHeight}px;
                    left: ${Math.random() * window.innerWidth}px;
                    animation: celebrateParticle 1.5s ease-out forwards;
                    pointer-events: none;
                    z-index: 999;
                `;
                
                document.body.appendChild(particle);
                setTimeout(() => particle.remove(), 1500);
            }, i * 50);
        }
        
        // Remove celebration class
        setTimeout(() => {
            this.textDisplay.classList.remove('complete');
        }, 1000);
    }

    async requestNewText() {
        try {
            const response = await fetch(`/api/new_text/${this.sessionId}`);
            if (response.ok) {
                const data = await response.json();
                this.currentText = data.text;
                this.currentPosition = 0;
                this.progressFill.style.width = '0%';
                this.lastKeystrokeTime = null;
                this.renderText();
                
                // Focus input for next round
                this.typingInput.focus();
            }
        } catch (error) {
            console.error('Failed to fetch new text:', error);
            // Fallback text
            this.currentText = "Practice makes perfect. Keep typing to improve your skills.";
            this.currentPosition = 0;
            this.renderText();
        }
    }

    async fetchAnalysis() {
        try {
            const response = await fetch(`/api/analysis/${this.sessionId}`);
            if (response.ok) {
                const analysis = await response.json();
                this.updateAnalysisDisplay(analysis);
                this.updateFocusChars(analysis);
            }
        } catch (error) {
            console.error('Failed to fetch analysis:', error);
        }
    }

    updateAnalysisDisplay(analysis) {
        // Update focus areas
        this.focusList.innerHTML = '';
        
        if (analysis.focus_areas && analysis.focus_areas.length > 0) {
            analysis.focus_areas.forEach(area => {
                const item = document.createElement('div');
                item.className = 'focus-item';
                
                let icon = 'fa-exclamation-circle';
                let content = '';
                
                switch (area.type) {
                    case 'high_error_keys':
                        content = `Practice these keys: <strong>${area.items.join(', ')}</strong>`;
                        icon = 'fa-keyboard';
                        break;
                    case 'slow_transitions':
                        content = `Slow transitions: <strong>${area.items.join(', ')}</strong>`;
                        icon = 'fa-exchange-alt';
                        break;
                    case 'weak_fingers':
                        content = `Work on <strong>${area.items.join(', ')}</strong> finger(s)`;
                        icon = 'fa-hand-paper';
                        break;
                }
                
                item.innerHTML = `
                    <i class="fas ${icon}"></i>
                    <span>${content} (${area.priority} priority)</span>
                `;
                
                this.focusList.appendChild(item);
            });
        } else {
            this.focusList.innerHTML = `
                <div class="focus-item">
                    <i class="fas fa-check-circle"></i>
                    <span>Keep going! No major issues detected.</span>
                </div>
            `;
        }
        
        // Update insights
        this.insightsList.innerHTML = '';
        
        if (analysis.insights && analysis.insights.length > 0) {
            analysis.insights.forEach(insight => {
                const item = document.createElement('div');
                item.className = 'insight-item';
                item.innerHTML = `
                    <i class="fas fa-lightbulb"></i>
                    <span>${insight}</span>
                `;
                this.insightsList.appendChild(item);
            });
        } else {
            this.insightsList.innerHTML = `
                <div class="insight-item">
                    <i class="fas fa-info-circle"></i>
                    <span>Continue typing to get personalized insights.</span>
                </div>
            `;
        }
    }

    updateFocusChars(analysis) {
        this.focusChars.clear();
        
        if (analysis.focus_areas) {
            analysis.focus_areas.forEach(area => {
                if (area.type === 'high_error_keys') {
                    area.items.forEach(key => {
                        this.focusChars.add(key.toLowerCase());
                    });
                }
            });
        }
        
        // Re-render to highlight focus characters
        this.renderText();
    }

    async showDetailedAnalysis() {
        try {
            const response = await fetch(`/api/analysis/${this.sessionId}`);
            if (response.ok) {
                const analysis = await response.json();
                this.populateAnalysisModal(analysis);
                this.modal.style.display = 'flex';
                document.body.style.overflow = 'hidden';
            }
        } catch (error) {
            console.error('Failed to fetch detailed analysis:', error);
        }
    }

    populateAnalysisModal(analysis) {
        // Populate keys chart
        const keysChart = document.getElementById('keys-chart');
        if (analysis.key_level && Object.keys(analysis.key_level).length > 0) {
            let html = '<div class="metrics-grid">';
            Object.entries(analysis.key_level).forEach(([key, stats]) => {
                const errorRate = (stats.error_rate * 100).toFixed(1);
                const avgTime = stats.avg_time_ms.toFixed(0);
                
                html += `
                    <div class="metric-item">
                        <div class="metric-header">"${key}"</div>
                        <div class="metric-bar" style="--error-rate: ${errorRate}%"></div>
                        <div class="metric-details">
                            <div><i class="fas fa-times-circle"></i> ${errorRate}% error</div>
                            <div><i class="fas fa-clock"></i> ${avgTime}ms avg</div>
                            <div><i class="fas fa-hashtag"></i> ${stats.sample_size} samples</div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            keysChart.innerHTML = html;
        } else {
            keysChart.innerHTML = '<p class="no-data">Not enough data for key analysis</p>';
        }
        
        // Populate bigrams chart
        const bigramsChart = document.getElementById('bigrams-chart');
        if (analysis.bigram_level && Object.keys(analysis.bigram_level).length > 0) {
            let html = '<div class="metrics-grid">';
            Object.entries(analysis.bigram_level).forEach(([bigram, stats]) => {
                html += `
                    <div class="metric-item">
                        <div class="metric-header">"${bigram}"</div>
                        <div class="metric-details">
                            <div><i class="fas fa-clock"></i> ${stats.avg_transition_time_ms.toFixed(0)}ms</div>
                            <div><i class="fas fa-hashtag"></i> ${stats.sample_size} samples</div>
                        </div>
                    </div>
                `;
            });
            html += '</div>';
            bigramsChart.innerHTML = html;
        } else {
            bigramsChart.innerHTML = '<p class="no-data">Not enough data for bigram analysis</p>';
        }
        
        // Populate fingers chart
        const fingersChart = document.getElementById('fingers-chart');
        if (analysis.finger_level && Object.keys(analysis.finger_level).length > 0) {
            let html = '<div class="finger-grid">';
            Object.entries(analysis.finger_level).forEach(([finger, stats]) => {
                const accuracy = (stats.accuracy * 100).toFixed(0);
                html += `
                    <div class="finger-item">
                        <div class="finger-name">${finger}</div>
                        <div class="finger-bar" style="--accuracy: ${accuracy}%"></div>
                        <div class="finger-stats">${accuracy}% accuracy</div>
                    </div>
                `;
            });
            html += '</div>';
            fingersChart.innerHTML = html;
        } else {
            fingersChart.innerHTML = '<p class="no-data">Not enough data for finger analysis</p>';
        }
        
        // Populate hands chart
        const handsChart = document.getElementById('hands-chart');
        if (analysis.hand_level && Object.keys(analysis.hand_level).length > 0) {
            let html = '<div class="hand-comparison">';
            if (analysis.hand_level.left && analysis.hand_level.right) {
                const leftAcc = (analysis.hand_level.left.accuracy * 100).toFixed(0);
                const rightAcc = (analysis.hand_level.right.accuracy * 100).toFixed(0);
                
                html += `
                    <div class="hand-item left-hand">
                        <div class="hand-label"><i class="fas fa-hand-point-left"></i> Left</div>
                        <div class="hand-bar" style="--accuracy: ${leftAcc}%"></div>
                        <div class="hand-stats">${leftAcc}% accuracy</div>
                    </div>
                    <div class="hand-item right-hand">
                        <div class="hand-label"><i class="fas fa-hand-point-right"></i> Right</div>
                        <div class="hand-bar" style="--accuracy: ${rightAcc}%"></div>
                        <div class="hand-stats">${rightAcc}% accuracy</div>
                    </div>
                `;
            }
            html += '</div>';
            handsChart.innerHTML = html;
        } else {
            handsChart.innerHTML = '<p class="no-data">Not enough data for hand analysis</p>';
        }
    }

    hideModal() {
        this.modal.style.display = 'none';
        document.body.style.overflow = 'auto';
        this.typingInput.focus();
    }

    switchTab(e) {
        const tabId = e.target.dataset.tab;
        
        // Update active tab button
        this.tabBtns.forEach(btn => btn.classList.remove('active'));
        e.target.classList.add('active');
        
        // Show corresponding tab content
        this.tabContents.forEach(content => {
            content.classList.remove('active');
            if (content.id === `${tabId}-tab`) {
                content.classList.add('active');
            }
        });
    }

    async resetSession() {
        if (confirm('Reset your session? Your data will be saved, but current stats will reset.')) {
            await this.startNewSession();
            this.stats = {
                score: 0,
                streak: 0,
                maxStreak: 0,
                combo: 1.0,
                errors: 0,
                wpm: 0,
                accuracy: 100,
                totalChars: 0,
                correctChars: 0,
                sessionChars: 0,
                sessionCorrect: 0
            };
            this.updateStatsDisplay();
        }
    }

    async saveProgress() {
        if (!this.userId) return;
        
        const originalText = this.saveBtn.innerHTML;
        this.saveBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
        
        try {
            const response = await fetch('/api/save_progress', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ user_id: this.userId })
            });
            
            if (response.ok) {
                this.saveBtn.innerHTML = '<i class="fas fa-check"></i> Saved';
                setTimeout(() => this.saveBtn.innerHTML = originalText, 2000);
            }
        } catch (e) { console.error(e); this.saveBtn.innerHTML = 'Error'; }
    }

    // Auth methods (can be connected to UI later)
    async login(username, password) {
        try {
            const response = await fetch('/api/login', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, password })
            });
            const data = await response.json();
            if (response.ok) {
                this.userId = data.user_id;
                localStorage.setItem('typing_user_id', this.userId);
                console.log('Logged in!', data);
                this.startNewSession(); // Restart with user context
                return true;
            }
        } catch (e) { console.error(e); }
        return false;
    }

    async register(username, password) {
        try {
            const response = await fetch('/api/register', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ username, password })
            });
            if (response.ok) {
                console.log('Registered!');
                return await this.login(username, password);
            }
        } catch (e) { console.error(e); }
        return false;
    }
    
    logout() {
        this.userId = null;
        localStorage.removeItem('typing_user_id');
        localStorage.removeItem('level');
        window.location.href = 'login.html';
    }
}

// Initialize the game when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Protect the page: if not logged in, redirect to login page.
    const userId = localStorage.getItem('typing_user_id');
    if (!userId && !window.location.pathname.endsWith('login.html')) {
        window.location.href = 'login.html';
        return; // Stop further execution
    }

    // --- Theme Handling ---
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    const themeIndicator = document.createElement('div');
    
    // Create theme change indicator
    themeIndicator.className = 'theme-indicator';
    document.body.appendChild(themeIndicator);
    
    // Check for saved theme preference or use system preference
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    if (savedTheme === 'night' || (!savedTheme && prefersDark)) {
        body.classList.add('night-mode');
        if (themeToggle) themeToggle.checked = true;
    }
    
    // Show temporary theme indicator
    function showThemeIndicator(text) {
        themeIndicator.textContent = text;
        themeIndicator.classList.add('show');
        
        setTimeout(() => {
            themeIndicator.classList.remove('show');
        }, 2000);
    }
    
    if (themeToggle) {
        // Toggle theme on switch
        themeToggle.addEventListener('change', function() {
            if (this.checked) {
                body.classList.add('night-mode');
                localStorage.setItem('theme', 'night');
                showThemeIndicator('Night mode on');
            } else {
                body.classList.remove('night-mode');
                localStorage.setItem('theme', 'light');
                showThemeIndicator('Light mode on');
            }
        });
    }
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!localStorage.getItem('theme')) {
            if (e.matches) {
                body.classList.add('night-mode');
                if (themeToggle) themeToggle.checked = true;
            } else {
                body.classList.remove('night-mode');
                if (themeToggle) themeToggle.checked = false;
            }
        }
    });

    // Initialize game
    window.typingGame = new TypingGame();
    
    // Add global keyboard shortcut for help
    document.addEventListener('keydown', (e) => {
        if (e.key === '?' && e.shiftKey) {
            window.typingGame.showDetailedAnalysis();
        }
        if (e.key === 'r' && e.ctrlKey) {
            window.typingGame.requestNewText();
        }
    });
});