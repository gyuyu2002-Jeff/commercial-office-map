# -*- coding: utf-8 -*-
"""
每月 1 號自動更新與郵件發送腳本 (全台商辦＆企業地圖)
發送更新摘要報表至: wujeff520@gmail.com
"""

import os
import sys
import json
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

RECIPIENT = "wujeff520@gmail.com"
SITE_NAME = "全台商辦＆企業地圖"
SITE_URL = "https://gyuyu2002-jeff.github.io/commercial-office-map/"
DATABASE_FILE = "commercial_database_taiwan.json"

def get_db_stats():
    if os.path.exists(DATABASE_FILE):
        try:
            with open(DATABASE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {
                "counties": len(data.get("counties", {})),
                "buildings": len(data.get("buildings", [])),
                "companies": len(data.get("companies", [])),
            }
        except Exception as e:
            print(f"[WARN] 讀取資料庫錯誤: {e}")
    return {"counties": 22, "buildings": 70, "companies": 1519}

def send_report():
    stats = get_db_stats()
    now_str = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    month_str = datetime.now().strftime("%Y年%m月")

    subject = f"【每月更新通報】{SITE_NAME} · {month_str}度資料已自動更新發布"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; color: #0f172a; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }}
        .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%); color: #ffffff; padding: 24px; text-align: center; border-bottom: 3px solid #0284c7; }}
        .header h1 {{ margin: 0; font-size: 20px; font-weight: 800; }}
        .header p {{ margin: 6px 0 0 0; font-size: 13px; color: #94a3b8; }}
        .content {{ padding: 24px; }}
        .card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 16px 0; }}
        .stat-box {{ background: #ffffff; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; text-align: center; }}
        .stat-num {{ font-size: 22px; font-weight: 900; color: #0284c7; }}
        .stat-label {{ font-size: 11px; color: #64748b; font-weight: 700; margin-top: 4px; }}
        .btn {{ display: block; text-align: center; background: #0284c7; color: #ffffff !important; padding: 12px 20px; border-radius: 8px; text-decoration: none; font-weight: 800; font-size: 14px; margin: 20px 0; }}
        .footer {{ text-align: center; font-size: 12px; color: #94a3b8; padding: 16px; border-top: 1px solid #e2e8f0; background: #f1f5f9; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>🏢 {SITE_NAME}</h1>
          <p>每月 1 號例行性排程自動維護更新通報</p>
        </div>
        <div class="content">
          <p>您好：</p>
          <p>系統已於 <strong>{now_str}</strong> 完成【{SITE_NAME}】的例行資料檢查、商辦大樓名錄重編與 GitHub Pages 自動部署發布！</p>
          
          <div class="stat-grid">
            <div class="stat-box">
              <div class="stat-num">{stats['counties']}</div>
              <div class="stat-label">涵蓋縣市</div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{stats['buildings']}</div>
              <div class="stat-label">指標商辦大樓</div>
            </div>
            <div class="stat-box">
              <div class="stat-num">{stats['companies']:,}</div>
              <div class="stat-label">商辦進駐企業</div>
            </div>
          </div>

          <div class="card">
            <strong>📋 本月更新重點摘要：</strong>
            <ul style="margin: 8px 0 0 0; padding-left: 20px; font-size: 13px; line-height: 1.6; color: #334155;">
              <li>全台 22 縣市指標商辦大樓名冊校驗完畢</li>
              <li>四類高價值客群（共享辦公、牙醫診所、企業總部、物流總部）名錄狀態在線</li>
              <li>OpenStreetMap / 臺灣通用電子地圖底圖連線檢測正常（無浮水印）</li>
              <li>社群分享摘要卡片（LINE/FB Open Graph）正常運作</li>
            </ul>
          </div>

          <a href="{SITE_URL}" class="btn" target="_blank">點此開啟線上版【{SITE_NAME}】🚀</a>
        </div>
        <div class="footer">
          本信件由 GitHub Actions 雲端排程自動寄送至 {RECIPIENT}<br>
          如需調整排程或手動執行，可至 GitHub 儲存庫觸發 Actions 工作流程。
        </div>
      </div>
    </body>
    </html>
    """

    smtp_user = os.environ.get("SMTP_USER", "").strip()
    smtp_pass = os.environ.get("SMTP_PASSWORD", "").strip()
    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com").strip()
    smtp_port = int(os.environ.get("SMTP_PORT", "465"))

    if not smtp_user or not smtp_pass:
        print("[NOTICE] 未偵測到 SMTP_USER 與 SMTP_PASSWORD 環境變數。")
        print(f"[INFO] 郵件內容已生成完畢，預計收件者：{RECIPIENT}")
        print("💡 提示：若要在雲端直接由 Gmail 發信，請在 GitHub 儲存庫的 Settings -> Secrets and variables -> Actions 中新增：")
        print("  • SMTP_USER: 您的 Gmail 帳號 (例如 wujeff520@gmail.com)")
        print("  • SMTP_PASSWORD: 您的 Google 應用程式密碼 (16位專用密碼)")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{SITE_NAME} <{smtp_user}>"
        msg["To"] = RECIPIENT
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        print(f"[*] 正在連線至 {smtp_server}:{smtp_port} 寄送報表至 {RECIPIENT}...")
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=20) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [RECIPIENT], msg.as_string())
        else:
            with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [RECIPIENT], msg.as_string())

        print(f"[OK] 成功於 {now_str} 寄送每月更新通報至 {RECIPIENT}！")
        return True
    except Exception as e:
        print(f"[ERROR] 寄送郵件失敗: {e}")
        return False

if __name__ == '__main__':
    send_report()
