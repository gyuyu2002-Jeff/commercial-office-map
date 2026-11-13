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
  let rows = [], resultCount = 0, scanned = 0, districtCounts = {}, statusCounts = {}, addressCount = 0;
  let searchTimer, composing = false, selectedId = null, directoryRequestId = 0, directoryOffset = 0, directoryTimer, directoryMode = 'names';
  let map, markersLayer, locationMarker, baseLayers = {}, baseLayerName = 'osm', autoLabels = true;
  let activeModal = null, modalTrigger = null;
  const backgroundInert = new Map();

  function initialFilters() { return { district: 'all', category: 'ALL', capital: Core.DEFAULT_CAPITAL, address: '', buildingId: '', market: 'ALL', status: 'ALL', query: '' }; }
  function selectedBuilding() { return catalog?.named_buildings?.find(building => building.id === filters.buildingId); }
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
    $('searchSuggestions').replaceChildren();
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
    $('searchSuggestions').replaceChildren();
    $('btnClearSearch').style.display = filters.query ? 'block' : 'none';
    queryId++; complete = false; loading = true; failed = false; loadingPage = false;
    exporting = false; pendingExport = exportAfter; rows = []; resultCount = 0; scanned = 0;
    districtCounts = {}; statusCounts = {}; addressCount = 0;
    renderFilters(); renderList(); renderMapMarkers();
    $('clientList').scrollTop = 0;
    if (!storageProblem) notice('');
    worker.postMessage({ type: 'query', id: queryId, countyId: currentCounty, filters: { ...filters }, statuses });
  }

  function handleWorkerMessage(event) {
    const message = event.data;
    if (message.id !== queryId) return;
    if (message.type === 'progress' || message.type === 'done') {
      rows = message.rows; resultCount = message.count; districtCounts = message.districtCounts; statusCounts = message.statusCounts;
      if (message.type === 'done') {
        complete = true; loading = false; addressCount = message.addressCount;
        scanned = counties[currentCounty].company_count; renderFilters(); renderSuggestions();
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
      downloadBlob(message.blob, `全台商辦樓內企業名單_${currentCounty}_${new Date().toISOString().slice(0, 10)}.csv`);
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
    currentCounty = id; filters.district = 'all'; filters.address = ''; filters.buildingId = ''; selectedId = null;
    setText('currentCountyDisplay', counties[id].name); setText('headerCountyBadge', counties[id].name);
    runQuery();
    if (map && counties[id].center) map.setView(counties[id].center, counties[id].zoom || 11);
  }
  function chooseFilter(key, value) {
    if (key === 'address') filters.buildingId = '';
    filters[key] = value; selectedId = null; runQuery();
    const container = { address: 'buildingChips', district: 'districtNavBar' }[key];
    if (container) Array.from($(container).querySelectorAll('button')).find(node => node.dataset.value === value)?.focus({ preventScroll: true });
  }
  function switchDistrict(id) {
    filters.district = id; filters.address = ''; filters.buildingId = ''; selectedId = null; runQuery();
    const district = (counties[currentCounty].districts || []).find(d => d.id === id);
    if (map && district?.center) map.setView(district.center, 12);
  }
  function chip(text, value, selected, className, action) {
    const node = button(text, `${className}${selected ? ' active' : ''}`, action);
    node.dataset.value = value; node.setAttribute('aria-pressed', String(selected)); return node;
  }
  function sectionName(id) { return catalog.industry_sections?.[id] || (id === 'UNKNOWN' ? '來源未提供' : '來源分類未辨識'); }

  function renderIndustries() {
    const select = $('industrySelect'), names = new Map();
    for (const id of Object.keys(catalog.industry_sections || {}).sort()) {
      const name = sectionName(id);
      if (!names.has(name)) names.set(name, []);
      names.get(name).push(id);
    }
    const groups = [
      ['農林漁牧與礦業', 1, 6], ['製造業', 8, 34], ['能源與環境', 35, 39], ['營建工程', 41, 43],
      ['批發與零售', 45, 48], ['運輸與倉儲', 49, 54], ['住宿與餐飲', 55, 56], ['資訊與傳播', 58, 63],
      ['金融與保險', 64, 66], ['不動產', 67, 68], ['專業服務', 69, 76], ['支援服務', 77, 82],
      ['公共服務、教育與醫療', 83, 88], ['藝文與其他服務', 90, 99]
    ];
    const option = (label, ids) => {
      const node = element('option', '', label); node.value = ids; return node;
    };
    select.replaceChildren(option('全部產業', 'ALL'));
    for (const [label, min, max] of groups) {
      const entries = [...names].filter(([, ids]) => Number(ids[0]) >= min && Number(ids[0]) <= max);
      if (!entries.length) continue;
      const group = element('optgroup'); group.label = label;
      if (entries.length > 1) group.append(option(`全部${label}`, entries.flatMap(([, ids]) => ids).join(',')));
      for (const [name, ids] of entries) { group.append(option(name, ids.join(','))); names.delete(name); }
      select.append(group);
    }
    for (const [name, ids] of names) select.append(option(name, ids.join(',')));
    select.append(option('來源未提供行業', 'UNKNOWN'));
    select.value = filters.category;
  }

  function activeConditions() {
    if (!catalog) return [];
    const district = counties[currentCounty].districts.find(d => d.id === filters.district);
    return [
      filters.district !== 'all' && ['district', district?.name || '行政區待分類', 'all'],
      filters.category !== 'ALL' && ['category', $('industrySelect').selectedOptions[0]?.textContent || '產業', 'ALL'],
      filters.capital !== 'ALL' && ['capital', `資本額 ${$('capitalCurrentLabel').textContent}`, 'ALL'],
      filters.address && ['address', filters.address, ''],
      filters.buildingId && ['buildingId', selectedBuilding()?.name || '已選大樓', ''],
      filters.market !== 'ALL' && ['market', filters.market === 'LISTED' ? '只看上市櫃' : `只看${filters.market}`, 'ALL'],
      filters.status !== 'ALL' && ['status', filters.status, 'ALL']
    ].filter(Boolean);
  }

  function renderActiveConditions() {
    setText('searchScope', `搜尋${counties[currentCounty].name}已收錄的商辦企業`);
    const list = $('activeFilters');
    list.replaceChildren();
    for (const [key, label, value] of activeConditions()) {
      const node = button(`${label} ×`, 'filter-token', () => {
        if (key === 'district') switchDistrict('all'); else chooseFilter(key, value);
        $('searchInput').focus({ preventScroll: true });
      });
      node.setAttribute('aria-label', `取消${label}`); list.append(node);
    }
    if (!list.childNodes.length) list.append(element('span', 'search-hint', '目前縣市 · 未限制其他條件'));
  }

  function renderSuggestions() {
    const list = $('searchSuggestions'); list.replaceChildren();
    if (!filters.query) return;
    for (const row of rows.slice(0, 6)) {
      const info = catalog.enrichment[row[1]] || {}, option = element('option');
      option.value = row[3]; option.label = `統編 ${row[1]}${info.stock_code ? ` · ${info.market} ${info.stock_code}` : ''} · ${row[0]}`;
      list.append(option);
    }
  }

  function renderFilters() {
    if (!catalog) return;
    const county = counties[currentCounty];
    $('districtNavBar').replaceChildren(chip(`全${county.name} (${county.company_count.toLocaleString()})`, 'all', filters.district === 'all', 'district-btn', () => switchDistrict('all')));
    (county.districts || []).forEach(d => $('districtNavBar').append(chip(`${d.name} (${d.company_count.toLocaleString()})`, d.id,
      filters.district === d.id, 'district-btn', () => switchDistrict(d.id))));
    renderIndustries();
    $('buildingChips').replaceChildren(chip('全部商辦大樓', '', !filters.address && !filters.buildingId, 'chip', () => chooseFilter('address', '')));
    if (filters.address) $('buildingChips').append(chip(filters.address, filters.address, true, 'chip', () => chooseFilter('address', '')));
    $('buildingChips').append(button('用名稱找大樓', 'chip', openAllBuildingsDirectory));
    $('buildingChips').append(button(complete ? `目前結果的 ${addressCount.toLocaleString()} 個門牌` : '搜尋完成後查看門牌', 'chip', openAddressDirectory));
    setText('buildingCurrentLabel', selectedBuilding()?.name || filters.address || '全部商辦大樓');
    document.querySelectorAll('#capitalChips [data-tier]').forEach(node => {
      const selected = node.dataset.tier === filters.capital;
      node.classList.toggle('active', selected); node.setAttribute('aria-pressed', String(selected));
      if (selected) setText('capitalCurrentLabel', node.textContent);
    });
    const styles = { ALL: 'all', 尚未拜訪: 'pending', 洽談中: 'negotiating', 已拜訪: 'done' };
    document.querySelectorAll('#statusChips [data-status]').forEach(node => {
      Object.values(styles).forEach(name => node.classList.remove(`active-${name}`));
      const selected = node.dataset.status === filters.status;
      if (selected) node.classList.add(`active-${styles[filters.status]}`);
      node.setAttribute('aria-pressed', String(selected));
    });
    document.querySelectorAll('#marketChips [data-market]').forEach(node => {
      const selected = node.dataset.market === filters.market;
      node.classList.toggle('active', selected); node.setAttribute('aria-pressed', String(selected));
    });
    renderActiveConditions();
    updateFilterToggleBadge();
  }

  function detail(label, value) { return element('div', 'card-detail', `${label}：${value || '來源未提供'}`); }
  function companyCard(row) {
    const id = Core.companyId(row[1]), info = catalog.enrichment[String(row[1])] || {};
    const card = element('article', 'company-card'); card.id = `card-${id}`; card.classList.toggle('selected', selectedId === id);
    const top = element('div', 'card-top-row'), title = element('div', 'card-name');
    title.append(button(row[3], 'card-title-button', () => selectCompany(row)));
    top.append(title);
    if (info.market) top.append(element('span', 'badge-listed', `${info.market} ${info.stock_code || ''}`));
    const identity = element('div', 'card-bld-tag', `統編 ${row[1]}`);
    const industries = [];
    for (let index = 8; index < 16; index += 2) if (row[index] || row[index + 1]) industries.push(`${row[index]} ${row[index + 1]}`.trim());
    const full = element('details', 'company-details');
    full.append(element('summary', '', '查看完整資料'), detail('總機構統編', row[2]), detail('資本額（完整金額）', Core.formatCapital(row[4])),
      detail('設立日期', `${Core.formatEstablished(row[5])}（來源原值：${row[5] || '未提供'}）`), detail('組織別', row[6]),
      detail('使用統一發票', row[7] === 'Y' ? '是（Y）' : row[7] === 'N' ? '否（N）' : row[7]), detail('全部登記行業', industries.join('；')));
    card.append(top, identity, element('div', 'card-addr', `登記地址：${row[0] || '來源未提供'}`),
      detail('資本額', Core.compactCapital(row[4])), detail('主要行業', row[9]));
    if (info.market) {
      const contact = element('div', 'card-contact-row');
      const phone = Core.phoneURL(info.phone);
      contact.append(element('span', '', '上市櫃公司總機：'), phone ? link(info.phone, phone, '') : element('span', '', info.phone || '來源未提供'));
      card.append(contact); full.append(detail('董事長', info.chairperson));
      const website = Core.safeURL(info.website), source = Core.safeURL(info.source_url);
      const links = element('div', 'card-contact-row');
      if (website) links.append(link(`公司網站：${info.website_raw || info.website}`, website, ''));
      else if (info.website_raw) links.append(detail('公司網站（來源原值）', info.website_raw));
      if (source) links.append(link('上市櫃資訊來源', source, ''));
      if (links.childNodes.length) full.append(links);
    } else full.append(element('p', 'record-note', '電話、代表人、網站及上市櫃資訊：本來源未提供，未自行補填。'));
    const actions = element('div', 'card-actions-row'), label = element('label', 'status-select-wrapper', '拜訪紀錄 ');
    const select = element('select', 'status-select'); select.setAttribute('aria-label', `${row[3]}的拜訪紀錄`);
    Core.STATUSES.forEach(status => { const option = element('option', '', status); option.value = status; select.append(option); });
    select.value = statuses[id] || Core.STATUSES[0];
    select.addEventListener('change', event => updateCompanyStatus(id, event.target.value)); label.append(select); actions.append(label);
    if (row[0]) actions.append(link('查登記地址', `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(row[0])}`, 'card-btn'));
    full.append(element('p', 'record-note', '主要行業依來源第一項登記行業顯示。登記地址不代表實際營業或進駐位置；總機及董事長資訊僅限統編相符的上市櫃公司。'));
    card.append(actions, full);
    return card;
  }

  function emptyResults() {
    const node = element('div', 'empty-state'), conditions = activeConditions();
    node.append(element('strong', '', '目前條件下沒有找到企業'),
      element('p', '', `搜尋範圍：${counties[currentCounty].name}${conditions.length ? ' · ' + conditions.map(([, label]) => label).join(' · ') : ''}`));
    if (filters.query) node.append(element('p', '', `關鍵字：「${filters.query}」`));
    node.append(element('p', '', '僅搜尋本站已收錄的商辦企業；沒有結果不代表公司不存在。可逐一放寬條件：'));
    const actions = element('div', 'empty-actions');
    for (const [key, label, value] of conditions) actions.append(button(`取消${label}`, 'card-btn', () => {
      if (key === 'district') switchDistrict('all'); else chooseFilter(key, value);
    }));
    if (filters.query) actions.append(button('清除關鍵字', 'card-btn', () => { clearSearch(); runQuery(); }));
    actions.append(button('切換縣市，保留關鍵字', 'card-btn', openCountyModal));
    node.append(actions); return node;
  }

  function renderList() {
    const total = counties[currentCounty]?.company_count || 0;
    setText('resultCountText', loading ? `檢索中 ${scanned.toLocaleString()}／${total.toLocaleString()} · 暫時符合 ${resultCount.toLocaleString()} 筆`
      : failed ? `搜尋未完成 · 暫時符合 ${resultCount.toLocaleString()} 筆`
        : `符合 ${resultCount.toLocaleString()} 筆 · 已顯示 ${rows.length.toLocaleString()} 筆`);
    setText('mobileCount', resultCount.toLocaleString());
    [['countAll', 'ALL'], ['countPending', '尚未拜訪'], ['countNegotiating', '洽談中'], ['countDone', '已拜訪']]
      .forEach(([id, key]) => setText(id, (statusCounts[key] || 0).toLocaleString()));
    const list = $('clientList'), scroller = window.innerWidth <= 768 ? document.querySelector('.sidebar') : list;
    const scrollTop = scroller?.scrollTop || 0;
    list.replaceChildren();
    renderBuildingContext(list);
    if (!rows.length) list.append(loading || failed ? element('p', 'empty-state', loading ? '正在搜尋所選縣市，請稍候…'
      : '資料尚未完整載入，請使用上方提示重試。') : emptyResults());
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
      node.append(element('span', 'county-card-name', c.name), element('span', 'county-card-badge', `${c.building_count ? `${c.building_count.toLocaleString()} 棟商辦 · ` : ''}${c.company_count.toLocaleString()} 家樓內企業`)); grid.append(node);
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

  function namedBuildingEntry(building) {
    const node = button('', 'building-directory-entry', () => selectNamedBuilding(building));
    node.append(element('strong', '', building.name), element('span', '', building.addresses.join('、')),
      ...(building.name_status === 'address_only' ? [element('span', '', '門牌已核對 · 大樓名稱待查')] : []),
      element('span', '', building.company_count ? `本期收錄 ${building.company_count.toLocaleString()} 家 · 未套用企業條件` : '本期企業名單未收錄此門牌，不代表沒有企業'));
    return node;
  }
  function selectNamedBuilding(building) {
    const capital = filters.capital;
    closeModal('modalBuilding'); resetFilters(); filters.capital = capital;
    currentCounty = building.county_id; filters.buildingId = building.id;
    setText('currentCountyDisplay', counties[currentCounty].name); setText('headerCountyBadge', counties[currentCounty].name);
    runQuery(); setMobileView('list');
    if (map && counties[currentCounty].center) map.setView(counties[currentCounty].center, counties[currentCounty].zoom || 11);
    $('clientList').scrollTop = 0;
    $('searchInput').focus({ preventScroll: true });
  }
  function renderBuildingContext(list) {
    const building = selectedBuilding();
    if (building) {
      const section = element('section', 'building-context'); section.id = 'selectedBuilding';
      section.append(element('h3', '', building.name));
      if (building.name_status === 'address_only') section.append(element('p', '', '門牌已核對 · 大樓名稱待查'));
      if (building.note) section.append(element('p', 'search-hint', building.note));
      for (const address of building.addresses) section.append(element('p', '', `${address} · 本期收錄 ${building.address_counts[address].toLocaleString()} 家`));
      section.append(element('p', 'search-hint', `核對日期：${building.checked_at}。名單依已核對門牌的稅籍登記彙整，並非實際進駐或既有客戶名單。`));
      const sources = element('details', 'building-sources'); sources.append(element('summary', '', building.name_status === 'address_only' ? '門牌登記來源' : '大樓名稱與門牌來源'));
      for (const id of new Set(building.references.map(ref => ref.source_id))) {
        const source = catalog.building_name_sources[id], url = Core.safeURL(source.url);
        if (url) sources.append(link(source.title, url, ''));
      }
      section.append(sources, button('查看本棟全部收錄企業', 'card-btn', () => {
        resetFilters(); filters.capital = 'ALL'; filters.buildingId = building.id; runQuery();
      }));
      list.append(section);
    } else if (filters.query) {
      const matches = Core.findNamedBuildings(catalog.named_buildings, filters.query);
      if (!matches.length) return;
      const section = element('section', 'building-context'); section.id = 'buildingCandidates';
      section.append(element('h3', '', '符合名稱或門牌的大樓'), element('p', 'search-hint', '選定門牌後查看企業；保留資本額，清除其他企業條件。'));
      matches.slice(0, 3).forEach(item => section.append(namedBuildingEntry(item)));
      if (matches.length > 3) section.append(button(`查看全部 ${matches.length} 棟`, 'text-button', () => openAllBuildingsDirectory(filters.query)));
      list.append(section);
    }
  }
  function directoryModes() {
    const nav = element('div', 'directory-modes'); nav.setAttribute('aria-label', '大樓查找方式');
    nav.append(chip('全台大樓與門牌', 'names', directoryMode === 'names', 'chip', openAllBuildingsDirectory));
    const addresses = chip('目前結果的門牌', 'addresses', directoryMode === 'addresses', 'chip', openAddressDirectory);
    addresses.disabled = !complete; nav.append(addresses); return nav;
  }
  function renderNamedDirectory() {
    const list = $('directoryRows'); if (directoryMode !== 'names' || !list) return;
    const countyId = $('directoryCounty')?.value || 'ALL';
    const buildings = (catalog.named_buildings || []).filter(item => countyId === 'ALL' || item.county_id === countyId);
    const matches = Core.findNamedBuildings(buildings, $('directorySearch').value);
    list.replaceChildren(element('p', 'search-hint', `找到 ${matches.length} 個入口 · 不套用企業篩選條件`));
    matches.forEach(building => list.append(namedBuildingEntry(building)));
    if (!matches.length) {
      list.append(element('p', 'empty-state', buildings.length ? '這個名稱尚未收錄。可改用街道門牌查詢；零筆不代表大樓或企業不存在。' : '本縣市的大樓名稱仍待核對；已收錄的企業與門牌仍可搜尋。'));
      if (countyId !== 'ALL') list.append(button(`查詢${counties[countyId].name}企業與門牌`, 'card-btn', () => {
        closeModal('modalBuilding'); resetFilters(); switchCounty(countyId);
      }));
    }
  }
  function openAllBuildingsDirectory(query = '') {
    if (!catalog) return;
    directoryMode = 'names'; clearTimeout(directoryTimer);
    setText('bldModalTitle', '找大樓 · 全台縣市');
    const entries = catalog.named_buildings || [], addressOnly = entries.filter(item => item.name_status === 'address_only').length;
    setText('bldModalSubtitle', `首批 ${entries.length - addressOnly} 棟已核對名稱${addressOnly ? `、${addressOnly} 個僅核對門牌` : ''}，更新 ${catalog.building_names_updated_at || '未提供'}。選取後切換地區、保留資本額並清除其他企業條件；僅比對列出的門牌。`);
    const countySelect = element('select', 'industry-select'); countySelect.id = 'directoryCounty'; countySelect.setAttribute('aria-label', '選擇大樓所在縣市');
    const option = (value, text) => { const node = element('option', '', text); node.value = value; return node; };
    countySelect.append(option('ALL', '全台縣市 · 名稱與門牌'));
    for (const [id, county] of Object.entries(counties)) {
      const local = entries.filter(item => item.county_id === id), doors = local.filter(item => item.name_status === 'address_only').length;
      const names = local.length - doors;
      countySelect.append(option(id, `${county.name} · ${names ? `${names} 棟名稱已核對` : ''}${names && doors ? '、' : ''}${doors ? `${doors} 個門牌已核對，名稱待查` : ''}${local.length ? '' : '名稱待核對，可查企業門牌'}`));
    }
    countySelect.addEventListener('change', renderNamedDirectory);
    const search = element('input', 'directory-search'); search.type = 'search'; search.id = 'directorySearch';
    search.placeholder = '輸入招牌名稱，例如：世貿帝國'; search.setAttribute('aria-label', '搜尋大樓名稱、別名或地址');
    search.value = typeof query === 'string' ? query : '';
    search.addEventListener('input', renderNamedDirectory);
    const directoryRows = element('div', 'directory-rows'); directoryRows.id = 'directoryRows';
    $('bldModalList').replaceChildren(directoryModes(), countySelect, search, directoryRows);
    renderNamedDirectory(); openModal('modalBuilding'); search.focus();
  }
  function openAddressDirectory() {
    if (!complete) { notice('請等完整搜尋完成後再開啟商辦大樓名錄。'); return; }
    directoryMode = 'addresses'; clearTimeout(directoryTimer);
    setText('bldModalTitle', `${counties[currentCounty].name} · 商辦大樓名錄`);
    setText('bldModalSubtitle', `目前條件符合 ${addressCount.toLocaleString()} 棟大樓地址；點選後查看該棟符合相同條件的登記企業。`);
    const list = $('bldModalList'), search = element('input', 'directory-search');
    search.type = 'search'; search.id = 'directorySearch'; search.placeholder = '搜尋商辦大樓地址'; search.setAttribute('aria-label', '搜尋目前名錄中的商辦大樓地址');
    search.addEventListener('input', () => { clearTimeout(directoryTimer); directoryTimer = setTimeout(() => requestDirectory(0), 150); });
    const directoryRows = element('div', 'directory-rows'); directoryRows.id = 'directoryRows';
    list.replaceChildren(directoryModes(), search, directoryRows); openModal('modalBuilding'); requestDirectory(0);
  }
  function requestDirectory(offset) {
    directoryRequestId++; directoryOffset = offset;
    worker.postMessage({ type: 'directory', id: queryId, requestId: directoryRequestId, offset, query: $('directorySearch')?.value || '' });
  }
  function renderDirectoryPage(message) {
    const list = $('directoryRows'); if (!list || activeModal?.id !== 'modalBuilding' || directoryMode !== 'addresses') return;
    if (!message.offset) list.replaceChildren();
    list.querySelector('.list-pagination')?.remove();
    if (!message.total) list.append(element('p', 'empty-state', '沒有符合的商辦大樓。'));
    message.addresses.forEach(item => {
      const node = button('', 'building-directory-entry', () => openBuildingDirectory(item.address));
      node.append(element('strong', '', item.address || '來源未提供地址'), element('span', '', `${item.count.toLocaleString()} 家樓內企業`)); list.append(node);
    });
    const next = message.offset + message.addresses.length;
    if (next < message.total) list.append(button(`載入更多商辦大樓（剩餘 ${(message.total - next).toLocaleString()} 棟）`, 'list-pagination', () => requestDirectory(next)));
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
    const count = activeConditions().filter(([key]) => key !== 'district').length;
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
    });
    [['btnDesktopList', 'list'], ['btnDesktopSplit', 'split'], ['btnDesktopMap', 'map']].forEach(([id, value]) => {
      $(id)?.classList.toggle('active', view === value); $(id)?.setAttribute('aria-pressed', String(view === value));
    }); if (map) setTimeout(() => map.invalidateSize(), 100);
  }

  function wireEvents() {
    const scheduleSearch = () => { clearTimeout(searchTimer); if (!composing) searchTimer = setTimeout(() => runQuery(), 300); };
    $('searchInput').addEventListener('compositionstart', () => { composing = true; clearTimeout(searchTimer); });
    $('searchInput').addEventListener('compositionend', () => { composing = false; scheduleSearch(); });
    $('searchInput').addEventListener('input', event => { if (!event.isComposing) scheduleSearch(); });
    $('searchInput').addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.isComposing && !composing && event.keyCode !== 229) { event.preventDefault(); runQuery(); }
    });
    $('btnDoSearch').addEventListener('click', () => runQuery());
    $('btnClearSearch').addEventListener('click', () => { clearSearch(); runQuery(); $('searchInput').focus(); });
    $('btnResetFilter').addEventListener('click', () => { resetFilters(); runQuery(); });
    $('btnClearFilters').addEventListener('click', () => { resetFilters(); filters.capital = 'ALL'; runQuery(); });
    $('industrySelect').addEventListener('change', event => chooseFilter('category', event.target.value));
    document.querySelectorAll('#marketChips [data-market]').forEach(node => node.addEventListener('click', () => chooseFilter('market', node.dataset.market)));
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
    ['modalBuilding', 'modalCountySelect', 'modalSources', 'modalHelp'].forEach(id => $(id)?.addEventListener('click', event => { if (event.target === $(id)) closeModal(id); }));
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
      const bldCount = catalog.total_buildings || catalog.coverage?.commercial_buildings || 0;
      const bldPart = bldCount ? `${bldCount.toLocaleString()} 棟商辦 · ` : '';
      setText('bannerSummary', `財政部商辦大樓稅籍 · ${bldPart}${count.toLocaleString()} 家樓內企業 · ${Object.keys(counties).length} 縣市`);
      setText('dataVersionText', `來源快照：${catalog.source.source_date || '以來源標示為準'} · 取得時間：${catalog.source.retrieved_at || '未提供'} · 版本 ${catalog.dataset_version.slice(0, 12)}`);
      setText('sourceSummary', `本版自財政部完整稅籍資料嚴格篩選 ${bldPart}${count.toLocaleString()} 筆商業辦公大樓內登記企業。包含企業名稱、統編、樓層地址、資本額及行業等原始欄位。`);
      const sourceURL = Core.safeURL(catalog.source.url);
      if ($('sourceDownloadLink') && sourceURL) { $('sourceDownloadLink').href = sourceURL; $('sourceDownloadLink').target = '_blank'; $('sourceDownloadLink').rel = 'noopener noreferrer'; }
      startWorker(); initMap(); switchCounty(currentCounty);
    } catch (_) { notice('無法載入正式資料目錄。請檢查網路並確認使用網站網址開啟，再重試。', boot); }
    finally { clearTimeout(timeout); }
  }
  Object.assign(window, { switchCounty, updateCompanyStatus, openCountyModal, confirmCountySelection, openBuildingDirectory, openAllBuildingsDirectory,
    closeCountyModal: () => closeModal('modalCountySelect'), closeBuildingModal: () => closeModal('modalBuilding'),
    openSourceModal: () => openModal('modalSources'), closeSourceModal: () => closeModal('modalSources'),
    openHelpModal: () => openModal('modalHelp'), closeHelpModal: () => closeModal('modalHelp'),
    cycleBasemap, toggleAutoLabels, toggleAdvancedFilters, toggleChipsExpand, setMobileView,
    bookmarkSite: () => { notice(/Mac|iPhone|iPad/.test(navigator.platform) ? '按 ⌘ + D 加入書籤；手機可由分享選單加入主畫面。' : '按 Ctrl + D 加入書籤；手機可由瀏覽器選單加入主畫面。'); closeMenus(); } });
  function start() {
    if (!Core) { notice('搜尋元件未載入，請重新整理頁面。'); return; }
    wireEvents(); setMobileView(window.innerWidth <= 768 ? 'list' : 'split'); boot();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true }); else start();
})();
