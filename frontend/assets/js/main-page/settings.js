// ===== SETTINGS =====

// ===== SETTINGS DEFAULTS =====

var DEFAULT_SETTINGS = {
  theme: 'light',
  notifications: true,
  autoSave: true,
  language: 'ru',
  defaultSection: 'ВК',
};

// ===== GET SETTINGS =====

function getSettings() {
  if (typeof appSettings !== 'undefined' && appSettings) {
    return appSettings;
  }

  return DEFAULT_SETTINGS;
}

// ===== RENDER SETTINGS =====

function renderSettings() {
  var settings = getSettings();

  var themeSelect = document.getElementById('settingTheme');

  var notifications = document.getElementById('settingNotifications');

  var autoSave = document.getElementById('settingAutoSave');

  var languageSelect = document.getElementById('settingLanguage');

  var sectionSelect = document.getElementById('settingDefaultSection');

  if (themeSelect) {
    themeSelect.value = settings.theme || 'light';
  }

  if (notifications) {
    notifications.checked = settings.notifications !== false;
  }

  if (autoSave) {
    autoSave.checked = settings.autoSave !== false;
  }

  if (languageSelect) {
    languageSelect.value = settings.language || 'ru';
  }

  if (sectionSelect) {
    sectionSelect.value = settings.defaultSection || 'ВК';
  }
}

// ===== SAVE SETTINGS =====

function saveSettings() {
  if (typeof appSettings === 'undefined') {
    return;
  }

  var themeSelect = document.getElementById('settingTheme');

  var notifications = document.getElementById('settingNotifications');

  var autoSave = document.getElementById('settingAutoSave');

  var languageSelect = document.getElementById('settingLanguage');

  var sectionSelect = document.getElementById('settingDefaultSection');

  if (themeSelect) {
    appSettings.theme = themeSelect.value;
  }

  if (notifications) {
    appSettings.notifications = notifications.checked;
  }

  if (autoSave) {
    appSettings.autoSave = autoSave.checked;
  }

  if (languageSelect) {
    appSettings.language = languageSelect.value;
  }

  if (sectionSelect) {
    appSettings.defaultSection = sectionSelect.value;
  }

  applySettings();

  showToast('Настройки сохранены', 'success');
}

// ===== APPLY SETTINGS =====

function applySettings() {
  var settings = getSettings();

  // ===== THEME =====

  if (settings.theme === 'dark') {
    document.body.classList.add('dark-theme');
  } else {
    document.body.classList.remove('dark-theme');
  }

  // ===== LANGUAGE =====

  document.documentElement.setAttribute('lang', settings.language || 'ru');
}

// ===== RESET SETTINGS =====

function resetSettings() {
  if (typeof appSettings === 'undefined') {
    return;
  }

  appSettings.theme = DEFAULT_SETTINGS.theme;

  appSettings.notifications = DEFAULT_SETTINGS.notifications;

  appSettings.autoSave = DEFAULT_SETTINGS.autoSave;

  appSettings.language = DEFAULT_SETTINGS.language;

  appSettings.defaultSection = DEFAULT_SETTINGS.defaultSection;

  renderSettings();

  applySettings();

  showToast('Настройки сброшены', 'info');
}

// ===== INITIALIZE SETTINGS =====

function initSettings() {
  renderSettings();
  applySettings();
}

// ===== SETTINGS EVENTS =====

document.addEventListener('DOMContentLoaded', function () {
  initSettings();
});
