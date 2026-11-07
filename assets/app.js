/* Official tax registry browser. Personal visit records stay on this device. */
(() => {
  'use strict';
  const Core = window.CommercialMapCore;
  const STORAGE_KEY = 'commercial_tax_visit_status_v1';
  const DEFAULT_COUNTY_KEY = 'default_commercial_county';
  const $ = id => document.getElementById(id);
  let catalog, counties = {}, worker, currentCounty = 'taoyuan', selectedCounty = 'taoyuan', countyRegion = 'ALL';
  let filters = initialFilters(), statuses = Object.create(null), storageProblem = false, unreadableStorage = false;
  let queryId = 0, complete = false, loading = false, failed = false, loadingPage = false, exporting = false, pendingExport = false;
  let rows = [], resultCount = 0, scanned = 0, sectionCounts = {}, districtCounts = {}, statusCounts = {}, addressCount = 0;
  let searchTimer, selectedId = null, directoryRequestId = 0, directoryOffset = 0, directoryTimer;
  let map, markersLayer, locationMarker, baseLayers = {}, baseLayerName = 'osm', autoLabels = true;
  let activeModal = null, modalTrigger = null;
  const backgroundInert = new Map();

  function initialFilters() { return { district: 'all', category: 'ALL', capital: Core.DEFAULT_CAPITAL, address: '', status: 'ALL', query: '' }; }
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }
  function button(text, className, action) {
    const node = element('button', className, text);
    node.type = 'button'; node.addEventListener('click', action); return node;
  }
  function setText(id, text) { if ($(id)) $(id).textContent = text; }
  function link(text, url, className) {
    const node = element('a', className, text);
    node.href = url; node.target = '_blank'; node.rel = 'noopener noreferrer'; return node;
  }
  function notice(message, action, label = '重試', target = 'appNotice') {
    const node = $(target);
    if (!node) return;
    node.replaceChildren(); node.hidden = !message;
    if (message) node.append(element('span', '', message));
    if (message && action) node.append(button(label, 'notice-action', action));
  }
  function setMapToolLabel(id, icon, label) {
    const node = $(id);
    const [name, value] = label.split('：');
    node.replaceChildren(element('span', 'tool-icon', icon), element('span', 'tool-short', name),
      element('span', 'tool-text', value ? `：${value}` : ''));
    node.setAttribute('aria-label', label); node.title = label;
  }
  function closeMenus() { document.querySelectorAll('details.more-actions[open]').forEach(node => { node.open = false; }); }

  function saveStatuses() {
    try {
      if (unreadableStorage) throw new Error('原始紀錄無法讀取');
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ schema_version: 1, kind: Core.BACKUP_KIND, statuses }));
      storageProblem = false; return true;
    } catch (_) {
      storageProblem = true;
      notice(unreadableStorage ? '原有紀錄無法讀取，因此不覆寫；請先備份目前紀錄，再還原有效檔案。'
        : '瀏覽器無法保存紀錄；本次變更仍在頁面中，請下載備份。', backupRecords, '下載備份');
      return false;
    }
  }
  function loadStatuses() {
    try { statuses = Core.loadStoredStatuses(localStorage.getItem(STORAGE_KEY)); }
    catch (_) {
      unreadableStorage = true; storageProblem = true;
      notice('無法讀取正式拜訪紀錄；原始儲存內容保留，請還原有效備份。舊示範紀錄不會套用到真實企業。');
    }
  }
  function clearSearch() {
    clearTimeout(searchTimer); $('searchInput').value = ''; $('btnClearSearch').style.display = 'none';
  }
  function resetFilters() { filters = initialFilters(); selectedId = null; clearSearch(); }

  function startWorker() {
    if (worker) worker.terminate();
    const url = new URL('assets/search-worker.js', document.baseURI);
    url.searchParams.set('v', catalog.dataset_version);
    url.searchParams.set('app', catalog.app_version || catalog.dataset_version);
    worker = new Worker(url);
    worker.addEventListener('message', handleWorkerMessage);
    worker.addEventListener('error', () => {
      complete = false; loading = false; failed = true; exporting = false; renderList();
      notice('背景搜尋無法執行。請重新載入搜尋元件後重試。', () => { startWorker(); runQuery(); });
    });
    worker.postMessage({ type: 'init', catalog });
  }

  function runQuery(exportAfter = false) {
    if (!worker || !catalog) return;
    clearTimeout(searchTimer);
    filters.query = $('searchInput').value.trim();
    $('btnClearSearch').style.display = filters.query ? 'block' : 'none';
    queryId++; complete = false; loading = true; failed = false; loadingPage = false;
    exporting = false; pendingExport = exportAfter; rows = []; resultCount = 0; scanned = 0;
    districtCounts = {}; statusCounts = {}; addressCount = 0;
    renderFilters(); renderList(); renderMapMarkers();
    if (!storageProblem) notice('');
    worker.postMessage({ type: 'query', id: queryId, countyId: currentCounty, filters: { ...filters }, statuses });
  }

  function handleWorkerMessage(event) {
    const message = event.data;
    if (message.id !== queryId) return;
    if (message.type === 'progress' || message.type === 'done') {
      rows = message.rows; resultCount = message.count; districtCounts = message.districtCounts; statusCounts = message.statusCounts;
      if (message.type === 'done') {
        complete = true; loading = false; sectionCounts = message.sectionCounts; addressCount = message.addressCount;
        scanned = counties[currentCounty].company_count; renderFilters();
      } else scanned = message.scanned;
      renderList(); renderMapMarkers();
      if (complete && pendingExport) { pendingExport = false; startExport(); }
    } else if (message.type === 'page') {
      if (message.offset !== rows.length) return;
      rows.push(...message.rows); loadingPage = false; renderList();
      $(`card-${Core.companyId(message.rows[0]?.[1])}`)?.querySelector('button')?.focus({ preventScroll: true });
    } else if (message.type === 'directory') {
      if (message.requestId === directoryRequestId) renderDirectoryPage(message);
    } else if (message.type === 'exportProgress') {
      notice(`正在匯出全部篩選結果：${message.completed.toLocaleString()}／${message.total.toLocaleString()} 筆…`);
    } else if (message.type === 'export') {
      exporting = false;
      downloadBlob(message.blob, `官方營業人名單_${currentCounty}_${new Date().toISOString().slice(0, 10)}.csv`);
      notice(`已匯出全部 ${message.count.toLocaleString()} 筆篩選結果。使用 Excel 匯入時，統編欄請設定為文字。`);
    } else if (message.type === 'error') {
      if (message.operation === 'query') { complete = false; loading = false; failed = true; pendingExport = false; renderList(); }
      if (message.operation === 'page') { loadingPage = false; renderList(); }
      exporting = false;
      const retry = message.operation === 'page' ? loadMore : message.operation === 'export' ? startExport : runQuery;
      notice(message.message + ' 未將不完整結果視為完成。', () => retry());
    }
  }

  function switchCounty(id) {
    if (!Object.hasOwn(counties, id)) return;
    currentCounty = id; resetFilters(); sectionCounts = {};
    setText('currentCountyDisplay', counties[id].name); setText('headerCountyBadge', counties[id].name);
    runQuery();
    if (map && counties[id].center) map.setView(counties[id].center, counties[id].zoom || 11);
  }
  function chooseFilter(key, value) {
    filters[key] = value; selectedId = null; runQuery();
    const container = { category: 'categoryChips', address: 'buildingChips', district: 'districtNavBar' }[key];
    if (container) Array.from($(container).querySelectorAll('button')).find(node => node.dataset.value === value)?.focus({ preventScroll: true });
  }
  function switchDistrict(id) {
    resetFilters(); filters.district = id; sectionCounts = {}; runQuery();
    const district = (counties[currentCounty].districts || []).find(d => d.id === id);
    if (map && district?.center) map.setView(district.center, 12);
  }
  function chip(text, value, selected, className, action) {
    const node = button(text, `${className}${selected ? ' active' : ''}`, action);
    node.dataset.value = value; node.setAttribute('aria-pressed', String(selected)); return node;
  }
  function sectionName(id) { return catalog.industry_sections?.[id] || (id === 'UNKNOWN' ? '來源未提供' : '來源分類未辨識'); }

  function renderFilters() {
    if (!catalog) return;
    const county = counties[currentCounty];
    $('districtNavBar').replaceChildren(chip(`全${county.name} (${county.company_count.toLocaleString()})`, 'all', filters.district === 'all', 'district-btn', () => switchDistrict('all')));
    (county.districts || []).forEach(d => $('districtNavBar').append(chip(`${d.name} (${d.company_count.toLocaleString()})`, d.id,
      filters.district === d.id, 'district-btn', () => switchDistrict(d.id))));
    $('categoryChips').replaceChildren(chip('全部主要行業', 'ALL', filters.category === 'ALL', 'chip', () => chooseFilter('category', 'ALL')));
    const available = Object.keys(sectionCounts).length ? Object.keys(sectionCounts) : Object.keys(catalog.industry_sections || {});
    available.sort().forEach(id => $('categoryChips').append(chip(`${id} ${sectionName(id)}${sectionCounts[id] ? ` (${sectionCounts[id].toLocaleString()})` : ''}`, id,
      filters.category === id, 'chip', () => chooseFilter('category', filters.category === id ? 'ALL' : id))));
    $('buildingChips').replaceChildren(chip('全部登記地址', '', !filters.address, 'chip', () => chooseFilter('address', '')));
    if (filters.address) $('buildingChips').append(chip(filters.address, filters.address, true, 'chip', () => chooseFilter('address', '')));
    $('buildingChips').append(button(complete ? `查看 ${addressCount.toLocaleString()} 個登記地址` : '搜尋完成後查看地址', 'chip', openAllBuildingsDirectory));
    setText('catCurrentLabel', filters.category === 'ALL' ? '全部行業' : `${filters.category} ${sectionName(filters.category)}`);
    setText('buildingCurrentLabel', filters.address || '全部地址');
    document.querySelectorAll('#capitalChips [data-tier]').forEach(node => {
      const selected = node.dataset.tier === filters.capital;
      node.classList.toggle('active', selected); node.setAttribute('aria-pressed', String(selected));
      if (selected) setText('capitalCurrentLabel', node.textContent);
    });
    const styles = { ALL: 'all', LISTED: 'listed', 尚未拜訪: 'pending', 洽談中: 'negotiating', 已拜訪: 'done' };
    document.querySelectorAll('#statusChips [data-status]').forEach(node => {
      Object.values(styles).forEach(name => node.classList.remove(`active-${name}`));
      const selected = node.dataset.status === filters.status;
      if (selected) node.classList.add(`active-${styles[filters.status]}`);
      node.setAttribute('aria-pressed', String(selected));
    });
    updateFilterToggleBadge();
  }

  function detail(label, value) { return element('div', 'card-detail', `${label}：${value || '來源未提供'}`); }
  function companyCard(row) {
    const id = Core.companyId(row[1]), info = catalog.enrichment[String(row[1])] || {};
    const card = element('article', 'company-card'); card.id = `card-${id}`; card.classList.toggle('selected', selectedId === id);
    const top = element('div', 'card-top-row'), title = element('div', 'card-name');
    title.append(button(row[3], 'card-title-button', () => selectCompany(row)));
    top.append(title, element('span', 'badge-cat', '官方稅籍'));
    if (info.market) top.append(element('span', 'badge-listed', `${info.market} ${info.stock_code || ''}`));
    const identity = element('div', 'card-bld-tag', `統編 ${row[1]} · 總機構統編 ${row[2] || '來源未提供'}`);
    const industries = [];
    for (let index = 8; index < 16; index += 2) if (row[index] || row[index + 1]) industries.push(`${row[index]} ${row[index + 1]}`.trim());
    card.append(top, identity, element('div', 'card-addr', row[0] || '來源未提供登記地址'),
      detail('資本額', Core.formatCapital(row[4])), detail('設立日期', Core.formatEstablished(row[5])),
      detail('組織別', row[6]), detail('使用統一發票', row[7]), detail('行業', industries.join('；')));
    if (info.market) {
      const contact = element('div', 'card-contact-row');
      const phone = Core.phoneURL(info.phone);
      contact.append(element('span', '', '上市櫃公司總機：'), phone ? link(info.phone, phone, '') : element('span', '', info.phone || '來源未提供'));
      card.append(contact, detail('董事長', info.chairperson));
      const website = Core.safeURL(info.website), source = Core.safeURL(info.source_url);
      const links = element('div', 'card-contact-row');
      if (website) links.append(link(`公司網站：${info.website_raw || info.website}`, website, ''));
      else if (info.website_raw) links.append(detail('公司網站（來源原值）', info.website_raw));
      if (source) links.append(link('上市櫃資訊來源', source, ''));
      if (links.childNodes.length) card.append(links);
    } else card.append(element('p', 'record-note', '電話、代表人、網站及上市櫃資訊：本來源未提供，未自行補填。'));
    const actions = element('div', 'card-actions-row'), label = element('label', 'status-select-wrapper', '拜訪紀錄 ');
    const select = element('select', 'status-select'); select.setAttribute('aria-label', `${row[3]}的拜訪紀錄`);
    Core.STATUSES.forEach(status => { const option = element('option', '', status); option.value = status; select.append(option); });
    select.value = statuses[id] || Core.STATUSES[0];
    select.addEventListener('change', event => updateCompanyStatus(id, event.target.value)); label.append(select); actions.append(label);
    if (row[0]) actions.append(link('查登記地址', `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(row[0])}`, 'card-btn'));
    card.append(element('p', 'record-note', '登記地址不代表實際營業或進駐位置；總機及董事長資訊僅限統編相符的上市櫃公司。'), actions);
    return card;
  }

  function renderList() {
    const total = counties[currentCounty]?.company_count || 0;
    setText('resultCountText', loading ? `檢索中 ${scanned.toLocaleString()}／${total.toLocaleString()} · 暫時符合 ${resultCount.toLocaleString()} 筆`
      : failed ? `搜尋未完成 · 暫時符合 ${resultCount.toLocaleString()} 筆`
        : `符合 ${resultCount.toLocaleString()} 筆 · 已顯示 ${rows.length.toLocaleString()} 筆`);
    setText('mobileCount', resultCount.toLocaleString());
    [['countAll', 'ALL'], ['countListed', 'LISTED'], ['countPending', '尚未拜訪'], ['countNegotiating', '洽談中'], ['countDone', '已拜訪']]
      .forEach(([id, key]) => setText(id, (statusCounts[key] || 0).toLocaleString()));
    const list = $('clientList'), scroller = window.innerWidth <= 768 ? document.querySelector('.sidebar') : list;
    const scrollTop = scroller?.scrollTop || 0;
    list.replaceChildren();
    if (!rows.length) list.append(element('p', 'empty-state', loading ? '正在讀取完整縣市資料，請稍候…'
      : failed ? '資料尚未完整載入，請使用上方提示重試。' : '沒有符合條件的資料。可重設篩選或更換縣市。'));
    const fragment = document.createDocumentFragment(); rows.forEach(row => fragment.append(companyCard(row))); list.append(fragment);
    if (loading) list.append(element('p', 'record-note', '以上是暫時結果；所有分片完成後才能匯出完整清單。'));
    if (complete && rows.length < resultCount) {
      const more = button(loadingPage ? '載入中…' : `載入更多（尚有 ${(resultCount - rows.length).toLocaleString()} 筆）`, 'list-pagination', loadMore);
      more.disabled = loadingPage; list.append(more);
    }
    if (scroller) scroller.scrollTop = scrollTop;
  }
  function loadMore() {
    if (!complete || loadingPage) return;
    loadingPage = true; renderList(); worker.postMessage({ type: 'page', id: queryId, offset: rows.length });
  }
  function selectCompany(row) {
    selectedId = Core.companyId(row[1]);
    document.querySelectorAll('.company-card').forEach(node => node.classList.toggle('selected', node.id === `card-${selectedId}`));
    const district = counties[currentCounty].districts.find(d => d.id === row[16]);
    if (map && district?.center) {
      map.setView(district.center, 12);
      notice(`地圖顯示${district.name}行政區概覽，並非這家企業的門牌位置。`, null, '', 'mapNotice');
    }
  }
  function updateCompanyStatus(id, status, event) {
    if (event) event.stopPropagation();
    if (!rows.some(row => Core.companyId(row[1]) === id) || !Core.STATUSES.includes(status)) return;
    try { statuses = Core.mergeStatuses(statuses, { [id]: status }); }
    catch (error) { notice(error.message); return; }
    const saved = saveStatuses(); runQuery();
    if (saved) notice('拜訪紀錄已存於此瀏覽器；正在重新套用完整篩選。');
  }

  function initMap() {
    if (map) return;
    try {
      if (!window.L) throw new Error('Map unavailable');
      map = L.map('map', { center: counties[currentCounty]?.center || [23.7, 121], zoom: 8, wheelPxPerZoomLevel: 180, wheelDebounceTime: 150 });
      markersLayer = L.layerGroup().addTo(map);
      baseLayers = {
        osm: L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' }),
        nlsc: L.tileLayer('https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}', { maxZoom: 19,
          attribution: '&copy; <a href="https://maps.nlsc.gov.tw/">內政部國土測繪中心</a>' }),
        sat: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19,
          attribution: '&copy; Esri, Maxar, Earthstar Geographics and the GIS User Community' })
      };
      Object.values(baseLayers).forEach(layer => layer.on('tileerror', () => {
        if (map.hasLayer(layer)) notice('部分底圖無法載入，名錄仍可使用。', cycleBasemap, '切換圖資', 'mapNotice');
      }));
      baseLayers.osm.addTo(map); map.on('zoomend moveend', renderMapMarkers);
      notice('', null, '', 'mapNotice');
    } catch (_) {
      if (map) { map.remove(); map = null; }
      notice('地圖無法啟用，真實企業名錄與篩選仍可使用。', null, '', 'mapNotice');
    }
  }
  function cycleBasemap() {
    if (!map) return;
    map.removeLayer(baseLayers[baseLayerName]);
    const names = ['osm', 'nlsc', 'sat']; baseLayerName = names[(names.indexOf(baseLayerName) + 1) % names.length];
    baseLayers[baseLayerName].addTo(map); notice('', null, '', 'mapNotice');
    setMapToolLabel('btnToggleLayer', '🗺️', { osm: '圖資：標準街道', nlsc: '圖資：臺灣通用', sat: '圖資：衛星影像' }[baseLayerName]);
  }
  function renderMapMarkers() {
    if (!map || !markersLayer || !catalog) return;
    markersLayer.clearLayers();
    const districts = counties[currentCounty].districts.filter(d => d.center && districtCounts[d.id]);
    const groups = districts.map(d => ({ members: [d], point: map.project(d.center, map.getZoom()) }));
    let merged = true;
    while (merged) {
      merged = false;
      mergePair: for (let i = 0; i < groups.length; i++) for (let j = i + 1; j < groups.length; j++) {
        const a = groups[i], b = groups[j];
        if (a.point.distanceTo(b.point) >= 60) continue;
        const count = a.members.length + b.members.length;
        a.point = L.point((a.point.x * a.members.length + b.point.x * b.members.length) / count,
          (a.point.y * a.members.length + b.point.y * b.members.length) / count);
        a.members.push(...b.members); groups.splice(j, 1); merged = true; break mergePair;
      }
    }
    groups.forEach(group => {
      const count = group.members.reduce((sum, d) => sum + districtCounts[d.id], 0);
      const names = group.members.map(d => d.name).join('、');
      const label = group.members.length === 1 && autoLabels && map.getZoom() >= 13 ? `${names} · ${count.toLocaleString()}` : count.toLocaleString();
      const visual = element('div', group.members.length === 1 && autoLabels && map.getZoom() >= 13 ? 'bld-marker' : 'cluster-marker', label);
      const title = `${names}：${count.toLocaleString()} 筆，行政區統計，非企業位置`;
      const marker = L.marker(map.unproject(group.point, map.getZoom()), { icon: L.divIcon({ className: 'custom-bld-pin', html: visual, iconSize: null }), title, alt: title });
      marker.on('click', () => {
        if (group.members.length === 1) switchDistrict(group.members[0].id);
        else map.fitBounds(group.members.map(d => d.center), { padding: [40, 40], maxZoom: 15 });
      });
      markersLayer.addLayer(marker);
    });
  }
  function toggleAutoLabels() {
    autoLabels = !autoLabels; setMapToolLabel('btnToggleLabels', '🏷️', autoLabels ? '標籤：自動' : '標籤：關閉');
    $('btnToggleLabels').setAttribute('aria-pressed', String(autoLabels)); renderMapMarkers();
  }

  function openModal(id) {
    const modal = $(id); if (!modal) return;
    const trigger = activeModal ? modalTrigger : document.activeElement;
    if (activeModal && activeModal !== modal) closeModal(activeModal.id, false);
    modalTrigger = trigger?.closest('details.more-actions')?.querySelector('summary') || trigger;
    closeMenus(); activeModal = modal; modal.hidden = false; modal.style.display = 'flex';
    for (const child of document.body.children) if (child !== modal && !child.contains(modal) && child.tagName !== 'SCRIPT' && !backgroundInert.has(child)) {
      backgroundInert.set(child, child.inert); child.inert = true;
    }
    modal.querySelector('button, input, [tabindex="0"]')?.focus();
  }
  function closeModal(id, restoreFocus = true) {
    const modal = $(id); if (!modal) return;
    modal.style.display = 'none'; modal.hidden = true;
    if (activeModal === modal) {
      activeModal = null; backgroundInert.forEach((value, node) => { node.inert = value; }); backgroundInert.clear();
      if (restoreFocus && modalTrigger?.isConnected) modalTrigger.focus();
    }
  }

  function countyRegionOf(county) {
    if (county.region) return county.region;
    for (const [region, ids] of Object.entries({ 北部: ['taipei', 'new_taipei', 'keelung', 'taoyuan', 'hsinchu_city', 'hsinchu_county', 'yilan'],
      中部: ['miaoli', 'taichung', 'changhua', 'nantou', 'yunlin'], 南部: ['chiayi_city', 'chiayi_county', 'tainan', 'kaohsiung', 'pingtung'],
      東部: ['hualien', 'taitung'], 離島: ['penghu', 'kinmen', 'lienchiang'] })) if (ids.includes(county.id)) return region;
    return '其他';
  }
  function renderCountyGrid() {
    const grid = $('countyGridContainer'); grid.replaceChildren();
    const tabs = element('div', 'county-region-tabs');
    const records = Object.entries(counties).map(([id, county]) => ({ ...county, id }));
    ['ALL', ...new Set(records.map(countyRegionOf))].forEach(region => {
      const count = records.filter(c => region === 'ALL' || countyRegionOf(c) === region).length;
      tabs.append(chip(`${region === 'ALL' ? '全部' : region} (${count})`, region, countyRegion === region, 'chip', () => {
        countyRegion = region; renderCountyGrid();
        Array.from(grid.querySelectorAll('.county-region-tabs button')).find(node => node.dataset.value === region)?.focus();
      }));
    }); grid.append(tabs);
    records.filter(c => countyRegion === 'ALL' || countyRegionOf(c) === countyRegion).forEach(c => {
      const node = button('', `county-card-btn${selectedCounty === c.id ? ' selected' : ''}`, () => {
        selectedCounty = c.id; renderCountyGrid();
        Array.from(grid.querySelectorAll('[data-county]')).find(item => item.dataset.county === c.id)?.focus();
      });
      node.dataset.county = c.id; node.setAttribute('aria-pressed', String(selectedCounty === c.id));
      node.append(element('span', 'county-card-name', c.name), element('span', 'county-card-badge', `${c.company_count.toLocaleString()} 家營業人`)); grid.append(node);
    });
  }
  function openCountyModal() { if (catalog) { selectedCounty = currentCounty; renderCountyGrid(); openModal('modalCountySelect'); } }
  function confirmCountySelection() {
    closeModal('modalCountySelect');
    try {
      if ($('chkSetDefaultCounty')?.checked) localStorage.setItem(DEFAULT_COUNTY_KEY, selectedCounty);
      else localStorage.removeItem(DEFAULT_COUNTY_KEY);
    } catch (_) { notice('瀏覽器無法記住預設縣市，本次仍可正常切換。'); }
    switchCounty(selectedCounty);
  }

  function openAllBuildingsDirectory() {
    if (!complete) { notice('請等完整搜尋完成後再開啟登記地址名錄。'); return; }
    setText('bldModalTitle', `${counties[currentCounty].name} · 登記地址名錄`);
    setText('bldModalSubtitle', `目前篩選中的 ${addressCount.toLocaleString()} 個登記地址；非大樓實際進駐清冊。`);
    const list = $('bldModalList'), search = element('input', 'directory-search');
    search.type = 'search'; search.id = 'directorySearch'; search.placeholder = '搜尋登記地址'; search.setAttribute('aria-label', '搜尋目前名錄中的登記地址');
    search.addEventListener('input', () => { clearTimeout(directoryTimer); directoryTimer = setTimeout(() => requestDirectory(0), 150); });
    const directoryRows = element('div', 'directory-rows'); directoryRows.id = 'directoryRows';
    list.replaceChildren(search, directoryRows); openModal('modalBuilding'); requestDirectory(0);
  }
  function requestDirectory(offset) {
    directoryRequestId++; directoryOffset = offset;
    worker.postMessage({ type: 'directory', id: queryId, requestId: directoryRequestId, offset, query: $('directorySearch')?.value || '' });
  }
  function renderDirectoryPage(message) {
    const list = $('directoryRows'); if (!list || activeModal?.id !== 'modalBuilding') return;
    if (!message.offset) list.replaceChildren();
    list.querySelector('.list-pagination')?.remove();
    if (!message.total) list.append(element('p', 'empty-state', '沒有符合的登記地址。'));
    message.addresses.forEach(item => {
      const node = button('', 'building-directory-entry', () => openBuildingDirectory(item.address));
      node.append(element('strong', '', item.address || '來源未提供地址'), element('span', '', `${item.count.toLocaleString()} 家登記營業人`)); list.append(node);
    });
    const next = message.offset + message.addresses.length;
    if (next < message.total) list.append(button(`載入更多地址（剩餘 ${(message.total - next).toLocaleString()} 個）`, 'list-pagination', () => requestDirectory(next)));
  }
  function openBuildingDirectory(address, event) {
    if (event) event.stopPropagation();
    closeModal('modalBuilding'); chooseFilter('address', address);
  }

  function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob), node = element('a'); node.href = url; node.download = filename;
    document.body.append(node); node.click(); node.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000); closeMenus();
  }
  function startExport() {
    if (!complete || exporting) return;
    if (!resultCount) { notice('目前沒有可匯出的資料。'); return; }
    if (resultCount > Core.MAX_EXPORT_ROWS) {
      notice(`目前符合 ${resultCount.toLocaleString()} 筆。為避免瀏覽器記憶體不足，請先選行政區縮小至 100,000 筆以內，或下載官方全國原始檔；不會截斷匯出。`,
        () => $('sourceDownloadLink')?.click(), '官方完整來源'); return;
    }
    exporting = true; notice(`正在準備全部 ${resultCount.toLocaleString()} 筆篩選結果…`);
    worker.postMessage({ type: 'export', id: queryId });
  }
  function exportCSV() {
    if (!catalog) return;
    if (filters.query !== $('searchInput').value.trim()) { runQuery(true); return; }
    if (!complete) { pendingExport = true; notice('會在所有資料分片檢索完成後匯出完整篩選結果。'); return; }
    startExport();
  }
  function backupRecords() {
    if (!catalog) return;
    const backup = { schema_version: 1, kind: Core.BACKUP_KIND, dataset_version: catalog.dataset_version, exported_at: new Date().toISOString(), statuses };
    downloadBlob(new Blob([JSON.stringify(backup, null, 2)], { type: 'application/json;charset=utf-8' }), `正式拜訪紀錄_${new Date().toISOString().slice(0, 10)}.json`);
  }
  async function restoreRecords(event) {
    const file = event.target.files?.[0]; event.target.value = ''; if (!file || !catalog) return;
    try {
      if (file.size > Core.MAX_BACKUP_BYTES) throw new Error('備份超過 1 MB，未匯入。');
      const incoming = Core.validateBackup(JSON.parse(await file.text()));
      statuses = Core.mergeStatuses(statuses, incoming); unreadableStorage = false;
      const saved = saveStatuses(); runQuery();
      if (saved) notice(`已合併 ${Object.keys(incoming).length.toLocaleString()} 筆正式紀錄，其他縣市紀錄保留。未收錄於本期官方資料的統編不會新增企業。`);
    } catch (error) { notice(error instanceof SyntaxError ? '備份不是有效 JSON；未匯入任何資料。' : error.message); }
  }

  function updateFilterToggleBadge() {
    const collapsed = $('advancedFiltersBox')?.classList.contains('collapsed');
    const count = Number(filters.capital !== 'ALL') + Number(Boolean(filters.address)) + Number(filters.status !== 'ALL');
    setText('filterToggleState', `${count ? `${count} 項條件 · ` : ''}${collapsed ? '展開 ▼' : '收合 ▲'}`);
    $('btnFilterToggle')?.setAttribute('aria-expanded', String(!collapsed));
  }
  function toggleAdvancedFilters() { $('advancedFiltersBox')?.classList.toggle('collapsed'); updateFilterToggleBadge(); }
  function toggleChipsExpand(containerId, buttonId) {
    const container = $(containerId), trigger = $(buttonId); if (!container || !trigger) return;
    const expanded = container.classList.toggle('expanded'); trigger.textContent = expanded ? '收合 ▲' : '展開全部 ▼'; trigger.setAttribute('aria-expanded', String(expanded));
  }
  function setMobileView(view) {
    if (!['list', 'split', 'map'].includes(view)) return;
    const app = $('appContainer'); app.classList.remove('mobile-list', 'mobile-split', 'mobile-map'); app.classList.add(`mobile-${view}`);
    [['btnViewList', 'list'], ['btnViewSplit', 'split'], ['btnViewMap', 'map']].forEach(([id, value]) => {
      $(id)?.classList.toggle('active', view === value); $(id)?.setAttribute('aria-pressed', String(view === value));
    }); if (map) setTimeout(() => map.invalidateSize(), 100);
  }

  function wireEvents() {
    $('searchInput').addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => runQuery(), 150); });
    $('searchInput').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); runQuery(); } });
    $('btnDoSearch').addEventListener('click', () => runQuery());
    $('btnClearSearch').addEventListener('click', () => { clearSearch(); runQuery(); $('searchInput').focus(); });
    $('btnResetFilter').addEventListener('click', () => { resetFilters(); sectionCounts = {}; runQuery(); });
    document.querySelectorAll('#capitalChips [data-tier]').forEach(node => node.addEventListener('click', () => chooseFilter('capital', node.dataset.tier)));
    document.querySelectorAll('#statusChips [data-status]').forEach(node => node.addEventListener('click', () => chooseFilter('status', node.dataset.status)));
    $('btnExport').addEventListener('click', exportCSV); $('btnBackup')?.addEventListener('click', backupRecords);
    $('btnRestore')?.addEventListener('click', () => $('inputRestore')?.click()); $('inputRestore')?.addEventListener('change', restoreRecords);
    $('btnFitBounds').addEventListener('click', () => {
      const points = counties[currentCounty]?.districts.filter(d => d.center && districtCounts[d.id]).map(d => d.center) || [];
      if (map && points.length) map.fitBounds(points, { padding: [40, 40], maxZoom: 13 });
    });
    $('btnLocateMe').addEventListener('click', () => {
      if (!map || !navigator.geolocation) { notice('目前無法在地圖顯示定位；企業名錄仍可使用。'); return; }
      navigator.geolocation.getCurrentPosition(position => {
        const point = [position.coords.latitude, position.coords.longitude]; if (locationMarker) map.removeLayer(locationMarker);
        locationMarker = L.circleMarker(point, { radius: 8 }).addTo(map);
        locationMarker.bindPopup(element('span', '', '目前位置，僅在此頁顯示')).openPopup(); map.setView(point, 15);
      }, () => notice('無法取得位置。請確認定位權限，或手動操作地圖。'), { timeout: 8000, maximumAge: 60000 });
    });
    document.addEventListener('keydown', event => {
      if (!activeModal) return;
      if (event.key === 'Escape') { event.preventDefault(); closeModal(activeModal.id); return; }
      if (event.key !== 'Tab') return;
      const nodes = Array.from(activeModal.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex="0"]')).filter(node => node.getClientRects().length);
      const first = nodes[0], last = nodes[nodes.length - 1];
      if (!first) { event.preventDefault(); activeModal.focus(); }
      else if (event.shiftKey && (document.activeElement === first || !activeModal.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !activeModal.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
    });
    ['modalBuilding', 'modalCountySelect', 'modalSources'].forEach(id => $(id)?.addEventListener('click', event => { if (event.target === $(id)) closeModal(id); }));
  }

  async function boot() {
    notice('正在載入官方資料目錄…');
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch('data/catalog.json', { signal: controller.signal, cache: 'no-cache' });
      if (!response.ok) throw new Error('無法讀取目錄');
      const data = await response.json();
      if (data.schema_version !== 2 || data.data_mode !== 'official' || !Core.isRecord(data.counties)
        || JSON.stringify(data.columns) !== JSON.stringify(Core.SOURCE_COLUMNS) || !Core.isRecord(data.enrichment)) throw new Error('目錄格式不符');
      catalog = data; counties = data.counties; notice(''); loadStatuses();
      try { const saved = localStorage.getItem(DEFAULT_COUNTY_KEY); if (saved && Object.hasOwn(counties, saved)) currentCounty = saved; }
      catch (_) { notice('瀏覽器無法讀取預設縣市，先顯示桃園市。'); }
      if (!Object.hasOwn(counties, currentCounty)) currentCounty = Object.keys(counties)[0];
      const count = catalog.total_count || Object.values(counties).reduce((sum, county) => sum + county.company_count, 0);
      setText('bannerSummary', `財政部官方稅籍 · ${count.toLocaleString()} 家營業人 · ${Object.keys(counties).length} 縣市`);
      setText('dataVersionText', `來源快照：${catalog.source.source_date || '以來源標示為準'} · 取得時間：${catalog.source.retrieved_at || '未提供'} · 版本 ${catalog.dataset_version.slice(0, 12)}`);
      setText('sourceSummary', `本版完整載入官方來源 ${count.toLocaleString()} 筆。包含營業人名稱、統編、登記地址、資本額及行業等原始欄位；不代表實地訪查或大樓進駐。`);
      const sourceURL = Core.safeURL(catalog.source.url);
      if ($('sourceDownloadLink') && sourceURL) { $('sourceDownloadLink').href = sourceURL; $('sourceDownloadLink').target = '_blank'; $('sourceDownloadLink').rel = 'noopener noreferrer'; }
      startWorker(); initMap(); switchCounty(currentCounty);
    } catch (_) { notice('無法載入正式資料目錄。請檢查網路並確認使用網站網址開啟，再重試。', boot); }
    finally { clearTimeout(timeout); }
  }
  Object.assign(window, { switchCounty, updateCompanyStatus, openCountyModal, confirmCountySelection, openBuildingDirectory, openAllBuildingsDirectory,
    closeCountyModal: () => closeModal('modalCountySelect'), closeBuildingModal: () => closeModal('modalBuilding'),
    openSourceModal: () => openModal('modalSources'), closeSourceModal: () => closeModal('modalSources'),
    cycleBasemap, toggleAutoLabels, toggleAdvancedFilters, toggleChipsExpand, setMobileView,
    bookmarkSite: () => { notice(/Mac|iPhone|iPad/.test(navigator.platform) ? '按 ⌘ + D 加入書籤；手機可由分享選單加入主畫面。' : '按 Ctrl + D 加入書籤；手機可由瀏覽器選單加入主畫面。'); closeMenus(); } });
  function start() {
    if (!Core) { notice('搜尋元件未載入，請重新整理頁面。'); return; }
    wireEvents(); if (window.innerWidth <= 768) setMobileView('list'); boot();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true }); else start();
})();
