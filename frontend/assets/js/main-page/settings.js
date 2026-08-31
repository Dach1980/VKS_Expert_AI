// ===== SETTINGS =====

var DEFAULT_SETTINGS = {
  theme: 'light',
  notifications: true,
  autoSave: true,
  language: 'ru',
  defaultSection: 'ВК',
};

const NORMS_STORAGE_API = 'http://127.0.0.1:8000/api/norms/storage';

function getSettings() {
  if (typeof appSettings !== 'undefined' && appSettings) return appSettings;
  return DEFAULT_SETTINGS;
}

function renderSettings() {
  var settings = getSettings();
  var themeSelect = document.getElementById('settingTheme');
  var notifications = document.getElementById('settingNotifications');
  var autoSave = document.getElementById('settingAutoSave');
  var languageSelect = document.getElementById('settingLanguage');
  var sectionSelect = document.getElementById('settingDefaultSection');
  if (themeSelect) themeSelect.value = settings.theme || 'light';
  if (notifications) notifications.checked = settings.notifications !== false;
  if (autoSave) autoSave.checked = settings.autoSave !== false;
  if (languageSelect) languageSelect.value = settings.language || 'ru';
  if (sectionSelect) sectionSelect.value = settings.defaultSection || 'ВК';
  renderStorageSettings();
}

function saveSettings() {
  if (typeof appSettings === 'undefined') return;
  var themeSelect = document.getElementById('settingTheme');
  var notifications = document.getElementById('settingNotifications');
  var autoSave = document.getElementById('settingAutoSave');
  var languageSelect = document.getElementById('settingLanguage');
  var sectionSelect = document.getElementById('settingDefaultSection');
  if (themeSelect) appSettings.theme = themeSelect.value;
  if (notifications) appSettings.notifications = notifications.checked;
  if (autoSave) appSettings.autoSave = autoSave.checked;
  if (languageSelect) appSettings.language = languageSelect.value;
  if (autoSave) appSettings.autoSave = autoSave.checked;
  if (languageSelect) appSettings.language = languageSelect.value;
  if (sectionSelect) appSettings.defaultSection = sectionSelect.value;
  applySettings();
  showToast('Настройки сохранены', 'success');
}

function applySettings() {
  var settings = getSettings();
  document.documentElement.setAttribute('data-theme', settings.theme === 'dark' ? 'dark' : 'light');
  document.documentElement.setAttribute('lang', settings.language || 'ru');
}

function resetSettings() {
  if (typeof appSettings === 'undefined') return;
  Object.assign(appSettings, DEFAULT_SETTINGS);
  renderSettings();
  applySettings();
  showToast('Настройки сброшены', 'info');
}

// ------------------------------------------------------------
// Хранилище данных
// ------------------------------------------------------------
// Пути хранения относятся к backend Project Expert AI. Браузер не
// может напрямую открыть серверную папку Windows, поэтому «Обзор»
// показывает содержимое серверного каталога через backend API.

function renderStorageSettings() {
  var fields = [
    { id: 'dbPath', value: 'data/database.db' },
    { id: 'docsPath', value: 'knowledge/regulations + data/documents' },
    { id: 'cachePath', value: 'knowledge/index + data/cache' },
  ];

  fields.forEach(function (field) {
    var input = document.getElementById(field.id);
    if (!input) return;
    input.value = field.value;
    input.readOnly = true;
    input.title = 'Путь управляется сервером Project Expert AI';
  });

  ['dbPath', 'docsPath', 'cachePath'].forEach(function (id) {
    var input = document.getElementById(id);
    if (!input) return;
    var group = input.parentElement;
    if (!group) return;
    var button = group.querySelector('button');
    if (button) {
      // Кнопка больше не отключается: для серверных каталогов «Обзор»
      // открывает безопасный просмотр через API.
      button.disabled = false;
      button.textContent = 'Обзор';
      button.setAttribute('onclick', 'selectFolder(\'' + id + '\')');
      button.title = 'Просмотреть серверное хранилище';
    }
  });

  document.querySelectorAll('button').forEach(function (button) {
    var onclick = button.getAttribute('onclick') || '';
    if (onclick.indexOf('saveStoragePaths') !== -1 || onclick.indexOf('resetStoragePaths') !== -1) {
      button.style.display = 'none';
    }
  });
}

