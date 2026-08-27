// ============================================================
// utils.js
// ОБЩИЕ ФУНКЦИИ ПРИЛОЖЕНИЯ
// ============================================================
//
// Этот файл должен загружаться после state.js,
// но ДО остальных файлов:
//
// state.js
// utils.js
// dashboard.js
// norms.js
// documents.js
// checks.js
// reports.js
// settings.js
//
// ============================================================

console.log('[Utils] utils.js загружен');

// ============================================================
// HTML ESCAPE
// ============================================================
//
// Защищает текст, поступающий из названий файлов,
// описаний, нормативов и т.д. от интерпретации как HTML.
//

function escapeHtml(value) {
  if (value === null || value === undefined) {
    return '';
  }

  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ============================================================
// FORMAT FILE SIZE
// ============================================================

function formatFileSize(bytes) {
  var size = Number(bytes);

  if (!isFinite(size) || size < 0) {
    return '0 Б';
  }

  if (size < 1024) {
    return size + ' Б';
  }

  if (size < 1024 * 1024) {
    return (size / 1024).toFixed(1) + ' КБ';
  }

  if (size < 1024 * 1024 * 1024) {
    return (size / (1024 * 1024)).toFixed(1) + ' МБ';
  }

  return (size / (1024 * 1024 * 1024)).toFixed(1) + ' ГБ';
}

// ============================================================
// DATE FORMAT
// ============================================================

function formatDate(date) {
  if (!date) {
    return '';
  }

  var value = date;

  if (!(date instanceof Date)) {
    value = new Date(date);
  }

  if (isNaN(value.getTime())) {
    return String(date);
  }

  return value.toLocaleDateString('ru-RU');
}

// ============================================================
// ISO DATE
// ============================================================

function getCurrentDateISO() {
  return new Date().toISOString().split('T')[0];
}

// ============================================================
// CURRENT DATETIME
// ============================================================

function getCurrentDateTime() {
  return new Date().toLocaleString('ru-RU');
}

// ============================================================
// DEBOUNCE
// ============================================================

function debounce(func, delay) {
  var timeoutId = null;

  return function () {
    var context = this;
    var args = arguments;

    clearTimeout(timeoutId);

    timeoutId = setTimeout(function () {
      func.apply(context, args);
    }, delay);
  };
}

// ============================================================
// THROTTLE
// ============================================================

function throttle(func, delay) {
  var waiting = false;

  return function () {
    if (waiting) {
      return;
    }

    var context = this;
    var args = arguments;

    func.apply(context, args);

    waiting = true;

    setTimeout(function () {
      waiting = false;
    }, delay);
  };
}

// ============================================================
// SAFE JSON PARSE
// ============================================================

function safeJsonParse(value, fallback) {
  if (fallback === undefined) {
    fallback = null;
  }

  try {
    return JSON.parse(value);
  } catch (error) {
    console.error('[Utils] Ошибка JSON:', error);
    return fallback;
  }
}

// ============================================================
// SHOW TOAST
// ============================================================
//
// Универсальное уведомление.
//
// Поддерживаемые типы:
// success
// error
// warning
// info
//

function showToast(message, type) {
  type = type || 'info';

  var container = document.getElementById('toastContainer');

  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';

    container.style.position = 'fixed';
    container.style.right = '24px';
    container.style.bottom = '24px';
    container.style.zIndex = '99999';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '10px';

    document.body.appendChild(container);
  }

  var toast = document.createElement('div');

  toast.className = 'toast toast-' + type;

  toast.style.minWidth = '280px';
  toast.style.maxWidth = '420px';
  toast.style.padding = '14px 18px';
  toast.style.borderRadius = '10px';
  toast.style.background = '#ffffff';
  toast.style.border = '1px solid #e2e8f0';
  toast.style.boxShadow = '0 10px 30px rgba(0, 0, 0, 0.12)';
  toast.style.fontSize = '14px';
  toast.style.lineHeight = '1.4';
  toast.style.color = '#1e293b';
  toast.style.cursor = 'pointer';
  toast.style.transition = 'opacity 0.2s ease, transform 0.2s ease';

  var typeColors = {
    success: '#16a34a',
    error: '#dc2626',
    warning: '#d97706',
    info: '#2563eb',
  };

  toast.style.borderLeft = '4px solid ' + (typeColors[type] || typeColors.info);

  toast.textContent = message;

  toast.addEventListener('click', function () {
    removeToast(toast);
  });

  container.appendChild(toast);

  setTimeout(function () {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';

    setTimeout(function () {
      removeToast(toast);
    }, 200);
  }, 4000);
}

