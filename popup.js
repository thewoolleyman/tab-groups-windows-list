document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('groups-container');
  const helpBtn = document.getElementById('help-btn');
  const helpModal = document.getElementById('help-modal');
  const closeModal = document.getElementById('close-modal');

  // Help Modal Logic
  if (helpBtn) helpBtn.addEventListener('click', () => helpModal.style.display = 'block');
  if (closeModal) closeModal.addEventListener('click', () => helpModal.style.display = 'none');
  if (helpModal) helpModal.addEventListener('click', (e) => { if (e.target === helpModal) helpModal.style.display = 'none'; });

  try {
    // 1. Fetch all data
    const windows = await chrome.windows.getAll({ populate: true });
    const groups = await chrome.tabGroups.query({});

    if (windows.length === 0) {
      container.innerHTML = '<div class="empty-msg">No windows found.</div>';
      return;
    }

    container.innerHTML = ''; // Clear loading message

    // 2. Build Hierarchy: Window -> Group -> Tab
    windows.forEach(win => {
      const windowEl = document.createElement('div');
      windowEl.className = 'window-item';
      
      const windowHeader = document.createElement('div');
      windowHeader.className = 'window-header';
      
      const expandIcon = document.createElement('span');
      expandIcon.className = 'expand-icon';
      expandIcon.textContent = '▶';
      
      const windowTitle = document.createElement('span');
      // Use custom name if available, otherwise fallback to Window [ID]
      windowTitle.textContent = win.title || `Window ${win.id}`;
      
      windowHeader.appendChild(expandIcon);
      windowHeader.appendChild(windowTitle);
      
      // Click to focus window
      windowHeader.addEventListener('click', (e) => {
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
      
      // Also find tabs in this window that are NOT in a group
      const ungroupedTabs = win.tabs.filter(t => t.groupId === -1);

      // Add Groups
      groupsInWindow.forEach(group => {
        const groupEl = document.createElement('div');
        groupEl.className = 'group-item';
        
        const groupHeader = document.createElement('div');
        groupHeader.className = 'group-header';
        
        const gExpandIcon = document.createElement('span');
        gExpandIcon.className = 'expand-icon';
        gExpandIcon.textContent = '▶';
        
        const gDot = document.createElement('div');
        gDot.className = 'group-dot';
        gDot.style.backgroundColor = mapColor(group.color);
        
        const gTitle = document.createElement('span');
        gTitle.textContent = group.title || '(Untitled Group)';
        
        groupHeader.appendChild(gExpandIcon);
        groupHeader.appendChild(gDot);
        groupHeader.appendChild(gTitle);
        
        // Click to focus first tab in group
        groupHeader.addEventListener('click', (e) => {
          if (e.target === gExpandIcon) {
            groupEl.classList.toggle('expanded');
          } else {
            const firstTab = win.tabs.find(t => t.groupId === group.id);
            if (firstTab) {
              chrome.windows.update(win.id, { focused: true });
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

        // Add Tabs in this group
        const tabsInGroup = win.tabs.filter(t => t.groupId === group.id);
        tabsInGroup.forEach(tab => {
          const tabEl = createTabElement(tab, win.id);
          groupContent.appendChild(tabEl);
        });

        groupEl.appendChild(groupHeader);
        groupEl.appendChild(groupContent);
        windowContent.appendChild(groupEl);
      });

      // Add Ungrouped Tabs
      if (ungroupedTabs.length > 0) {
        ungroupedTabs.forEach(tab => {
          const tabEl = createTabElement(tab, win.id);
          tabEl.style.marginLeft = '24px'; // Align with groups
          windowContent.appendChild(tabEl);
        });
      }

      windowEl.appendChild(windowHeader);
      windowEl.appendChild(windowContent);
      container.appendChild(windowEl);
    });

  } catch (error) {
    console.error('Error loading data:', error);
    container.innerHTML = '<div class="empty-msg">Error loading windows.</div>';
  }
});

function createTabElement(tab, windowId) {
  const tabEl = document.createElement('div');
  tabEl.className = 'tab-item';
  
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
