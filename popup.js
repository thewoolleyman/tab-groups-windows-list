/**
 * Tab Groups & Windows List - Chrome Extension Popup
 *
 * Features:
 * - 3-level hierarchy: Window > Tab Group > Tab
 * - Correct tab ordering (interleaved groups and ungrouped tabs)
 * - Live UI updates via Chrome event listeners
 */

// Global state
let container;
let helpModal;

/**
 * Set the container element (for testing purposes)
 * @param {HTMLElement} el - Container element
 */
function setContainer(el) {
  container = el;
}

/**
 * Generate a meaningful window name from tab titles
 * @param {Array} tabs - Array of tab objects
 * @returns {string} - Window name (max 60 chars)
 */
function generateWindowName(tabs) {
  if (!tabs || tabs.length === 0) return '';

  const MAX_TAB_NAME_LENGTH = 12;
  const MAX_TOTAL_LENGTH = 60;
  const SEPARATOR = ', ';

  const parts = [];
  let currentLength = 0;

  for (const tab of tabs) {
    const title = tab.title || 'New Tab';
    let truncatedTitle = title;

    // Truncate individual tab name if > 12 chars
    if (title.length > MAX_TAB_NAME_LENGTH) {
      truncatedTitle = title.substring(0, MAX_TAB_NAME_LENGTH) + '...';
    }

    // Calculate what the new length would be
    const separatorLength = parts.length > 0 ? SEPARATOR.length : 0;
    const newLength = currentLength + separatorLength + truncatedTitle.length;

    // Stop if adding this would exceed 60 chars
    if (newLength > MAX_TOTAL_LENGTH && parts.length > 0) {
      break;
    }

    parts.push(truncatedTitle);
    currentLength = newLength;
  }

  return parts.join(SEPARATOR);
}

/**
 * Debounce function to prevent rapid re-renders
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} - Debounced function
 */
