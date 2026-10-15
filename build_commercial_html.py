# -*- coding: utf-8 -*-
"""
全台商辦＆企業地圖 (National Commercial Office & Corporate Map)
HTML 編譯器 · 支援全台所有都會區與縣市、首次進入詢問預設責任縣市、
商辦大樓水牌模式、四類邊界金礦標籤、Base64 我的最愛高清圖示內嵌
"""

import json
import os
import sys
import base64

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATABASE_FILE = 'commercial_database_taiwan.json'

if not os.path.exists(DATABASE_FILE):
    raise FileNotFoundError(f"找不到 {DATABASE_FILE}！請先執行 generate_nationwide_commercial_database.py")

with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
    database_bundle = json.load(f)

print(f"[OK] 成功載入 {DATABASE_FILE}，內含 {len(database_bundle['companies']):,} 家企業、{len(database_bundle['buildings']):,} 棟商辦大樓、涵蓋 {len(database_bundle['counties'])} 個主要都會縣市")

database_json = json.dumps(database_bundle, ensure_ascii=False)

def get_base64_data_uri(filepath, mime='image/png'):
    if os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            b64 = base64.b64encode(f.read()).decode('ascii')
            return f"data:{mime};base64,{b64}"
    return ""

b64_32_uri = get_base64_data_uri('favicon-32x32.png')
b64_16_uri = get_base64_data_uri('favicon-16x16.png')
b64_apple_uri = get_base64_data_uri('apple-touch-icon.png')