// ============================================================
// REMOVE TOAST
// ============================================================

function removeToast(toast) {
  if (!toast || !toast.parentNode) {
    return;
  }

  toast.parentNode.removeChild(toast);
}

// ============================================================
// NAVIGATION
// ============================================================

function navigateTo(section) {
  if (!section) {
    return;
  }

  console.log('[Utils] Переход в раздел:', section);

  if (typeof appState !== 'undefined') {
    appState.currentSection = section;
  }

  // Скрываем все секции
  var sections = document.querySelectorAll('.section');

  for (var i = 0; i < sections.length; i++) {
    sections[i].classList.remove('active');
  }

  // Показываем нужную секцию
  var target = document.getElementById('section-' + section);

  if (!target) {
    // Возможный альтернативный ID
    target = document.getElementById(section);
  }

  if (target) {
    target.classList.add('active');
  }

  // Обновляем активный пункт меню
  var navItems = document.querySelectorAll('[data-section]');

  for (var j = 0; j < navItems.length; j++) {
    var itemSection = navItems[j].getAttribute('data-section');

    if (itemSection === section) {
      navItems[j].classList.add('active');
    } else {
      navItems[j].classList.remove('active');
    }
  }

  // Вызываем renderer соответствующего раздела
  if (section === 'dashboard') {
    if (typeof renderDashboardTable === 'function') {
      renderDashboardTable();
    }

    if (typeof updateDashboardMetrics === 'function') {
      updateDashboardMetrics();
    }
  }

  if (section === 'norms') {
    if (typeof renderNorms === 'function') {
      renderNorms();
    }
  }

  if (section === 'documents') {
    if (typeof renderDocs === 'function') {
      renderDocs();
    }
  }

  if (section === 'checks') {
    if (typeof renderChecks === 'function') {
      renderChecks();
    }
  }

  if (section === 'reports') {
    if (typeof renderReports === 'function') {
      renderReports();
    }
  }
}

// ============================================================
// UPDATE BADGES
// ============================================================
//
// Обновляет счетчики в интерфейсе.
//
// Поддерживаемые ID:
// docsBadge
// normsBadge
// checksBadge
// reportsBadge
//
// Также поддерживаются варианты с названием section.
//

function updateBadges() {
  var docsCount = Array.isArray(docsData) ? docsData.length : 0;
  var normsCount = Array.isArray(normsData) ? normsData.length : 0;
  var checksCount = Array.isArray(checksData) ? checksData.length : 0;
  var reportsCount = Array.isArray(reportsData) ? reportsData.length : 0;

  updateElementText('docsBadge', docsCount);
  updateElementText('normsBadge', normsCount);
  updateElementText('checksBadge', checksCount);
  updateElementText('reportsBadge', reportsCount);

  updateElementText('documentsBadge', docsCount);
  updateElementText('normativeBadge', normsCount);
  updateElementText('normsCount', normsCount);
  updateElementText('documentsCount', docsCount);
  updateElementText('checksCount', checksCount);
  updateElementText('reportsCount', reportsCount);
}

// ============================================================
// UPDATE ELEMENT TEXT
// ============================================================

function updateElementText(id, value) {
  var element = document.getElementById(id);

  if (element) {
    element.textContent = value;
  }
}

