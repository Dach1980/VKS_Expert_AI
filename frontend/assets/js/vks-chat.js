
        // ===== CONFIGURATION =====
        const LMSTUDIO_URL = 'http://127.0.0.1:1234/v1';
        let chatHistory = [];
        let isProcessing = false;

        // ===== SIDEBAR TOGGLES =====
        function toggleLeftSidebar() {
            const sidebar = document.getElementById('leftSidebar');
            sidebar.classList.toggle('collapsed');
        }

        function toggleRightPanel() {
            const panel = document.getElementById('rightPanel');
            panel.classList.toggle('collapsed');
        }

        // ===== CHAT FUNCTIONS =====
        function goToHome() {
            // Пробуем вернуться на предыдущую страницу
            if (window.history.length > 1) {
                window.history.back();
            } else {
                // Если истории нет, показываем сообщение
                alert('Откройте test-page.html для возврата на главную страницу');
            }
        }

        function newChat() {
            chatHistory = [];
            const chatMessages = document.getElementById('chatMessages');
            chatMessages.innerHTML = `
                <div class="welcome-screen" id="welcomeScreen">
                    <div class="welcome-icon">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                        </svg>
                    </div>
                    <h2>База знаний</h2>
                    <p>Задайте вопрос по нормативным документам или проектной документации. Система найдёт релевантную информацию и предоставит ответ с ссылками на источники.</p>
                    
                    <div class="example-queries">
                        <div class="example-query" onclick="sendExample('Какие требования к диаметру труб для внутреннего водопровода согласно СП 30.13330.2020?')">
                            Какие требования к диаметру труб для внутреннего водопровода согласно СП 30.13330.2020?
                        </div>
                        <div class="example-query" onclick="sendExample('Что говорит СП 30.13330.2020 о скорости воды в трубах и как её рассчитать?')">
                            Что говорит СП 30.13330.2020 о скорости воды в трубах и как её рассчитать?
                        </div>
                        <div class="example-query" onclick="sendExample('Как рассчитать потери напора в трубопроводе по формуле Дарси-Вейсбаха?')">
                            Как рассчитать потери напора в трубопроводе по формуле Дарси-Вейсбаха?
                        </div>
                    </div>
                </div>
            `;
        }

        function sendExample(question) {
            document.getElementById('chatInput').value = question;
            sendMessage();
        }

        function handleInputKeydown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        function autoResizeInput(textarea) {
            textarea.style.height = 'auto';
            textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
        }

        function addMessageToChat(role, content, sources = null) {
            const welcomeScreen = document.getElementById('welcomeScreen');
            if (welcomeScreen) {
                welcomeScreen.remove();
            }

            const chatMessages = document.getElementById('chatMessages');
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;

            const avatar = role === 'user' ? 'Вы' : 'AI';
            
            let sourcesHTML = '';
            if (sources && sources.length > 0) {
                sourcesHTML = `
                    <div class="sources-block">
                        <div class="sources-title">Источники</div>
                        ${sources.map(source => `
                            <div class="source-item">
                                <span class="source-doc">${source.document}</span>
                                <div>${source.text}</div>
                            </div>
                        `).join('')}
                    </div>
                `;
            }

            messageDiv.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    ${content}
                    ${sourcesHTML}
                </div>
            `;

            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function showTypingIndicator() {
            const chatMessages = document.getElementById('chatMessages');
            const typingDiv = document.createElement('div');
            typingDiv.className = 'message ai';
            typingDiv.id = 'typingIndicator';
            typingDiv.innerHTML = `
                <div class="message-avatar">AI</div>
                <div class="message-content">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            `;
            chatMessages.appendChild(typingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }

        function hideTypingIndicator() {
            const typingIndicator = document.getElementById('typingIndicator');
            if (typingIndicator) {
                typingIndicator.remove();
            }
        }

        // ===== SEND MESSAGE TO LM STUDIO =====
        async function sendMessage() {
            const input = document.getElementById('chatInput');
            const message = input.value.trim();
            
            if (!message || isProcessing) return;

            const searchInNorms = document.getElementById('searchInNorms').checked;
            const searchInDocs = document.getElementById('searchInDocs').checked;

            // Hide welcome screen
            const welcomeScreen = document.getElementById('welcomeScreen');
            if (welcomeScreen) {
                welcomeScreen.remove();
            }

            // Add user message
            addMessageToChat('user', message);
            input.value = '';
            input.style.height = 'auto';

            // Show typing indicator
            showTypingIndicator();
            isProcessing = true;

            try {
                // Direct call to LM Studio API
                const response = await fetch(`${LMSTUDIO_URL}/chat/completions`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        model: 'local-model',
                        messages: [
                            {
                                role: 'system',
                                content: 'Вы эксперт по нормоконтролю в строительстве, специализирующийся на внутренних водопроводных и канализационных системах. Отвечайте на вопросы на основе нормативных документов (СП, ГОСТ, СНиП). Если информация не найдена, честно скажите об этом.'
                            },
                            {
                                role: 'user',
                                content: message
                            }
                        ],
                        temperature: 0.3,
                        max_tokens: 2000,
                        stream: false
                    })
                });

                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }

                const data = await response.json();
                const answer = data.choices[0].message.content;

                // Add AI response
                addMessageToChat('ai', answer);

            } catch (error) {
                console.error('Error:', error);
                addMessageToChat('ai', `Ошибка при обработке запроса: ${error.message}. Убедитесь, что LM Studio запущена на ${LMSTUDIO_URL}`);
            } finally {
                hideTypingIndicator();
                isProcessing = false;
            }
        }

        // ===== INITIALIZATION =====
        document.addEventListener('DOMContentLoaded', function() {
            console.log('Knowledge Base Chat initialized');
            console.log('LM Studio URL:', LMSTUDIO_URL);
        });