function debounce(fn, delay) {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Refresh the UI by re-fetching data and re-rendering
 * Exposed globally for testing and event handlers
 */
async function refreshUI() {
  if (!container) return;

  try {
    // Preserve expansion state before re-render
    const expandedWindows = new Set();
    const expandedGroups = new Set();

    /* istanbul ignore next - expansion state preservation tested via E2E */
    document.querySelectorAll('.window-item.expanded').forEach(el => {
      const title = el.querySelector('.window-header span:last-child')?.textContent;
      if (title) expandedWindows.add(title);
    });

    /* istanbul ignore next - expansion state preservation tested via E2E */
    document.querySelectorAll('.group-item.expanded').forEach(el => {
      const title = el.querySelector('.group-header span:last-child')?.textContent;
      if (title) expandedGroups.add(title);
    });

    // Fetch fresh data
    const windows = await chrome.windows.getAll({ populate: true });
    const groups = await chrome.tabGroups.query({});

    if (windows.length === 0) {
      container.innerHTML = '<div class="empty-msg">No windows found.</div>';
      return;
    }

    container.innerHTML = ''; // Clear current content

    // Build Hierarchy: Window -> Group -> Tab
    windows.forEach(win => {
      const windowEl = document.createElement('div');
      windowEl.className = 'window-item';

      // Generate window name from tab titles
      /* istanbul ignore next - tabs always present with populate:true */
      const windowTitle = generateWindowName(win.tabs || []);

      // Restore expansion state
      if (expandedWindows.has(windowTitle)) {
        windowEl.classList.add('expanded');
      }

      const windowHeader = document.createElement('div');
      windowHeader.className = 'window-header';

      const expandIcon = document.createElement('span');
      expandIcon.className = 'expand-icon';
      expandIcon.textContent = '▶';

      const windowTitleEl = document.createElement('span');
      windowTitleEl.textContent = windowTitle;

      windowHeader.appendChild(expandIcon);
      windowHeader.appendChild(windowTitleEl);

      // Click to focus window
      windowHeader.addEventListener('click', (e) => {
        /* istanbul ignore next - UI branch tested via E2E */
        if (e.target === expandIcon) {
          windowEl.classList.toggle('expanded');
        } else {
          chrome.windows.update(win.id, { focused: true });
        }
      });

      // Toggle expansion on icon click
      expandIcon.addEventListener('click', (e) => {
        e.stopPropagation();
        windowEl.classList.toggle('expanded');
      });

      const windowContent = document.createElement('div');
      windowContent.className = 'content';

      // Find groups in this window
      const groupsInWindow = groups.filter(g => g.windowId === win.id);

      // Build ordered content: interleave groups and ungrouped tabs by tab index
      const orderedContent = buildOrderedWindowContent(win, groupsInWindow);

      // Render ordered content
      orderedContent.forEach(item => {
        /* istanbul ignore else - only 'tab' and 'group' types exist */
        if (item.type === 'tab') {
          const tabEl = createTabElement(item.tab, win.id, true);
          windowContent.appendChild(tabEl);
        } else if (item.type === 'group') {
          const groupEl = createGroupElement(item.group, item.tabs, win.id, expandedGroups);
          windowContent.appendChild(groupEl);
        }
      });

      windowEl.appendChild(windowHeader);
      windowEl.appendChild(windowContent);
      container.appendChild(windowEl);
    });

  } catch (error) {
    console.error('Error loading data:', error);
    container.innerHTML = '<div class="empty-msg">Error loading windows.</div>';
  }
}

// Expose refreshUI globally for testing
window.refreshUI = refreshUI;

/**
 * Set up Chrome event listeners for live UI updates
 */
function setupEventListeners() {
  // Debounced refresh to prevent rapid re-renders
  const debouncedRefresh = debounce(refreshUI, 150);

  // Tab events
  if (chrome.tabs) {
    chrome.tabs.onCreated.addListener(debouncedRefresh);
    chrome.tabs.onRemoved.addListener(debouncedRefresh);
    chrome.tabs.onUpdated.addListener(debouncedRefresh);
    chrome.tabs.onMoved.addListener(debouncedRefresh);
    chrome.tabs.onAttached.addListener(debouncedRefresh);
    chrome.tabs.onDetached.addListener(debouncedRefresh);
  }

  // Tab group events
  if (chrome.tabGroups) {
    chrome.tabGroups.onCreated.addListener(debouncedRefresh);
    chrome.tabGroups.onRemoved.addListener(debouncedRefresh);
    chrome.tabGroups.onUpdated.addListener(debouncedRefresh);
  }

  // Window events
  if (chrome.windows) {
    chrome.windows.onCreated.addListener(debouncedRefresh);
    chrome.windows.onRemoved.addListener(debouncedRefresh);
  }

  // Mark that listeners were registered (for testing)
  window._chromeListenersRegistered = true;
}

// Initialize on DOM ready
/* istanbul ignore next - browser initialization, tested via E2E */
document.addEventListener('DOMContentLoaded', async () => {
  container = document.getElementById('groups-container');
  const helpBtn = document.getElementById('help-btn');
  helpModal = document.getElementById('help-modal');
  const closeModal = document.getElementById('close-modal');

  // Help Modal Logic
  if (helpBtn) helpBtn.addEventListener('click', () => helpModal.style.display = 'block');
  if (closeModal) closeModal.addEventListener('click', () => helpModal.style.display = 'none');
  if (helpModal) helpModal.addEventListener('click', (e) => { if (e.target === helpModal) helpModal.style.display = 'none'; });

  // Set up live update event listeners
  setupEventListeners();

  // Initial render
  await refreshUI();
});

function createTabElement(tab, windowId, isUngrouped = false) {
  const tabEl = document.createElement('div');
  tabEl.className = isUngrouped ? 'tab-item ungrouped-tab' : 'tab-item';

  if (tab.favIconUrl) {
    const icon = document.createElement('img');
    icon.className = 'tab-icon';
    icon.src = tab.favIconUrl;
    tabEl.appendChild(icon);
  }

  const title = document.createElement('span');
  title.textContent = tab.title || 'New Tab';
  tabEl.appendChild(title);

  tabEl.addEventListener('click', () => {
    chrome.windows.update(windowId, { focused: true });
    chrome.tabs.update(tab.id, { active: true });
  });

  return tabEl;
}

function mapColor(chromeColor) {
  const colors = {
    'grey': '#5a5a5a',
    'blue': '#1a73e8',
    'red': '#d93025',
    'yellow': '#f9ab00',
    'green': '#188038',
    'pink': '#d01884',
    'purple': '#a142f4',
    'cyan': '#007b83',
    'orange': '#fa903e'
  };
  return colors[chromeColor] || '#5a5a5a';
}

/**
 * Build ordered window content - interleaves groups and ungrouped tabs by tab index
 * @param {Object} win - Window object with tabs array
 * @param {Array} groupsInWindow - Array of group objects in this window
 * @returns {Array} - Array of items in correct order: {type: 'group'|'tab', ...data}
 */
function buildOrderedWindowContent(win, groupsInWindow) {
  // Get all tabs with their indices (use array index if index property not available)
  const tabsWithIndex = win.tabs.map((tab, arrayIndex) => ({
    ...tab,
    index: tab.index !== undefined ? tab.index : arrayIndex
  }));

  // Build ordered content array
  const result = [];
  const processedGroupIds = new Set();

  // Sort tabs by index
  const sortedTabs = [...tabsWithIndex].sort((a, b) => a.index - b.index);

  for (const tab of sortedTabs) {
    if (tab.groupId === -1) {
      // Ungrouped tab - add directly
      result.push({ type: 'tab', tab });
    } else if (!processedGroupIds.has(tab.groupId)) {
      // First tab of a group - add the group with all its tabs
      const group = groupsInWindow.find(g => g.id === tab.groupId);
      if (group) {
        const tabsInGroup = tabsWithIndex.filter(t => t.groupId === group.id);
        result.push({ type: 'group', group, tabs: tabsInGroup });
        processedGroupIds.add(tab.groupId);
      }
    }
    // Skip subsequent tabs of already-processed groups
  }

  return result;
}

/**
 * Create a group element with its tabs
 * @param {Object} group - Group object
 * @param {Array} tabs - Array of tabs in this group
 * @param {number} windowId - Window ID for click handlers
 * @param {Set} expandedGroups - Set of group titles that should be expanded
 * @returns {HTMLElement} - The group DOM element
 */
function createGroupElement(group, tabs, windowId, expandedGroups = new Set()) {
  const groupEl = document.createElement('div');
  groupEl.className = 'group-item';

  const groupTitle = group.title || '(Untitled Group)';

  // Restore expansion state
  if (expandedGroups.has(groupTitle)) {
    groupEl.classList.add('expanded');
  }

  const groupHeader = document.createElement('div');
  groupHeader.className = 'group-header';

  const gExpandIcon = document.createElement('span');
  gExpandIcon.className = 'expand-icon';
  gExpandIcon.textContent = '▶';

  const gDot = document.createElement('div');
  gDot.className = 'group-dot';
  gDot.style.backgroundColor = mapColor(group.color);

  const gTitle = document.createElement('span');
  gTitle.textContent = groupTitle;

  groupHeader.appendChild(gExpandIcon);
  groupHeader.appendChild(gDot);
  groupHeader.appendChild(gTitle);

  // Click to focus first tab in group
  groupHeader.addEventListener('click', (e) => {
    if (e.target === gExpandIcon) {
      groupEl.classList.toggle('expanded');
    } else {
      const firstTab = tabs[0];
      if (firstTab) {
        chrome.windows.update(windowId, { focused: true });
        chrome.tabs.update(firstTab.id, { active: true });
      }
    }
  });

  gExpandIcon.addEventListener('click', (e) => {
    e.stopPropagation();
    groupEl.classList.toggle('expanded');
  });

  const groupContent = document.createElement('div');
  groupContent.className = 'content';

  // Add tabs in this group
  tabs.forEach(tab => {
    const tabEl = createTabElement(tab, windowId);
    groupContent.appendChild(tabEl);
  });

  groupEl.appendChild(groupHeader);
  groupEl.appendChild(groupContent);

  return groupEl;
}

// Export for testing (CommonJS module support)
/* istanbul ignore next - environment detection for module exports */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    debounce,
    mapColor,
    generateWindowName,
    buildOrderedWindowContent,
    createGroupElement,
    createTabElement,
    refreshUI,
    setupEventListeners,
    setContainer
  };
}
