const linksInput = document.querySelector('#links');
const queue = document.querySelector('#queue');
const linkCount = document.querySelector('#link-count');
const queueCount = document.querySelector('#queue-count');
const queueStatus = document.querySelector('#queue-status');
const toast = document.querySelector('#toast');

function links() {
  return [...new Set(linksInput.value.split(/\r?\n/).map(x => x.trim()).filter(x => x && !x.startsWith('#')))]
    .filter(x => /^https?:\/\//i.test(x));
}

function renderQueue(states = {}) {
  const items = links();
  linkCount.textContent = `${items.length} link${items.length === 1 ? '' : 's'} ready`;
  queueCount.textContent = items.length;
  queue.classList.toggle('empty', items.length === 0);
  queue.innerHTML = items.length ? items.map((url, i) => `<div class="queue-item"><span class="queue-number">${String(i + 1).padStart(2, '0')}</span><span class="queue-url" title="${url}">${url}</span><span class="queue-state ${states[i] === 'Done' ? 'done' : ''}">${states[i] || 'Ready'}</span></div>`).join('') : '<div class="empty-icon">⌁</div><p>Your links will appear here.</p>';
}

function showToast(message) { toast.textContent = message; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 3500); }

linksInput.value = localStorage.getItem('wavequeue-links') || '';
linksInput.addEventListener('input', () => { localStorage.setItem('wavequeue-links', linksInput.value); renderQueue(); });
document.querySelector('#clear-btn').addEventListener('click', () => { linksInput.value = ''; localStorage.removeItem('wavequeue-links'); renderQueue(); });
document.querySelector('#download-btn').addEventListener('click', async () => {
  const items = links();
  if (!items.length) return showToast('Add at least one valid URL first.');
  const states = Object.fromEntries(items.map((_, i) => [i, 'Queued'])); renderQueue(states); queueStatus.textContent = 'Processing locally…';
  try {
    const response = await fetch('/api/download', { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({urls: items}) });
    if (!response.ok) throw new Error(await response.text());
    const result = await response.json();
    // Use a native attachment URL so desktop and mobile browsers save it to
    // their normal Downloads location instead of treating it as media.
    for (const file of result.files || []) {
      const link = document.createElement('a');
      link.href = `/api/file?name=${encodeURIComponent(file)}`;
      link.download = file;
      document.body.appendChild(link); link.click(); link.remove();
      await new Promise(resolve => setTimeout(resolve, 500));
    }
    Object.keys(states).forEach(i => states[i] = 'Done'); renderQueue(states); queueStatus.textContent = 'All downloads complete'; showToast(`Downloaded ${result.count || items.length} MP3 file(s) to your browser Downloads folder.`);
  } catch (error) { Object.keys(states).forEach(i => states[i] = 'Backend needed'); renderQueue(states); queueStatus.textContent = 'Downloader unavailable'; showToast('Start server.py, then try again.'); console.error(error); }
});
renderQueue();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');