// ============================================================
// GET ELEMENT
// ============================================================

function $(selector) {
  return document.querySelector(selector);
}

// ============================================================
// GET ELEMENTS
// ============================================================

function $$(selector) {
  return document.querySelectorAll(selector);
}

// ============================================================
// GENERATE ID
// ============================================================

function generateId(prefix) {
  prefix = prefix || 'id';

  return (
    prefix +
    '_' +
    Date.now().toString(36) +
    '_' +
    Math.random().toString(36).substring(2, 8)
  );
}

// ============================================================
// CLONE OBJECT
// ============================================================

function cloneObject(value) {
  if (value === null || value === undefined) {
    return value;
  }

  try {
    return JSON.parse(JSON.stringify(value));
  } catch (error) {
    console.error('[Utils] Ошибка клонирования объекта:', error);
    return value;
  }
}

// ============================================================
// ARRAY CHECK
// ============================================================

function isArray(value) {
  return Array.isArray(value);
}

// ============================================================
// EMPTY VALUE CHECK
// ============================================================

function isEmpty(value) {
  return (
    value === null ||
    value === undefined ||
    value === '' ||
    (Array.isArray(value) && value.length === 0)
  );
}

// ============================================================
// NUMBER CHECK
// ============================================================

function isNumber(value) {
  return typeof value === 'number' && isFinite(value);
}

// ============================================================
// LIMIT STRING
// ============================================================

function truncateText(value, maxLength) {
  if (value === null || value === undefined) {
    return '';
  }

  var text = String(value);

  if (!maxLength || text.length <= maxLength) {
    return text;
  }

  return text.substring(0, Math.max(0, maxLength - 3)) + '...';
}

// ============================================================
// ESCAPE ATTRIBUTE
// ============================================================

function escapeAttribute(value) {
  return escapeHtml(value);
}

// ============================================================
// NORMALIZE FILE NAME
// ============================================================

function removeFileExtension(fileName) {
  if (!fileName) {
    return '';
  }

  return String(fileName).replace(/\.[^/.]+$/, '');
}

// ============================================================
// LOCAL STORAGE
// ============================================================

function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch (error) {
    console.error('[Utils] Ошибка сохранения в localStorage:', error);
    return false;
  }
}

function loadFromStorage(key, fallback) {
  if (fallback === undefined) {
    fallback = null;
  }

  try {
    var value = localStorage.getItem(key);

    if (value === null) {
      return fallback;
    }

    return JSON.parse(value);
  } catch (error) {
    console.error('[Utils] Ошибка чтения localStorage:', error);
    return fallback;
  }
}

function removeFromStorage(key) {
  try {
    localStorage.removeItem(key);
    return true;
  } catch (error) {
    console.error('[Utils] Ошибка удаления из localStorage:', error);
    return false;
  }
}

// ============================================================
// MODAL HELPERS
// ============================================================

function openModal(modalId) {
  var modal = document.getElementById(modalId);

  if (!modal) {
    console.warn('[Utils] Модальное окно не найдено:', modalId);
    return;
  }

  modal.classList.add('active');
  modal.style.display = 'flex';
}

function closeModal(modalId) {
  var modal = document.getElementById(modalId);

  if (!modal) {
    return;
  }

  modal.classList.remove('active');
  modal.style.display = 'none';
}

// ============================================================
// DATE FOR FILE NAME
// ============================================================

function getDateForFileName() {
  var date = new Date();

  var year = date.getFullYear();
  var month = String(date.getMonth() + 1).padStart(2, '0');
  var day = String(date.getDate()).padStart(2, '0');

  return year + '-' + month + '-' + day;
}

// ============================================================
// DOWNLOAD BLOB
// ============================================================

function downloadBlob(blob, fileName) {
  if (!blob) {
    showToast('Не удалось создать файл', 'error');
    return false;
  }

  var url = URL.createObjectURL(blob);
  var link = document.createElement('a');

  link.href = url;
  link.download = fileName || 'download';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  setTimeout(function () {
    URL.revokeObjectURL(url);
  }, 1000);

  return true;
}

