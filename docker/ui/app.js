'use strict';
(() => {
  const $ = id => document.getElementById(id);
  const active = status => status === 'pending' || status === 'working';
  const statusNames = {ok: 'Completed', working: 'Running', pending: 'Pending', failed: 'Failed'};
  const PAGE_SIZE = 8;
  let jobs = [], page = 1, refreshPromise = null, lastUpdated = null, deleting = null, openJobId = null;
  const dateFormat = new Intl.DateTimeFormat(undefined, {month: 'short', day: 'numeric'});
  const timeFormat = new Intl.DateTimeFormat(undefined, {hour: '2-digit', minute: '2-digit'});

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function dateText(value, full = false) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 'Unknown date' : full ? date.toLocaleString() : dateFormat.format(date);
  }
  function jobPath(job) { return '/api/v1/jobs/' + encodeURIComponent(job.ID); }
  function badge(status) { return element('span', 'badge ' + (Object.hasOwn(statusNames, status) ? status : ''), statusNames[status] || status || 'Unknown'); }
  function showMessage(message, error = false) {
    $('form-message').textContent = message;
    $('form-message').className = 'form-message' + (error ? ' error' : '');
    $('form-message').hidden = false;
  }
  async function request(path, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 20000);
    try {
      const response = await fetch(path, {...options, signal: controller.signal, cache: 'no-store'});
      const text = await response.text();
      if (!response.ok) {
        let message = text;
        try { message = JSON.parse(text).message || text; } catch (_) { /* Plain-text engine error. */ }
        const error = new Error(('HTTP ' + response.status + ': ' + message).slice(0, 500));
        error.status = response.status;
        throw error;
      }
      if (!text.trim()) return null;
      return JSON.parse(text);
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('The request timed out. Check the engine and try refreshing.');
      throw error;
    } finally { clearTimeout(timer); }
  }

  function renderJobs() {
    const query = $('filter-text').value.trim().toLocaleLowerCase();
    const filter = $('filter-status').value;
    const filtered = jobs.filter(job => {
      const haystack = [job.Name, job.ID, ...(job.Data?.keywords || [])].join(' ').toLocaleLowerCase();
      return (!query || haystack.includes(query)) && (filter === 'all' || (filter === 'active' ? active(job.Status) : job.Status === filter));
    });
    const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    page = Math.min(Math.max(1, page), pages);
    const slice = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
    $('job-rows').replaceChildren();
    $('jobs-table-wrap').hidden = filtered.length === 0;
    $('jobs-empty').hidden = filtered.length > 0;
    $('empty-title').textContent = jobs.length ? 'No matching searches' : 'Your first search starts here';
    $('empty-description').textContent = jobs.length ? 'Try another keyword or change the status filter.' : 'Create a search to begin building your lead list.';
    for (const job of slice) {
      const row = element('tr');
      const nameCell = element('td');
      const nameButton = element('button', 'job-name', job.Name || 'Untitled search');
      nameButton.type = 'button';
      nameButton.title = job.Name || 'Untitled search';
      nameButton.setAttribute('aria-label', 'View details for ' + (job.Name || job.ID));
      nameButton.addEventListener('click', () => viewJob(job));
      const keywords = (job.Data?.keywords || []).join(' · ');
      const queryLine = element('span', 'job-query', keywords || job.ID);
      queryLine.dir = 'auto';
      queryLine.title = keywords || job.ID;
      nameCell.append(nameButton, queryLine);
      const statusCell = element('td'); statusCell.append(badge(job.Status));
      const dateCell = element('td', 'job-date', dateText(job.Date)); dateCell.title = dateText(job.Date, true);
      const actionsCell = element('td');
      const actions = element('div', 'row-actions');
      if (job.Status === 'ok') {
        const link = element('a', 'download-link', 'CSV ↓');
        link.href = jobPath(job) + '/download';
        link.setAttribute('aria-label', 'Download CSV for ' + (job.Name || job.ID));
        actions.append(link);
      }
      const remove = element('button', 'delete-job', '×'); remove.type = 'button';
      remove.setAttribute('aria-label', 'Delete job ' + (job.Name || job.ID));
      remove.title = active(job.Status) ? 'Wait for this job to finish before deleting it' : 'Delete job';
      remove.disabled = active(job.Status);
      remove.addEventListener('click', () => {
        deleting = job;
        $('delete-name').textContent = job.Name || job.ID;
        $('delete-error').hidden = true;
        $('confirm-delete').disabled = false;
        $('delete-dialog').showModal();
        $('cancel-delete').focus();
      });
      actions.append(remove); actionsCell.append(actions); row.append(nameCell, statusCell, dateCell, actionsCell);
      $('job-rows').append(row);
    }
    $('results-count').textContent = filtered.length ? `${(page - 1) * PAGE_SIZE + 1}–${Math.min(page * PAGE_SIZE, filtered.length)} of ${filtered.length} jobs` : '0 matching jobs';
    $('page-count').textContent = `${page} / ${pages}`;
    $('previous').disabled = page <= 1;
    $('next').disabled = page >= pages;
  }

  function refreshJobs() {
    if (refreshPromise) return refreshPromise;
    $('refresh').disabled = true;
    refreshPromise = (async () => {
      try {
        const data = await request('/api/v1/jobs');
        if (data !== null && !Array.isArray(data)) throw new Error('The engine returned an unexpected job list.');
        if ((data || []).some(job => !job || typeof job.ID !== 'string' || job.Data?.keywords && !Array.isArray(job.Data.keywords))) throw new Error('The engine returned an invalid job.');
        jobs = (data || []).sort((a, b) => (Date.parse(b.Date) || 0) - (Date.parse(a.Date) || 0));
        lastUpdated = new Date();
        $('total-count').textContent = jobs.length;
        $('active-count').textContent = jobs.filter(job => active(job.Status)).length;
        $('completed-count').textContent = jobs.filter(job => job.Status === 'ok').length;
        $('nav-count').textContent = jobs.length;
        $('connection').className = 'connection online';
        $('connection').replaceChildren(element('i'), document.createTextNode('Engine connected'));
        $('load-error').hidden = true;
        $('jobs-loading').hidden = true;
        $('updated-at').textContent = 'Last updated ' + timeFormat.format(lastUpdated) + ' · refreshes every 15 seconds';
        renderJobs();
      } catch (error) {
        $('connection').className = 'connection offline';
        $('connection').replaceChildren(element('i'), document.createTextNode('Connection unavailable'));
        $('load-error-text').textContent = 'Could not refresh jobs. ' + error.message;
        $('load-error').hidden = false;
        $('jobs-loading').hidden = true;
        if (!lastUpdated) {
          $('jobs-empty').hidden = false;
          $('empty-title').textContent = 'Workspace unavailable';
          $('empty-description').textContent = 'Start the local engine, then try refreshing.';
          $('results-count').textContent = 'No connection';
        } else {
          $('updated-at').textContent = 'Showing saved view from ' + timeFormat.format(lastUpdated) + ' · refresh failed';
        }
      } finally { $('refresh').disabled = false; refreshPromise = null; }
    })();
    return refreshPromise;
  }

  function showDetails(job) {
    $('job-dialog-title').textContent = job.Name || 'Untitled search';
    const details = element('dl');
    const fields = [
      ['Status', statusNames[job.Status] || job.Status], ['Job ID', job.ID], ['Created', dateText(job.Date, true)],
      ['Keywords', (job.Data?.keywords || []).join('\n')], ['Language', job.Data?.lang],
      ['Location', [job.Data?.lat, job.Data?.lon].join(', ')], ['Search depth', job.Data?.depth],
      ['Time limit', job.Data?.max_time ? (job.Data.max_time / 1e9 / 60).toLocaleString(undefined, {maximumFractionDigits: 1}) + ' minutes' : 'Not specified'],
      ['Email collection', job.Data?.email ? 'Enabled' : 'Disabled']
    ];
    for (const [label, value] of fields) details.append(element('dt', '', label), element('dd', '', String(value ?? 'Not specified')));
    $('job-detail').replaceChildren(details);
    $('detail-download').hidden = job.Status !== 'ok';
    $('detail-download').href = jobPath(job) + '/download';
  }
  async function viewJob(job) {
    openJobId = job.ID;
    showDetails(job);
    $('job-dialog').showModal();
    try {
      const fresh = await request(jobPath(job));
      if (openJobId === job.ID && $('job-dialog').open) showDetails(fresh);
    } catch (error) {
      if (openJobId === job.ID && $('job-dialog').open) $('job-detail').append(element('p', '', 'Could not refresh details: ' + error.message));
    }
  }
  document.querySelectorAll('.close-dialog').forEach(button => button.addEventListener('click', () => button.closest('dialog').close()));
  $('job-dialog').addEventListener('close', () => { openJobId = null; });
  $('confirm-delete').addEventListener('click', async () => {
    if (!deleting) return;
    const selected = deleting;
    $('confirm-delete').disabled = true;
    try {
      const fresh = await request(jobPath(selected));
      if (active(fresh.Status)) throw new Error('This job is still running. Wait until it finishes.');
      await request(jobPath(selected), {method: 'DELETE'});
      $('delete-dialog').close(); deleting = null;
      await refreshJobs();
    } catch (error) {
      $('delete-error').textContent = error.message;
      $('delete-error').hidden = false;
    } finally { $('confirm-delete').disabled = false; }
  });
  $('search-form').addEventListener('submit', async event => {
    event.preventDefault();
    if (!$('search-form').reportValidity()) return;
    const name = $('name').value.trim();
    const keywords = [...new Set($('keywords').value.split(/\r?\n/).map(line => line.trim()).filter(Boolean))];
    if (!name || !keywords.length) { showMessage('Add a search name and at least one search term.', true); return; }
    const body = {
      name, keywords, lang: $('lang').value, depth: Number($('depth').value),
      lat: $('lat').value.trim(), lon: $('lon').value.trim(), zoom: Number($('zoom').value), radius: Number($('radius').value),
      max_time: Number($('max-time').value) * 60, fast_mode: $('fast-mode').checked, email: $('email').checked,
      proxies: $('proxies').value.split(/\r?\n/).map(line => line.trim()).filter(Boolean)
    };
    const submit = $('submit-search'); submit.disabled = true; submit.textContent = 'Starting search…';
    $('form-message').hidden = true;
    try {
      const created = await request('/api/v1/jobs', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)});
      if (!created || typeof created.id !== 'string') throw new Error('The engine did not return a job ID.');
      $('proxies').value = '';
      showMessage('Search created. Follow its progress in Search history.');
      page = 1; $('filter-text').value = ''; $('filter-status').value = 'all';
      await refreshJobs();
    } catch (error) {
      const uncertain = !error.status || error.status >= 500;
      showMessage(error.message + (uncertain ? ' The job may already exist. Refresh history before submitting again.' : ''), true);
    } finally { submit.disabled = false; submit.replaceChildren(document.createTextNode('Start search '), element('span', '', '→')); }
  });
  $('cairo-example').addEventListener('click', () => { $('lat').value = '30.0444'; $('lon').value = '31.2357'; });
  for (const id of ['filter-text', 'filter-status']) $(id).addEventListener(id === 'filter-text' ? 'input' : 'change', () => { page = 1; if (lastUpdated) renderJobs(); });
  $('previous').addEventListener('click', () => { page--; renderJobs(); });
  $('next').addEventListener('click', () => { page++; renderJobs(); });
  $('refresh').addEventListener('click', refreshJobs);
  $('retry').addEventListener('click', refreshJobs);
  setInterval(() => { if (!document.hidden) refreshJobs(); }, 15000);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refreshJobs(); });
  refreshJobs();
})();
