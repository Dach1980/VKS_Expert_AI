        // ===== RENDER: NORMS =====
        function renderNorms() {
            var grid = document.getElementById('normsGrid');
            if (normsData.length === 0) {
                grid.innerHTML = '<div style="text-align:center;padding:48px;color:var(--text-secondary);">Нет нормативных документов. Перетащите файлы или нажмите на зону загрузки.</div>';
                return;
            }
            var html = '';
            for (var i = 0; i < normsData.length; i++) {
                var norm = normsData[i];
                html += '<div class="norm-card">';
                html += '<div class="norm-card-header">';
                html += '<div style="flex:1;">';
                html += '<div class="norm-card-title">' + escapeHtml(norm.title) + '</div>';
                html += '<div class="norm-card-subtitle">' + escapeHtml(norm.subtitle) + '</div>';
                html += '</div>';
                html += '<button class="delete-btn" onclick="deleteNorm(' + norm.id + ')" title="Удалить">';
                html += '<svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">';
                html += '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>';
                html += '</svg></button>';
                html += '</div>';
                html += '<div class="norm-card-meta">';
                html += '<span>📅 ' + norm.date + '</span>';
                html += '<span>📑 ' + norm.points + ' пунктов</span>';
                html += '<span>📂 ' + norm.sections.join(', ') + '</span>';
                html += '</div>';
                if (norm.status === 'indexed') {
                    html += '<div class="progress-bar"><div class="progress-fill" style="width:' + norm.progress + '%"></div></div>';
                    html += '<div style="margin-top:8px;font-size:12px;color:var(--text-secondary);">Индексировано: ' + norm.progress + '%</div>';
                } else if (norm.status === 'indexing') {
                    html += '<div class="progress-bar"><div class="progress-fill" style="width:' + norm.progress + '%"></div></div>';
                    html += '<div style="margin-top:8px;font-size:12px;color:var(--accent);">Индексация: ' + norm.progress + '%</div>';
                } else {
                    html += '<div style="margin-top:12px;"><span class="status-badge info">Ожидает индексации</span></div>';
                }
                html += '<div class="norm-card-actions">';
                html += '<button class="btn btn-secondary btn-sm">Просмотр</button>';
                html += '<button class="btn btn-secondary btn-sm">Информация</button>';
                html += '</div>';
                html += '</div>';
            }
            grid.innerHTML = html;
        }

                // ===== DELETE FUNCTIONS =====
        function deleteNorm(id) {
            var norm = normsData.find(function(n) { return n.id === id; });
            normsData = normsData.filter(function(n) { return n.id !== id; });
            renderNorms();
            updateBadges();
            showToast('Нормативный документ удалён: ' + (norm ? norm.title : ''), 'success');
        }

        
        // ===== INDEX ALL NORMS =====
        function indexAllNorms() {
            var pending = normsData.filter(function(n) { return n.status !== 'indexed'; });
            if (pending.length === 0 && normsData.length > 0) {
                showToast('Все документы уже индексированы', 'info');
                return;
            }
            if (normsData.length === 0) {
                showToast('Нет документов для индексации', 'error');
                return;
            }

            var progressEl = document.getElementById('indexingProgress');
            var fillEl = document.getElementById('indexingFill');
            var labelEl = document.getElementById('indexingLabel');
            progressEl.classList.add('active');

            showToast('Начата индексация нормативных документов...', 'info');

            var total = normsData.length;
            var done = 0;

            function indexNext() {
                if (done >= total) {
                    fillEl.style.width = '100%';
                    labelEl.textContent = 'Индексация завершена!';
                    setTimeout(function() {
                        progressEl.classList.remove('active');
                    }, 1500);
                    showToast('Индексация завершена: ' + total + ' документ(ов)', 'success');
                    return;
                }

                var norm = normsData[done];
                norm.status = 'indexing';
                norm.progress = 0;
                renderNorms();

                var progress = 0;
                var interval = setInterval(function() {
                    progress += 20;
                    norm.progress = Math.min(progress, 100);
                    fillEl.style.width = Math.round(((done + norm.progress / 100) / total) * 100) + '%';
                    labelEl.textContent = 'Индексация: ' + norm.title + ' (' + norm.progress + '%)';
                    renderNorms();

                    if (progress >= 100) {
                        clearInterval(interval);
                        norm.status = 'indexed';
                        norm.progress = 100;
                        done++;
                        renderNorms();
                        setTimeout(indexNext, 200);
                    }
                }, 100);
            }

            indexNext();
        }

                // ===== FILE UPLOAD: DROPZONE CLICK =====
        function handleDropzoneClick(type) {
            var input = document.createElement('input');
            input.type = 'file';
            input.multiple = true;
            if (type === 'norms') {
                input.accept = '.pdf,.docx,.txt';
            } else {
                input.accept = '.pdf,.dwg,.docx';
            }
            input.addEventListener('change', function(e) {
                if (e.target.files && e.target.files.length > 0) {
                    handleFiles(e.target.files, type);
                }
            });
            input.click();
        }

        // ===== FILE UPLOAD: DRAG & DROP =====
        function handleDrop(e, type) {
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.classList.remove('dragover');

            var files = e.dataTransfer.files;
            if (files && files.length > 0) {
                handleFiles(files, type);
            }
        }

        function handleDragOver(e) {
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.classList.add('dragover');
        }

        function handleDragLeave(e) {
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.classList.remove('dragover');
        }

        function handleFiles(files, type) {
            var count = files.length;
            for (var i = 0; i < files.length; i++) {
                var file = files[i];
                if (type === 'norms') {
                    var newNorm = {
                        id: nextNormId++,
                        title: file.name.replace(/\.[^/.]+$/, ''),
                        subtitle: file.name,
                        date: new Date().toISOString().split('T')[0],
                        points: Math.floor(Math.random() * 500) + 100,
                        status: 'pending',
                        progress: 0,
                        sections: ['ВК'],
                        fileName: file.name
                    };
                    normsData.push(newNorm);
                } else {
                    var newDoc = {
                        id: nextDocId++,
                        name: file.name,
                        size: formatFileSize(file.size),
                        date: new Date().toISOString().split('T')[0],
                        status: 'new',
                        sheets: Math.floor(Math.random() * 30) + 5,
                        section: 'ВК',
                        checked: false
                    };
                    docsData.push(newDoc);
                }
            }

            if (type === 'norms') {
                renderNorms();
            } else {
                renderDocs();
            }

            updateBadges();
            showToast('Добавлено файлов: ' + count, 'success');
        }

        function formatFileSize(bytes) {
            if (bytes < 1024) return bytes + ' Б';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' КБ';
            return (bytes / (1024 * 1024)).toFixed(1) + ' МБ';
        }
