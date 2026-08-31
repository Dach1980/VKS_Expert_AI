// ===== SETTINGS =====

var DEFAULT_SETTINGS = {
  theme: 'light',
  notifications: true,
  autoSave: true,
  language: 'ru',
  defaultSection: 'ВК',
};

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
// должен менять произвольные пути файловой системы сервера.
// Поэтому «Обзор» здесь не нужен и намеренно не открывает
// системный каталог пользователя.

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
      button.disabled = true;
      button.textContent = 'Серверный путь';
      button.removeAttribute('onclick');
      button.title = 'Путь определяется backend';
    }
  });

  document.querySelectorAll('button').forEach(function (button) {
    var onclick = button.getAttribute('onclick') || '';
    if (onclick.indexOf('saveStoragePaths') !== -1 || onclick.indexOf('resetStoragePaths') !== -1) {
      button.style.display = 'none';
    }
  });
}

function selectFolder() {
  showToast('Пути хранения управляются backend и не выбираются из браузера.', 'info');
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
window.saveStoragePaths = saveStoragePaths;
window.resetStoragePaths = resetStoragePaths;