// ============================================================
// DOWNLOAD TEXT
// ============================================================

function downloadText(text, fileName, mimeType) {
  mimeType = mimeType || 'text/plain;charset=utf-8';

  var blob = new Blob([text], {
    type: mimeType,
  });

  return downloadBlob(blob, fileName);
}

// ============================================================
// COPY TO CLIPBOARD
// ============================================================

function copyToClipboard(text) {
  if (!navigator.clipboard) {
    showToast('Буфер обмена недоступен', 'error');
    return Promise.reject(new Error('Clipboard API unavailable'));
  }

  return navigator.clipboard
    .writeText(String(text))
    .then(function () {
      showToast('Скопировано в буфер обмена', 'success');
    })
    .catch(function (error) {
      console.error('[Utils] Ошибка копирования:', error);
      showToast('Не удалось скопировать данные', 'error');
      throw error;
    });
}

// ============================================================
// ARRAY REMOVE BY ID
// ============================================================

function removeById(array, id) {
  if (!Array.isArray(array)) {
    return array;
  }

  return array.filter(function (item) {
    return item.id !== id;
  });
}

// ============================================================
// ARRAY FIND BY ID
// ============================================================

function findById(array, id) {
  if (!Array.isArray(array)) {
    return null;
  }

  return (
    array.find(function (item) {
      return item.id === id;
    }) || null
  );
}

// ============================================================
// RANDOM INTEGER
// ============================================================

function randomInt(min, max) {
  min = Math.ceil(min);
  max = Math.floor(max);

  return Math.floor(Math.random() * (max - min + 1)) + min;
}

// ============================================================
// WAIT
// ============================================================

function wait(ms) {
  return new Promise(function (resolve) {
    setTimeout(resolve, ms);
  });
}

// ============================================================
// SAFE DOM EVENT
// ============================================================

function addEventListenerSafe(elementId, eventName, handler) {
  var element = document.getElementById(elementId);

  if (!element) {
    console.warn(
      '[Utils] Элемент не найден для события:',
      elementId,
      eventName,
    );
    return false;
  }

  element.addEventListener(eventName, handler);

  return true;
}

// ============================================================
// DOCUMENT READY
// ============================================================

function onDocumentReady(callback) {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', callback);
  } else {
    callback();
  }
}

// ============================================================
// EXPORT TO WINDOW
// ============================================================

window.escapeHtml = escapeHtml;
window.escapeAttribute = escapeAttribute;
window.formatFileSize = formatFileSize;
window.formatDate = formatDate;
window.getCurrentDateISO = getCurrentDateISO;
window.getCurrentDateTime = getCurrentDateTime;

window.debounce = debounce;
window.throttle = throttle;

window.safeJsonParse = safeJsonParse;

window.showToast = showToast;
window.removeToast = removeToast;

window.navigateTo = navigateTo;
window.updateBadges = updateBadges;
window.updateElementText = updateElementText;

window.$ = $;
window.$$ = $$;

window.generateId = generateId;
window.cloneObject = cloneObject;

window.isArray = isArray;
window.isEmpty = isEmpty;
window.isNumber = isNumber;

window.truncateText = truncateText;
window.removeFileExtension = removeFileExtension;

window.saveToStorage = saveToStorage;
window.loadFromStorage = loadFromStorage;
window.removeFromStorage = removeFromStorage;

window.openModal = openModal;
window.closeModal = closeModal;

window.getDateForFileName = getDateForFileName;

window.downloadBlob = downloadBlob;
window.downloadText = downloadText;

window.copyToClipboard = copyToClipboard;

window.removeById = removeById;
window.findById = findById;

window.randomInt = randomInt;
window.wait = wait;

window.addEventListenerSafe = addEventListenerSafe;
window.onDocumentReady = onDocumentReady;

console.log('[Utils] utils.js готов');
