// ===== STORAGE PATHS MANAGEMENT =====
function selectFolder(inputId) {
  const input = document.getElementById(inputId);
  if (!input) return;

  // В реальном приложении здесь будет диалог выбора папки
  // Для демо просто показываем подсказку
  const paths = {
    dbPath: 'База данных',
    docsPath: 'Документация',
    reportsPath: 'Отчёты',
    vectorDbPath: 'Векторная база',
    cachePath: 'Кэш эмбеддингов',
  };

  const pathName = paths[inputId] || 'папку';
  showToast(
    `Выберите ${pathName.toLowerCase()} через диалог (в реальном приложении)`,
    'info',
  );

  // Симуляция выбора папки
  const simulatedPaths = {
    dbPath: '/home/user/vk-normcontrol/data/database.db',
    docsPath: '/home/user/vk-normcontrol/data/documents',
    reportsPath: '/home/user/vk-normcontrol/data/reports',
    vectorDbPath: '/home/user/vk-normcontrol/data/vectordb',
    cachePath: '/home/user/vk-normcontrol/data/cache',
  };

  input.value = simulatedPaths[inputId] || input.value;
}

function saveStoragePaths() {
  const paths = {
    dbPath: document.getElementById('dbPath')?.value || './data/database.db',
    docsPath: document.getElementById('docsPath')?.value || './data/documents',
    reportsPath:
      document.getElementById('reportsPath')?.value || './data/reports',
    vectorDbPath:
      document.getElementById('vectorDbPath')?.value || './data/vectordb',
    cachePath: document.getElementById('cachePath')?.value || './data/cache',
  };

  localStorage.setItem('storagePaths', JSON.stringify(paths));
  showToast('Пути хранения сохранены', 'success');
}

function resetStoragePaths() {
  const defaultPaths = {
    dbPath: './data/database.db',
    docsPath: './data/documents',
    reportsPath: './data/reports',
    vectorDbPath: './data/vectordb',
    cachePath: './data/cache',
  };

  document.getElementById('dbPath').value = defaultPaths.dbPath;
  document.getElementById('docsPath').value = defaultPaths.docsPath;
  document.getElementById('reportsPath').value = defaultPaths.reportsPath;
  document.getElementById('vectorDbPath').value = defaultPaths.vectorDbPath;
  document.getElementById('cachePath').value = defaultPaths.cachePath;

  localStorage.removeItem('storagePaths');
  showToast('Пути сброшены по умолчанию', 'info');
}

function loadStoragePaths() {
  const saved = localStorage.getItem('storagePaths');
  if (!saved) return;

  try {
    const paths = JSON.parse(saved);
    if (paths.dbPath) document.getElementById('dbPath').value = paths.dbPath;
    if (paths.docsPath)
      document.getElementById('docsPath').value = paths.docsPath;
    if (paths.reportsPath)
      document.getElementById('reportsPath').value = paths.reportsPath;
    if (paths.vectorDbPath)
      document.getElementById('vectorDbPath').value = paths.vectorDbPath;
    if (paths.cachePath)
      document.getElementById('cachePath').value = paths.cachePath;
  } catch (e) {
    console.error('Ошибка загрузки путей:', e);
  }
}
