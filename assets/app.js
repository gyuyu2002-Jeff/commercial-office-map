/* Public demo catalogue; user visit records remain on this browser. */
(() => {
  'use strict';
  const Core = window.CommercialMapCore;
  const STORAGE_KEY = 'commercial_status_overrides_v3';
  const LEGACY_KEY = 'commercial_status_overrides_v2';
  const DEFAULT_COUNTY_KEY = 'default_commercial_county';
  const PAGE_SIZE = 40;
  const $ = id => document.getElementById(id);
  let catalog, counties = {}, buildings = [], categories = [], companies = [];
  let currentCounty = 'taoyuan', selectedCounty = 'taoyuan', countyRegion = 'ALL';
  let filters = initialFilters(), visibleCount = PAGE_SIZE, selectedCompany = null;
  let statusOverrides = Object.create(null), knownIds = new Set(), storageProblem = false;
  let loadSequence = 0, loading = false, searchTimer, countyAbort;
  const countyCache = new Map();
  let map, markersLayer, locationMarker, baseLayers = {}, baseLayerName = 'osm', autoLabels = true;
  let currentResults = [], activeModal = null, modalTrigger = null;
  const backgroundInert = new Map();

  function initialFilters() {
    return { district: 'all', category: 'ALL', capital: 'ALL', building: 'ALL', status: 'ALL', query: '' };
  }

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = String(text);
    return node;
  }

  function button(text, className, action) {
    const node = element('button', className, text);
    node.type = 'button';
    node.addEventListener('click', action);
    return node;
  }

  function setText(id, text) { if ($(id)) $(id).textContent = text; }

  function setMapToolLabel(id, icon, label) {
    const node = $(id);
    if (!node) return;
    const [name, value] = label.split('：');
    node.replaceChildren(element('span', 'tool-icon', icon), element('span', 'tool-short', name),
      element('span', 'tool-text', value ? `：${value}` : ''));
    node.setAttribute('aria-label', label);
    node.title = label;
  }

  function listScrollContainer() {
    return window.innerWidth <= 768 ? document.querySelector('.sidebar') : $('clientList');
  }

  function notice(message, action, label = '重試', target = 'appNotice') {
    const node = $(target);
    if (!node) return;
    node.replaceChildren();
    node.hidden = !message;
    if (!message) return;
    node.append(element('span', '', message));
    if (action) node.append(button(label, 'notice-action', action));
  }

  function storageNotice() {
    storageProblem = true;
    notice('瀏覽器無法保存紀錄；目前變更只保留於本次頁面，請下載備份。', backupRecords, '下載備份');
  }

  function saveStatuses() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ schema_version: 3, statuses: statusOverrides }));
      storageProblem = false;
      return true;
    } catch (_) { storageNotice(); return false; }
  }

  function loadStatuses() {
    try {
      const result = Core.loadStoredStatuses(localStorage.getItem(STORAGE_KEY), localStorage.getItem(LEGACY_KEY), catalog.legacy_id_map, knownIds);
      statusOverrides = result.statuses;
      if (result.migrated && saveStatuses()) notice(`已保留 ${Object.keys(statusOverrides).length} 筆您曾修改的狀態；示範資料原有的隨機狀態已重設。`);
    } catch (_) {
      storageProblem = true;
      notice('無法讀取本機拜訪紀錄；原始儲存內容未刪除。請先匯入有效備份，或下載目前紀錄備份。');
    }
  }

  function applyStatuses() {
    companies.forEach(company => { company.status = statusOverrides[company.id] || Core.STATUSES[0]; });
  }

  async function readJSON(url, signal) {
    const response = await fetch(url, { signal });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  }

  function clearSearch() {
    clearTimeout(searchTimer);
    if ($('searchInput')) $('searchInput').value = '';
    if ($('btnClearSearch')) $('btnClearSearch').style.display = 'none';
  }

  function resetFilters() {
    filters = initialFilters();
    visibleCount = PAGE_SIZE;
    selectedCompany = null;
    clearSearch();
  }

  async function switchCounty(countyId) {
    if (!Object.hasOwn(counties, countyId)) return;
    const sequence = ++loadSequence;
    if (countyAbort) countyAbort.abort();
    const controller = new AbortController();
    countyAbort = controller;
    currentCounty = countyId;
    resetFilters();
    companies = [];
    loading = true;
    setText('currentCountyDisplay', counties[countyId].name);
    setText('headerCountyBadge', counties[countyId].name);
    renderFilters();
    renderList();
    if (!storageProblem) notice('');
    const timeout = setTimeout(() => controller.abort(), 15000);
    try {
      let records = countyCache.get(countyId);
      if (!records) {
        const data = await readJSON(`data/counties/${encodeURIComponent(countyId)}.json?v=${encodeURIComponent(catalog.dataset_version)}`, controller.signal);
        records = Array.isArray(data) ? data : data.companies;
        if (!Array.isArray(records) || records.some(c => !Core.isRecord(c) || c.county_id !== countyId
          || !knownIds.has(c.id) || !c.is_demo)) throw new Error('資料格式不符');
        countyCache.set(countyId, records);
      }
      if (sequence !== loadSequence) return;
      companies = records;
      loading = false;
      applyStatuses();
      renderFilters();
      renderList();
      if (map) map.setView(counties[countyId].center, counties[countyId].zoom || 13);
    } catch (_) {
      if (sequence !== loadSequence) return;
      loading = false;
      renderList();
      notice(`無法載入${counties[countyId].name}資料。請檢查網路後重試，或切換其他縣市。`, () => switchCounty(countyId));
    } finally { clearTimeout(timeout); }
  }

  function scopeCompanies() {
    return companies.filter(c => filters.district === 'all' || c.district_id === filters.district);
  }

  function scopeBuildings() {
    return buildings.filter(b => b.county_id === currentCounty && (filters.district === 'all' || b.district_id === filters.district));
  }

  function chooseFilter(key, value) {
    filters[key] = value;
    visibleCount = PAGE_SIZE;
    selectedCompany = null;
    renderFilters();
    renderList();
    const containerId = { category: 'categoryChips', building: 'buildingChips' }[key];
    if (containerId) Array.from($(containerId).querySelectorAll('button')).find(node => node.dataset.value === value)?.focus({ preventScroll: true });
  }

  function switchDistrict(id) {
    resetFilters();
    filters.district = id;
    renderFilters();
    renderList();
    Array.from($('districtNavBar').querySelectorAll('button')).find(node => node.dataset.value === id)?.focus({ preventScroll: true });
    const district = (counties[currentCounty].districts || []).find(d => d.id === id);
    const center = district || counties[currentCounty];
    if (map && center.center) map.setView(center.center, center.zoom || 13);
  }

  function chip(text, value, selected, className, action) {
    const node = button(text, `${className}${selected ? ' active' : ''}`, action);
    node.dataset.value = value;
    node.setAttribute('aria-pressed', String(selected));
    return node;
  }

  function renderFilters() {
    if (!catalog) return;
    const county = counties[currentCounty], scoped = scopeCompanies();
    $('districtNavBar').replaceChildren(chip(`全${county.name} (${companies.length})`, 'all', filters.district === 'all', 'district-btn', () => switchDistrict('all')));
    (county.districts || []).forEach(d => $('districtNavBar').append(chip(`${d.name} (${companies.filter(c => c.district_id === d.id).length})`, d.id,
      filters.district === d.id, 'district-btn', () => switchDistrict(d.id))));
    $('categoryChips').replaceChildren(chip(`全部 (${scoped.length})`, 'ALL', filters.category === 'ALL', 'chip', () => chooseFilter('category', 'ALL')));
    categories.forEach(cat => {
      const count = scoped.filter(c => c.category === cat.name).length;
      if (count) $('categoryChips').append(chip(`${cat.icon || ''} ${cat.name} (${count})`, cat.name,
        filters.category === cat.name, 'chip', () => chooseFilter('category', filters.category === cat.name ? 'ALL' : cat.name)));
    });
    const scopedBuildings = scopeBuildings();
    $('buildingChips').replaceChildren(chip(`全部大樓 (${scopedBuildings.length})`, 'ALL', filters.building === 'ALL', 'chip', () => chooseFilter('building', 'ALL')));
    scopedBuildings.forEach(b => $('buildingChips').append(chip(`${b.name} (${scoped.filter(c => c.building_id === b.id).length})`, b.id,
      filters.building === b.id, 'chip', () => {
        chooseFilter('building', filters.building === b.id ? 'ALL' : b.id);
        if (map && filters.building !== 'ALL') map.setView([b.lat, b.lng], 17);
      })));
    setText('catCurrentLabel', filters.category === 'ALL' ? '全部企業' : filters.category);
    setText('buildingCurrentLabel', buildings.find(b => b.id === filters.building)?.name || '全部大樓');
    document.querySelectorAll('#capitalChips [data-tier]').forEach(node => {
      const selected = node.dataset.tier === filters.capital;
      node.classList.toggle('active', selected);
      node.setAttribute('aria-pressed', String(selected));
      if (selected) setText('capitalCurrentLabel', node.textContent);
    });
    const states = { ALL: 'all', LISTED: 'listed', 尚未拜訪: 'pending', 洽談中: 'negotiating', 已拜訪: 'done' };
    document.querySelectorAll('#statusChips [data-status]').forEach(node => {
      Object.values(states).forEach(name => node.classList.remove(`active-${name}`));
      const selected = node.dataset.status === filters.status;
      if (selected) node.classList.add(`active-${states[filters.status]}`);
      node.setAttribute('aria-pressed', String(selected));
    });
    updateFilterToggleBadge();
  }

  function updateCounts(filtered) {
    const base = Core.filterCompanies(companies, filters, true);
    setText('resultCountText', loading ? '正在載入資料…' : `符合 ${filtered.length} 筆示範資料 · 已顯示 ${Math.min(visibleCount, filtered.length)} 筆`);
    setText('mobileCount', filtered.length);
    setText('countAll', base.length);
    setText('countListed', base.filter(c => c.is_listed).length);
    setText('countPending', base.filter(c => c.status === '尚未拜訪').length);
    setText('countNegotiating', base.filter(c => c.status === '洽談中').length);
    setText('countDone', base.filter(c => c.status === '已拜訪').length);
  }

  function companyCard(company) {
    const card = element('article', 'company-card');
    card.id = `card-${company.id}`;
    card.classList.toggle('selected', selectedCompany === company.id);
    const top = element('div', 'card-top-row'), title = element('div', 'card-name');
    title.append(button(company.name, 'card-title-button', () => selectCompany(company)));
    top.append(title, element('span', 'badge-cat', '示範資料'));
    const building = element('div', 'card-bld-tag');
    building.append(element('strong', '', company.building_name), element('span', 'card-floor-pill', company.floor));
    const details = element('div', 'card-contact-row', `${company.category} · 模擬資本額 ${company.capital_str}`);
    const actions = element('div', 'card-actions-row'), label = element('label', 'status-select-wrapper', '練習拜訪狀態 ');
    const select = element('select', 'status-select');
    select.setAttribute('aria-label', `${company.name}的練習拜訪狀態`);
    Core.STATUSES.forEach(status => { const option = element('option', '', status); option.value = status; select.append(option); });
    select.value = company.status;
    select.addEventListener('change', event => updateCompanyStatus(company.id, event.target.value));
    label.append(select);
    actions.append(label, button('大樓示範名錄', 'card-btn', () => openBuildingDirectory(company.building_id)));
    card.append(top, building, element('div', 'card-addr', company.address), details,
      element('p', 'demo-note', '示範樓層與進駐資料，尚未查核。'), actions);
    return card;
  }

  function renderList() {
    currentResults = Core.filterCompanies(companies, filters);
    updateCounts(currentResults);
    const list = $('clientList');
    const scroller = listScrollContainer(), scrollTop = scroller?.scrollTop || 0;
    list.replaceChildren();
    if (loading || !currentResults.length) {
      list.append(element('div', 'empty-state', loading ? '正在載入縣市名錄…' : '沒有符合條件的示範資料。可重設篩選或更換縣市。'));
    } else {
      const fragment = document.createDocumentFragment();
      currentResults.slice(0, visibleCount).forEach(company => fragment.append(companyCard(company)));
      if (visibleCount < currentResults.length) {
        fragment.append(button(`載入更多（尚有 ${currentResults.length - visibleCount} 筆）`, 'list-pagination', () => {
          const nextIndex = visibleCount;
          visibleCount += PAGE_SIZE;
          renderList();
          const next = $(`card-${currentResults[nextIndex]?.id}`)?.querySelector('button');
          if (next) next.focus({ preventScroll: true });
        }));
      }
      list.append(fragment);
    }
    if (scroller) scroller.scrollTop = scrollTop;
    renderMapMarkers();
  }

  function selectCompany(company) {
    selectedCompany = company.id;
    document.querySelectorAll('.company-card').forEach(node => node.classList.toggle('selected', node.id === `card-${company.id}`));
    const building = buildings.find(b => b.id === company.building_id);
    if (map && building) map.setView([building.lat, building.lng], 17);
    if (map && window.innerWidth <= 768) setMobileView('map');
  }

  function updateCompanyStatus(id, status, event) {
    if (event) event.stopPropagation();
    const company = companies.find(c => c.id === id);
    if (!company || !Core.STATUSES.includes(status)) return;
    statusOverrides[id] = status;
    company.status = status;
    const saved = saveStatuses();
    renderList();
    if (saved) notice('練習狀態已儲存於此瀏覽器。');
    const remaining = $(`card-${id}`)?.querySelector('select');
    if (remaining) remaining.focus({ preventScroll: true });
    else $('btnResetFilter')?.focus({ preventScroll: true });
  }

  function initMap() {
    if (map) return;
    try {
      if (!window.L) throw new Error('地圖套件尚未載入');
      map = L.map('map', { center: counties[currentCounty]?.center || [23.7, 121], zoom: 8,
        wheelPxPerZoomLevel: 180, wheelDebounceTime: 150 });
      markersLayer = L.layerGroup().addTo(map);
      baseLayers = {
        osm: L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>' }),
        nlsc: L.tileLayer('https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}', { maxZoom: 19,
          attribution: '&copy; <a href="https://maps.nlsc.gov.tw/">內政部國土測繪中心</a>' }),
        sat: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { maxZoom: 19,
          attribution: 'Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community' })
      };
      Object.values(baseLayers).forEach(layer => layer.on('tileerror', () => {
        if (map.hasLayer(layer)) notice('部分底圖無法載入；名錄仍可使用。可切換圖資後重試。', cycleBasemap, '切換圖資', 'mapNotice');
      }));
      baseLayers.osm.addTo(map);
      map.on('zoomend moveend', renderMapMarkers);
      notice('', null, '', 'mapNotice');
      renderMapMarkers();
    } catch (_) {
      if (map) { map.remove(); map = null; }
      notice('地圖無法啟用，企業名錄與篩選仍可使用。', null, '', 'mapNotice');
    }
  }

  function cycleBasemap() {
    if (!map) return;
    map.removeLayer(baseLayers[baseLayerName]);
    const layers = ['osm', 'nlsc', 'sat'];
    baseLayerName = layers[(layers.indexOf(baseLayerName) + 1) % layers.length];
    notice('', null, '', 'mapNotice');
    baseLayers[baseLayerName].addTo(map);
    setMapToolLabel('btnToggleLayer', '🗺️', { osm: '圖資：標準街道', nlsc: '圖資：臺灣通用', sat: '圖資：衛星空照' }[baseLayerName]);
  }

  function renderMapMarkers() {
    if (!map || !markersLayer) return;
    markersLayer.clearLayers();
    const counts = new Map();
    currentResults.forEach(c => counts.set(c.building_id, (counts.get(c.building_id) || 0) + 1));
    const matched = buildings.filter(b => counts.has(b.id));
    const detailed = map.getZoom() >= 16;
    const groups = matched.map(b => ({ members: [b], point: map.project([b.lat, b.lng], map.getZoom()) }));
    // Recompute centroids after each merge so a grid boundary cannot leave overlapping pins.
    if (!detailed) {
      let merged = true;
      while (merged) {
        merged = false;
        mergePair: for (let i = 0; i < groups.length; i++) {
          for (let j = i + 1; j < groups.length; j++) {
            const a = groups[i], b = groups[j];
            if (a.point.distanceTo(b.point) >= 54) continue;
            const count = a.members.length + b.members.length;
            a.point = L.point((a.point.x * a.members.length + b.point.x * b.members.length) / count,
              (a.point.y * a.members.length + b.point.y * b.members.length) / count);
            a.members.push(...b.members);
            groups.splice(j, 1);
            merged = true;
            break mergePair;
          }
        }
      }
    }
    groups.forEach(cluster => {
      const group = cluster.members;
      const total = group.reduce((sum, b) => sum + counts.get(b.id), 0);
      const center = map.unproject(cluster.point, map.getZoom());
      const label = group.length === 1 && detailed && autoLabels ? `${group[0].name} · ${total}` : String(total);
      const visual = element('div', group.length === 1 && detailed && autoLabels ? 'bld-marker' : 'cluster-marker', label);
      const title = group.length === 1 ? `${group[0].name}：${total} 筆示範資料（未查核）` : `${group.length} 棟大樓，共 ${total} 筆示範資料`;
      const marker = L.marker(center, { icon: L.divIcon({ className: 'custom-bld-pin', html: visual, iconSize: null }), title,
        keyboard: true, alt: title });
      marker.on('click', () => {
        if (group.length === 1) openBuildingDirectory(group[0].id);
        else map.fitBounds(group.map(b => [b.lat, b.lng]), { padding: [40, 40], maxZoom: 17 });
      });
      markersLayer.addLayer(marker);
    });
  }

  function toggleAutoLabels() {
    autoLabels = !autoLabels;
    setMapToolLabel('btnToggleLabels', '🏷️', autoLabels ? '標籤：自動' : '標籤：關閉');
    $('btnToggleLabels')?.setAttribute('aria-pressed', String(autoLabels));
    renderMapMarkers();
  }

  function closeMenus() { document.querySelectorAll('details.more-actions[open]').forEach(node => { node.open = false; }); }

  function openModal(id) {
    const modal = $(id);
    if (!modal) return;
    const trigger = activeModal ? modalTrigger : document.activeElement;
    if (activeModal && activeModal !== modal) closeModal(activeModal.id, false);
    modalTrigger = trigger?.closest('details.more-actions')?.querySelector('summary') || trigger;
    closeMenus();
    activeModal = modal;
    modal.hidden = false;
    modal.style.display = 'flex';
    for (const child of document.body.children) {
      if (child !== modal && !child.contains(modal) && child.tagName !== 'SCRIPT' && !backgroundInert.has(child)) {
        backgroundInert.set(child, child.inert);
        child.inert = true;
      }
    }
    modal.querySelector('button, input, [tabindex="0"]')?.focus();
  }

  function closeModal(id, restoreFocus = true) {
    const modal = $(id);
    if (!modal) return;
    modal.style.display = 'none';
    modal.hidden = true;
    if (activeModal === modal) {
      activeModal = null;
      backgroundInert.forEach((wasInert, node) => { node.inert = wasInert; });
      backgroundInert.clear();
      if (restoreFocus && modalTrigger?.isConnected) modalTrigger.focus();
    }
  }

  function renderCountyGrid() {
    const grid = $('countyGridContainer');
    grid.replaceChildren();
    const tabs = element('div', 'county-region-tabs');
    ['ALL', '北部', '中部', '南部', '東部', '離島'].forEach(region => {
      const count = Object.values(counties).filter(c => region === 'ALL' || c.region === region).length;
      tabs.append(chip(`${region === 'ALL' ? '全部' : region} (${count})`, region, countyRegion === region, 'chip', () => {
        countyRegion = region; renderCountyGrid();
        Array.from(grid.querySelectorAll('.county-region-tabs button')).find(node => node.dataset.value === region)?.focus();
      }));
    });
    grid.append(tabs);
    Object.values(counties).filter(c => countyRegion === 'ALL' || c.region === countyRegion).forEach(c => {
      const node = button('', `county-card-btn${selectedCounty === c.id ? ' selected' : ''}`, () => {
        selectedCounty = c.id;
        renderCountyGrid();
        Array.from(grid.querySelectorAll('[data-county]')).find(item => item.dataset.county === c.id)?.focus();
      });
      node.dataset.county = c.id;
      node.setAttribute('aria-pressed', String(selectedCounty === c.id));
      node.append(element('span', 'county-card-name', c.name), element('span', 'county-card-desc', c.description || c.desc || ''),
        element('span', 'county-card-badge', `${c.building_count || 0} 棟 · ${c.company_count || 0} 筆示範資料`));
      grid.append(node);
    });
  }

  function openCountyModal() {
    if (!catalog) return;
    selectedCounty = currentCounty;
    renderCountyGrid();
    openModal('modalCountySelect');
  }

  function confirmCountySelection() {
    closeModal('modalCountySelect');
    if ($('chkSetDefaultCounty')?.checked) {
      try { localStorage.setItem(DEFAULT_COUNTY_KEY, selectedCounty); }
      catch (_) { storageNotice(); }
    } else {
      try { localStorage.removeItem(DEFAULT_COUNTY_KEY); }
      catch (_) { storageNotice(); }
    }
    switchCounty(selectedCounty);
  }

  function openBuildingDirectory(id, event) {
    if (event) event.stopPropagation();
    const building = buildings.find(b => b.id === id && b.county_id === currentCounty);
    if (!building) return;
    setText('bldModalTitle', `${building.name} · 示範名錄`);
    setText('bldModalSubtitle', `${building.address} · 建物與進駐關係未查核`);
    const list = $('bldModalList');
    list.replaceChildren(button('← 全部大樓', 'card-btn', openAllBuildingsDirectory));
    const records = companies.filter(c => c.building_id === id).sort((a, b) => b.floor_num - a.floor_num);
    if (!records.length) list.append(element('p', 'empty-state', '尚無示範名錄。'));
    records.forEach(c => {
      const row = element('div', 'building-directory-entry');
      row.append(element('strong', '', `${c.floor} · ${c.name}`), element('p', '', `${c.category} · ${c.status} · 示範資料`));
      list.append(row);
    });
    openModal('modalBuilding');
  }

  function openAllBuildingsDirectory() {
    if (!catalog) return;
    setText('bldModalTitle', `${counties[currentCounty].name} · 全部大樓`);
    setText('bldModalSubtitle', '點選大樓查看示範企業；建物與進駐關係未經實地查核。');
    const list = $('bldModalList');
    list.replaceChildren();
    buildings.filter(b => b.county_id === currentCounty).forEach(b => {
      const node = button('', 'building-directory-entry', () => openBuildingDirectory(b.id));
      node.append(element('strong', '', b.name), element('span', '', `${b.address} · ${b.company_count || 0} 筆示範資料`));
      list.append(node);
    });
    openModal('modalBuilding');
  }

  function download(content, type, filename) {
    const url = URL.createObjectURL(new Blob([content], { type }));
    const link = element('a');
    link.href = url; link.download = filename;
    document.body.append(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    closeMenus();
  }

  function exportCSV() {
    runSearch();
    const records = Core.filterCompanies(companies, filters);
    if (!records.length) { notice('目前沒有可匯出的資料。'); return; }
    const rows = [['資料性質', '資料版本', '資料識別碼', '示範企業名稱', '縣市', '大樓', '模擬樓層', '模擬產業', '模擬資本額', '示範地址', '練習拜訪狀態', '來源與查核狀態']];
    records.forEach(c => rows.push(['示範資料', catalog.dataset_version, c.id, c.name, counties[currentCounty].name,
      c.building_name, c.floor, c.category, c.capital_str, c.address, c.status, '合成示範資料；企業、建物與進駐關係未查核，不可作真實聯絡名單']));
    download(Core.csvDocument(rows), 'text/csv;charset=utf-8', `示範商辦名單_${currentCounty}_${new Date().toISOString().slice(0, 10)}.csv`);
    notice(`已匯出 ${records.length} 筆示範資料，檔案已標示未查核來源。`);
  }

  function backupRecords() {
    if (!catalog) return;
    const backup = { schema_version: 1, kind: Core.BACKUP_KIND, dataset_version: catalog.dataset_version,
      exported_at: new Date().toISOString(), statuses: statusOverrides };
    download(JSON.stringify(backup, null, 2), 'application/json;charset=utf-8', `商辦練習紀錄備份_${new Date().toISOString().slice(0, 10)}.json`);
  }

  async function restoreRecords(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file || !catalog) return;
    try {
      if (file.size > Core.MAX_BACKUP_BYTES) throw new Error('備份超過 1 MB，未匯入。');
      const parsed = JSON.parse(await file.text());
      const restored = Core.validateBackup(parsed, knownIds);
      statusOverrides = Core.mergeStatuses(statusOverrides, restored, knownIds);
      const saved = saveStatuses();
      applyStatuses();
      renderList();
      if (saved) notice(`已合併 ${Object.keys(restored).length} 筆紀錄；同一企業採備份狀態，其他紀錄保留。`);
    } catch (error) {
      notice(error instanceof SyntaxError ? '備份不是有效的 JSON；未匯入任何資料。' : error.message);
    }
  }

  function updateFilterToggleBadge() {
    const collapsed = $('advancedFiltersBox')?.classList.contains('collapsed');
    const count = ['capital', 'building', 'status'].filter(key => filters[key] !== 'ALL').length;
    setText('filterToggleState', `${count ? `${count} 項條件 · ` : ''}${collapsed ? '展開 ▼' : '收合 ▲'}`);
    $('btnFilterToggle')?.setAttribute('aria-expanded', String(!collapsed));
  }

  function toggleAdvancedFilters() {
    $('advancedFiltersBox')?.classList.toggle('collapsed');
    updateFilterToggleBadge();
  }

  function toggleChipsExpand(containerId, buttonId) {
    const container = $(containerId), trigger = $(buttonId);
    if (!container || !trigger) return;
    const expanded = container.classList.toggle('expanded');
    trigger.textContent = expanded ? '收合 ▲' : '展開全部 ▼';
    trigger.setAttribute('aria-expanded', String(expanded));
  }

  function setMobileView(view) {
    if (!['list', 'split', 'map'].includes(view)) return;
    const app = $('appContainer');
    app.classList.remove('mobile-list', 'mobile-split', 'mobile-map');
    app.classList.add(`mobile-${view}`);
    [['btnViewList', 'list'], ['btnViewSplit', 'split'], ['btnViewMap', 'map']].forEach(([id, value]) => {
      $(id)?.classList.toggle('active', view === value);
      $(id)?.setAttribute('aria-pressed', String(view === value));
    });
    if (map) setTimeout(() => map.invalidateSize(), 100);
  }

  function runSearch() {
    clearTimeout(searchTimer);
    filters.query = $('searchInput').value.trim();
    $('btnClearSearch').style.display = filters.query ? 'block' : 'none';
    visibleCount = PAGE_SIZE;
    renderList();
  }

  function wireEvents() {
    $('searchInput').addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(runSearch, 150); });
    $('searchInput').addEventListener('keydown', event => { if (event.key === 'Enter') { event.preventDefault(); runSearch(); } });
    $('btnDoSearch').addEventListener('click', runSearch);
    $('btnClearSearch').addEventListener('click', () => { clearSearch(); runSearch(); $('searchInput').focus(); });
    $('btnResetFilter').addEventListener('click', () => { resetFilters(); renderFilters(); renderList(); });
    document.querySelectorAll('#capitalChips [data-tier]').forEach(node => node.addEventListener('click', () => chooseFilter('capital', node.dataset.tier)));
    document.querySelectorAll('#statusChips [data-status]').forEach(node => node.addEventListener('click', () => chooseFilter('status', node.dataset.status)));
    $('btnExport').addEventListener('click', exportCSV);
    $('btnBackup')?.addEventListener('click', backupRecords);
    $('btnRestore')?.addEventListener('click', () => $('inputRestore')?.click());
    $('inputRestore')?.addEventListener('change', restoreRecords);
    $('btnFitBounds').addEventListener('click', () => {
      if (!map) return;
      const ids = new Set(currentResults.map(c => c.building_id));
      const points = buildings.filter(b => ids.has(b.id)).map(b => [b.lat, b.lng]);
      if (points.length) map.fitBounds(points, { padding: [32, 32], maxZoom: 17 });
    });
    $('btnLocateMe').addEventListener('click', () => {
      if (!map) { notice('地圖尚未啟用，無法顯示位置。'); return; }
      if (!navigator.geolocation) { notice('此瀏覽器不支援定位。'); return; }
      navigator.geolocation.getCurrentPosition(position => {
        const point = [position.coords.latitude, position.coords.longitude];
        if (locationMarker) map.removeLayer(locationMarker);
        locationMarker = L.circleMarker(point, { radius: 8 }).addTo(map);
        locationMarker.bindPopup(element('span', '', '目前位置，僅在此頁顯示')).openPopup();
        map.setView(point, 16);
      }, () => notice('無法取得位置。請確認定位權限；仍可手動操作地圖。'), { timeout: 8000, maximumAge: 60000 });
    });
    document.addEventListener('keydown', event => {
      if (!activeModal) return;
      if (event.key === 'Escape') { event.preventDefault(); closeModal(activeModal.id); return; }
      if (event.key !== 'Tab') return;
      const nodes = Array.from(activeModal.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex="0"]'))
        .filter(node => node.getClientRects().length);
      const first = nodes[0], last = nodes[nodes.length - 1];
      if (!first) { event.preventDefault(); activeModal.focus(); }
      else if (event.shiftKey && (document.activeElement === first || !activeModal.contains(document.activeElement))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !activeModal.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    });
    ['modalBuilding', 'modalCountySelect', 'modalSources'].forEach(id => {
      $(id)?.addEventListener('click', event => { if (event.target === $(id)) closeModal(id); });
    });
  }

  async function boot() {
    notice('正在載入資料目錄…');
    const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 15000);
    try {
      const data = await readJSON('data/catalog.json', controller.signal);
      if (data.schema_version !== 1 || data.data_mode !== 'demo' || !Core.isRecord(data.counties)
        || !Array.isArray(data.buildings) || !Array.isArray(data.categories) || !Core.isRecord(data.legacy_id_map)) throw new Error('資料目錄格式不符');
      catalog = data; counties = data.counties; buildings = data.buildings; categories = data.categories;
      knownIds = new Set(Object.values(data.legacy_id_map));
      notice('');
      loadStatuses();
      try {
        const saved = localStorage.getItem(DEFAULT_COUNTY_KEY);
        if (saved && Object.hasOwn(counties, saved)) currentCounty = saved;
      } catch (_) { storageNotice(); }
      if (!Object.hasOwn(counties, currentCounty)) currentCounty = Object.keys(counties)[0];
      setText('dataVersionText', `示範資料版本 ${String(catalog.dataset_version).slice(0, 12)} · 產生時間 ${catalog.generated_at || '未提供'} · 真實資料尚未查核`);
      initMap();
      await switchCounty(currentCounty);
    } catch (_) {
      notice('無法載入資料目錄。若以本機檔案開啟，請改用網站網址；網路恢復後可重試。', boot);
    } finally { clearTimeout(timeout); }
  }

  Object.assign(window, { switchCounty, updateCompanyStatus, openCountyModal, confirmCountySelection,
    closeCountyModal: () => closeModal('modalCountySelect'), openBuildingDirectory, openAllBuildingsDirectory,
    closeBuildingModal: () => closeModal('modalBuilding'), openSourceModal: () => openModal('modalSources'),
    closeSourceModal: () => closeModal('modalSources'), cycleBasemap, toggleAutoLabels, toggleAdvancedFilters,
    toggleChipsExpand, setMobileView, bookmarkSite: () => {
      notice(/Mac|iPhone|iPad/.test(navigator.platform) ? '按 ⌘ + D 加入書籤；手機可使用分享選單加入主畫面。' : '按 Ctrl + D 加入書籤；手機可使用瀏覽器選單加入主畫面。'); closeMenus();
    } });

  function start() {
    if (!Core) { notice('程式元件未載入，請重新整理頁面。'); return; }
    wireEvents();
    if (window.innerWidth <= 768) setMobileView('list');
    boot();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
