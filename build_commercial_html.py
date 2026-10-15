# -*- coding: utf-8 -*-
"""
全國商辦與企業地圖 · 桃園旗艦示範區 (Commercial Office & Corporate Map)
HTML 編譯器
"""

import json
import os
import sys

# UTF-8 safety
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

DATABASE_FILE = 'commercial_database_taoyuan.json'

if not os.path.exists(DATABASE_FILE):
    raise FileNotFoundError(f"找不到 {DATABASE_FILE}！請先執行 generate_taoyuan_commercial_database.py")

with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
    database_bundle = json.load(f)

print(f"[OK] 成功載入 {DATABASE_FILE}，內含 {len(database_bundle['companies']):,} 家企業、{len(database_bundle['buildings']):,} 棟商辦大樓")

database_json = json.dumps(database_bundle, ensure_ascii=False)

html_template = '''<!DOCTYPE html>
<html lang="zh-TW">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  <title>全台商辦＆企業地圖 · 桃園示範區</title>
  <meta name="application-name" content="全台商辦＆企業地圖">
  <meta name="apple-mobile-web-app-title" content="全台商辦＆企業地圖">
  <meta name="theme-color" content="#0F172A">

  <!-- Favicon & Bookmarks Icons -->
  <link rel="icon" type="image/svg+xml" href="favicon.svg">
  <link rel="icon" type="image/png" sizes="32x32" href="favicon-32x32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="favicon-16x16.png">
  <link rel="apple-touch-icon" sizes="180x180" href="apple-touch-icon.png">
  <link rel="shortcut icon" href="favicon.ico">
  
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
      --green: #16A34A;
      --green-light: #DCFCE7;
      --purple: #7C3AED;
      --purple-light: #EDE9FE;
      --border: #E2E8F0;
      --text-main: #0F172A;
      --text-muted: #64748B;
      --card-bg: #FFFFFF;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
    }

    body {
      font-family: 'Noto Sans TC', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background-color: var(--bg-primary);
      color: var(--text-main);
      display: flex;
      flex-direction: column;
      height: 100vh;
      height: 100dvh;
      overflow: hidden;
    }

    /* Top Navigation Header */
    header {
      background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
      color: #FFFFFF;
      padding: 9px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #38BDF8;
      box-shadow: 0 4px 16px rgba(15, 23, 42, 0.25);
      z-index: 1000;
      flex-shrink: 0;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .brand-logo {
      width: 36px;
      height: 36px;
      background: linear-gradient(135deg, #38BDF8 0%, #0284C7 100%);
      border-radius: 9px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
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
      font-size: 10px;
      font-weight: 800;
      padding: 2px 6px;
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
    }

    .btn {
      background: #334155;
      color: #FFFFFF;
      border: 1px solid #475569;
      padding: 7px 12px;
      border-radius: 7px;
      font-size: 12.5px;
      font-weight: 700;
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      gap: 5px;
      transition: all 0.15s ease;
      font-family: inherit;
    }

    .btn:hover {
      background: #475569;
      border-color: #64748B;
    }

    .btn-primary {
      background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%);
      border-color: #38BDF8;
      color: #FFFFFF;
      box-shadow: 0 2px 8px rgba(2, 132, 199, 0.35);
    }

    .btn-primary:hover {
      background: linear-gradient(135deg, #0369A1 0%, #075985 100%);
    }

    .btn-gold {
      background: linear-gradient(135deg, #D97706 0%, #B45309 100%);
      border-color: #FBBF24;
      color: #FFFFFF;
    }

    /* District Nav Bar (桃園 5 大精華商務區) */
    .district-nav-bar {
      background: #FFFFFF;
      border-bottom: 1.5px solid var(--border);
      padding: 6px 14px;
      display: flex;
      gap: 8px;
      overflow-x: auto;
      scrollbar-width: none;
      flex-shrink: 0;
      z-index: 900;
    }

    .district-nav-bar::-webkit-scrollbar {
      display: none;
    }

    .district-btn {
      background: #F1F5F9;
      border: 1.5px solid #E2E8F0;
      color: #334155;
      padding: 6px 13px;
      border-radius: 20px;
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
      background: #E2E8F0;
      color: var(--navy);
    }

    .district-btn.active {
      background: #0F172A;
      color: #FFFFFF;
      border-color: #0F172A;
      box-shadow: 0 3px 10px rgba(15, 23, 42, 0.25);
    }

    /* Main Container */
    .app-container {
      display: flex;
      flex: 1;
      min-height: 0;
      position: relative;
      overflow: hidden;
    }

    /* Sidebar (Filtering & Companies) */
    .sidebar {
      width: 480px;
      max-width: 45vw;
      background: var(--bg-primary);
      border-right: 1.5px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 500;
      flex-shrink: 0;
      box-shadow: 3px 0 16px rgba(15, 23, 42, 0.05);
      height: 100%;
    }

    .sidebar-controls {
      padding: 12px 16px;
      background: #FFFFFF;
      border-bottom: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 10px;
      flex-shrink: 0;
    }

    /* Search Box */
    .search-row {
      display: flex;
      gap: 6px;
      align-items: center;
    }

    .search-input-wrapper {
      position: relative;
      flex: 1;
      display: flex;
      align-items: center;
    }

    .search-icon-left {
      position: absolute;
      left: 10px;
      font-size: 13px;
      color: var(--text-muted);
      pointer-events: none;
    }

    .search-input-wrapper input {
      width: 100%;
      padding: 8px 32px 8px 32px;
      font-size: 13px;
      border: 1.5px solid var(--border);
      border-radius: 7px;
      outline: none;
      font-family: inherit;
      background: #F8FAFC;
      transition: all 0.15s;
    }

    .search-input-wrapper input:focus {
      border-color: var(--blue);
      background: #FFFFFF;
      box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.12);
    }

    .search-clear-btn {
      position: absolute;
      right: 8px;
      background: none;
      border: none;
      color: #94A3B8;
      cursor: pointer;
      font-size: 14px;
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
      color: var(--text-muted);
      letter-spacing: 0.04em;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .chips-scroll {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      max-height: 72px;
      overflow-y: auto;
      overflow-x: hidden;
      padding: 2px 1px;
      scrollbar-width: thin;
      transition: max-height 0.2s ease;
    }

    .chips-scroll::-webkit-scrollbar {
      width: 4px;
    }
    .chips-scroll::-webkit-scrollbar-thumb {
      background: #CBD5E1;
      border-radius: 2px;
    }

    .chips-scroll.expanded {
      max-height: 280px;
    }

    .chip {
      padding: 4px 9px;
      border-radius: 6px;
      font-size: 11.5px;
      font-weight: 600;
      background: #F1F5F9;
      color: #475569;
      border: 1px solid #E2E8F0;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.15s;
      flex-shrink: 0;
      display: inline-flex;
      align-items: center;
      gap: 4px;
    }

    .chip:hover {
      background: #E2E8F0;
      color: var(--navy);
    }

    .chip.active {
      background: #0F172A;
      color: #FFFFFF;
      border-color: #0F172A;
      font-weight: 800;
    }

    /* Specialized Border Group Badges (第3組高弱電金礦標籤) */
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
      flex: 1 1 auto;
      min-width: 86px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      padding: 5px 8px;
      font-size: 11.5px;
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

    .chip-status:hover {
      border-color: var(--navy);
      color: var(--navy);
    }

    .chip-status.active-all { background: var(--navy); color: #FFF; border-color: var(--navy); }
    .chip-status.active-listed { background: #D97706; color: #FFF; border-color: #D97706; }
    .chip-status.active-pending { background: #0284C7; color: #FFF; border-color: #0284C7; }
    .chip-status.active-negotiating { background: #7C3AED; color: #FFF; border-color: #7C3AED; }
    .chip-status.active-done { background: #16A34A; color: #FFF; border-color: #16A34A; }

    /* Client List Area */
    .client-list-header {
      padding: 8px 16px;
      background: #F1F5F9;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11.5px;
      color: var(--text-muted);
      font-weight: 700;
      flex-shrink: 0;
    }

    .client-list {
      flex: 1;
      overflow-y: auto;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 10px;
      scrollbar-width: thin;
      -webkit-overflow-scrolling: touch;
    }

    /* Client Card */
    .client-card {
      background: var(--card-bg);
      border: 1.5px solid var(--border);
      border-radius: 9px;
      padding: 12px 14px;
      box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
      display: flex;
      flex-direction: column;
      gap: 7px;
      cursor: pointer;
      transition: all 0.15s ease;
      position: relative;
    }

    .client-card:hover {
      border-color: var(--blue);
      box-shadow: 0 4px 14px rgba(2, 132, 199, 0.12);
      transform: translateY(-1px);
    }

    .client-card.active-selected {
      border-color: #0284C7;
      background: #F0F9FF;
      box-shadow: 0 0 0 2px rgba(2, 132, 199, 0.25);
    }

    .card-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
    }

    .card-title {
      font-weight: 900;
      font-size: 14.5px;
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

    .card-address {
      font-size: 11.5px;
      color: #64748B;
      line-height: 1.35;
    }

    .card-contact {
      font-size: 11.5px;
      color: #334155;
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    /* Weak point note box (弱電需求痛點) */
    .card-weakpoint {
      background: #F0FDF4;
      border: 1px dashed #86EFAC;
      border-radius: 6px;
      padding: 6px 8px;
      font-size: 11px;
      color: #166534;
      line-height: 1.4;
    }

    /* Visit box summary */
    .card-visit-box {
      background: #F8FAFC;
      border: 1px solid #E2E8F0;
      border-radius: 6px;
      padding: 6px 8px;
      font-size: 11px;
    }

    .card-actions {
      display: flex;
      gap: 5px;
      margin-top: 2px;
      padding-top: 6px;
      border-top: 1px solid #F1F5F9;
    }

    .card-btn {
      flex: 1;
      padding: 5px 8px;
      font-size: 11px;
      font-weight: 700;
      border-radius: 5px;
      border: 1px solid var(--border);
      background: #FFFFFF;
      color: var(--navy);
      cursor: pointer;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 3px;
      text-decoration: none;
      transition: all 0.15s;
    }

    .card-btn:hover {
      background: #F1F5F9;
    }

    .card-btn.btn-visited {
      background: #DCFCE7;
      color: #16A34A;
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

    #map.show-auto-labels .leaflet-tooltip.marker-auto-tooltip {
      display: flex !important;
      flex-direction: column;
      opacity: 1 !important;
    }

    .marker-auto-tooltip .lbl-title {
      font-weight: 800;
      font-size: 11.5px;
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .marker-auto-tooltip .lbl-detail {
      font-size: 10px;
      color: #64748B;
      margin-top: 1px;
    }

    /* Map Tools Panel */
    .map-controls-panel {
      position: absolute;
      top: 16px;
      right: 16px;
      z-index: 800;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .map-tool-btn {
      background: #FFFFFF;
      border: 1.5px solid var(--border);
      color: var(--navy);
      padding: 8px 12px;
      border-radius: 8px;
      font-weight: 700;
      font-size: 12px;
      cursor: pointer;
      box-shadow: 0 4px 14px rgba(15, 23, 42, 0.1);
      display: flex;
      align-items: center;
      gap: 5px;
    }

    .map-tool-btn.active-state {
      background: #E0F2FE;
      border-color: #0284C7;
      color: #0284C7;
      font-weight: 800;
    }

    /* Building Directory Sheet (大樓水牌模式抽屜) */
    .bld-modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.6);
      z-index: 2000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }

    .bld-modal-overlay.open {
      display: flex;
    }

    .bld-card {
      background: #FFFFFF;
      width: 100%;
      max-width: 520px;
      max-height: 85vh;
      border-radius: 12px;
      display: flex;
      flex-direction: column;
      box-shadow: 0 20px 40px rgba(15, 23, 42, 0.3);
      overflow: hidden;
    }

    .bld-header {
      background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
      color: #FFF;
      padding: 14px 18px;
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
          <span class="brand-badge">桃園示範區</span>
        </div>
        <div class="brand-subtitle">辦公室設備與弱電系統規劃專用 · 門禁考勤 · 監視監控 · 機房PBX · 視訊會議 · OA</div>
      </div>
    </div>

    <div class="header-actions">
      <button class="btn btn-gold" id="btnBuildingMode" onclick="openAllBuildingsDirectory()" title="檢視全區商辦大樓清單與水牌">
        <span>🏢</span><span> 大樓水牌</span>
      </button>
      <button class="btn" id="btnExport" title="匯出當前企業名單與弱電需求為 CSV 檔">
        <span>📤</span><span> 匯出名單</span>
      </button>
    </div>
  </header>

  <!-- District Navigation Bar (桃園 5 大精華商務區) -->
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
            <input type="text" id="searchInput" placeholder="搜尋商辦大樓名稱、企業名稱、路段、統編、聯絡人..." autocomplete="off" />
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
          <div style="font-size:11px; font-weight:800; color:#38BDF8; text-transform:uppercase;">商辦大樓水牌名錄</div>
          <h3 id="bldModalTitle" style="margin:2px 0 0 0; font-size:17px; font-weight:900;">大樓名稱</h3>
          <div id="bldModalAddress" style="font-size:11.5px; color:#94A3B8; margin-top:2px;"></div>
        </div>
        <button type="button" class="btn" onclick="closeBuildingModal()" style="padding:4px 8px; font-size:14px;">✕</button>
      </div>
      <div style="padding:8px 16px; background:#F8FAFC; border-bottom:1px solid var(--border); font-size:11.5px; color:var(--text-muted); display:flex; justify-content:space-between; align-items:center;">
        <span>依樓層由高到低排列（掃樓動線）</span>
        <span id="bldModalCount" style="font-weight:800; color:var(--blue);">共 0 家企業</span>
      </div>
      <div class="bld-list" id="bldModalList">
        <!-- Rendered by JavaScript -->
      </div>
    </div>
  </div>

  <!-- Leaflet JS -->
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" integrity="sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=" crossorigin=""></script>

  <script>
    const DATABASE = __DATABASE_BUNDLE_PLACEHOLDER__;
    const DISTRICTS = DATABASE.districts;
    const CATEGORIES = DATABASE.categories;
    const BUILDINGS = DATABASE.buildings;
    const ALL_COMPANIES = DATABASE.companies;

    let currentDistrict = "all";
    let activeCategory = "ALL";
    let activeCapitalTier = "ALL";
    let activeBuilding = "ALL";
    let activeStatus = "ALL";
    let searchQuery = "";
    let map = null;
    let markers = {};
    let bldMarkers = {};
    let currentFiltered = [];
    let displayedCount = 60;
    let searchDebounceTimer = null;
    let autoLabelsEnabled = true;

    // --- Mobile View Switcher ---
    window.setMobileView = function(mode) {
      const appContainer = document.getElementById('appContainer');
      appContainer.classList.remove('mobile-list', 'mobile-map', 'mobile-split');
      appContainer.classList.add(`mobile-${mode}`);
      document.querySelectorAll('#mobileViewToggle .view-btn').forEach(btn => btn.classList.remove('active'));
      if (mode === 'list') document.getElementById('btnViewList').classList.add('active');
      else if (mode === 'split') document.getElementById('btnViewSplit').classList.add('active');
      else if (mode === 'map') document.getElementById('btnViewMap').classList.add('active');
      if (map) setTimeout(() => map.invalidateSize(), 200);
    };

    // --- Chips Expand Toggle ---
    window.toggleChipsExpand = function(containerId, btnId) {
      const container = document.getElementById(containerId);
      const btn = document.getElementById(btnId);
      if (!container) return;
      const isExp = container.classList.toggle('expanded');
      if (btn) btn.innerText = isExp ? '收合 ▲' : '展開全部 ▼';
    };

    // --- Initialize Leaflet Map ---
    function initMap() {
      map = L.map('map', {
        zoomControl: true,
        attributionControl: false
      }).setView([25.0050, 121.2850], 13);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
      }).addTo(map);

      L.control.attribution({ position: 'bottomright' })
        .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>')
        .addTo(map);

      function updateLabels() {
        if (!map) return;
        const currentZoom = map.getZoom();
        const mapEl = document.getElementById('map');
        if (!mapEl) return;
        if (autoLabelsEnabled) {
          mapEl.classList.toggle('show-auto-labels', currentZoom >= 16);
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

      const allBtn = document.createElement('button');
      allBtn.className = `district-btn ${currentDistrict === 'all' ? 'active' : ''}`;
      allBtn.innerHTML = `<span>🏙️ 全桃園總覽</span> <span style="font-size:11px;opacity:0.8;">(${ALL_COMPANIES.length})</span>`;
      allBtn.onclick = () => switchDistrict('all');
      nav.appendChild(allBtn);

      Object.values(DISTRICTS).forEach(d => {
        const btn = document.createElement('button');
        btn.className = `district-btn ${currentDistrict === d.id ? 'active' : ''}`;
        const count = ALL_COMPANIES.filter(c => c.district_id === d.id).length;
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
        if (distId === 'all') {
          map.flyTo([25.0150, 121.2800], 12, { duration: 1 });
        } else {
          const d = DISTRICTS[distId];
          if (d && d.center) {
            map.flyTo(d.center, d.zoom || 15, { duration: 1 });
          }
        }
      }
    }

    // --- Setup Category Chips (含第3組高弱電金礦醒目標籤) ---
    function setupCategoryChips() {
      const container = document.getElementById('categoryChips');
      container.innerHTML = '';

      const baseList = currentDistrict === 'all' ? ALL_COMPANIES : ALL_COMPANIES.filter(c => c.district_id === currentDistrict);

      const allBtn = document.createElement('button');
      allBtn.className = `chip ${activeCategory === 'ALL' ? 'active' : ''}`;
      allBtn.innerText = `全部企業 (${baseList.length})`;
      allBtn.onclick = () => {
        activeCategory = 'ALL';
        document.querySelectorAll('#categoryChips .chip').forEach(b => b.classList.remove('active'));
        allBtn.classList.add('active');
        document.getElementById('catCurrentLabel').innerText = '全部企業';
        renderList();
      };
      container.appendChild(allBtn);

      CATEGORIES.forEach(cat => {
        const count = baseList.filter(c => c.category_id === cat.id).length;
        if (count === 0) return;

        const btn = document.createElement('button');
        let borderClass = '';
        if (cat.id === 'COWORKING') borderClass = 'border-gold';
        else if (cat.id === 'CLINIC') borderClass = 'border-red';
        else if (cat.id === 'FNB_HQ') borderClass = 'border-orange';
        else if (cat.id === 'LOGISTICS_HQ') borderClass = 'border-cyan';

        btn.className = `chip ${borderClass} ${activeCategory === cat.id ? 'active' : ''}`;
        btn.innerText = `${cat.icon} ${cat.name} (${count})`;
        btn.onclick = () => {
          activeCategory = cat.id;
          document.querySelectorAll('#categoryChips .chip').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          document.getElementById('catCurrentLabel').innerText = cat.name;
          renderList();
        };
        container.appendChild(btn);
      });
    }

    // --- Setup Building Chips ---
    function setupBuildingChips() {
      const container = document.getElementById('buildingChips');
      container.innerHTML = '';

      const bldList = currentDistrict === 'all' ? BUILDINGS : BUILDINGS.filter(b => b.district_id === currentDistrict);

      const allBtn = document.createElement('button');
      allBtn.className = `chip ${activeBuilding === 'ALL' ? 'active' : ''}`;
      allBtn.innerText = `全部大樓 (${bldList.length}棟)`;
      allBtn.onclick = () => {
        activeBuilding = 'ALL';
        document.querySelectorAll('#buildingChips .chip').forEach(b => b.classList.remove('active'));
        allBtn.classList.add('active');
        document.getElementById('buildingCurrentLabel').innerText = '全部大樓';
        renderList();
      };
      container.appendChild(allBtn);

      bldList.forEach(b => {
        const btn = document.createElement('button');
        btn.className = `chip ${activeBuilding === b.name ? 'active' : ''}`;
        btn.innerText = `🏢 ${b.name} (${b.company_count}家)`;
        btn.onclick = () => {
          activeBuilding = b.name;
          document.querySelectorAll('#buildingChips .chip').forEach(c => c.classList.remove('active'));
          btn.classList.add('active');
          document.getElementById('buildingCurrentLabel').innerText = b.name;
          renderList();
          if (map) map.flyTo([b.lat, b.lng], 17, { duration: 1 });
        };
        container.appendChild(btn);
      });
    }

    // --- Execute Filters ---
    function executeFilter() {
      const q = (searchQuery || "").trim().toLowerCase();
      const keywords = q ? q.split(/\\s+/).filter(Boolean) : [];

      currentFiltered = ALL_COMPANIES.filter(c => {
        // District filter
        if (currentDistrict !== 'all' && c.district_id !== currentDistrict) return false;

        // Category filter
        if (activeCategory !== 'ALL' && c.category_id !== activeCategory) return false;

        // Capital tier filter
        if (activeCapitalTier !== 'ALL' && c.capital_tier !== activeCapitalTier) return false;

        // Building filter
        if (activeBuilding !== 'ALL' && c.building_name !== activeBuilding) return false;

        // Status filter
        if (activeStatus === 'LISTED') {
          if (c.is_listed !== '是') return false;
        } else if (activeStatus !== 'ALL' && c.status !== activeStatus) {
          return false;
        }

        // Keywords match
        if (keywords.length > 0) {
          const targetStr = `${c.name} ${c.building_name} ${c.road} ${c.address} ${c.contact} ${c.phone} ${c.notes} ${c.category_name}`.toLowerCase();
          const matchAll = keywords.every(kw => targetStr.includes(kw));
          if (!matchAll) return false;
        }

        return true;
      });
    }

    // --- Render List & Markers ---
    function renderList() {
      executeFilter();

      const countText = `顯示 ${currentFiltered.length.toLocaleString()} 家商辦企業（全區共 ${ALL_COMPANIES.length.toLocaleString()} 家）`;
      document.getElementById('resultCountText').innerText = countText;
      document.getElementById('mobileCount').innerText = currentFiltered.length;

      updateStatusCounts();
      renderCardsSlice(true);
      updateMarkers(currentFiltered);
    }

    function updateStatusCounts() {
      const base = currentDistrict === 'all' ? ALL_COMPANIES : ALL_COMPANIES.filter(c => c.district_id === currentDistrict);
      document.getElementById('countAll').innerText = base.length;
      document.getElementById('countListed').innerText = base.filter(c => c.is_listed === '是').length;
      document.getElementById('countPending').innerText = base.filter(c => c.status === '尚未拜訪').length;
      document.getElementById('countNegotiating').innerText = base.filter(c => c.status === '洽談中').length;
      document.getElementById('countDone').innerText = base.filter(c => c.status === '已拜訪').length;
    }

    function renderCardsSlice(isReset) {
      const container = document.getElementById('clientList');
      if (isReset) {
        container.innerHTML = "";
        displayedCount = 60;
      }

      if (currentFiltered.length === 0) {
        container.innerHTML = `
          <div style="text-align:center; padding:40px 16px; color:#64748B;">
            <div style="font-size:36px; margin-bottom:8px;">🔍</div>
            <div style="font-weight:800; font-size:15px; color:#0F172A;">查無符合條件的商辦企業</div>
            <div style="font-size:12px; margin-top:4px;">請嘗試更換產業類別或點擊右上角「重設篩選」</div>
          </div>
        `;
        return;
      }

      const startIndex = isReset ? 0 : container.querySelectorAll('.client-card').length;
      const endIndex = Math.min(displayedCount, currentFiltered.length);

      for (let i = startIndex; i < endIndex; i++) {
        const c = currentFiltered[i];
        const card = document.createElement('div');
        card.className = "client-card";
        card.id = `card-${c.id}`;

        const isDone = c.status === '已拜訪';
        const isNeg = c.status === '洽談中';

        card.innerHTML = `
          <div class="card-top">
            <div class="card-title">${c.name}</div>
            <div class="card-badges-row">
              ${c.is_listed === '是' ? '<span class="badge-listed">★ 上市櫃</span>' : ''}
              <span class="badge-capital ${c.capital_tier === 'TIER_100M' ? 'tier-100m' : ''}">${c.capital_str}</span>
            </div>
          </div>

          <div class="card-bld-tag" onclick="openBuildingByName('${c.building_name}')" title="點擊查看整棟大樓水牌">
            <span>🏢 ${c.building_name}</span>
            <span class="card-floor-pill">${c.floor}</span>
            <span class="badge-cat" style="background:${c.category_color}15; color:${c.category_color};">${c.category_icon} ${c.category_name}</span>
          </div>

          <div class="card-address">
            📍 ${c.road} · ${c.address}
          </div>

          <div class="card-contact">
            <span>👤 ${c.contact}</span>
            <span>📞 ${c.phone}</span>
          </div>

          <div class="card-weakpoint">
            💡 <strong>弱電與設備痛點：</strong>${c.notes}
          </div>

          <div class="card-actions">
            <button class="card-btn ${isDone ? 'btn-visited' : ''}" onclick="toggleVisitStatus(${c.id}, event)">
              ${isDone ? '✅ 已拜訪' : (isNeg ? '💬 洽談中' : '✓ 標記已訪')}
            </button>
            <button class="card-btn" onclick="openBuildingByName('${c.building_name}')">
              🏢 整棟水牌
            </button>
            <a href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(c.address)}" target="_blank" class="card-btn btn-nav" onclick="event.stopPropagation()">
              🚗 導航
            </a>
          </div>
        `;

        card.onclick = () => {
          document.querySelectorAll('.client-card').forEach(el => el.classList.remove('active-selected'));
          card.classList.add('active-selected');
          if (markers[c.id]) {
            markers[c.id].openPopup();
            map.flyTo([c.lat, c.lng], 17, { duration: 0.8 });
          }
        };

        container.appendChild(card);
      }
    }

    // --- Update Leaflet Markers ---
    function updateMarkers(filteredList) {
      if (!map) return;
      Object.values(markers).forEach(m => map.removeLayer(m));
      markers = {};

      const bounds = L.latLngBounds();

      filteredList.forEach(c => {
        let pinColor = c.category_color || "#0284C7";
        if (c.status === "已拜訪") pinColor = "#16A34A";
        else if (c.status === "洽談中") pinColor = "#7C3AED";

        const iconHtml = `<div class="comp-marker" style="background:${pinColor};">${c.is_listed === '是' ? '★' : c.category_icon}</div>`;
        const icon = L.divIcon({
          html: iconHtml,
          className: '',
          iconSize: [26, 26],
          iconAnchor: [13, 13],
          popupAnchor: [0, -13]
        });

        const marker = L.marker([c.lat, c.lng], { icon: icon }).addTo(map);

        // Auto Tooltip on Zoom
        const tooltipContent = `
          <div class="lbl-title">
            <span>${c.name}</span>
            <span style="font-size:10px;color:#0284C7;font-weight:900;">${c.floor}</span>
          </div>
          <div class="lbl-detail">
            <span>🏢 ${c.building_name}</span> · <span>${c.capital_str}</span>
          </div>
        `;

        marker.bindTooltip(tooltipContent, {
          permanent: true,
          direction: 'top',
          offset: [0, -14],
          className: 'marker-auto-tooltip'
        });

        const popupContent = `
          <div style="font-family:inherit; min-width:240px; padding:2px;">
            <div style="font-weight:900; font-size:14px; color:#0F172A; margin-bottom:2px;">
              ${c.name}
            </div>
            <div style="font-size:11.5px; color:#0284C7; font-weight:800; margin-bottom:4px;">
              🏢 ${c.building_name} · ${c.floor}
            </div>
            <div style="font-size:11px; color:#64748B; margin-bottom:6px;">
              📍 ${c.address}
            </div>
            <div style="font-size:11px; background:#F0FDF4; border:1px dashed #86EFAC; padding:4px 6px; border-radius:4px; color:#166534; margin-bottom:8px;">
              💡 <strong>弱電痛點：</strong>${c.notes}
            </div>
            <div style="display:flex; gap:5px;">
              <button onclick="openBuildingByName('${c.building_name}')" style="flex:1; background:#0F172A; color:#FFF; border:none; padding:6px; border-radius:5px; font-size:11px; font-weight:700; cursor:pointer;">
                🏢 大樓全棟水牌
              </button>
              <a href="https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(c.address)}" target="_blank" style="background:#0284C7; color:#FFF; text-decoration:none; padding:6px 10px; border-radius:5px; font-size:11px; font-weight:800; display:inline-flex; align-items:center;">
                🚗 導航
              </a>
            </div>
          </div>
        `;
        marker.bindPopup(popupContent);

        markers[c.id] = marker;
        bounds.extend([c.lat, c.lng]);
      });

      if (filteredList.length > 0 && bounds.isValid() && filteredList.length <= 120) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 });
      }

      if (autoLabelsEnabled && map.getZoom() >= 16) {
        document.getElementById('map').classList.add('show-auto-labels');
      }
    }

    // --- Building Directory View (大樓水牌模式) ---
    window.openBuildingByName = function(bldName) {
      const companies = ALL_COMPANIES.filter(c => c.building_name === bldName);
      if (companies.length === 0) return;

      // Sort by floor descending (e.g. 32F down to 2F)
      companies.sort((a, b) => b.floor_num - a.floor_num);

      document.getElementById('bldModalTitle').innerText = `🏢 ${bldName}`;
      document.getElementById('bldModalAddress').innerText = companies[0].address.replace(companies[0].floor, '');
      document.getElementById('bldModalCount').innerText = `全棟共 ${companies.length} 家企業客戶`;

      const listContainer = document.getElementById('bldModalList');
      listContainer.innerHTML = '';

      companies.forEach(c => {
        const item = document.createElement('div');
        item.style.cssText = 'background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 12px; display:flex; flex-direction:column; gap:4px;';
        item.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="background:#0F172A; color:#38BDF8; font-weight:900; font-size:11px; padding:1px 6px; border-radius:4px;">${c.floor}</span>
              <span style="font-weight:900; font-size:13px; color:#0F172A;">${c.name}</span>
            </div>
            <span style="font-size:10.5px; font-weight:800; color:#B45309; background:#FEF3C7; padding:1px 5px; border-radius:4px;">${c.capital_str}</span>
          </div>
          <div style="font-size:11px; color:#64748B; display:flex; gap:8px;">
            <span>${c.category_icon} ${c.category_name}</span> · <span>👤 ${c.contact}</span> · <span>📞 ${c.phone}</span>
          </div>
          <div style="font-size:10.5px; color:#166534; background:#DCFCE7; padding:3px 6px; border-radius:4px; margin-top:2px;">
            💡 ${c.notes}
          </div>
        `;
        listContainer.appendChild(item);
      });

      document.getElementById('modalBuilding').classList.add('open');
    };

    window.closeBuildingModal = function() {
      document.getElementById('modalBuilding').classList.remove('open');
    };

    window.openAllBuildingsDirectory = function() {
      const bldList = currentDistrict === 'all' ? BUILDINGS : BUILDINGS.filter(b => b.district_id === currentDistrict);
      document.getElementById('bldModalTitle').innerText = `🏢 桃園商辦大樓總名錄`;
      document.getElementById('bldModalAddress').innerText = `共收錄 ${bldList.length} 棟指標商務大樓`;
      document.getElementById('bldModalCount').innerText = `點擊任一大樓展開樓層水牌`;

      const listContainer = document.getElementById('bldModalList');
      listContainer.innerHTML = '';

      bldList.forEach(b => {
        const item = document.createElement('div');
        item.style.cssText = 'background:#FFFFFF; border:1.5px solid #E2E8F0; border-radius:8px; padding:10px 12px; display:flex; justify-content:space-between; align-items:center; cursor:pointer;';
        item.innerHTML = `
          <div>
            <div style="font-weight:900; font-size:13.5px; color:#0F172A;">🏢 ${b.name}</div>
            <div style="font-size:11.5px; color:#64748B;">📍 ${b.address} · 樓高 ${b.floors} 層</div>
          </div>
          <button class="btn btn-primary" style="padding:5px 10px; font-size:11px;">
            掃樓名錄 (${b.company_count}家)
          </button>
        `;
        item.onclick = () => openBuildingByName(b.name);
        listContainer.appendChild(item);
      });

      document.getElementById('modalBuilding').classList.add('open');
    };

    window.toggleVisitStatus = function(id, event) {
      if (event) event.stopPropagation();
      const comp = ALL_COMPANIES.find(c => c.id === id);
      if (!comp) return;
      comp.status = (comp.status === "已拜訪") ? "尚未拜訪" : "已拜訪";
      renderList();
    };

    // --- CSV Export ---
    document.getElementById('btnExport').addEventListener('click', () => {
      let csvContent = "\\uFEFF統一編號,行政區,商辦大樓名稱,所在樓層,公司名稱,所在路段,完整地址,緯度,經度,產業類別,資本額,是否上市櫃,拜訪狀態,聯絡窗口,聯絡電話,弱電需求痛點備忘\\n";
      currentFiltered.forEach(c => {
        const row = [
          c.id,
          `"${c.district_name}"`,
          `"${c.building_name}"`,
          `"${c.floor}"`,
          `"${c.name}"`,
          `"${c.road}"`,
          `"${c.address}"`,
          c.lat,
          c.lng,
          `"${c.category_name}"`,
          `"${c.capital_str}"`,
          c.is_listed,
          `"${c.status}"`,
          `"${c.contact}"`,
          `"${c.phone}"`,
          `"${c.notes}"`
        ].join(",");
        csvContent += row + "\\n";
      });

      const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `桃園商辦與企業地圖_弱電外勤名冊_${new Date().toISOString().slice(0,10)}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    });

    // --- DOMContentLoaded ---
    document.addEventListener("DOMContentLoaded", () => {
      initMap();
      renderDistrictNavBar();
      setupCategoryChips();
      setupBuildingChips();
      renderList();

      // Search listeners
      const searchInput = document.getElementById('searchInput');
      const clearBtn = document.getElementById('btnClearSearch');
      function triggerSearch() {
        searchQuery = searchInput.value.trim();
        clearBtn.style.display = searchQuery ? 'block' : 'none';
        renderList();
      }
      searchInput.addEventListener('input', () => {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(triggerSearch, 100);
      });
      clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        triggerSearch();
      });
      document.getElementById('btnDoSearch').addEventListener('click', triggerSearch);

      // Capital tier listener
      document.querySelectorAll('#capitalChips .chip-capital').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('#capitalChips .chip-capital').forEach(b => b.classList.remove('active'));
          btn.classList.add('active');
          activeCapitalTier = btn.getAttribute('data-tier');
          document.getElementById('capitalCurrentLabel').innerText = btn.innerText;
          renderList();
        });
      });

      // Status buttons listener
      document.querySelectorAll('#statusChips .chip-status').forEach(btn => {
        btn.addEventListener('click', () => {
          document.querySelectorAll('#statusChips .chip-status').forEach(b => b.className = "chip-status");
          const st = btn.getAttribute('data-status');
          activeStatus = st;
          if (st === "ALL") btn.classList.add('active-all');
          else if (st === "LISTED") btn.classList.add('active-listed');
          else if (st === "尚未拜訪") btn.classList.add('active-pending');
          else if (st === "洽談中") btn.classList.add('active-negotiating');
          else if (st === "已拜訪") btn.classList.add('active-done');
          renderList();
        });
      });

      // Reset Filter
      document.getElementById('btnResetFilter').addEventListener('click', () => {
        searchQuery = '';
        searchInput.value = '';
        clearBtn.style.display = 'none';
        activeCategory = 'ALL';
        activeCapitalTier = 'ALL';
        activeBuilding = 'ALL';
        activeStatus = 'ALL';
        setupCategoryChips();
        setupBuildingChips();
        document.querySelectorAll('#capitalChips .chip-capital').forEach(b => b.classList.remove('active'));
        document.querySelector('[data-tier="ALL"]').classList.add('active');
        document.querySelectorAll('#statusChips .chip-status').forEach(b => b.className = "chip-status");
        document.querySelector('[data-status="ALL"]').classList.add('active-all');
        renderList();
      });

      // Locate GPS
      document.getElementById('btnLocateMe').addEventListener('click', () => {
        if (!navigator.geolocation) {
          alert("設備不支援定位");
          return;
        }
        navigator.geolocation.getCurrentPosition(pos => {
          const lat = pos.coords.latitude;
          const lng = pos.coords.longitude;
          L.circleMarker([lat, lng], { radius: 8, color: '#0284C7', fillColor: '#38BDF8', fillOpacity: 0.9 }).addTo(map).bindPopup("<b>📍 您的目前位置</b>").openPopup();
          map.flyTo([lat, lng], 16);
        });
      });

      // Fit bounds
      document.getElementById('btnFitBounds').addEventListener('click', () => {
        const bounds = L.latLngBounds(currentFiltered.map(c => [c.lat, c.lng]));
        if (bounds.isValid()) map.fitBounds(bounds, { padding: [50, 50] });
      });

      // Infinite scroll
      const clientListContainer = document.getElementById('clientList');
      clientListContainer.addEventListener('scroll', () => {
        if (clientListContainer.scrollTop + clientListContainer.clientHeight >= clientListContainer.scrollHeight - 160) {
          if (displayedCount < currentFiltered.length) {
            displayedCount += 60;
            renderCardsSlice(false);
          }
        }
      });

      // Modal backdrop click
      document.getElementById('modalBuilding')?.addEventListener('click', (e) => {
        if (e.target.id === 'modalBuilding') closeBuildingModal();
      });

      if (window.innerWidth <= 768) {
        setMobileView("split");
      }
    });
  </script>
</body>
</html>
'''

full_html = html_template.replace('__DATABASE_BUNDLE_PLACEHOLDER__', database_json)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(full_html)

print(f"[OK] 成功編譯生成全台商辦＆企業地圖 index.html！檔案大小：{len(full_html.encode('utf-8')):,} bytes")