html_template = '''<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>全台商辦＆企業地圖 · 辦公室設備與弱電系統規劃</title>
  <meta name="application-name" content="全台商辦＆企業地圖">
  <meta name="apple-mobile-web-app-title" content="全台商辦＆企業地圖">
  <meta name="theme-color" content="#0F172A">

  <!-- Favicon & Bookmarks Icons (我的最愛與分頁專屬高清小圖示 - 內嵌 Data URI 保證離線與書籤即時抓取) -->
  <link rel="shortcut icon" type="image/png" href="__B64_32_URI__">
  <link rel="icon" type="image/png" sizes="32x32" href="__B64_32_URI__">
  <link rel="icon" type="image/png" sizes="16x16" href="__B64_16_URI__">
  <link rel="apple-touch-icon" sizes="180x180" href="__B64_APPLE_URI__">
  <link rel="icon" type="image/x-icon" href="favicon.ico">
  <link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png">
  <link rel="apple-touch-icon" href="apple-touch-icon.png">
  <link rel="icon" type="image/svg+xml" href="favicon.svg">
  <meta name="msapplication-TileColor" content="#0F172A">
  <meta name="msapplication-TileImage" content="icon-192.png">
  
  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=" crossorigin="" />
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&family=Noto+Serif+TC:wght@700;900&display=swap" rel="stylesheet">

  <style>
    :root {
      --bg-primary: #F8FAFC;
      --navy: #0F172A;
      --navy-light: #1E293B;
      --blue: #0284C7;
      --blue-light: #E0F2FE;
      --sky: #38BDF8;
      --gold: #D97706;
      --gold-light: #FEF3C7;
      --border: #E2E8F0;
      --card-bg: #FFFFFF;
      --text-main: #0F172A;
      --text-muted: #64748B;
      --shadow-sm: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
      --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.08), 0 2px 4px -1px rgba(0,0,0,0.04);
      --shadow-lg: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -2px rgba(0,0,0,0.05);
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans TC", Roboto, Helvetica, Arial, sans-serif;
      -webkit-tap-highlight-color: transparent;
    }

    html, body {
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: var(--bg-primary);
      color: var(--text-main);
    }

    body {
      display: flex;
      flex-direction: column;
    }

    /* Top Brand Navigation */
    header {
      background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
      color: #FFFFFF;
      padding: 10px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 2px solid #0284C7;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.25);
      z-index: 1000;
      flex-shrink: 0;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .brand-logo {
      width: 38px;
      height: 38px;
      background: linear-gradient(135deg, #38BDF8 0%, #0284C7 100%);
      border-radius: 9px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 21px;
      box-shadow: 0 2px 10px rgba(56, 189, 248, 0.4);
    }

    .brand-title {
      font-weight: 900;
      font-size: 17px;
      letter-spacing: 0.02em;
      color: #FFFFFF;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .brand-badge {
      background: #D97706;
      color: #FFF;
      font-size: 11px;
      font-weight: 800;
      padding: 2px 7px;
      border-radius: 4px;
      letter-spacing: 0.05em;
    }

    .brand-subtitle {
      font-size: 11.5px;
      color: #94A3B8;
      margin-top: 2px;
    }

    .header-actions {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }

    .btn {
      display: inline-flex;
      align-items: center;
      gap: 5px;
      padding: 6px 12px;
      border-radius: 6px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      border: 1px solid var(--border);
      background: #FFFFFF;
      color: var(--navy);
      transition: all 0.15s ease;
      white-space: nowrap;
    }

    .btn:hover {
      background: #F1F5F9;
      border-color: #94A3B8;
    }

    .btn-county-select {
      background: #1E293B;
      color: #38BDF8;
      border: 1.5px solid #38BDF8;
      font-weight: 800;
    }
    .btn-county-select:hover {
      background: #0284C7;
      color: #FFFFFF;
    }

    .btn-bookmark {
      background: #FEF3C7;
      color: #B45309;
      border: 1.5px solid #FCD34D;
      font-weight: 800;
    }
    .btn-bookmark:hover {
      background: #FDE68A;
      border-color: #F59E0B;
    }

    .btn-primary {
      background: var(--blue);
      color: #FFFFFF;
      border-color: var(--blue);
    }
    .btn-primary:hover {
      background: #0369A1;
      border-color: #0369A1;
    }

    .btn-gold {
      background: #FEF3C7;
      color: #92400E;
      border-color: #FCD34D;
    }
    .btn-gold:hover {
      background: #FDE68A;
    }

    /* District Sub-Navbar */
    .district-nav-bar {
      background: #FFFFFF;
      border-bottom: 1px solid var(--border);
      display: flex;
      overflow-x: auto;
      padding: 6px 14px;
      gap: 8px;
      flex-shrink: 0;
      scrollbar-width: thin;
      box-shadow: 0 1px 3px rgba(0,0,0,0.03);
      z-index: 900;
    }

    .district-btn {
      padding: 6px 13px;
      border-radius: 20px;
      border: 1px solid var(--border);
      background: #F8FAFC;
      color: #334155;
      font-size: 12.5px;
      font-weight: 700;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .district-btn:hover {
      border-color: var(--blue);
      color: var(--blue);
      background: #FFFFFF;
    }

    .district-btn.active {
      background: #0F172A;
      color: #38BDF8;
      border-color: #0F172A;
      box-shadow: 0 2px 6px rgba(15, 23, 42, 0.2);
    }

    /* Main Container Split View */
    .app-container {
      flex: 1;
      display: flex;
      overflow: hidden;
      position: relative;
    }

    /* Sidebar */
    .sidebar {
      width: 480px;
      flex-shrink: 0;
      background: #FFFFFF;
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 800;
      box-shadow: 2px 0 10px rgba(0,0,0,0.03);
    }

    .sidebar-controls {
      padding: 12px 14px;
      border-bottom: 1px solid var(--border);
      background: #F8FAFC;
      display: flex;
      flex-direction: column;
      gap: 10px;
      flex-shrink: 0;
    }

    .search-row {
      display: flex;
      gap: 6px;
    }

    .search-input-wrapper {
      flex: 1;
      position: relative;
      display: flex;
      align-items: center;
    }

    .search-icon-left {
      position: absolute;
      left: 10px;
      font-size: 14px;
      color: #94A3B8;
      pointer-events: none;
    }

    .search-input-wrapper input {
      width: 100%;
      padding: 8px 30px 8px 32px;
      border: 1px solid var(--border);
      border-radius: 6px;
      font-size: 13px;
      outline: none;
      background: #FFFFFF;
      transition: border-color 0.15s;
    }

    .search-input-wrapper input:focus {
      border-color: var(--blue);
      box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.15);
    }

    .search-clear-btn {
      position: absolute;
      right: 8px;
      background: none;
      border: none;
      color: #94A3B8;
      font-size: 14px;
      cursor: pointer;
      display: none;
    }

    /* Chips Groups */
    .chips-group {
      display: flex;
      flex-direction: column;
      gap: 5px;
    }

    .chips-label {
      font-size: 11px;
      font-weight: 800;
      color: #64748B;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .chips-scroll {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      width: 100%;
      max-height: 76px;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 2px 0;
    }

    .chips-scroll.expanded {
      max-height: 220px;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 4px 8px;
      font-size: 11.5px;
      font-weight: 700;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: #FFFFFF;
      color: #334155;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
      line-height: 1.2;
    }

    .chip:hover {
      border-color: var(--blue);
      color: var(--blue);
    }

    .chip.active {
      background: #0284C7;
      color: #FFFFFF;
      border-color: #0284C7;
      box-shadow: 0 1px 4px rgba(2, 132, 199, 0.3);
    }

    /* Border Category Special Styling */
    .chip.border-gold {
      border: 1.5px solid #F59E0B;
      color: #B45309;
      background: #FEF3C7;
      font-weight: 800;
    }
    .chip.border-gold.active {
      background: #D97706;
      color: #FFFFFF;
      border-color: #D97706;
    }

    .chip.border-red {
      border: 1.5px solid #F87171;
      color: #B91C1C;
      background: #FEE2E2;
      font-weight: 800;
    }
    .chip.border-red.active {
      background: #DC2626;
      color: #FFFFFF;
      border-color: #DC2626;
    }

    .chip.border-orange {
      border: 1.5px solid #FB923C;
      color: #C2410C;
      background: #FFEDD5;
      font-weight: 800;
    }
    .chip.border-orange.active {
      background: #EA580C;
      color: #FFFFFF;
      border-color: #EA580C;
    }

    .chip.border-cyan {
      border: 1.5px solid #38BDF8;
      color: #0369A1;
      background: #E0F2FE;
      font-weight: 800;
    }
    .chip.border-cyan.active {
      background: #0284C7;
      color: #FFFFFF;
      border-color: #0284C7;
    }

    /* Capital Tiers Buttons */
    .capital-chips-scroll {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      width: 100%;
    }

    .chip-capital {
      flex: 1 1 auto;
      min-width: 80px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 5px 8px;
      font-size: 11px;
      font-weight: 700;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: #FFFFFF;
      color: #475569;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
      box-sizing: border-box;
    }

    .chip-capital:hover {
      border-color: var(--blue);
      color: var(--blue);
    }

    .chip-capital.active {
      background: var(--blue);
      color: #FFFFFF;
      border-color: var(--blue);
    }

    /* Status Filters */
    .status-chips-scroll {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      width: 100%;
    }

    .chip-status {
      flex: 1 1 calc(33.333% - 6px);
      min-width: 90px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 6px 8px;
      font-size: 11.5px;
      font-weight: 800;
      border-radius: 6px;
      border: 1px solid var(--border);
      background: #FFFFFF;
      color: #475569;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s ease;
      box-sizing: border-box;
    }

    .chip-status:hover {
      border-color: #94A3B8;
      background: #F1F5F9;
    }

    .chip-status.active-all {
      background: #0F172A;
      color: #FFFFFF;
      border-color: #0F172A;
    }
    .chip-status.active-listed {
      background: #F59E0B;
      color: #FFFFFF;
      border-color: #F59E0B;
    }
    .chip-status.active-pending {
      background: #64748B;
      color: #FFFFFF;
      border-color: #64748B;
    }
    .chip-status.active-negotiating {
      background: #0284C7;
      color: #FFFFFF;
      border-color: #0284C7;
    }
    .chip-status.active-done {
      background: #10B981;
      color: #FFFFFF;
      border-color: #10B981;
    }

    /* Company List Content */
    .client-list-header {
      padding: 8px 14px;
      background: #F1F5F9;
      border-bottom: 1px solid var(--border);
      font-size: 12px;
      font-weight: 800;
      color: #475569;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .client-list {
      flex: 1;
      overflow-y: auto;
      padding: 10px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      background: #F8FAFC;
    }

    .company-card {
      background: #FFFFFF;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 14px;
      box-shadow: var(--shadow-sm);
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      flex-direction: column;
      gap: 6px;
      position: relative;
    }

    .company-card:hover {
      border-color: var(--blue);
      box-shadow: var(--shadow-md);
      transform: translateY(-1px);
    }

    .company-card.selected {
      border-color: var(--blue);
      background: #F0F9FF;
      box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.25);
    }

    .card-top-row {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
    }

    .card-name {
      font-size: 15px;
      font-weight: 800;
      color: var(--navy);
      line-height: 1.3;
    }

    .card-badges-row {
      display: flex;
      gap: 4px;
      align-items: center;
      flex-wrap: wrap;
    }

    .badge-listed {
      font-size: 10px;
      font-weight: 800;
      background: #FEF3C7;
      color: #92400E;
      padding: 1px 5px;
      border-radius: 4px;
      border: 1px solid #FDE68A;
      white-space: nowrap;
    }

    .badge-cat {
      font-size: 10.5px;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      white-space: nowrap;
    }

    .badge-capital {
      font-size: 10px;
      font-weight: 800;
      background: #F1F5F9;
      color: #334155;
      padding: 1px 5px;
      border-radius: 4px;
      border: 1px solid #E2E8F0;
    }

    .badge-capital.tier-100m {
      background: #FEF3C7;
      color: #B45309;
      border-color: #FCD34D;
    }

    /* Building & Floor Tag */
    .card-bld-tag {
      font-size: 12px;
      color: #0F172A;
      font-weight: 700;
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .card-floor-pill {
      background: #0F172A;
      color: #38BDF8;
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 900;
      letter-spacing: 0.03em;
    }

    .card-addr {
      font-size: 12px;
      color: #64748B;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .card-low-voltage-box {
      background: #F1F5F9;
      border-left: 3px solid #0284C7;
      padding: 6px 8px;
      border-radius: 0 4px 4px 0;
      font-size: 11.5px;
      color: #334155;
      line-height: 1.4;
      margin-top: 2px;
    }

    .card-actions-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 4px;
      padding-top: 6px;
      border-top: 1px dashed var(--border);
    }

    .status-select-wrapper {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .status-select {
      font-size: 11.5px;
      font-weight: 700;
      padding: 3px 6px;
      border-radius: 4px;
      border: 1px solid var(--border);
      background: #FFF;
      cursor: pointer;
    }

    .card-btn {
      padding: 4px 8px;
      font-size: 11px;
      font-weight: 700;
      border-radius: 4px;
      border: 1px solid var(--border);
      background: #FFFFFF;
      color: #334155;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 3px;
      cursor: pointer;
    }

    .card-btn:hover {
      background: #F1F5F9;
      border-color: #94A3B8;
    }

    .card-btn.btn-call {
      background: #DCFCE7;
      color: #166534;
      border-color: #86EFAC;
    }

    .card-btn.btn-nav {
      background: #0284C7;
      color: #FFF;
      border-color: #0284C7;
    }

    /* Map Area */
    #map {
      flex: 1;
      height: 100%;
      background: #E2E8F0;
    }

    /* Custom Leaflet Markers */
    .bld-marker {
      background: #0F172A;
      border: 2px solid #38BDF8;
      color: #FFFFFF;
      border-radius: 8px;
      padding: 2px 6px;
      font-size: 11px;
      font-weight: 900;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.4);
      display: flex;
      align-items: center;
      gap: 3px;
      cursor: pointer;
      white-space: nowrap;
      transition: transform 0.15s;
    }

    .bld-marker:hover {
      transform: scale(1.1);
      z-index: 9999 !important;
      border-color: #F59E0B;
    }

    .comp-marker {
      width: 26px;
      height: 26px;
      border-radius: 50%;
      color: #FFF;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 900;
      border: 2px solid #FFFFFF;
      box-shadow: 0 3px 8px rgba(0,0,0,0.3);
      cursor: pointer;
    }

    /* Auto Labels on Zoom */
    .leaflet-tooltip.marker-auto-tooltip {
      display: none !important;
      opacity: 0 !important;
      background: #FFFFFF;
      color: #0F172A;
      border: 1.5px solid #CBD5E1;
      border-radius: 6px;
      padding: 3px 8px;
      box-shadow: 0 4px 12px rgba(15, 23, 42, 0.18);
      font-family: inherit;
      pointer-events: auto;
      cursor: pointer;
      white-space: nowrap;
      transition: opacity 0.15s ease;
      z-index: 600;
    }

    .leaflet-tooltip.marker-auto-tooltip::before {
      border-top-color: #FFFFFF;
    }

    #map.show-auto-labels .leaflet-tooltip.marker-auto-tooltip {
      display: block !important;
      opacity: 1 !important;
    }

    /* Map Controls Panel */
    .map-controls-panel {
      position: absolute;
      top: 14px;
      right: 14px;
      z-index: 900;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .map-tool-btn {
      background: #FFFFFF;
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px 12px;
      font-size: 12px;
      font-weight: 800;
      color: var(--navy);
      box-shadow: var(--shadow-md);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s;
    }

    .map-tool-btn:hover {
      background: #F8FAFC;
      border-color: var(--blue);
      transform: translateY(-1px);
    }

    .map-tool-btn.active-state {
      background: #0284C7;
      color: #FFFFFF;
      border-color: #0284C7;
    }

    /* Building Directory Modal (商辦大樓整棟水牌檢視) */
    .bld-modal-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.7);
      backdrop-filter: blur(4px);
      z-index: 2000;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }

    .bld-card {
      background: #FFFFFF;
      width: 100%;
      max-width: 540px;
      max-height: 85vh;
      border-radius: 14px;
      display: flex;
      flex-direction: column;
      box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.35);
      overflow: hidden;
    }

    .bld-header {
      background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
      color: #FFF;
      padding: 15px 18px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }

    .bld-list {
      flex: 1;
      overflow-y: auto;
      padding: 12px 16px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    /* County Modal Styles */
    .county-modal-overlay {
      display: none;
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.75);
      backdrop-filter: blur(6px);
      z-index: 2100;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }

    .county-modal-card {
      background: #FFFFFF;
      width: 100%;
      max-width: 680px;
      border-radius: 16px;
      box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.35);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      animation: modalScaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @keyframes modalScaleIn {
      from { opacity: 0; transform: scale(0.95); }
      to { opacity: 1; transform: scale(1); }
    }

    .county-modal-header {
      background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
      color: #FFF;
      padding: 16px 20px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .county-modal-body {
      padding: 18px 20px;
      max-height: 75vh;
      overflow-y: auto;
    }

    .county-modal-tip {
      background: #F0F9FF;
      border: 1px solid #BAE6FD;
      color: #0369A1;
      padding: 10px 14px;
      border-radius: 8px;
      font-size: 12.5px;
      line-height: 1.5;
      margin-bottom: 14px;
    }

    .county-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: 10px;
      margin-bottom: 16px;
    }

    .county-card-btn {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      padding: 12px 14px;
      background: #F8FAFC;
      border: 2px solid #E2E8F0;
      border-radius: 10px;
      cursor: pointer;
      transition: all 0.15s ease;
      text-align: left;
    }

    .county-card-btn:hover {
      border-color: #38BDF8;
      background: #F0F9FF;
      transform: translateY(-2px);
    }

    .county-card-btn.selected {
      border-color: #0284C7;
      background: #E0F2FE;
      box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.2);
    }

    .county-card-name {
      font-size: 15px;
      font-weight: 800;
      color: #0F172A;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .county-card-desc {
      font-size: 11px;
      color: #64748B;
      margin-top: 4px;
      line-height: 1.3;
    }

    .county-card-badge {
      margin-top: 8px;
      font-size: 10px;
      font-weight: 800;
      background: #E2E8F0;
      color: #334155;
      padding: 2px 6px;
      border-radius: 4px;
    }

    .county-card-btn.selected .county-card-badge {
      background: #0284C7;
      color: #FFFFFF;
    }

    .county-modal-footer {
      padding: 14px 20px;
      background: #F1F5F9;
      border-top: 1px solid #E2E8F0;
      display: flex;
      justify-content: flex-end;
    }

    .btn-confirm-county {
      background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%);
      color: #FFFFFF;
      border: none;
      padding: 10px 22px;
      font-size: 14px;
      font-weight: 800;
      border-radius: 8px;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
      transition: all 0.15s ease;
    }

    .btn-confirm-county:hover {
      background: #0284C7;
      box-shadow: 0 6px 16px rgba(2, 132, 199, 0.4);
    }

    /* Mobile View Toggle Bar */
    .mobile-view-toggle {
      display: none;
      background: #0F172A;
      padding: 8px 14px;
      padding-bottom: calc(8px + env(safe-area-inset-bottom, 0px));
      gap: 8px;
      justify-content: space-around;
      border-top: 1.5px solid #38BDF8;
      flex-shrink: 0;
      z-index: 950;
    }

    .view-btn {
      flex: 1;
      padding: 8px 10px;
      font-size: 12px;
      font-weight: 800;
      border-radius: 8px;
      border: 1px solid #334155;
      background: #1E293B;
      color: #94A3B8;
      cursor: pointer;
    }

    .view-btn.active {
      background: #0284C7;
      color: #FFF;
      border-color: #38BDF8;
    }

    /* RWD */
    @media (max-width: 1024px) {
      .sidebar {
        width: 440px;
      }
    }

    @media (max-width: 768px) {
      .sidebar {
        width: 100%;
        max-width: 100%;
      }

      .mobile-view-toggle {
        display: flex;
      }

      .app-container.mobile-list #map { display: none !important; }
      .app-container.mobile-list .sidebar { display: flex !important; flex: 1; }

      .app-container.mobile-map .sidebar { display: none !important; }
      .app-container.mobile-map #map { display: block !important; flex: 1; }

      .app-container.mobile-split {
        flex-direction: column;
      }
      .app-container.mobile-split #map {
        height: 38%;
        flex: none;
      }
      .app-container.mobile-split .sidebar {
        height: 62%;
        flex: none;
      }
    }
  </style>
</head>
<body>

  <!-- Top Header Navigation -->
  <header>
    <div class="brand">
      <div class="brand-logo">🏢</div>
      <div>
        <div class="brand-title">
          <span>全台商辦＆企業地圖</span>
          <span class="brand-badge" id="headerCountyBadge">桃園市</span>
        </div>
        <div class="brand-subtitle">辦公室設備與弱電系統規劃專用 · 門禁考勤 · 監視監控 · 機房PBX · 視訊會議 · OA</div>
      </div>
    </div>

    <div class="header-actions">
      <!-- County Switcher Button -->
      <button class="btn btn-county-select" id="btnCountySelect" onclick="openCountyModal()" title="切換或設定預設責任縣市">
        <span>📍</span> <span id="currentCountyDisplay">桃園市</span> <span>▼</span>
      </button>

      <!-- Bookmark Helper Button -->
      <button class="btn btn-bookmark" id="btnBookmark" onclick="bookmarkSite()" title="將全台商辦＆企業地圖加到我的最愛 (Ctrl+D)">
        <span>⭐</span><span> 加到最愛</span>
      </button>

      <button class="btn btn-gold" id="btnBuildingMode" onclick="openAllBuildingsDirectory()" title="檢視全區商辦大樓清單與水牌">
        <span>🏢</span><span> 大樓水牌</span>
      </button>

      <button class="btn" id="btnExport" title="匯出當前企業名單與弱電需求為 CSV 檔">
        <span>📤</span><span> 匯出名單</span>
      </button>
    </div>
  </header>

  <!-- District Navigation Bar (動態依所選縣市載入商圈) -->
  <nav class="district-nav-bar" id="districtNavBar">
    <!-- Populated by JavaScript -->
  </nav>

  <!-- Main Container -->
  <div class="app-container mobile-split" id="appContainer">
    
    <!-- Sidebar -->
    <aside class="sidebar">
      
      <div class="sidebar-controls">
        <!-- Search Row -->
        <div class="search-row">
          <div class="search-input-wrapper">
            <span class="search-icon-left">🔍</span>
            <input type="text" id="searchInput" placeholder="搜尋商辦大樓、企業名稱、路段、統編、聯絡人..." autocomplete="off" />
            <button id="btnClearSearch" class="search-clear-btn">✕</button>
          </div>
          <button id="btnDoSearch" class="btn btn-primary" style="padding: 7px 12px;">搜尋</button>
        </div>

        <!-- Filter 1: 產業與高弱電客群快篩 (包含第3組4大邊界金礦標籤) -->
        <div class="chips-group">
          <div class="chips-label">
            <span>🎯 產業客群快篩（點擊標籤秒過濾）</span>
            <span style="display:flex; align-items:center; gap:8px;">
              <span id="catCurrentLabel" style="color:var(--blue);">全部企業</span>
              <button type="button" id="btnExpandCat" onclick="toggleChipsExpand('categoryChips', 'btnExpandCat')" style="background:none; border:none; color:var(--blue); font-size:11px; font-weight:700; cursor:pointer; text-decoration:underline;">展開全部 ▼</button>
            </span>
          </div>
          <div class="chips-scroll" id="categoryChips">
            <!-- Dynamically populated -->
          </div>
        </div>

        <!-- Filter 2: 資本額規模階層快篩 -->
        <div class="chips-group">
          <div class="chips-label">
            <span>💰 資本額規模階層</span>
            <span id="capitalCurrentLabel" style="color:var(--blue);">全部規模</span>
          </div>
          <div class="capital-chips-scroll" id="capitalChips">
            <button class="chip-capital active" data-tier="ALL">全部規模</button>
            <button class="chip-capital" data-tier="TIER_100M">👑 1億以上</button>
            <button class="chip-capital" data-tier="TIER_30M">💎 3,000萬~1億</button>
            <button class="chip-capital" data-tier="TIER_5M">🏢 500萬~3,000萬</button>
            <button class="chip-capital" data-tier="TIER_UNDER_5M">🌱 500萬以下</button>
          </div>
        </div>

        <!-- Filter 3: 商辦大樓與掃樓快篩 -->
        <div class="chips-group">
          <div class="chips-label">
            <span>🏢 指標商辦大樓（點擊進入整棟掃樓名錄）</span>
            <span style="display:flex; align-items:center; gap:8px;">
              <span id="buildingCurrentLabel" style="color:var(--blue);">全部大樓</span>
              <button type="button" id="btnExpandBld" onclick="toggleChipsExpand('buildingChips', 'btnExpandBld')" style="background:none; border:none; color:var(--blue); font-size:11px; font-weight:700; cursor:pointer; text-decoration:underline;">展開全部 ▼</button>
            </span>
          </div>
          <div class="chips-scroll" id="buildingChips">
            <!-- Dynamically populated -->
          </div>
        </div>

        <!-- Filter 4: 外勤拜訪與上市櫃狀態 -->
        <div class="chips-group">
          <div class="chips-label">📋 拜訪進度與等級</div>
          <div class="status-chips-scroll" id="statusChips">
            <button class="chip-status active-all" data-status="ALL">全部 (<span id="countAll">0</span>)</button>
            <button class="chip-status" data-status="LISTED">⭐ 上市櫃 (<span id="countListed">0</span>)</button>
            <button class="chip-status" data-status="尚未拜訪">⏳ 尚未拜訪 (<span id="countPending">0</span>)</button>
            <button class="chip-status" data-status="洽談中">💬 洽談中 (<span id="countNegotiating">0</span>)</button>
            <button class="chip-status" data-status="已拜訪">✅ 已拜訪 (<span id="countDone">0</span>)</button>
          </div>
        </div>

      </div>

      <!-- Result Count Header -->
      <div class="client-list-header">
        <span id="resultCountText">顯示 0 家商辦企業</span>
        <button id="btnResetFilter" style="background:none; border:none; color:var(--blue); font-size:11.5px; font-weight:700; cursor:pointer;">重設篩選</button>
      </div>

      <!-- Companies List -->
      <div class="client-list" id="clientList">
        <!-- Rendered by JavaScript -->
      </div>

    </aside>

    <!-- Map Container -->
    <div id="map"></div>

    <!-- Map Floating Tools -->
    <div class="map-controls-panel">
      <button class="map-tool-btn active-state" id="btnToggleLabels" onclick="toggleAutoLabels()">
        🏷️ 廠名: 自動
      </button>
      <button class="map-tool-btn" id="btnToggleLayer" onclick="cycleBasemap()">
        🗺️ 圖資: 標準街道
      </button>
      <button class="map-tool-btn" id="btnLocateMe">
        🎯 我的位置
      </button>
      <button class="map-tool-btn" id="btnFitBounds">
        🗺️ 全區視野
      </button>
    </div>

  </div>

  <!-- Mobile View Toggle Bar -->
  <div class="mobile-view-toggle" id="mobileViewToggle">
    <button class="view-btn" id="btnViewList" onclick="setMobileView('list')">
      📋 企業名單 (<span id="mobileCount">0</span>)
    </button>
    <button class="view-btn active" id="btnViewSplit" onclick="setMobileView('split')">
      ⚖️ 分割
    </button>
    <button class="view-btn" id="btnViewMap" onclick="setMobileView('map')">
      🗺️ 地圖視野
    </button>
  </div>

  <!-- Building Directory Modal (商辦大樓整棟水牌檢視) -->
  <div class="bld-modal-overlay" id="modalBuilding">
    <div class="bld-card">
      <div class="bld-header">
        <div>
          <div style="font-size: 16px; font-weight: 900;" id="bldModalTitle">商辦大樓水牌名錄</div>
          <div style="font-size: 11.5px; opacity: 0.8; margin-top: 2px;" id="bldModalSubtitle">樓層分佈與弱電規劃名冊</div>
        </div>
        <button onclick="closeBuildingModal()" style="background:none; border:none; color:#FFF; font-size:18px; cursor:pointer;">✕</button>
      </div>
      <div class="bld-list" id="bldModalList">
        <!-- Populated dynamically -->
      </div>
    </div>
  </div>

  <!-- First-time / County Selector Modal -->
  <div class="county-modal-overlay" id="modalCountySelect">
    <div class="county-modal-card">
      <div class="county-modal-header">
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size:26px;">🏢</span>
          <div>
            <div style="font-size:17px; font-weight:900; color:#FFFFFF;">選擇業務責任縣市</div>
            <div style="font-size:12px; color:#94A3B8;">全台商辦＆企業地圖 · 辦公室設備與弱電系統規劃</div>
          </div>
        </div>
        <button onclick="closeCountyModal()" style="background:none; border:none; color:#FFF; font-size:18px; cursor:pointer;">✕</button>
      </div>

      <div class="county-modal-body">
        <div class="county-modal-tip">
          💡 <strong>請選擇您主要巡訪或規劃的業務責任縣市：</strong>
          <br>系統將自動載入該都會區之指標商辦大樓群、樓層水牌與企業名錄。
        </div>

        <div class="county-grid" id="countyGridContainer">
          <!-- Populated dynamically -->
        </div>

        <div style="margin-top:10px; padding: 10px 14px; background: #F8FAFC; border-radius: 8px; border: 1px solid #E2E8F0;">
          <label style="display:flex; align-items:center; gap:8px; cursor:pointer; font-size:13px; font-weight:700; color:#334155;">
            <input type="checkbox" id="chkSetDefaultCounty" checked style="width:16px; height:16px; cursor:pointer;" />
            <span>記住此設定為「預設責任縣市」（下次開啟自動載入，隨時可於頂部更換）</span>
          </label>
        </div>
      </div>

      <div class="county-modal-footer">
        <button class="btn-confirm-county" onclick="confirmCountySelection()">
          確認進入商辦地圖 🚀
        </button>
      </div>
    </div>
  </div>

  <!-- Leaflet JS -->
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>

  <script>
    // --- Injected Database ---
    const DB = __DATABASE_BUNDLE_PLACEHOLDER__;
    const COUNTIES = DB.counties;
    const ALL_BUILDINGS = DB.buildings;
    const ALL_COMPANIES = DB.companies;
    const CATEGORIES = DB.categories;

    // --- State Variables ---
    let currentCounty = 'taoyuan';
    let currentDistrict = 'all';
    let activeCategory = 'ALL';
    let activeCapitalTier = 'ALL';
    let activeBuilding = 'ALL';
    let activeStatus = 'ALL';
    let searchQuery = '';
    let autoLabelsEnabled = true;

    let selectedCountyTemp = 'taoyuan';

    // Status persistence in localStorage
    const STORAGE_KEY_STATUS = 'commercial_status_overrides_v2';
    let statusOverrides = {};
    try {
      const saved = localStorage.getItem(STORAGE_KEY_STATUS);
      if (saved) statusOverrides = JSON.parse(saved);
    } catch(e) {}

    // Apply persistent statuses
    ALL_COMPANIES.forEach(c => {
      if (statusOverrides[c.id]) {
        c.status = statusOverrides[c.id];
      }
    });

    // --- Bookmark Helper (我的最愛功能) ---
    window.bookmarkSite = function() {
      const isMac = /Mac|iPod|iPhone|iPad/.test(navigator.platform);
      const keyCombo = isMac ? '⌘ + D' : 'Ctrl + D';
      
      try {
        const iconLink = document.querySelector("link[rel*='icon']");
        if (iconLink) iconLink.href = iconLink.href;
      } catch(e) {}

      alert('⭐【加入我的最愛提示】\\n\\n請按鍵盤快捷鍵【' + keyCombo + '】將「全台商辦＆企業地圖」存入您的書籤！\\n\\n專屬高質感摩天大樓 Skyline 小圖示已為您準備就緒。');
    };

    // --- County Modal Handling ---
    window.openCountyModal = function() {
      selectedCountyTemp = currentCounty;
      renderCountyGrid();
      document.getElementById('modalCountySelect').style.display = 'flex';
    };

    window.closeCountyModal = function() {
      document.getElementById('modalCountySelect').style.display = 'none';
    };

    let activeCountyRegion = 'ALL';

    function renderCountyGrid() {
      const grid = document.getElementById('countyGridContainer');
      grid.innerHTML = '';

      // Region Filter Tabs Bar
      const regionTabs = document.createElement('div');
      regionTabs.style.cssText = 'grid-column: 1 / -1; display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px;';
      
      const regions = [
        { id: 'ALL', name: '全部 (22)' },
        { id: '北部', name: '🌲 北部 (7)' },
        { id: '中部', name: '🌾 中部 (5)' },
        { id: '南部', name: '🌴 南部 (5)' },
        { id: '東部', name: '🌊 東部 (2)' },
        { id: '離島', name: '🚢 離島 (3)' }
      ];

      regions.forEach(r => {
        const tab = document.createElement('button');
        const isActive = (activeCountyRegion === r.id);
        tab.style.cssText = `padding: 5px 11px; font-size: 11.5px; font-weight: 800; border-radius: 6px; border: 1px solid ${isActive ? '#0F172A' : '#CBD5E1'}; cursor: pointer; transition: all 0.15s; background: ${isActive ? '#0F172A' : '#FFFFFF'}; color: ${isActive ? '#38BDF8' : '#475569'};`;
        tab.textContent = r.name;
        tab.onclick = () => {
          activeCountyRegion = r.id;
          renderCountyGrid();
        };
        regionTabs.appendChild(tab);
      });

      grid.appendChild(regionTabs);

      const countiesToShow = Object.values(COUNTIES).filter(c => {
        if (activeCountyRegion === 'ALL') return true;
        return c.region === activeCountyRegion;
      });

      countiesToShow.forEach(c => {
        const btn = document.createElement('div');
        btn.className = `county-card-btn ${selectedCountyTemp === c.id ? 'selected' : ''}`;
        
        const bldCount = ALL_BUILDINGS.filter(b => b.county_id === c.id).length;
        const compCount = ALL_COMPANIES.filter(comp => comp.county_id === c.id).length;
        const districtNames = (c.districts || []).map(d => d.name).slice(0, 2).join(' · ');

        btn.innerHTML = `
          <div class="county-card-name">
            <span>${c.icon}</span>
            <span>${c.name}</span>
          </div>
          <div class="county-card-desc">${districtNames || '主要商辦特區'}</div>
          <div class="county-card-badge">${bldCount}棟商辦 · ${compCount}家企業</div>
        `;

        btn.onclick = () => {
          selectedCountyTemp = c.id;
          renderCountyGrid();
        };

        grid.appendChild(btn);
      });
    }

    window.confirmCountySelection = function() {
      const chk = document.getElementById('chkSetDefaultCounty');
      if (chk && chk.checked) {
        try {
          localStorage.setItem('default_commercial_county', selectedCountyTemp);
        } catch(e) {}
      }

      switchCounty(selectedCountyTemp);
      closeCountyModal();
    };

    function switchCounty(countyId) {
      if (!COUNTIES[countyId]) return;
      currentCounty = countyId;
      currentDistrict = 'all';

      // Update Header Text & Badge
      const c = COUNTIES[countyId];
      document.getElementById('currentCountyDisplay').textContent = c.name;
      document.getElementById('headerCountyBadge').textContent = c.name;

      renderDistrictNavBar();

      activeCategory = "ALL";
      activeCapitalTier = "ALL";
      activeBuilding = "ALL";
      activeStatus = "ALL";

      setupCategoryChips();
      setupBuildingChips();
      renderList();

      // Fly map to county center
      if (map && c.center) {
        map.flyTo(c.center, c.zoom || 13, { duration: 1.2 });
      }
    }

    // --- Leaflet Map Init ---
    let map = null;
    let markersLayer = L.layerGroup();
    let baseLayers = {};
    let currentBaseLayer = 'osm';

    window.cycleBasemap = function() {
      if (!map || !baseLayers[currentBaseLayer]) return;
      map.removeLayer(baseLayers[currentBaseLayer]);
      const btn = document.getElementById('btnToggleLayer');
      if (currentBaseLayer === 'osm') {
        currentBaseLayer = 'nlsc';
        if (btn) btn.innerHTML = '🇹🇼 圖資: 臺灣通用';
      } else if (currentBaseLayer === 'nlsc') {
        currentBaseLayer = 'sat';
        if (btn) btn.innerHTML = '🛰️ 圖資: 衛星空照';
      } else {
        currentBaseLayer = 'osm';
        if (btn) btn.innerHTML = '🗺️ 圖資: 標準街道';
      }
      baseLayers[currentBaseLayer].addTo(map);
      baseLayers[currentBaseLayer].bringToBack();
    };

    function initMap() {
      const initialCenter = COUNTIES[currentCounty] ? COUNTIES[currentCounty].center : [24.9936, 121.3010];
      const initialZoom = COUNTIES[currentCounty] ? COUNTIES[currentCounty].zoom : 13;

      map = L.map('map', {
        center: initialCenter,
        zoom: initialZoom,
        zoomControl: true
      });

      // High-quality, watermark-free basemaps (OSM / NLSC 國土測繪雲 / Esri Satellite)
      baseLayers = {
        osm: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 19,
          attribution: '&copy; OpenStreetMap contributors'
        }),
        nlsc: L.tileLayer('https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}', {
          maxZoom: 19,
          attribution: '&copy; 內政部國土測繪中心'
        }),
        sat: L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
          maxZoom: 19,
          attribution: '&copy; Esri & Earthstar Geographics'
        })
      };

      // Set OpenStreetMap as clean default
      baseLayers['osm'].addTo(map);

      markersLayer.addTo(map);

      // Auto Labels Handler on Zoom
      function updateLabels() {
        if (!map) return;
        const zoom = map.getZoom();
        const mapEl = document.getElementById('map');
        if (autoLabelsEnabled && zoom >= 16) {
          mapEl.classList.add('show-auto-labels');
        } else {
          mapEl.classList.remove('show-auto-labels');
        }
      }

      map.on('zoomend', updateLabels);
      map.on('zoom', updateLabels);
      map.on('moveend', updateLabels);
    }

    window.toggleAutoLabels = function() {
      autoLabelsEnabled = !autoLabelsEnabled;
      const btn = document.getElementById('btnToggleLabels');
      if (btn) {
        btn.innerHTML = autoLabelsEnabled ? '🏷️ 廠名: 自動' : '🏷️ 廠名: 關閉';
        btn.classList.toggle('active-state', autoLabelsEnabled);
      }
      if (map) {
        document.getElementById('map').classList.toggle('show-auto-labels', autoLabelsEnabled && map.getZoom() >= 16);
      }
    };

    // --- Render District Nav Bar ---
    function renderDistrictNavBar() {
      const nav = document.getElementById('districtNavBar');
      nav.innerHTML = '';

      const c = COUNTIES[currentCounty];
      const countyCompanies = ALL_COMPANIES.filter(comp => comp.county_id === currentCounty);

      const allBtn = document.createElement('button');
      allBtn.className = `district-btn ${currentDistrict === 'all' ? 'active' : ''}`;
      allBtn.innerHTML = `<span>🏙️ 全${c.name}總覽</span> <span style="font-size:11px;opacity:0.8;">(${countyCompanies.length})</span>`;
      allBtn.onclick = () => switchDistrict('all');
      nav.appendChild(allBtn);

      const districts = c.districts || [];
      districts.forEach(d => {
        const btn = document.createElement('button');
        btn.className = `district-btn ${currentDistrict === d.id ? 'active' : ''}`;
        const count = countyCompanies.filter(comp => comp.district_id === d.id).length;
        btn.innerHTML = `<span>${d.icon} ${d.name}</span> <span style="font-size:11px;opacity:0.8;">(${count})</span>`;
        btn.onclick = () => switchDistrict(d.id);
        nav.appendChild(btn);
      });
    }

    function switchDistrict(distId) {
      currentDistrict = distId;
      renderDistrictNavBar();

      activeCategory = "ALL";
      activeCapitalTier = "ALL";
      activeBuilding = "ALL";
      activeStatus = "ALL";

      setupCategoryChips();
      setupBuildingChips();
      renderList();

      if (map) {
        const c = COUNTIES[currentCounty];
        if (distId === 'all') {
          map.flyTo(c.center, c.zoom || 13, { duration: 1 });
        } else {
          const d = (c.districts || []).find(item => item.id === distId);
          if (d && d.center) {
            map.flyTo(d.center, d.zoom || 16, { duration: 1 });
          }
        }
      }
    }

    // --- Setup Category Chips (含第3組高弱電金礦醒目標籤) ---
    function setupCategoryChips() {
      const container = document.getElementById('categoryChips');
      container.innerHTML = '';

      let baseList = ALL_COMPANIES.filter(c => c.county_id === currentCounty);
      if (currentDistrict !== 'all') {
        baseList = baseList.filter(c => c.district_id === currentDistrict);
      }

      // "全部" Chip
      const allBtn = document.createElement('button');
      allBtn.className = `chip ${activeCategory === 'ALL' ? 'active' : ''}`;
      allBtn.textContent = `全部 (${baseList.length})`;
      allBtn.onclick = () => {
        activeCategory = 'ALL';
        updateCategoryChipsSelection();
        renderList();
      };
      container.appendChild(allBtn);

      // Render Each Category with Special Border Badges
      CATEGORIES.forEach(cat => {
        const count = baseList.filter(c => c.category === cat.name).length;
        if (count === 0) return;

        const btn = document.createElement('button');
        let borderClass = '';
        if (cat.border === 'COWORKING') borderClass = 'border-red';
        else if (cat.border === 'CLINIC') borderClass = 'border-cyan';
        else if (cat.border === 'CORP_HQ') borderClass = 'border-orange';
        else if (cat.border === 'LOGISTICS') borderClass = 'border-gold';

        btn.className = `chip ${borderClass} ${activeCategory === cat.name ? 'active' : ''}`;
        
        let prefix = cat.border !== 'NONE' ? '⭐ ' : '';
        btn.innerHTML = `<span>${cat.icon}</span> <span>${prefix}${cat.name} (${count})</span>`;
        btn.onclick = () => {
          activeCategory = (activeCategory === cat.name) ? 'ALL' : cat.name;
          updateCategoryChipsSelection();
          renderList();
        };
        container.appendChild(btn);
      });

      updateCategoryChipsSelection();
    }

    function updateCategoryChipsSelection() {
      const chips = document.querySelectorAll('#categoryChips .chip');
      chips.forEach((c, idx) => {
        if (idx === 0) {
          c.classList.toggle('active', activeCategory === 'ALL');
        } else {
          const text = c.textContent;
          c.classList.toggle('active', activeCategory !== 'ALL' && text.includes(activeCategory));
        }
      });
      document.getElementById('catCurrentLabel').textContent = activeCategory === 'ALL' ? '全部企業' : activeCategory;
    }

    // --- Setup Building Chips (指標商辦大樓整棟名單) ---
    function setupBuildingChips() {
      const container = document.getElementById('buildingChips');
      container.innerHTML = '';

      let baseBlds = ALL_BUILDINGS.filter(b => b.county_id === currentCounty);
      if (currentDistrict !== 'all') {
        baseBlds = baseBlds.filter(b => b.district_id === currentDistrict);
      }

      // "全部大樓" Chip
      const allBtn = document.createElement('button');
      allBtn.className = `chip ${activeBuilding === 'ALL' ? 'active' : ''}`;
      allBtn.textContent = `全部大樓 (${baseBlds.length})`;
      allBtn.onclick = () => {
        activeBuilding = 'ALL';
        updateBuildingChipsSelection();
        renderList();
      };
      container.appendChild(allBtn);

      baseBlds.forEach(b => {
        const compCount = ALL_COMPANIES.filter(c => c.building_id === b.id).length;
        const btn = document.createElement('button');
        btn.className = `chip ${activeBuilding === b.id ? 'active' : ''}`;
        btn.innerHTML = `<span>🏢</span> <span>${b.name} (${compCount})</span>`;
        btn.onclick = () => {
          activeBuilding = (activeBuilding === b.id) ? 'ALL' : b.id;
          updateBuildingChipsSelection();
          renderList();
          if (activeBuilding !== 'ALL' && map) {
            map.flyTo([b.lat, b.lng], 17, { duration: 0.8 });
          }
        };
        container.appendChild(btn);
      });

      updateBuildingChipsSelection();
    }

    function updateBuildingChipsSelection() {
      const chips = document.querySelectorAll('#buildingChips .chip');
      chips.forEach((c, idx) => {
        if (idx === 0) {
          c.classList.toggle('active', activeBuilding === 'ALL');
        } else {
          c.classList.toggle('active', activeBuilding !== 'ALL' && c.innerHTML.includes(activeBuilding));
        }
      });
      const bObj = ALL_BUILDINGS.find(b => b.id === activeBuilding);
      document.getElementById('buildingCurrentLabel').textContent = bObj ? bObj.name : '全部大樓';
    }

    // Toggle Expand/Collapse for Chips Containers
    window.toggleChipsExpand = function(containerId, btnId) {
      const el = document.getElementById(containerId);
      const btn = document.getElementById(btnId);
      if (!el || !btn) return;
      const isExp = el.classList.toggle('expanded');
      btn.textContent = isExp ? '收合 ▲' : '展開全部 ▼';
    };

    // --- Capital Tier Filtering Setup ---
    document.querySelectorAll('#capitalChips .chip-capital').forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll('#capitalChips .chip-capital').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeCapitalTier = btn.dataset.tier;
        document.getElementById('capitalCurrentLabel').textContent = btn.textContent;
        renderList();
      };
    });

    // --- Status Filtering Setup ---
    document.querySelectorAll('#statusChips .chip-status').forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll('#statusChips .chip-status').forEach(b => {
          b.className = 'chip-status';
        });
        const st = btn.dataset.status;
        activeStatus = st;
        if (st === 'ALL') btn.classList.add('active-all');
        else if (st === 'LISTED') btn.classList.add('active-listed');
        else if (st === '尚未拜訪') btn.classList.add('active-pending');
        else if (st === '洽談中') btn.classList.add('active-negotiating');
        else if (st === '已拜訪') btn.classList.add('active-done');
        renderList();
      };
    });

    // --- Search Input Setup ---
    const searchInput = document.getElementById('searchInput');
    const btnClearSearch = document.getElementById('btnClearSearch');

    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.trim().toLowerCase();
      btnClearSearch.style.display = searchQuery ? 'block' : 'none';
      renderList();
    });

    btnClearSearch.addEventListener('click', () => {
      searchInput.value = '';
      searchQuery = '';
      btnClearSearch.style.display = 'none';
      renderList();
    });

    document.getElementById('btnResetFilter').onclick = () => {
      activeCategory = 'ALL';
      activeCapitalTier = 'ALL';
      activeBuilding = 'ALL';
      activeStatus = 'ALL';
      searchQuery = '';
      searchInput.value = '';
      btnClearSearch.style.display = 'none';

      document.querySelectorAll('#capitalChips .chip-capital').forEach((b, idx) => b.classList.toggle('active', idx === 0));
      document.querySelectorAll('#statusChips .chip-status').forEach((b, idx) => {
        b.className = 'chip-status';
        if (idx === 0) b.classList.add('active-all');
      });

      updateCategoryChipsSelection();
      updateBuildingChipsSelection();
      renderList();
    };

    // --- Render List & Map Markers ---
    function getFilteredCompanies() {
      return ALL_COMPANIES.filter(c => {
        if (c.county_id !== currentCounty) return false;
        if (currentDistrict !== 'all' && c.district_id !== currentDistrict) return false;
        if (activeCategory !== 'ALL' && c.category !== activeCategory) return false;
        if (activeCapitalTier !== 'ALL' && c.capital_tier !== activeCapitalTier) return false;
        if (activeBuilding !== 'ALL' && c.building_id !== activeBuilding) return false;
        if (activeStatus === 'LISTED') {
          if (!c.is_listed) return false;
        } else if (activeStatus !== 'ALL') {
          if (c.status !== activeStatus) return false;
        }

        if (searchQuery) {
          const matchName = c.name.toLowerCase().includes(searchQuery);
          const matchBld = c.building_name.toLowerCase().includes(searchQuery);
          const matchAddr = c.address.toLowerCase().includes(searchQuery);
          const matchTax = (c.tax_id || '').includes(searchQuery);
          const matchRep = (c.rep_name || '').toLowerCase().includes(searchQuery);
          if (!matchName && !matchBld && !matchAddr && !matchTax && !matchRep) return false;
        }

        return true;
      });
    }

    function updateCounts(filtered) {
      document.getElementById('resultCountText').textContent = `顯示 ${filtered.length} 家商辦企業`;
      document.getElementById('mobileCount').textContent = filtered.length;

      let countyCompanies = ALL_COMPANIES.filter(c => c.county_id === currentCounty);
      if (currentDistrict !== 'all') {
        countyCompanies = countyCompanies.filter(c => c.district_id === currentDistrict);
      }

      document.getElementById('countAll').textContent = countyCompanies.length;
      document.getElementById('countListed').textContent = countyCompanies.filter(c => c.is_listed).length;
      document.getElementById('countPending').textContent = countyCompanies.filter(c => c.status === '尚未拜訪').length;
      document.getElementById('countNegotiating').textContent = countyCompanies.filter(c => c.status === '洽談中').length;
      document.getElementById('countDone').textContent = countyCompanies.filter(c => c.status === '已拜訪').length;
    }

    function renderList() {
      const filtered = getFilteredCompanies();
      updateCounts(filtered);

      const listContainer = document.getElementById('clientList');
      listContainer.innerHTML = '';

      if (filtered.length === 0) {
        listContainer.innerHTML = `
          <div style="text-align:center; padding:40px 10px; color:#94A3B8;">
            <div style="font-size:32px; margin-bottom:8px;">🏢</div>
            <div style="font-size:14px; font-weight:700;">查無符合條件之商辦企業</div>
            <div style="font-size:12px; margin-top:4px;">請調整上方篩選條件或重設搜尋關鍵字</div>
          </div>
        `;
      } else {
        filtered.forEach(comp => {
          const card = document.createElement('div');
          card.className = 'company-card';
          card.id = `card-${comp.id}`;

          let borderBadge = '';
          if (comp.border_group === 'COWORKING') borderBadge = '<span class="badge-cat" style="background:#FEE2E2;color:#DC2626;">⭐ 共享辦公</span>';
          else if (comp.border_group === 'CLINIC') borderBadge = '<span class="badge-cat" style="background:#E0F2FE;color:#0284C7;">⭐ 診所體系</span>';
          else if (comp.border_group === 'CORP_HQ') borderBadge = '<span class="badge-cat" style="background:#FFEDD5;color:#EA580C;">⭐ 企業總部</span>';
          else if (comp.border_group === 'LOGISTICS') borderBadge = '<span class="badge-cat" style="background:#FEF3C7;color:#D97706;">⭐ 海空運總部</span>';

          card.innerHTML = `
            <div class="card-top-row">
              <div class="card-name">${comp.name}</div>
              <div class="card-badges-row">
                ${comp.is_listed ? '<span class="badge-listed">👑 上市櫃</span>' : ''}
                ${borderBadge}
                <span class="badge-capital ${comp.capital_tier === 'TIER_100M' ? 'tier-100m' : ''}">資本額: ${comp.capital_str}</span>
              </div>
            </div>

            <div class="card-bld-tag">
              <span>🏢</span> <strong>${comp.building_name}</strong>
              <span class="card-floor-pill">${comp.floor}</span>
              <span style="font-size:11px; color:#64748B;">(統編: ${comp.tax_id})</span>
            </div>

            <div class="card-addr">
              <span>📍</span> <span>${comp.address}</span>
            </div>

            <div class="card-low-voltage-box">
              ⚡ <strong>弱電與設備規劃指引：</strong><br>${comp.low_voltage_needs}
            </div>

            <div class="card-actions-row">
              <div class="status-select-wrapper">
                <span style="font-size:11px; color:#64748B; font-weight:700;">狀態:</span>
                <select class="status-select" onchange="updateCompanyStatus('${comp.id}', this.value, event)">
                  <option value="尚未拜訪" ${comp.status === '尚未拜訪' ? 'selected' : ''}>⏳ 尚未拜訪</option>
                  <option value="洽談中" ${comp.status === '洽談中' ? 'selected' : ''}>💬 洽談中</option>
                  <option value="已拜訪" ${comp.status === '已拜訪' ? 'selected' : ''}>✅ 已拜訪</option>
                </select>
              </div>

              <div style="display:flex; gap:5px;">
                <button class="card-btn" onclick="openBuildingDirectory('${comp.building_id}', event)" title="檢視整棟大樓水牌">
                  🏢 水牌
                </button>
                <a class="card-btn btn-call" href="tel:${comp.phone}" onclick="event.stopPropagation()">
                  📞 撥號
                </a>
                <a class="card-btn btn-nav" href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(comp.address)}" target="_blank" onclick="event.stopPropagation()">
                  🧭 導航
                </a>
              </div>
            </div>
          `;

          card.onclick = () => {
            selectCompany(comp);
          };

          listContainer.appendChild(card);
        });
      }

      renderMapMarkers(filtered);
    }

    function selectCompany(comp) {
      document.querySelectorAll('.company-card').forEach(c => c.classList.remove('selected'));
      const targetCard = document.getElementById(`card-${comp.id}`);
      if (targetCard) {
        targetCard.classList.add('selected');
        targetCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }

      if (map) {
        map.flyTo([comp.lat, comp.lng], 18, { duration: 0.8 });
      }
    }

    window.updateCompanyStatus = function(compId, newStatus, evt) {
      if (evt) evt.stopPropagation();
      const comp = ALL_COMPANIES.find(c => c.id === compId);
      if (comp) {
        comp.status = newStatus;
        statusOverrides[compId] = newStatus;
        try {
          localStorage.setItem(STORAGE_KEY_STATUS, JSON.stringify(statusOverrides));
        } catch(e) {}
        updateCounts(getFilteredCompanies());
      }
    };

    // --- Render Map Markers ---
    function renderMapMarkers(filtered) {
      if (!map) return;
      markersLayer.clearLayers();

      // Group filtered companies by building
      const bldMap = {};
      filtered.forEach(c => {
        if (!bldMap[c.building_id]) bldMap[c.building_id] = [];
        bldMap[c.building_id].push(c);
      });

      // Plot Landmark Building Markers
      ALL_BUILDINGS.filter(b => b.county_id === currentCounty).forEach(bld => {
        const compsInBld = bldMap[bld.id] || [];
        if (compsInBld.length === 0 && activeBuilding !== 'ALL') return;

        const countText = compsInBld.length > 0 ? `${compsInBld.length}家` : `${bld.company_count}家`;
        
        const bldIcon = L.divIcon({
          className: 'custom-bld-pin',
          html: `
            <div class="bld-marker" title="${bld.name} (${countText})">
              <span>🏢</span>
              <span>${bld.name}</span>
              <span style="background:#0284C7;color:#FFF;padding:1px 4px;border-radius:4px;font-size:10px;">${countText}</span>
            </div>
          `,
          iconSize: [140, 28],
          iconAnchor: [70, 14]
        });

        const marker = L.marker([bld.lat, bld.lng], { icon: bldIcon });

        // Auto tooltip on zoom
        marker.bindTooltip(`🏢 ${bld.name} · ${bld.floors}F · ${bld.address}`, {
          permanent: true,
          direction: 'top',
          offset: [0, -10],
          className: 'marker-auto-tooltip'
        });

        marker.on('click', () => {
          openBuildingDirectory(bld.id);
        });

        markersLayer.addLayer(marker);
      });
    }

    // --- Building Directory Modal (商辦水牌名錄) ---
    window.openBuildingDirectory = function(bldId, evt) {
      if (evt) evt.stopPropagation();
      const bld = ALL_BUILDINGS.find(b => b.id === bldId);
      if (!bld) return;

      document.getElementById('bldModalTitle').textContent = `🏢 ${bld.name} 水牌名錄`;
      document.getElementById('bldModalSubtitle').textContent = `${bld.address} · 全棟 ${bld.floors} 層 · 總進駐企業名冊`;

      const bldList = document.getElementById('bldModalList');
      bldList.innerHTML = '';

      const comps = ALL_COMPANIES.filter(c => c.building_id === bldId)
                                 .sort((a, b) => b.floor_num - a.floor_num);

      if (comps.length === 0) {
        bldList.innerHTML = '<div style="text-align:center;padding:30px;color:#94A3B8;">本大樓目前尚無登錄之商辦企業</div>';
      } else {
        comps.forEach(c => {
          const item = document.createElement('div');
          item.style.cssText = 'background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 12px; display:flex; justify-content:space-between; align-items:center;';
          
          let borderIcon = '';
          if (c.border_group !== 'NONE') borderIcon = '⭐ ';

          item.innerHTML = `
            <div>
              <div style="display:flex; align-items:center; gap:6px;">
                <span class="card-floor-pill">${c.floor}</span>
                <span style="font-size:14px; font-weight:800; color:#0F172A;">${borderIcon}${c.name}</span>
                ${c.is_listed ? '<span class="badge-listed">上市櫃</span>' : ''}
              </div>
              <div style="font-size:11.5px; color:#64748B; margin-top:3px;">
                ${c.cat_icon} ${c.category} · 資本額: ${c.capital_str} · 統編: ${c.tax_id}
              </div>
              <div style="font-size:11px; color:#0284C7; margin-top:3px;">
                ⚡ ${c.low_voltage_needs}
              </div>
            </div>
            <div>
              <button class="card-btn btn-call" onclick="window.location.href='tel:${c.phone}'">📞 撥號</button>
            </div>
          `;
          bldList.appendChild(item);
        });
      }

      document.getElementById('modalBuilding').style.display = 'flex';
    };

    window.closeBuildingModal = function() {
      document.getElementById('modalBuilding').style.display = 'none';
    };

    window.openAllBuildingsDirectory = function() {
      const bld = ALL_BUILDINGS.find(b => b.county_id === currentCounty);
      if (bld) openBuildingDirectory(bld.id);
    };

    // --- Export CSV (中文表頭) ---
    document.getElementById('btnExport').onclick = () => {
      const filtered = getFilteredCompanies();
      if (filtered.length === 0) {
        alert('當前篩選條件下無任何企業資料可供匯出！');
        return;
      }

      const headers = ["公司名稱", "所屬縣市", "商辦大樓", "所在樓層", "統一編號", "產業類別", "資本額規模", "上市櫃", "代表聯絡人", "電話", "完整地址", "外勤拜訪狀態", "弱電與設備規劃指引"];
      const rows = filtered.map(c => [
        `"${c.name}"`,
        `"${COUNTIES[c.county_id] ? COUNTIES[c.county_id].name : c.county_id}"`,
        `"${c.building_name}"`,
        `"${c.floor}"`,
        `"\t${c.tax_id}"`,
        `"${c.category}"`,
        `"${c.capital_str}"`,
        `"${c.is_listed ? '是' : '否'}"`,
        `"${c.rep_name}"`,
        `"\t${c.phone}"`,
        `"${c.address}"`,
        `"${c.status}"`,
        `"${c.low_voltage_needs.replace(/"/g, '""')}"`
      ]);

      const csvContent = "\uFEFF" + [headers.join(','), ...rows.map(r => r.join(','))].join('\\n');
      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `全台商辦企業名冊_${COUNTIES[currentCounty].name}_${new Date().toISOString().slice(0,10)}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };

    // --- Floating Controls Handlers ---
    document.getElementById('btnFitBounds').onclick = () => {
      if (map && COUNTIES[currentCounty]) {
        map.flyTo(COUNTIES[currentCounty].center, COUNTIES[currentCounty].zoom || 13, { duration: 1 });
      }
    };

    document.getElementById('btnLocateMe').onclick = () => {
      if (!navigator.geolocation) {
        alert('您的瀏覽器不支援定位功能。');
        return;
      }
      navigator.geolocation.getCurrentPosition(
        pos => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          if (map) {
            map.flyTo([lat, lng], 17, { duration: 1 });
            L.circleMarker([lat, lng], {
              radius: 9,
              fillColor: '#0284C7',
              color: '#FFFFFF',
              weight: 3,
              opacity: 1,
              fillOpacity: 0.9
            }).addTo(map).bindPopup('📍 您目前的外勤位置').openPopup();
          }
        },
        err => {
          alert('無法取得您的位置：' + err.message);
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    };

    // --- Mobile Layout Toggle ---
    window.setMobileView = function(view) {
      const app = document.getElementById('appContainer');
      app.classList.remove('mobile-list', 'mobile-split', 'mobile-map');
      app.classList.add(`mobile-${view}`);

      document.getElementById('btnViewList').classList.toggle('active', view === 'list');
      document.getElementById('btnViewSplit').classList.toggle('active', view === 'split');
      document.getElementById('btnViewMap').classList.toggle('active', view === 'map');

      if (map) {
        setTimeout(() => map.invalidateSize(), 200);
      }
    };

    // --- Initial Boot Sequence (首次進入詢問預設縣市) ---
    window.addEventListener('DOMContentLoaded', () => {
      initMap();

      // Check for default county setting
      let defaultCounty = null;
      try {
        defaultCounty = localStorage.getItem('default_commercial_county');
      } catch(e) {}

      if (defaultCounty && COUNTIES[defaultCounty]) {
        currentCounty = defaultCounty;
        switchCounty(defaultCounty);
      } else {
        // First-time Entry: show onboarding modal immediately
        currentCounty = 'taoyuan';
        switchCounty('taoyuan');
        openCountyModal();
      }

      // Responsive init
      if (window.innerWidth <= 768) {
        setMobileView("split");
      }
    });
  </script>
</body>
</html>
'''

# Replace Data URIs and Database bundle
full_html = html_template.replace('__DATABASE_BUNDLE_PLACEHOLDER__', database_json)
full_html = full_html.replace('__B64_32_URI__', b64_32_uri)
full_html = full_html.replace('__B64_16_URI__', b64_16_uri)
full_html = full_html.replace('__B64_APPLE_URI__', b64_apple_uri)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(full_html)

print(f"[OK] 成功編譯生成全台商辦＆企業地圖 index.html！檔案大小：{len(full_html.encode('utf-8')):,} bytes")