function closeStorageBrowser() {
  var modal = document.getElementById('storageBrowserModal');
  if (modal) modal.remove();
}

function showStorageBrowser(data, requestedId) {
  closeStorageBrowser();
  var modal = document.createElement('div');
  modal.id = 'storageBrowserModal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:9999;display:flex;align-items:center;justify-content:center;padding:24px;';
  var indexes = Array.isArray(data.indexes) ? data.indexes : [];
  var rows = indexes.length ? indexes.map(function(item){
    var size = item.size_bytes || 0;
    var mb = (size / 1024 / 1024).toFixed(2);
    return '<div style="padding:9px 0;border-bottom:1px solid var(--border-color);font-size:12px;">'+
      '<div style="font-weight:600;">'+escapeStorageHtml(item.path)+'</div>'+
      '<div style="color:var(--text-secondary);margin-top:3px;">index.faiss · '+mb+' МБ</div></div>';
  }).join('') : '<div style="padding:20px 0;color:var(--text-secondary);">Индексированных нормативных версий пока нет.</div>';
  modal.innerHTML = '<div style="width:min(760px,100%);max-height:80vh;overflow:auto;background:var(--card-bg,#fff);border:1px solid var(--border-color);border-radius:12px;padding:20px;box-shadow:0 18px 60px rgba(0,0,0,.2);">'+
    '<div style="display:flex;justify-content:space-between;gap:16px;align-items:center;"><div><div style="font-size:17px;font-weight:700;">Векторная база</div><div style="margin-top:4px;color:var(--text-secondary);font-size:12px;">Backend: '+escapeStorageHtml(data.backend||'не определён')+'</div></div><button class="btn btn-secondary btn-sm" onclick="closeStorageBrowser()">Закрыть</button></div>'+
    '<div style="margin-top:14px;padding:10px 12px;border-radius:8px;background:var(--background-secondary,#f5f5f5);font-size:12px;"><strong>Папка:</strong> '+escapeStorageHtml(data.relative_path||data.path||'')+'</div>'+
    '<div style="margin-top:14px;">'+rows+'</div>'+
    '<div style="margin-top:14px;font-size:11px;color:var(--text-secondary);">Запрошено из: '+escapeStorageHtml(requestedId||'storage')+'</div>'+
    '</div>';
  modal.addEventListener('click', function(event){ if(event.target===modal) closeStorageBrowser(); });
  document.body.appendChild(modal);
}

function escapeStorageHtml(value) {
  return String(value == null ? '' : value).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\"/g,'&quot;').replace(/'/g,'&#039;');
}

async function selectFolder(requestedId) {
  try {
    var response = await fetch(NORMS_STORAGE_API);
    var data = await response.json();
    if (!response.ok) throw new Error(data.detail || ('HTTP '+response.status));
    showStorageBrowser(data, requestedId);
  } catch (error) {
    showToast('Не удалось открыть серверное хранилище: '+error.message, 'error');
  }
}

function saveStoragePaths() {
  showToast('Пути хранения управляются backend и не изменяются из интерфейса.', 'info');
}

function resetStoragePaths() {
  renderStorageSettings();
  showToast('Используются серверные пути Project Expert AI.', 'info');
}

function initSettings() {
  renderSettings();
  applySettings();
}

document.addEventListener('DOMContentLoaded', function () {
  initSettings();
});

window.renderSettings = renderSettings;
window.saveSettings = saveSettings;
window.resetSettings = resetSettings;
window.applySettings = applySettings;
window.selectFolder = selectFolder;
window.closeStorageBrowser = closeStorageBrowser;
window.saveStoragePaths = saveStoragePaths;
window.resetStoragePaths = resetStoragePaths;