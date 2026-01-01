// Main entry point for the popup
document.addEventListener('DOMContentLoaded', async () => {
  const container = document.getElementById('groups-container');

  try {
    // 1. Get all tab groups
    const groups = await chrome.tabGroups.query({});
    
    if (groups.length === 0) {
      container.innerHTML = '<div class="empty-msg">No tab groups found.</div>';
      return;
    }

    // 2. Get all windows to map windowId to window name (if any)
    const windows = await chrome.windows.getAll({ populate: false });
    const windowMap = {};
    windows.forEach(win => {
      // Note: Chrome doesn't have a built-in "window name" property in the API 
      // unless set via chrome.windows.update({titlePreface: ...}) or similar.
      // We'll use "Window [ID]" or the title if available.
      // In Manifest V3, we can try to get the window title if it's set.
      windowMap[win.id] = win.title || `Window ${win.id}`;
    });

    // 3. For each group, find which windows it belongs to
    // A group belongs to a single window, but we need to find which one.
    for (const group of groups) {
      const groupItem = document.createElement('div');
      groupItem.className = 'group-item';

      const header = document.createElement('div');
      header.className = 'group-header';
      
      // Color dot
      const dot = document.createElement('div');
      dot.className = 'group-color-dot';
      dot.style.backgroundColor = mapColor(group.color);
      
      const title = document.createElement('div');
      title.className = 'group-title';
      title.textContent = group.title || `(Untitled Group)`;
      
      const expandIcon = document.createElement('span');
      expandIcon.className = 'expand-icon';
      expandIcon.textContent = '▶';

      header.appendChild(dot);
      header.appendChild(title);
      header.appendChild(expandIcon);
      
      const windowList = document.createElement('div');
      windowList.className = 'window-list';
      
      // Find the window name for this group
      const windowName = windowMap[group.windowId] || `Unknown Window`;
      const windowItem = document.createElement('div');
      windowItem.className = 'window-item';
      windowItem.textContent = `📍 ${windowName}`;
      windowList.appendChild(windowItem);

      header.addEventListener('click', () => {
        groupItem.classList.toggle('expanded');
        expandIcon.textContent = groupItem.classList.contains('expanded') ? '▼' : '▶';
      });

      groupItem.appendChild(header);
      groupItem.appendChild(windowList);
      container.appendChild(groupItem);
    }
  } catch (error) {
    console.error('Error loading tab groups:', error);
    container.innerHTML = '<div class="empty-msg">Error loading groups.</div>';
  }
});

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
