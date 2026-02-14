"""
Comprehensive workflow template library.

Production-ready templates covering real business scenarios:
- E-commerce, Finance, HR, Customer Support, Marketing, DevOps,
  Data Processing, Compliance, IT Operations, Sales, Legal, Healthcare.

Each template includes detailed multi-step workflows with error handling,
retry logic, validations, and conditional branching.
"""

BUILTIN_TEMPLATES = [
    # ═══════════════════════════════════════════════════════════════════
    # DATA EXTRACTION
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-web-scraper",
        "name": "Web Scraper",
        "description": "Scrape data from a website using CSS selectors, then save results to a file.",
        "category": "data-extraction",
        "icon": "🕷️",
        "tags": ["web", "scraping", "data"],
        "difficulty": "beginner",
        "estimated_duration": "2-5 min",
        "steps": [
            {"id": "step-1", "name": "Scrape Page", "type": "web_scrape", "config": {"url": "https://example.com", "selectors": [{"name": "title", "selector": "h1", "extract": "text"}, {"name": "links", "selector": "a", "extract": "attribute", "attribute": "href", "multiple": True}]}},
            {"id": "step-2", "name": "Transform Data", "type": "data_transform", "config": {"script": "output = {'title': steps.step_1.title, 'link_count': len(steps.step_1.links)}"}, "depends_on": ["step-1"]},
        ],
    },
    {
        "id": "tpl-multi-page-scraper",
        "name": "Multi-Page Scraper with Pagination",
        "description": "Crawl paginated websites (e.g. product listings, search results), extract structured data from every page, handle pagination automatically, and export consolidated CSV.",
        "category": "data-extraction",
        "icon": "🌐",
        "tags": ["scraping", "pagination", "csv", "crawl", "multi-page"],
        "difficulty": "advanced",
        "estimated_duration": "10-30 min",
        "steps": [
            {"id": "step-1", "name": "Initialize Pagination", "type": "custom_script", "config": {"language": "python", "script": "state = {'page': 1, 'max_pages': 50, 'all_results': [], 'base_url': config.get('base_url', 'https://example.com/products?page=')}", "outputs": ["state"]}},
            {"id": "step-2", "name": "Fetch Current Page", "type": "http_request", "config": {"url": "{{ state.base_url }}{{ state.page }}", "method": "GET", "timeout": 15, "retry": {"max_attempts": 3, "delay": 2}, "validate": {"status_code": [200]}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Extract Product Data", "type": "web_scrape", "config": {"html": "{{ steps.step_2.body }}", "selectors": [{"name": "products", "selector": ".product-card", "multiple": True, "children": [{"name": "title", "selector": ".product-title", "extract": "text"}, {"name": "price", "selector": ".price", "extract": "text"}, {"name": "rating", "selector": ".rating", "extract": "attribute", "attribute": "data-value"}, {"name": "url", "selector": "a", "extract": "attribute", "attribute": "href"}, {"name": "in_stock", "selector": ".stock-status", "extract": "text"}]}, {"name": "next_page", "selector": ".pagination .next", "extract": "attribute", "attribute": "href"}]}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Accumulate & Check Next", "type": "custom_script", "config": {"language": "python", "script": "state['all_results'].extend(steps.step_3.products)\nstate['page'] += 1\nhas_more = bool(steps.step_3.next_page) and state['page'] <= state['max_pages']\noutput = {'has_more': has_more, 'total_collected': len(state['all_results'])}"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Loop or Continue", "type": "condition", "config": {"condition": "{{ steps.step_4.has_more == true }}", "on_true": "step-2", "on_false": "step-6"}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Clean & Deduplicate Data", "type": "data_transform", "config": {"script": "import re\nseen = set()\nclean = []\nfor p in state['all_results']:\n    key = p.get('url', p.get('title', ''))\n    if key not in seen:\n        seen.add(key)\n        price_str = re.sub(r'[^\\d.]', '', p.get('price', '0'))\n        clean.append({'title': p['title'].strip(), 'price': float(price_str) if price_str else 0, 'rating': float(p.get('rating', 0)), 'url': p.get('url', ''), 'in_stock': 'in stock' in p.get('in_stock', '').lower()})\noutput = sorted(clean, key=lambda x: x['price'], reverse=True)"}, "depends_on": ["step-5"]},
            {"id": "step-7", "name": "Export to CSV", "type": "file_write", "config": {"path": "/output/scraped_products_{{ timestamp }}.csv", "format": "csv", "headers": ["title", "price", "rating", "url", "in_stock"], "data": "{{ steps.step_6 }}"}, "depends_on": ["step-6"]},
            {"id": "step-8", "name": "Send Summary Email", "type": "email_send", "config": {"to": "{{ config.notify_email }}", "subject": "Scraping Complete: {{ steps.step_4.total_collected }} products collected", "body": "Scraping job finished.\n\nTotal products: {{ steps.step_4.total_collected }}\nUnique after dedup: {{ len(steps.step_6) }}\nFile: scraped_products_{{ timestamp }}.csv"}, "depends_on": ["step-7"]},
        ],
    },
    {
        "id": "tpl-competitor-price-tracker",
        "name": "Competitor Price Tracker",
        "description": "Monitor competitor product prices daily, compare with your pricing, detect changes > 5%, and alert team with actionable pricing recommendations via Slack/email.",
        "category": "data-extraction",
        "icon": "💰",
        "tags": ["pricing", "competitor", "monitoring", "e-commerce", "alerts"],
        "difficulty": "advanced",
        "estimated_duration": "5-15 min",
        "steps": [
            {"id": "step-1", "name": "Load Product List", "type": "http_request", "config": {"url": "{{ config.products_api }}/api/products?active=true", "method": "GET", "headers": {"Authorization": "Bearer {{ credentials.api_token }}"}}},
            {"id": "step-2", "name": "Load Previous Prices", "type": "database_query", "config": {"connection": "{{ credentials.db }}", "query": "SELECT product_sku, competitor, last_price, our_price FROM competitor_prices WHERE updated_at >= NOW() - INTERVAL '7 days'"}},
            {"id": "step-3", "name": "Scrape Competitor Sites", "type": "loop", "config": {"items": "{{ steps.step_1.data.products }}", "max_parallel": 5, "step": {"type": "web_scrape", "config": {"url": "{{ item.competitor_url }}", "selectors": [{"name": "price", "selector": "{{ item.price_selector }}", "extract": "text"}, {"name": "availability", "selector": "{{ item.stock_selector }}", "extract": "text"}], "proxy": True, "user_agent_rotation": True, "timeout": 20}}}, "depends_on": ["step-1"]},
            {"id": "step-4", "name": "Analyze Price Changes", "type": "custom_script", "config": {"language": "python", "script": "import re\nprev = {f\"{r['product_sku']}_{r['competitor']}\": r for r in steps.step_2.rows}\nalerts = []\nfor i, product in enumerate(steps.step_1.data.products):\n    scraped = steps.step_3.results[i]\n    price_str = re.sub(r'[^\\d.]', '', scraped.get('price', '0'))\n    new_price = float(price_str) if price_str else None\n    if not new_price: continue\n    key = f\"{product['sku']}_{product['competitor']}\"\n    prev_data = prev.get(key, {})\n    old_price = prev_data.get('last_price', new_price)\n    our_price = prev_data.get('our_price', product.get('our_price', 0))\n    change_pct = ((new_price - old_price) / old_price * 100) if old_price else 0\n    if abs(change_pct) >= 5:\n        alerts.append({'sku': product['sku'], 'name': product['name'], 'competitor': product['competitor'], 'old_price': old_price, 'new_price': new_price, 'change_pct': round(change_pct, 1), 'our_price': our_price, 'recommendation': 'LOWER PRICE' if new_price < our_price else 'MAINTAIN' if new_price > our_price * 1.1 else 'REVIEW'})\noutput = {'alerts': alerts, 'total_checked': len(steps.step_1.data.products), 'alerts_count': len(alerts)}"}, "depends_on": ["step-2", "step-3"]},
            {"id": "step-5", "name": "Save to Database", "type": "database_query", "config": {"connection": "{{ credentials.db }}", "query": "INSERT INTO competitor_prices (product_sku, competitor, last_price, scraped_at) VALUES {{ bulk_values }}", "bulk_data": "{{ steps.step_3.results }}"}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Alert if Changes Found", "type": "condition", "config": {"condition": "{{ steps.step_4.alerts_count > 0 }}", "on_true": "step-7", "on_false": "step-8"}, "depends_on": ["step-5"]},
            {"id": "step-7", "name": "Send Slack Alert", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "🚨 *Price Alert*: {{ steps.step_4.alerts_count }} competitor price changes detected!\n\n{% for a in steps.step_4.alerts %}• *{{ a.name }}* ({{ a.competitor }}): ${{ a.old_price }} → ${{ a.new_price }} ({{ a.change_pct }}%) — {{ a.recommendation }}\n{% endfor %}"}}, "depends_on": ["step-6"]},
            {"id": "step-8", "name": "Log Completion", "type": "custom_script", "config": {"language": "python", "script": "output = {'status': 'completed', 'products_checked': steps.step_4.total_checked, 'alerts_sent': steps.step_4.alerts_count}"}, "depends_on": ["step-6"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # MONITORING
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-api-monitor",
        "name": "API Health Monitor",
        "description": "Periodically check an API endpoint and send alerts on failure.",
        "category": "monitoring",
        "icon": "🔍",
        "tags": ["api", "monitoring", "health", "alerts"],
        "difficulty": "beginner",
        "estimated_duration": "1-2 min",
        "steps": [
            {"id": "step-1", "name": "Check API", "type": "http_request", "config": {"url": "https://api.example.com/health", "method": "GET", "timeout": 10, "validate": {"status_code": [200]}}},
            {"id": "step-2", "name": "Alert on Failure", "type": "condition", "config": {"condition": "{{ steps.step_1.success == false }}", "on_true": "step-3"}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Send Alert", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "🚨 API health check failed!"}}, "depends_on": ["step-2"]},
        ],
    },
    {
        "id": "tpl-uptime-multi-endpoint",
        "name": "Multi-Endpoint Uptime Monitor",
        "description": "Monitor 10+ endpoints simultaneously, measure response times, track SLA compliance, store metrics in DB, and generate daily/weekly uptime reports with graphs.",
        "category": "monitoring",
        "icon": "📊",
        "tags": ["uptime", "sla", "monitoring", "report", "multi-endpoint"],
        "difficulty": "advanced",
        "estimated_duration": "2-5 min",
        "steps": [
            {"id": "step-1", "name": "Load Endpoints Config", "type": "custom_script", "config": {"language": "python", "script": "endpoints = config.get('endpoints', [\n  {'name': 'Main API', 'url': 'https://api.example.com/health', 'expected_status': 200, 'max_response_ms': 2000, 'sla_target': 99.9},\n  {'name': 'Auth Service', 'url': 'https://auth.example.com/ping', 'expected_status': 200, 'max_response_ms': 1000, 'sla_target': 99.95},\n  {'name': 'Payment Gateway', 'url': 'https://pay.example.com/status', 'expected_status': 200, 'max_response_ms': 3000, 'sla_target': 99.99},\n])\noutput = endpoints"}},
            {"id": "step-2", "name": "Check All Endpoints", "type": "loop", "config": {"items": "{{ steps.step_1 }}", "max_parallel": 10, "step": {"type": "http_request", "config": {"url": "{{ item.url }}", "method": "GET", "timeout": "{{ item.max_response_ms / 1000 }}", "capture_timing": True, "retry": {"max_attempts": 2, "delay": 1}}}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Analyze Results", "type": "custom_script", "config": {"language": "python", "script": "from datetime import datetime\nresults = []\ndown = []\nfor i, ep in enumerate(steps.step_1):\n    check = steps.step_2.results[i]\n    is_up = check.get('status_code') == ep['expected_status']\n    resp_ms = check.get('response_time_ms', 9999)\n    is_slow = resp_ms > ep['max_response_ms']\n    results.append({'name': ep['name'], 'url': ep['url'], 'status': 'UP' if is_up else 'DOWN', 'response_ms': resp_ms, 'slow': is_slow, 'checked_at': datetime.utcnow().isoformat()})\n    if not is_up or is_slow:\n        down.append({'name': ep['name'], 'status': 'DOWN' if not is_up else 'SLOW', 'response_ms': resp_ms})\noutput = {'results': results, 'issues': down, 'total': len(results), 'healthy': len(results) - len(down)}"}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Save Metrics to DB", "type": "database_query", "config": {"connection": "{{ credentials.metrics_db }}", "query": "INSERT INTO uptime_checks (endpoint_name, status, response_ms, checked_at) VALUES {{ bulk_values }}", "bulk_data": "{{ steps.step_3.results }}"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Alert on Issues", "type": "condition", "config": {"condition": "{{ len(steps.step_3.issues) > 0 }}", "on_true": "step-6"}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Send PagerDuty/Slack Alert", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "🚨 *Uptime Alert* — {{ len(steps.step_3.issues) }} issue(s):\n{% for i in steps.step_3.issues %}• {{ i.name }}: {{ i.status }} ({{ i.response_ms }}ms)\n{% endfor %}\nHealthy: {{ steps.step_3.healthy }}/{{ steps.step_3.total }}"}}, "depends_on": ["step-5"]},
        ],
    },
    {
        "id": "tpl-ssl-certificate-monitor",
        "name": "SSL Certificate Expiry Monitor",
        "description": "Check SSL certificates for all your domains, alert 30/14/7 days before expiry, and auto-create renewal tickets in your project management tool.",
        "category": "monitoring",
        "icon": "🔒",
        "tags": ["ssl", "certificate", "security", "expiry", "devops"],
        "difficulty": "intermediate",
        "estimated_duration": "1-3 min",
        "steps": [
            {"id": "step-1", "name": "Load Domain List", "type": "custom_script", "config": {"language": "python", "script": "domains = config.get('domains', ['example.com', 'api.example.com', 'app.example.com', 'mail.example.com'])\noutput = domains"}},
            {"id": "step-2", "name": "Check SSL Certs", "type": "loop", "config": {"items": "{{ steps.step_1 }}", "max_parallel": 5, "step": {"type": "custom_script", "config": {"language": "python", "script": "import ssl, socket\nfrom datetime import datetime\ntry:\n    ctx = ssl.create_default_context()\n    conn = ctx.wrap_socket(socket.socket(), server_hostname=item)\n    conn.settimeout(10)\n    conn.connect((item, 443))\n    cert = conn.getpeercert()\n    exp = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')\n    days_left = (exp - datetime.utcnow()).days\n    output = {'domain': item, 'expires': exp.isoformat(), 'days_left': days_left, 'issuer': dict(x[0] for x in cert.get('issuer', [])).get('organizationName', 'Unknown'), 'status': 'CRITICAL' if days_left <= 7 else 'WARNING' if days_left <= 14 else 'NOTICE' if days_left <= 30 else 'OK'}\nexcept Exception as e:\n    output = {'domain': item, 'status': 'ERROR', 'error': str(e), 'days_left': -1}"}}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Filter Expiring", "type": "custom_script", "config": {"language": "python", "script": "expiring = [r for r in steps.step_2.results if r['status'] in ('CRITICAL', 'WARNING', 'NOTICE')]\nerrors = [r for r in steps.step_2.results if r['status'] == 'ERROR']\noutput = {'expiring': expiring, 'errors': errors, 'all_ok': len(expiring) == 0 and len(errors) == 0}"}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Alert if Expiring", "type": "condition", "config": {"condition": "{{ not steps.step_3.all_ok }}", "on_true": "step-5"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Send Alert + Create Ticket", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "🔒 *SSL Certificate Alert*\n{% for c in steps.step_3.expiring %}• {{ c.domain }}: {{ c.status }} — expires in {{ c.days_left }} days ({{ c.expires }})\n{% endfor %}{% for e in steps.step_3.errors %}• {{ e.domain }}: ❌ ERROR — {{ e.error }}\n{% endfor %}"}}, "depends_on": ["step-4"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # BROWSER AUTOMATION
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-form-automation",
        "name": "Form Submission Bot",
        "description": "Navigate to a page, fill a form with data, submit it, and capture the result.",
        "category": "browser-automation",
        "icon": "📝",
        "tags": ["form", "automation", "browser", "submit"],
        "difficulty": "intermediate",
        "estimated_duration": "3-8 min",
        "steps": [
            {"id": "step-1", "name": "Fill Form", "type": "form_fill", "config": {"url": "https://example.com/contact", "fields": [{"selector": "#name", "value": "John Doe", "action": "fill"}, {"selector": "#email", "value": "john@example.com", "action": "fill"}, {"selector": "#message", "value": "Automated message", "action": "fill"}], "submit": "button[type=submit]", "screenshot_after": True}},
        ],
    },
    {
        "id": "tpl-invoice-download",
        "name": "Automated Invoice Downloader",
        "description": "Log into supplier portals, navigate to invoices section, download all new invoices as PDF, rename with standardized naming convention, and upload to cloud storage/accounting system.",
        "category": "browser-automation",
        "icon": "🧾",
        "tags": ["invoice", "download", "accounting", "pdf", "finance"],
        "difficulty": "advanced",
        "estimated_duration": "5-20 min",
        "steps": [
            {"id": "step-1", "name": "Login to Portal", "type": "page_interaction", "config": {"url": "{{ config.portal_url }}/login", "steps": [{"action": "fill", "selector": "#username", "value": "{{ credentials.portal_user }}"}, {"action": "fill", "selector": "#password", "value": "{{ credentials.portal_pass }}"}, {"action": "click", "selector": "button[type=submit]"}, {"action": "wait", "selector": ".dashboard", "timeout": 10}]}},
            {"id": "step-2", "name": "Navigate to Invoices", "type": "page_interaction", "config": {"steps": [{"action": "click", "selector": "a[href*=invoice]"}, {"action": "wait", "selector": ".invoice-list"}, {"action": "select", "selector": "#date-range", "value": "last-30-days"}, {"action": "click", "selector": "#filter-btn"}, {"action": "wait", "timeout": 3}]}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Extract Invoice List", "type": "web_scrape", "config": {"selectors": [{"name": "invoices", "selector": ".invoice-row", "multiple": True, "children": [{"name": "number", "selector": ".inv-number", "extract": "text"}, {"name": "date", "selector": ".inv-date", "extract": "text"}, {"name": "amount", "selector": ".inv-amount", "extract": "text"}, {"name": "download_url", "selector": "a.download", "extract": "attribute", "attribute": "href"}, {"name": "status", "selector": ".inv-status", "extract": "text"}]}]}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Download New Invoices", "type": "loop", "config": {"items": "{{ steps.step_3.invoices }}", "filter": "{{ item.status == 'New' or item.status == 'Unpaid' }}", "step": {"type": "file_download", "config": {"url": "{{ item.download_url }}", "filename": "INV_{{ item.number }}_{{ item.date | replace('/', '-') }}.pdf", "directory": "/output/invoices/"}}}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Log Results", "type": "custom_script", "config": {"language": "python", "script": "downloaded = [i for i in steps.step_3.invoices if i['status'] in ('New', 'Unpaid')]\noutput = {'total_found': len(steps.step_3.invoices), 'downloaded': len(downloaded), 'filenames': [f\"INV_{i['number']}.pdf\" for i in downloaded]}"}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Notify Finance Team", "type": "email_send", "config": {"to": "{{ config.finance_email }}", "subject": "{{ steps.step_5.downloaded }} new invoices downloaded", "body": "Automated invoice download completed.\n\nTotal invoices found: {{ steps.step_5.total_found }}\nNew invoices downloaded: {{ steps.step_5.downloaded }}\n\nFiles saved to: /output/invoices/"}, "depends_on": ["step-5"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # REPORTING
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-report-generator",
        "name": "PDF Report Generator",
        "description": "Generate a PDF report from a web dashboard page.",
        "category": "reporting",
        "icon": "📄",
        "tags": ["pdf", "report", "dashboard", "export"],
        "difficulty": "beginner",
        "estimated_duration": "1-3 min",
        "steps": [
            {"id": "step-1", "name": "Generate PDF", "type": "pdf_generate", "config": {"url": "https://example.com/dashboard", "format": "A4", "print_background": True, "wait_for": ".chart-loaded"}},
        ],
    },
    {
        "id": "tpl-daily-kpi-report",
        "name": "Daily KPI Dashboard Report",
        "description": "Aggregate KPIs from multiple data sources (DB, APIs, Google Analytics), generate formatted HTML report with charts, convert to PDF, and email to stakeholders every morning.",
        "category": "reporting",
        "icon": "📈",
        "tags": ["kpi", "dashboard", "daily", "report", "analytics", "email"],
        "difficulty": "advanced",
        "estimated_duration": "3-10 min",
        "steps": [
            {"id": "step-1", "name": "Fetch Sales Data", "type": "database_query", "config": {"connection": "{{ credentials.main_db }}", "query": "SELECT DATE(created_at) as date, COUNT(*) as orders, SUM(total) as revenue, AVG(total) as avg_order FROM orders WHERE created_at >= CURRENT_DATE - INTERVAL '30 days' GROUP BY DATE(created_at) ORDER BY date"}},
            {"id": "step-2", "name": "Fetch User Metrics", "type": "database_query", "config": {"connection": "{{ credentials.main_db }}", "query": "SELECT DATE(created_at) as date, COUNT(*) as signups, COUNT(CASE WHEN is_active THEN 1 END) as active FROM users WHERE created_at >= CURRENT_DATE - INTERVAL '30 days' GROUP BY DATE(created_at)"}},
            {"id": "step-3", "name": "Fetch Support Metrics", "type": "http_request", "config": {"url": "{{ config.support_api }}/api/v2/stats/daily", "method": "GET", "headers": {"Authorization": "Bearer {{ credentials.support_token }}"}, "params": {"start_date": "{{ today - 30d }}", "end_date": "{{ today }}"}}, "depends_on": []},
            {"id": "step-4", "name": "Calculate KPIs", "type": "custom_script", "config": {"language": "python", "script": "from datetime import date, timedelta\nsales = steps.step_1.rows\nusers = steps.step_2.rows\ntoday_sales = sales[-1] if sales else {}\nyesterday_sales = sales[-2] if len(sales) > 1 else {}\nrevenue_change = ((today_sales.get('revenue',0) - yesterday_sales.get('revenue',0)) / max(yesterday_sales.get('revenue',1),1)) * 100\noutput = {\n  'today_revenue': today_sales.get('revenue', 0),\n  'today_orders': today_sales.get('orders', 0),\n  'avg_order_value': today_sales.get('avg_order', 0),\n  'revenue_change_pct': round(revenue_change, 1),\n  'monthly_revenue': sum(s.get('revenue', 0) for s in sales),\n  'total_signups_30d': sum(u.get('signups', 0) for u in users),\n  'active_users': users[-1].get('active', 0) if users else 0,\n  'sales_trend': [{'date': s['date'], 'revenue': s['revenue']} for s in sales[-14:]],\n  'support_tickets': steps.step_3.data if hasattr(steps.step_3, 'data') else []\n}"}, "depends_on": ["step-1", "step-2", "step-3"]},
            {"id": "step-5", "name": "Generate HTML Report", "type": "template_render", "config": {"template": "kpi_report.html", "data": "{{ steps.step_4 }}", "charts": [{"type": "line", "data": "{{ steps.step_4.sales_trend }}", "x": "date", "y": "revenue", "title": "Revenue Trend (14 days)"}]}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Convert to PDF", "type": "pdf_generate", "config": {"html": "{{ steps.step_5.html }}", "format": "A4", "filename": "KPI_Report_{{ today }}.pdf"}, "depends_on": ["step-5"]},
            {"id": "step-7", "name": "Email to Stakeholders", "type": "email_send", "config": {"to": "{{ config.stakeholders }}", "subject": "📈 Daily KPI Report — Revenue: ${{ steps.step_4.today_revenue | number_format }} ({{ steps.step_4.revenue_change_pct }}%)", "body": "Please find attached the daily KPI report.", "attachments": ["{{ steps.step_6.file_path }}"]}, "depends_on": ["step-6"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # AI-POWERED
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-ai-classifier",
        "name": "AI Content Classifier",
        "description": "Fetch content, classify it using AI, and route based on the result.",
        "category": "ai-powered",
        "icon": "🤖",
        "tags": ["ai", "classification", "routing", "claude"],
        "difficulty": "intermediate",
        "estimated_duration": "3-8 min",
        "steps": [
            {"id": "step-1", "name": "Fetch Content", "type": "http_request", "config": {"url": "https://api.example.com/tickets/latest", "method": "GET"}},
            {"id": "step-2", "name": "Classify with AI", "type": "ai_classify", "config": {"input": "{{ steps.step_1.data }}", "categories": ["bug", "feature_request", "question", "complaint"]}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Route by Category", "type": "condition", "config": {"condition": "{{ steps.step_2.category == 'bug' }}", "on_true": "step-4-bug", "on_false": "step-4-other"}, "depends_on": ["step-2"]},
        ],
    },
    {
        "id": "tpl-ai-email-responder",
        "name": "AI Email Auto-Responder",
        "description": "Read incoming support emails, analyze sentiment and intent with AI, draft personalized responses, route urgent issues to humans, and auto-reply to common questions with AI-generated answers.",
        "category": "ai-powered",
        "icon": "💬",
        "tags": ["ai", "email", "support", "sentiment", "auto-reply", "nlp"],
        "difficulty": "advanced",
        "estimated_duration": "2-5 min per email",
        "steps": [
            {"id": "step-1", "name": "Fetch Unread Emails", "type": "email_read", "config": {"server": "{{ credentials.imap_server }}", "username": "{{ credentials.email_user }}", "password": "{{ credentials.email_pass }}", "folder": "INBOX", "filter": "UNSEEN", "limit": 20}},
            {"id": "step-2", "name": "AI Analysis per Email", "type": "loop", "config": {"items": "{{ steps.step_1.emails }}", "step": {"type": "ai_analyze", "config": {"model": "claude-sonnet-4-20250514", "prompt": "Analyze this customer email:\n\nFrom: {{ item.from }}\nSubject: {{ item.subject }}\nBody: {{ item.body }}\n\nProvide JSON:\n{\"sentiment\": \"positive|neutral|negative|angry\", \"intent\": \"question|complaint|bug_report|feature_request|billing|other\", \"urgency\": \"low|medium|high|critical\", \"requires_human\": true/false, \"suggested_response\": \"...\", \"summary\": \"one-line summary\", \"language\": \"en|bg|de|...\"}"}}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Route Emails", "type": "custom_script", "config": {"language": "python", "script": "auto_reply = []\nhuman_review = []\nfor i, email in enumerate(steps.step_1.emails):\n    analysis = steps.step_2.results[i]\n    if analysis.get('requires_human') or analysis.get('urgency') in ('high', 'critical') or analysis.get('sentiment') == 'angry':\n        human_review.append({**email, 'analysis': analysis})\n    else:\n        auto_reply.append({**email, 'analysis': analysis})\noutput = {'auto_reply': auto_reply, 'human_review': human_review}"}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Send Auto-Replies", "type": "loop", "config": {"items": "{{ steps.step_3.auto_reply }}", "step": {"type": "email_send", "config": {"to": "{{ item.from }}", "subject": "Re: {{ item.subject }}", "body": "{{ item.analysis.suggested_response }}\n\n---\nThis is an automated response. A human agent will follow up if needed.", "reply_to": "{{ item.message_id }}"}}}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Create Tickets for Human Review", "type": "loop", "config": {"items": "{{ steps.step_3.human_review }}", "step": {"type": "http_request", "config": {"url": "{{ config.ticketing_api }}/tickets", "method": "POST", "body": {"title": "{{ item.analysis.summary }}", "from": "{{ item.from }}", "urgency": "{{ item.analysis.urgency }}", "sentiment": "{{ item.analysis.sentiment }}", "body": "{{ item.body }}", "suggested_response": "{{ item.analysis.suggested_response }}"}}}}, "depends_on": ["step-3"]},
            {"id": "step-6", "name": "Summary Report", "type": "custom_script", "config": {"language": "python", "script": "output = {'total_processed': len(steps.step_1.emails), 'auto_replied': len(steps.step_3.auto_reply), 'sent_to_humans': len(steps.step_3.human_review), 'sentiments': {a['analysis']['sentiment'] for a in steps.step_3.auto_reply + steps.step_3.human_review}}"}, "depends_on": ["step-4", "step-5"]},
        ],
    },
    {
        "id": "tpl-ai-document-processor",
        "name": "AI Document Processor & Summarizer",
        "description": "Process incoming documents (PDF, Word, scans), extract key information using OCR + AI, classify document type, extract structured data (dates, amounts, names), and store in database with searchable index.",
        "category": "ai-powered",
        "icon": "📑",
        "tags": ["ai", "ocr", "document", "extraction", "pdf", "classification"],
        "difficulty": "advanced",
        "estimated_duration": "1-5 min per doc",
        "steps": [
            {"id": "step-1", "name": "Scan Input Folder", "type": "file_watch", "config": {"directory": "{{ config.input_dir }}", "patterns": ["*.pdf", "*.docx", "*.jpg", "*.png"], "recursive": False}},
            {"id": "step-2", "name": "OCR if Image/Scanned", "type": "condition", "config": {"condition": "{{ steps.step_1.file.extension in ('jpg', 'png', 'tiff') }}", "on_true": "step-2a", "on_false": "step-2b"}, "depends_on": ["step-1"]},
            {"id": "step-2a", "name": "Run OCR", "type": "ocr_extract", "config": {"file": "{{ steps.step_1.file.path }}", "language": "auto", "output_format": "text"}, "depends_on": ["step-2"]},
            {"id": "step-2b", "name": "Extract Text from Doc", "type": "file_read", "config": {"file": "{{ steps.step_1.file.path }}", "extract_text": True}, "depends_on": ["step-2"]},
            {"id": "step-3", "name": "AI Classification & Extraction", "type": "ai_analyze", "config": {"model": "claude-sonnet-4-20250514", "prompt": "Analyze this document text and extract structured information:\n\n{{ steps.step_2a.text or steps.step_2b.text }}\n\nReturn JSON:\n{\"document_type\": \"invoice|contract|receipt|letter|report|id_document|other\", \"summary\": \"2-3 sentence summary\", \"key_entities\": {\"names\": [], \"organizations\": [], \"dates\": [], \"amounts\": [], \"addresses\": []}, \"language\": \"...\", \"confidence\": 0.0-1.0}"}, "depends_on": ["step-2a", "step-2b"]},
            {"id": "step-4", "name": "Save to Database", "type": "database_query", "config": {"connection": "{{ credentials.doc_db }}", "query": "INSERT INTO documents (filename, doc_type, summary, entities, full_text, processed_at) VALUES ({{ file.name }}, {{ steps.step_3.document_type }}, {{ steps.step_3.summary }}, {{ steps.step_3.key_entities | json }}, {{ text }}, NOW())"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Move to Processed", "type": "file_move", "config": {"source": "{{ steps.step_1.file.path }}", "destination": "{{ config.processed_dir }}/{{ steps.step_3.document_type }}/"}, "depends_on": ["step-4"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # FINANCE & ACCOUNTING
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-bank-reconciliation",
        "name": "Bank Statement Reconciliation",
        "description": "Download bank statements, parse transactions, match against internal accounting records, flag discrepancies, and generate reconciliation report with unmatched items for manual review.",
        "category": "finance",
        "icon": "🏦",
        "tags": ["bank", "reconciliation", "accounting", "finance", "matching"],
        "difficulty": "advanced",
        "estimated_duration": "5-15 min",
        "steps": [
            {"id": "step-1", "name": "Download Bank Statement", "type": "file_read", "config": {"path": "{{ config.bank_statement_path }}", "format": "csv", "parse_options": {"delimiter": ",", "date_format": "%m/%d/%Y", "columns": {"date": 0, "description": 1, "amount": 2, "balance": 3}}}},
            {"id": "step-2", "name": "Fetch Internal Records", "type": "database_query", "config": {"connection": "{{ credentials.accounting_db }}", "query": "SELECT id, transaction_date, description, amount, reference, category, reconciled FROM ledger_entries WHERE transaction_date BETWEEN '{{ config.start_date }}' AND '{{ config.end_date }}' AND reconciled = false ORDER BY transaction_date"}},
            {"id": "step-3", "name": "Match Transactions", "type": "custom_script", "config": {"language": "python", "script": "from datetime import datetime, timedelta\nbank = steps.step_1.rows\nledger = steps.step_2.rows\nmatched = []\nunmatched_bank = []\nunmatched_ledger = list(ledger)\nfor bt in bank:\n    best_match = None\n    best_score = 0\n    for lt in unmatched_ledger:\n        score = 0\n        if abs(float(bt['amount']) - float(lt['amount'])) < 0.01: score += 50\n        if bt['description'].lower() in lt['description'].lower() or lt['reference'] in bt['description']: score += 30\n        date_diff = abs((datetime.strptime(bt['date'], '%m/%d/%Y') - datetime.strptime(str(lt['transaction_date']), '%Y-%m-%d')).days)\n        if date_diff <= 1: score += 20\n        elif date_diff <= 3: score += 10\n        if score > best_score and score >= 50:\n            best_score = score\n            best_match = lt\n    if best_match:\n        matched.append({'bank': bt, 'ledger': best_match, 'confidence': best_score})\n        unmatched_ledger.remove(best_match)\n    else:\n        unmatched_bank.append(bt)\noutput = {'matched': matched, 'unmatched_bank': unmatched_bank, 'unmatched_ledger': unmatched_ledger, 'stats': {'total_bank': len(bank), 'total_ledger': len(ledger), 'matched': len(matched), 'unmatched_bank': len(unmatched_bank), 'unmatched_ledger': len(unmatched_ledger), 'match_rate': round(len(matched)/max(len(bank),1)*100, 1)}}"}, "depends_on": ["step-1", "step-2"]},
            {"id": "step-4", "name": "Mark Matched as Reconciled", "type": "database_query", "config": {"connection": "{{ credentials.accounting_db }}", "query": "UPDATE ledger_entries SET reconciled = true, reconciled_at = NOW() WHERE id IN ({{ matched_ids }})", "params": {"matched_ids": "{{ [m['ledger']['id'] for m in steps.step_3.matched] }}"}}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Generate Reconciliation Report", "type": "template_render", "config": {"template": "reconciliation_report.html", "data": "{{ steps.step_3 }}"}, "depends_on": ["step-3"]},
            {"id": "step-6", "name": "Email Report", "type": "email_send", "config": {"to": "{{ config.accounting_team }}", "subject": "Bank Reconciliation Report — Match Rate: {{ steps.step_3.stats.match_rate }}%", "body": "Reconciliation complete.\n\nMatched: {{ steps.step_3.stats.matched }}\nUnmatched bank transactions: {{ steps.step_3.stats.unmatched_bank }}\nUnmatched ledger entries: {{ steps.step_3.stats.unmatched_ledger }}\n\nPlease review attached report for unmatched items.", "attachments": ["{{ steps.step_5.file_path }}"]}, "depends_on": ["step-4", "step-5"]},
        ],
    },
    {
        "id": "tpl-expense-processor",
        "name": "Expense Report Processor",
        "description": "Collect expense receipts from email/folder, OCR and extract amounts/vendors/categories, validate against policy limits, auto-approve within threshold, flag violations, and generate expense report for accounting.",
        "category": "finance",
        "icon": "💳",
        "tags": ["expense", "receipt", "ocr", "policy", "approval", "accounting"],
        "difficulty": "advanced",
        "estimated_duration": "5-20 min",
        "steps": [
            {"id": "step-1", "name": "Collect Receipts", "type": "file_watch", "config": {"directory": "{{ config.receipts_dir }}", "patterns": ["*.pdf", "*.jpg", "*.png"], "recursive": True}},
            {"id": "step-2", "name": "OCR & Extract Data", "type": "loop", "config": {"items": "{{ steps.step_1.files }}", "step": {"type": "ai_analyze", "config": {"model": "claude-sonnet-4-20250514", "input_file": "{{ item.path }}", "prompt": "Extract receipt data as JSON: {\"vendor\": \"\", \"date\": \"YYYY-MM-DD\", \"total\": 0.00, \"currency\": \"USD\", \"tax\": 0.00, \"items\": [{\"description\": \"\", \"amount\": 0.00}], \"payment_method\": \"\", \"category\": \"meals|transport|accommodation|office_supplies|software|other\"}"}}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Validate Against Policy", "type": "custom_script", "config": {"language": "python", "script": "LIMITS = {'meals': 75, 'transport': 200, 'accommodation': 250, 'office_supplies': 100, 'software': 500, 'other': 50}\napproved = []\nflagged = []\nfor i, receipt in enumerate(steps.step_2.results):\n    limit = LIMITS.get(receipt.get('category', 'other'), 50)\n    if receipt['total'] <= limit:\n        approved.append({**receipt, 'status': 'auto_approved', 'file': steps.step_1.files[i]['name']})\n    else:\n        flagged.append({**receipt, 'status': 'needs_review', 'reason': f\"Exceeds {receipt['category']} limit of ${limit}\", 'file': steps.step_1.files[i]['name']})\noutput = {'approved': approved, 'flagged': flagged, 'total_amount': sum(r['total'] for r in approved + flagged)}"}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Save to Accounting System", "type": "database_query", "config": {"connection": "{{ credentials.accounting_db }}", "query": "INSERT INTO expenses (vendor, date, amount, category, status, receipt_file) VALUES {{ bulk_values }}", "bulk_data": "{{ steps.step_3.approved + steps.step_3.flagged }}"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Notify Manager of Flagged", "type": "condition", "config": {"condition": "{{ len(steps.step_3.flagged) > 0 }}", "on_true": "step-6"}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Send Review Request", "type": "email_send", "config": {"to": "{{ config.manager_email }}", "subject": "⚠️ {{ len(steps.step_3.flagged) }} expense(s) require approval", "body": "The following expenses exceed policy limits:\n\n{% for e in steps.step_3.flagged %}• {{ e.vendor }} — ${{ e.total }} ({{ e.category }}) — {{ e.reason }}\n{% endfor %}\n\nTotal amount pending: ${{ sum(e['total'] for e in steps.step_3.flagged) }}"}, "depends_on": ["step-5"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # HR & RECRUITMENT
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-employee-onboarding",
        "name": "Employee Onboarding Automation",
        "description": "Complete onboarding workflow: create accounts (email, Slack, Jira), provision access, send welcome email with resources, schedule orientation meetings, add to payroll, and generate onboarding checklist.",
        "category": "hr",
        "icon": "👋",
        "tags": ["hr", "onboarding", "employee", "accounts", "provisioning"],
        "difficulty": "advanced",
        "estimated_duration": "5-15 min",
        "steps": [
            {"id": "step-1", "name": "Load New Hire Data", "type": "http_request", "config": {"url": "{{ config.hr_api }}/api/new-hires/pending", "method": "GET", "headers": {"Authorization": "Bearer {{ credentials.hr_token }}"}}},
            {"id": "step-2", "name": "Create Email Account", "type": "http_request", "config": {"url": "{{ config.google_admin_api }}/users", "method": "POST", "headers": {"Authorization": "Bearer {{ credentials.google_admin }}"}, "body": {"primaryEmail": "{{ item.first_name|lower }}.{{ item.last_name|lower }}@company.com", "name": {"givenName": "{{ item.first_name }}", "familyName": "{{ item.last_name }}"}, "password": "{{ random_password }}", "changePasswordAtNextLogin": True, "orgUnitPath": "/{{ item.department }}"}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Add to Slack", "type": "http_request", "config": {"url": "https://slack.com/api/admin.users.invite", "method": "POST", "headers": {"Authorization": "Bearer {{ credentials.slack_admin }}"}, "body": {"email": "{{ steps.step_2.primaryEmail }}", "channel_ids": "{{ config.default_channels }}", "team_id": "{{ config.slack_team }}"}}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Create Jira Account", "type": "http_request", "config": {"url": "{{ config.jira_url }}/rest/api/3/user", "method": "POST", "headers": {"Authorization": "Basic {{ credentials.jira_admin }}"}, "body": {"emailAddress": "{{ steps.step_2.primaryEmail }}", "displayName": "{{ item.first_name }} {{ item.last_name }}"}}, "depends_on": ["step-2"]},
            {"id": "step-5", "name": "Schedule Orientation", "type": "http_request", "config": {"url": "https://www.googleapis.com/calendar/v3/calendars/primary/events", "method": "POST", "headers": {"Authorization": "Bearer {{ credentials.google_calendar }}"}, "body": {"summary": "Welcome Orientation — {{ item.first_name }} {{ item.last_name }}", "start": {"dateTime": "{{ item.start_date }}T09:00:00"}, "end": {"dateTime": "{{ item.start_date }}T10:00:00"}, "attendees": [{"email": "{{ steps.step_2.primaryEmail }}"}, {"email": "{{ item.manager_email }}"}, {"email": "{{ config.hr_contact }}"}]}}, "depends_on": ["step-2"]},
            {"id": "step-6", "name": "Send Welcome Email", "type": "email_send", "config": {"to": "{{ item.personal_email }}", "cc": "{{ item.manager_email }}", "subject": "Welcome to {{ config.company_name }}! 🎉", "body": "Dear {{ item.first_name }},\n\nWelcome to {{ config.company_name }}! We're excited to have you join as {{ item.position }} in the {{ item.department }} team.\n\nYour work email: {{ steps.step_2.primaryEmail }}\nStart date: {{ item.start_date }}\nManager: {{ item.manager_name }}\n\nOrientation has been scheduled for your first day at 9 AM.\n\nPlease complete the onboarding checklist: {{ config.onboarding_url }}\n\nBest regards,\nHR Team"}, "depends_on": ["step-5"]},
            {"id": "step-7", "name": "Update HR System", "type": "http_request", "config": {"url": "{{ config.hr_api }}/api/employees/{{ item.id }}/onboard", "method": "PATCH", "headers": {"Authorization": "Bearer {{ credentials.hr_token }}"}, "body": {"status": "onboarded", "email": "{{ steps.step_2.primaryEmail }}", "onboarded_at": "{{ now }}"}}, "depends_on": ["step-6"]},
        ],
    },
    {
        "id": "tpl-resume-screener",
        "name": "AI Resume Screener & Ranker",
        "description": "Process incoming job applications: parse resumes (PDF/DOCX), extract skills/experience with AI, score against job requirements, rank candidates, and create shortlist with detailed reports for hiring managers.",
        "category": "hr",
        "icon": "📋",
        "tags": ["hr", "resume", "screening", "ai", "recruitment", "hiring"],
        "difficulty": "advanced",
        "estimated_duration": "2-5 min per resume",
        "steps": [
            {"id": "step-1", "name": "Load Job Requirements", "type": "custom_script", "config": {"language": "python", "script": "output = config.get('job_requirements', {\n  'title': 'Senior Python Developer',\n  'required_skills': ['Python', 'FastAPI', 'PostgreSQL', 'Docker'],\n  'preferred_skills': ['Kubernetes', 'AWS', 'React', 'TypeScript'],\n  'min_experience_years': 5,\n  'education': 'Bachelor in CS or equivalent',\n  'languages': ['English']\n})"}},
            {"id": "step-2", "name": "Scan Resumes Folder", "type": "file_watch", "config": {"directory": "{{ config.resumes_dir }}", "patterns": ["*.pdf", "*.docx"]}},
            {"id": "step-3", "name": "AI Parse & Score Each Resume", "type": "loop", "config": {"items": "{{ steps.step_2.files }}", "step": {"type": "ai_analyze", "config": {"model": "claude-sonnet-4-20250514", "input_file": "{{ item.path }}", "prompt": "Parse this resume and score against these requirements: {{ steps.step_1 | json }}\n\nReturn JSON:\n{\"name\": \"\", \"email\": \"\", \"phone\": \"\", \"current_role\": \"\", \"years_experience\": 0, \"skills\": [], \"education\": \"\", \"languages\": [], \"score\": 0-100, \"matching_required\": [], \"missing_required\": [], \"matching_preferred\": [], \"summary\": \"2-3 sentences\", \"strengths\": [], \"concerns\": [], \"recommendation\": \"strong_yes|yes|maybe|no\"}"}}}, "depends_on": ["step-1", "step-2"]},
            {"id": "step-4", "name": "Rank & Shortlist", "type": "custom_script", "config": {"language": "python", "script": "candidates = sorted(steps.step_3.results, key=lambda x: x.get('score', 0), reverse=True)\nshortlist = [c for c in candidates if c.get('recommendation') in ('strong_yes', 'yes')]\noutput = {'all_candidates': candidates, 'shortlist': shortlist, 'total': len(candidates), 'shortlisted': len(shortlist)}"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Email Shortlist to Hiring Manager", "type": "email_send", "config": {"to": "{{ config.hiring_manager_email }}", "subject": "🎯 {{ steps.step_4.shortlisted }}/{{ steps.step_4.total }} candidates shortlisted for {{ steps.step_1.title }}", "body": "Resume screening complete for {{ steps.step_1.title }}.\n\nTotal applications: {{ steps.step_4.total }}\nShortlisted: {{ steps.step_4.shortlisted }}\n\nTop candidates:\n{% for c in steps.step_4.shortlist[:10] %}{{ loop.index }}. {{ c.name }} — Score: {{ c.score }}/100 — {{ c.current_role }} ({{ c.years_experience }}yr) — {{ c.recommendation }}\n   Strengths: {{ ', '.join(c.strengths[:3]) }}\n{% endfor %}"}, "depends_on": ["step-4"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # E-COMMERCE
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-order-fulfillment",
        "name": "Order Fulfillment Pipeline",
        "description": "End-to-end order processing: validate order data, check inventory, reserve stock, generate shipping label, update tracking, notify customer, and sync with accounting system.",
        "category": "e-commerce",
        "icon": "📦",
        "tags": ["order", "fulfillment", "shipping", "inventory", "e-commerce"],
        "difficulty": "advanced",
        "estimated_duration": "2-5 min per order",
        "steps": [
            {"id": "step-1", "name": "Fetch New Orders", "type": "http_request", "config": {"url": "{{ config.shop_api }}/orders?status=pending", "method": "GET", "headers": {"Authorization": "Bearer {{ credentials.shop_token }}"}}},
            {"id": "step-2", "name": "Process Each Order", "type": "loop", "config": {"items": "{{ steps.step_1.data.orders }}", "step": {"type": "custom_script", "config": {"language": "python", "script": "# Validate order\norder = item\nerrors = []\nif not order.get('shipping_address'): errors.append('Missing shipping address')\nif not order.get('items'): errors.append('No items')\nfor oi in order.get('items', []):\n    if oi.get('quantity', 0) <= 0: errors.append(f\"Invalid qty for {oi['sku']}\")\noutput = {'order_id': order['id'], 'valid': len(errors) == 0, 'errors': errors, 'items': order.get('items', [])}"}}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Check & Reserve Inventory", "type": "loop", "config": {"items": "{{ steps.step_2.results | selectattr('valid') }}", "step": {"type": "http_request", "config": {"url": "{{ config.inventory_api }}/reserve", "method": "POST", "body": {"order_id": "{{ item.order_id }}", "items": "{{ item.items }}"}}}}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Generate Shipping Labels", "type": "loop", "config": {"items": "{{ steps.step_3.results | selectattr('success') }}", "step": {"type": "http_request", "config": {"url": "{{ config.shipping_api }}/labels", "method": "POST", "headers": {"Authorization": "Bearer {{ credentials.shipping_token }}"}, "body": {"order_id": "{{ item.order_id }}", "carrier": "{{ config.default_carrier }}"}}}}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Update Order Status & Notify", "type": "loop", "config": {"items": "{{ steps.step_4.results }}", "step": {"type": "http_request", "config": {"url": "{{ config.shop_api }}/orders/{{ item.order_id }}", "method": "PATCH", "body": {"status": "shipped", "tracking_number": "{{ item.tracking_number }}", "carrier": "{{ item.carrier }}"}}}}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Send Shipping Notification", "type": "loop", "config": {"items": "{{ steps.step_4.results }}", "step": {"type": "email_send", "config": {"to": "{{ item.customer_email }}", "subject": "Your order #{{ item.order_id }} has shipped! 📦", "body": "Great news! Your order has been shipped.\n\nTracking: {{ item.tracking_number }}\nCarrier: {{ item.carrier }}\nEstimated delivery: {{ item.estimated_delivery }}\n\nTrack here: {{ config.tracking_url }}/{{ item.tracking_number }}"}}}, "depends_on": ["step-5"]},
        ],
    },
    {
        "id": "tpl-inventory-sync",
        "name": "Multi-Channel Inventory Sync",
        "description": "Synchronize inventory levels across multiple sales channels (Shopify, Amazon, eBay, WooCommerce), prevent overselling, and alert on low stock items.",
        "category": "e-commerce",
        "icon": "🔄",
        "tags": ["inventory", "sync", "multichannel", "shopify", "amazon", "e-commerce"],
        "difficulty": "advanced",
        "estimated_duration": "3-10 min",
        "steps": [
            {"id": "step-1", "name": "Fetch Master Inventory", "type": "database_query", "config": {"connection": "{{ credentials.inventory_db }}", "query": "SELECT sku, product_name, quantity, reorder_point, warehouse FROM inventory WHERE active = true"}},
            {"id": "step-2", "name": "Fetch Channel Stock", "type": "custom_script", "config": {"language": "python", "script": "channels = config.get('channels', ['shopify', 'amazon', 'ebay'])\noutput = {'channels': channels, 'master': steps.step_1.rows}"}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Sync to Each Channel", "type": "loop", "config": {"items": "{{ steps.step_2.channels }}", "step": {"type": "http_request", "config": {"url": "{{ config[item + '_api'] }}/inventory/bulk-update", "method": "PUT", "headers": {"Authorization": "Bearer {{ credentials[item + '_token'] }}"}, "body": {"updates": "{{ steps.step_2.master }}"}}}}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Check Low Stock", "type": "custom_script", "config": {"language": "python", "script": "low_stock = [item for item in steps.step_1.rows if item['quantity'] <= item['reorder_point']]\nout_of_stock = [item for item in steps.step_1.rows if item['quantity'] == 0]\noutput = {'low_stock': low_stock, 'out_of_stock': out_of_stock}"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Alert on Low Stock", "type": "condition", "config": {"condition": "{{ len(steps.step_4.low_stock) > 0 }}", "on_true": "step-6"}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Send Low Stock Alert", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "⚠️ *Low Stock Alert*\n\nOut of stock ({{ len(steps.step_4.out_of_stock) }}):\n{% for i in steps.step_4.out_of_stock %}• {{ i.product_name }} ({{ i.sku }})\n{% endfor %}\n\nLow stock ({{ len(steps.step_4.low_stock) }}):\n{% for i in steps.step_4.low_stock %}• {{ i.product_name }}: {{ i.quantity }} left (reorder at {{ i.reorder_point }})\n{% endfor %}"}}, "depends_on": ["step-5"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # DEVOPS & IT
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-db-backup",
        "name": "Automated Database Backup & Verify",
        "description": "Perform full database backup, compress, encrypt, upload to cloud storage (S3/GCS), verify backup integrity, rotate old backups (keep last 30 days), and report status.",
        "category": "devops",
        "icon": "💾",
        "tags": ["backup", "database", "s3", "encryption", "devops", "disaster-recovery"],
        "difficulty": "intermediate",
        "estimated_duration": "5-30 min",
        "steps": [
            {"id": "step-1", "name": "Create DB Dump", "type": "custom_script", "config": {"language": "bash", "script": "pg_dump -h {{ credentials.db_host }} -U {{ credentials.db_user }} -d {{ config.db_name }} -F c -f /tmp/backup_$(date +%Y%m%d_%H%M%S).dump", "timeout": 600}},
            {"id": "step-2", "name": "Compress & Encrypt", "type": "custom_script", "config": {"language": "bash", "script": "gzip /tmp/backup_*.dump && gpg --symmetric --cipher-algo AES256 --passphrase '{{ credentials.backup_passphrase }}' /tmp/backup_*.dump.gz"}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Upload to S3", "type": "custom_script", "config": {"language": "bash", "script": "aws s3 cp /tmp/backup_*.dump.gz.gpg s3://{{ config.backup_bucket }}/db-backups/$(date +%Y/%m)/ --storage-class STANDARD_IA"}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Verify Upload", "type": "custom_script", "config": {"language": "bash", "script": "aws s3 ls s3://{{ config.backup_bucket }}/db-backups/$(date +%Y/%m)/ --human-readable | tail -1"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Rotate Old Backups", "type": "custom_script", "config": {"language": "bash", "script": "aws s3 ls s3://{{ config.backup_bucket }}/db-backups/ --recursive | awk '{print $4}' | while read key; do\n  date=$(echo $key | grep -oP '\\d{8}')\n  if [ $(( ($(date +%s) - $(date -d $date +%s)) / 86400 )) -gt 30 ]; then\n    aws s3 rm s3://{{ config.backup_bucket }}/$key\n  fi\ndone"}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Report Status", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "✅ *DB Backup Complete*\n• Database: {{ config.db_name }}\n• Size: {{ steps.step_4.output }}\n• Location: s3://{{ config.backup_bucket }}/db-backups/\n• Encrypted: AES-256"}}, "depends_on": ["step-5"]},
        ],
    },
    {
        "id": "tpl-log-analyzer",
        "name": "Log Analysis & Anomaly Detector",
        "description": "Collect application logs, parse error patterns, detect anomalies (spike in errors, new error types), correlate with deployments, and create incident reports automatically.",
        "category": "devops",
        "icon": "🔎",
        "tags": ["logs", "analysis", "anomaly", "incident", "devops", "monitoring"],
        "difficulty": "advanced",
        "estimated_duration": "2-10 min",
        "steps": [
            {"id": "step-1", "name": "Fetch Recent Logs", "type": "http_request", "config": {"url": "{{ config.log_api }}/api/logs", "method": "POST", "body": {"query": "level:error OR level:critical", "time_range": "last_1h", "limit": 1000}, "headers": {"Authorization": "Bearer {{ credentials.log_token }}"}}},
            {"id": "step-2", "name": "Fetch Baseline (24h avg)", "type": "http_request", "config": {"url": "{{ config.log_api }}/api/stats", "method": "POST", "body": {"query": "level:error OR level:critical", "time_range": "last_24h", "granularity": "1h"}, "headers": {"Authorization": "Bearer {{ credentials.log_token }}"}}, "depends_on": []},
            {"id": "step-3", "name": "Analyze Anomalies", "type": "custom_script", "config": {"language": "python", "script": "from collections import Counter\nlogs = steps.step_1.data.get('logs', [])\nbaseline = steps.step_2.data.get('stats', {})\navg_errors_per_hour = baseline.get('avg_count', 10)\ncurrent_count = len(logs)\nis_spike = current_count > avg_errors_per_hour * 3\nerror_types = Counter(l.get('message', '')[:80] for l in logs)\ntop_errors = error_types.most_common(10)\nnew_errors = [e for e, c in top_errors if e not in baseline.get('known_patterns', [])]\noutput = {'is_spike': is_spike, 'current_count': current_count, 'baseline_avg': avg_errors_per_hour, 'spike_factor': round(current_count / max(avg_errors_per_hour, 1), 1), 'top_errors': top_errors, 'new_error_types': new_errors, 'severity': 'critical' if is_spike and current_count > avg_errors_per_hour * 10 else 'warning' if is_spike else 'info'}"}, "depends_on": ["step-1", "step-2"]},
            {"id": "step-4", "name": "Alert if Anomaly", "type": "condition", "config": {"condition": "{{ steps.step_3.is_spike }}", "on_true": "step-5"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Create Incident", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "🚨 *Log Anomaly Detected* ({{ steps.step_3.severity | upper }})\n\nErrors in last hour: {{ steps.step_3.current_count }} ({{ steps.step_3.spike_factor }}x baseline)\n\nTop errors:\n{% for e, c in steps.step_3.top_errors[:5] %}• ({{ c }}x) {{ e }}\n{% endfor %}\n{% if steps.step_3.new_error_types %}⚠️ *New error patterns*: {{ steps.step_3.new_error_types | join(', ') }}{% endif %}"}}, "depends_on": ["step-4"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # DATA PIPELINE / ETL
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-data-pipeline",
        "name": "Data Pipeline (ETL)",
        "description": "Fetch data from an API, transform it, and send results to another API.",
        "category": "data-extraction",
        "icon": "🔄",
        "tags": ["etl", "pipeline", "api", "data"],
        "difficulty": "intermediate",
        "estimated_duration": "2-5 min",
        "steps": [
            {"id": "step-1", "name": "Fetch Source Data", "type": "http_request", "config": {"url": "https://jsonplaceholder.typicode.com/posts", "method": "GET"}},
            {"id": "step-2", "name": "Transform", "type": "data_transform", "config": {"script": "output = [{'id': p['id'], 'title': p['title']} for p in input_data[:10]]"}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Send to Destination", "type": "http_request", "config": {"url": "https://httpbin.org/post", "method": "POST", "body_type": "json"}, "depends_on": ["step-2"]},
        ],
    },
    {
        "id": "tpl-csv-etl-pipeline",
        "name": "CSV Data Cleaning & ETL Pipeline",
        "description": "Load CSV files, clean data (remove duplicates, fix formats, handle missing values), validate against schema, transform columns, and load into database with full audit trail.",
        "category": "data-extraction",
        "icon": "🧹",
        "tags": ["csv", "etl", "cleaning", "validation", "database", "data-quality"],
        "difficulty": "intermediate",
        "estimated_duration": "3-15 min",
        "steps": [
            {"id": "step-1", "name": "Load CSV Files", "type": "file_read", "config": {"path": "{{ config.input_dir }}/*.csv", "format": "csv", "encoding": "auto"}},
            {"id": "step-2", "name": "Clean & Validate", "type": "custom_script", "config": {"language": "python", "script": "import re\nfrom datetime import datetime\nrows = steps.step_1.rows\n# Remove duplicates\nseen = set()\nclean = []\nerrors = []\nfor i, row in enumerate(rows):\n    key = tuple(sorted(row.items()))\n    if key in seen: continue\n    seen.add(key)\n    # Validate email\n    if 'email' in row:\n        if not re.match(r'^[^@]+@[^@]+\\.[^@]+$', row.get('email', '')):\n            errors.append(f\"Row {i}: invalid email '{row.get('email', '')}'\"); continue\n    # Clean phone\n    if 'phone' in row:\n        row['phone'] = re.sub(r'[^\\d+]', '', row.get('phone', ''))\n    # Parse dates\n    for k, v in row.items():\n        if 'date' in k.lower() and v:\n            for fmt in ('%m/%d/%Y', '%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):\n                try: row[k] = datetime.strptime(v, fmt).strftime('%Y-%m-%d'); break\n                except: pass\n    # Fill defaults\n    for k, v in row.items():\n        if v is None or v == '': row[k] = config.get('defaults', {}).get(k, '')\n    clean.append(row)\noutput = {'clean_rows': clean, 'errors': errors, 'original_count': len(rows), 'clean_count': len(clean), 'duplicates_removed': len(rows) - len(seen)}"}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Load into Database", "type": "database_query", "config": {"connection": "{{ credentials.target_db }}", "query": "INSERT INTO {{ config.target_table }} ({{ columns }}) VALUES {{ bulk_values }} ON CONFLICT ({{ config.unique_key }}) DO UPDATE SET {{ update_set }}", "bulk_data": "{{ steps.step_2.clean_rows }}"}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Generate Report", "type": "custom_script", "config": {"language": "python", "script": "output = f\"ETL Complete:\\n- Original rows: {steps.step_2.original_count}\\n- Duplicates removed: {steps.step_2.duplicates_removed}\\n- Clean rows loaded: {steps.step_2.clean_count}\\n- Validation errors: {len(steps.step_2.errors)}\\n\\nErrors:\\n\" + '\\n'.join(steps.step_2.errors[:20])"}, "depends_on": ["step-3"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # CUSTOMER SUPPORT
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-ticket-sla-monitor",
        "name": "Support Ticket SLA Monitor",
        "description": "Monitor open support tickets, check SLA breaches (first response time, resolution time), escalate overdue tickets, send daily SLA compliance report to management.",
        "category": "customer-support",
        "icon": "⏱️",
        "tags": ["sla", "support", "tickets", "escalation", "monitoring"],
        "difficulty": "intermediate",
        "estimated_duration": "2-5 min",
        "steps": [
            {"id": "step-1", "name": "Fetch Open Tickets", "type": "http_request", "config": {"url": "{{ config.helpdesk_api }}/tickets?status=open,pending", "method": "GET", "headers": {"Authorization": "Bearer {{ credentials.helpdesk_token }}"}}},
            {"id": "step-2", "name": "Check SLA Compliance", "type": "custom_script", "config": {"language": "python", "script": "from datetime import datetime, timedelta\nSLA = {'critical': {'first_response': 1, 'resolution': 4}, 'high': {'first_response': 4, 'resolution': 24}, 'medium': {'first_response': 8, 'resolution': 48}, 'low': {'first_response': 24, 'resolution': 120}}\nnow = datetime.utcnow()\nbreaches = []\nat_risk = []\non_track = []\nfor t in steps.step_1.data.get('tickets', []):\n    priority = t.get('priority', 'medium')\n    sla = SLA.get(priority, SLA['medium'])\n    created = datetime.fromisoformat(t['created_at'].replace('Z', '+00:00').replace('+00:00', ''))\n    hours_open = (now - created).total_seconds() / 3600\n    first_resp = t.get('first_response_at')\n    if not first_resp and hours_open > sla['first_response']:\n        breaches.append({**t, 'breach_type': 'first_response', 'hours_overdue': round(hours_open - sla['first_response'], 1)})\n    elif hours_open > sla['resolution']:\n        breaches.append({**t, 'breach_type': 'resolution', 'hours_overdue': round(hours_open - sla['resolution'], 1)})\n    elif hours_open > sla['resolution'] * 0.8:\n        at_risk.append({**t, 'hours_remaining': round(sla['resolution'] - hours_open, 1)})\n    else:\n        on_track.append(t)\noutput = {'breaches': breaches, 'at_risk': at_risk, 'on_track': on_track, 'compliance_rate': round(len(on_track) / max(len(steps.step_1.data.get('tickets', [])), 1) * 100, 1)}"}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Escalate Breaches", "type": "condition", "config": {"condition": "{{ len(steps.step_2.breaches) > 0 }}", "on_true": "step-4"}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Send Escalation Alert", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "🚨 *SLA Breach Alert* — {{ len(steps.step_2.breaches) }} ticket(s) breached\n\nCompliance Rate: {{ steps.step_2.compliance_rate }}%\n\n{% for b in steps.step_2.breaches[:10] %}• #{{ b.id }} [{{ b.priority | upper }}] {{ b.subject }} — {{ b.breach_type }} breach ({{ b.hours_overdue }}h overdue)\n{% endfor %}\n\n⚠️ At risk: {{ len(steps.step_2.at_risk) }} tickets"}}, "depends_on": ["step-3"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # MARKETING
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-social-media-scheduler",
        "name": "Social Media Content Scheduler",
        "description": "Load content calendar from spreadsheet, generate AI-optimized posts for each platform (Twitter/X, LinkedIn, Facebook), schedule posts via APIs, and track engagement metrics.",
        "category": "marketing",
        "icon": "📱",
        "tags": ["social-media", "scheduling", "marketing", "ai", "content"],
        "difficulty": "intermediate",
        "estimated_duration": "3-10 min",
        "steps": [
            {"id": "step-1", "name": "Load Content Calendar", "type": "file_read", "config": {"path": "{{ config.calendar_file }}", "format": "csv", "columns": ["date", "topic", "key_message", "target_audience", "platforms", "image_url"]}},
            {"id": "step-2", "name": "Generate Platform Posts", "type": "loop", "config": {"items": "{{ steps.step_1.rows }}", "filter": "{{ item.date == today }}", "step": {"type": "ai_analyze", "config": {"model": "claude-sonnet-4-20250514", "prompt": "Create social media posts for this content:\nTopic: {{ item.topic }}\nKey message: {{ item.key_message }}\nAudience: {{ item.target_audience }}\nPlatforms: {{ item.platforms }}\n\nReturn JSON with optimized posts for each platform:\n{\"twitter\": {\"text\": \"...(max 280 chars with hashtags)\"}, \"linkedin\": {\"text\": \"...(professional, 1-3 paragraphs)\"}, \"facebook\": {\"text\": \"...(engaging, with emoji)\"}}"}}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Post to Twitter/X", "type": "loop", "config": {"items": "{{ steps.step_2.results }}", "filter": "{{ 'twitter' in item.platforms }}", "step": {"type": "http_request", "config": {"url": "https://api.twitter.com/2/tweets", "method": "POST", "headers": {"Authorization": "Bearer {{ credentials.twitter_token }}"}, "body": {"text": "{{ item.twitter.text }}"}}}}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Post to LinkedIn", "type": "loop", "config": {"items": "{{ steps.step_2.results }}", "filter": "{{ 'linkedin' in item.platforms }}", "step": {"type": "http_request", "config": {"url": "https://api.linkedin.com/v2/ugcPosts", "method": "POST", "headers": {"Authorization": "Bearer {{ credentials.linkedin_token }}"}, "body": {"author": "{{ config.linkedin_author }}", "lifecycleState": "PUBLISHED", "specificContent": {"com.linkedin.ugc.ShareContent": {"shareCommentary": {"text": "{{ item.linkedin.text }}"}}}}}}},"depends_on": ["step-2"]},
            {"id": "step-5", "name": "Log Results", "type": "custom_script", "config": {"language": "python", "script": "output = {'posts_created': len(steps.step_2.results), 'twitter_posted': len(steps.step_3.results), 'linkedin_posted': len(steps.step_4.results)}"}, "depends_on": ["step-3", "step-4"]},
        ],
    },
    {
        "id": "tpl-seo-audit",
        "name": "SEO Audit & Reporting",
        "description": "Crawl website pages, check meta tags, headers, broken links, page speed, mobile-friendliness, generate comprehensive SEO audit report with actionable recommendations.",
        "category": "marketing",
        "icon": "🔍",
        "tags": ["seo", "audit", "crawl", "marketing", "reporting", "optimization"],
        "difficulty": "advanced",
        "estimated_duration": "10-30 min",
        "steps": [
            {"id": "step-1", "name": "Crawl Website", "type": "web_scrape", "config": {"url": "{{ config.site_url }}", "crawl": True, "max_pages": 100, "selectors": [{"name": "title", "selector": "title", "extract": "text"}, {"name": "meta_desc", "selector": "meta[name=description]", "extract": "attribute", "attribute": "content"}, {"name": "h1", "selector": "h1", "extract": "text"}, {"name": "h2s", "selector": "h2", "extract": "text", "multiple": True}, {"name": "images_no_alt", "selector": "img:not([alt])", "extract": "attribute", "attribute": "src", "multiple": True}, {"name": "links", "selector": "a[href]", "extract": "attribute", "attribute": "href", "multiple": True}, {"name": "canonical", "selector": "link[rel=canonical]", "extract": "attribute", "attribute": "href"}]}},
            {"id": "step-2", "name": "Check Broken Links", "type": "loop", "config": {"items": "{{ steps.step_1.all_links | unique }}", "max_parallel": 10, "step": {"type": "http_request", "config": {"url": "{{ item }}", "method": "HEAD", "timeout": 10, "follow_redirects": False}}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Analyze SEO Issues", "type": "custom_script", "config": {"language": "python", "script": "issues = []\nfor page in steps.step_1.pages:\n    if not page.get('title') or len(page['title']) > 60: issues.append({'page': page['url'], 'issue': 'Title missing or too long', 'severity': 'high'})\n    if not page.get('meta_desc') or len(page['meta_desc']) > 160: issues.append({'page': page['url'], 'issue': 'Meta description missing or too long', 'severity': 'medium'})\n    if not page.get('h1'): issues.append({'page': page['url'], 'issue': 'Missing H1 tag', 'severity': 'high'})\n    if page.get('images_no_alt'): issues.append({'page': page['url'], 'issue': f\"{len(page['images_no_alt'])} images missing alt text\", 'severity': 'medium'})\nbroken = [{'url': steps.step_2.results[i]['url'], 'status': steps.step_2.results[i].get('status_code', 0)} for i in range(len(steps.step_2.results)) if steps.step_2.results[i].get('status_code', 0) >= 400]\nfor b in broken: issues.append({'page': b['url'], 'issue': f\"Broken link (HTTP {b['status']})\", 'severity': 'high'})\noutput = {'issues': issues, 'total_pages': len(steps.step_1.pages), 'total_issues': len(issues), 'broken_links': len(broken), 'score': max(0, 100 - len(issues) * 2)}"}, "depends_on": ["step-1", "step-2"]},
            {"id": "step-4", "name": "Generate SEO Report", "type": "template_render", "config": {"template": "seo_report.html", "data": "{{ steps.step_3 }}"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Email Report", "type": "email_send", "config": {"to": "{{ config.marketing_team }}", "subject": "SEO Audit Report — Score: {{ steps.step_3.score }}/100 — {{ steps.step_3.total_issues }} issues found", "body": "SEO audit complete for {{ config.site_url }}.\n\nPages crawled: {{ steps.step_3.total_pages }}\nIssues found: {{ steps.step_3.total_issues }}\nBroken links: {{ steps.step_3.broken_links }}\nSEO Score: {{ steps.step_3.score }}/100", "attachments": ["{{ steps.step_4.file_path }}"]}, "depends_on": ["step-4"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # COMPLIANCE & LEGAL
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-gdpr-data-request",
        "name": "GDPR Data Subject Request Handler",
        "description": "Process GDPR/CCPA data subject requests: collect all user data from every system (DB, CRM, email, logs), compile into a portable format, generate response letter, and track request completion within legal deadlines.",
        "category": "compliance",
        "icon": "🛡️",
        "tags": ["gdpr", "ccpa", "privacy", "compliance", "data-request", "legal"],
        "difficulty": "advanced",
        "estimated_duration": "10-30 min",
        "steps": [
            {"id": "step-1", "name": "Load Request Details", "type": "custom_script", "config": {"language": "python", "script": "request = config.get('request', {'user_email': 'user@example.com', 'request_type': 'access', 'submitted_at': '2024-01-15'})\nfrom datetime import datetime, timedelta\ndeadline = datetime.fromisoformat(request['submitted_at']) + timedelta(days=30)\noutput = {**request, 'deadline': deadline.isoformat(), 'days_remaining': (deadline - datetime.utcnow()).days}"}},
            {"id": "step-2", "name": "Collect from Main DB", "type": "database_query", "config": {"connection": "{{ credentials.main_db }}", "query": "SELECT * FROM users WHERE email = '{{ steps.step_1.user_email }}'; SELECT * FROM orders WHERE user_email = '{{ steps.step_1.user_email }}'; SELECT * FROM support_tickets WHERE email = '{{ steps.step_1.user_email }}'"}},
            {"id": "step-3", "name": "Collect from CRM", "type": "http_request", "config": {"url": "{{ config.crm_api }}/contacts/search", "method": "POST", "body": {"email": "{{ steps.step_1.user_email }}"}, "headers": {"Authorization": "Bearer {{ credentials.crm_token }}"}}, "depends_on": []},
            {"id": "step-4", "name": "Collect from Analytics", "type": "http_request", "config": {"url": "{{ config.analytics_api }}/user-data", "method": "GET", "params": {"email": "{{ steps.step_1.user_email }}"}, "headers": {"Authorization": "Bearer {{ credentials.analytics_token }}"}}, "depends_on": []},
            {"id": "step-5", "name": "Compile Data Package", "type": "custom_script", "config": {"language": "python", "script": "import json\npackage = {\n  'subject': steps.step_1.user_email,\n  'request_type': steps.step_1.request_type,\n  'generated_at': datetime.utcnow().isoformat(),\n  'data_sources': {\n    'account': steps.step_2.rows[0] if steps.step_2.rows else {},\n    'orders': steps.step_2.rows[1] if len(steps.step_2.rows) > 1 else [],\n    'support_tickets': steps.step_2.rows[2] if len(steps.step_2.rows) > 2 else [],\n    'crm': steps.step_3.data if hasattr(steps.step_3, 'data') else {},\n    'analytics': steps.step_4.data if hasattr(steps.step_4, 'data') else {}\n  }\n}\noutput = package"}, "depends_on": ["step-2", "step-3", "step-4"]},
            {"id": "step-6", "name": "Generate Response", "type": "file_write", "config": {"path": "/output/gdpr/{{ steps.step_1.user_email }}_data_export.json", "content": "{{ steps.step_5 | json_pretty }}"}, "depends_on": ["step-5"]},
            {"id": "step-7", "name": "Send to Data Subject", "type": "email_send", "config": {"to": "{{ steps.step_1.user_email }}", "subject": "Your Data Access Request — Complete", "body": "Dear User,\n\nIn response to your data access request submitted on {{ steps.step_1.submitted_at }}, please find attached all personal data we hold about you.\n\nThis includes data from: account records, order history, support tickets, CRM records, and analytics.\n\nIf you have questions, please contact privacy@{{ config.company_domain }}.\n\nBest regards,\nData Protection Team", "attachments": ["{{ steps.step_6.file_path }}"]}, "depends_on": ["step-6"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # LEGACY / SIMPLE
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-screenshot-monitor",
        "name": "Visual Regression Monitor",
        "description": "Take periodic screenshots of a page for visual change detection.",
        "category": "monitoring",
        "icon": "📸",
        "tags": ["screenshot", "monitoring", "visual", "regression"],
        "difficulty": "beginner",
        "estimated_duration": "1-2 min",
        "steps": [
            {"id": "step-1", "name": "Capture Screenshot", "type": "screenshot", "config": {"url": "https://example.com", "full_page": True, "format": "png"}},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # SALES & CRM
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-lead-enrichment",
        "name": "Lead Enrichment & Scoring Pipeline",
        "description": "Enrich new leads from CRM with company data (LinkedIn, Clearbit, etc.), score based on ICP match, auto-assign to sales reps by territory, and create follow-up tasks.",
        "category": "sales",
        "icon": "🎯",
        "tags": ["lead", "enrichment", "scoring", "crm", "sales", "prospecting"],
        "difficulty": "advanced",
        "estimated_duration": "2-5 min per lead",
        "steps": [
            {"id": "step-1", "name": "Fetch New Leads", "type": "http_request", "config": {"url": "{{ config.crm_api }}/leads?status=new&limit=50", "method": "GET", "headers": {"Authorization": "Bearer {{ credentials.crm_token }}"}}},
            {"id": "step-2", "name": "Enrich Each Lead", "type": "loop", "config": {"items": "{{ steps.step_1.data.leads }}", "max_parallel": 5, "step": {"type": "http_request", "config": {"url": "https://api.clearbit.com/v2/combined/find", "method": "GET", "params": {"email": "{{ item.email }}"}, "headers": {"Authorization": "Bearer {{ credentials.clearbit_key }}"}}}}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Score & Assign", "type": "custom_script", "config": {"language": "python", "script": "ICP = config.get('icp', {'min_employees': 50, 'target_industries': ['technology', 'finance', 'healthcare'], 'target_countries': ['US', 'UK', 'DE']})\nTERRITORY = config.get('territories', {'US': 'rep-john', 'UK': 'rep-sarah', 'DE': 'rep-hans', 'default': 'rep-mike'})\nscored = []\nfor i, lead in enumerate(steps.step_1.data.leads):\n    enriched = steps.step_2.results[i] if i < len(steps.step_2.results) else {}\n    company = enriched.get('company', {})\n    score = 0\n    if company.get('metrics', {}).get('employees', 0) >= ICP['min_employees']: score += 30\n    if company.get('category', {}).get('industry', '').lower() in ICP['target_industries']: score += 30\n    if company.get('geo', {}).get('country', '') in ICP['target_countries']: score += 20\n    if lead.get('email', '').split('@')[-1] not in ('gmail.com', 'yahoo.com', 'hotmail.com'): score += 10\n    if enriched.get('person', {}).get('employment', {}).get('seniority', '') in ('executive', 'director', 'manager'): score += 10\n    country = company.get('geo', {}).get('country', 'default')\n    rep = TERRITORY.get(country, TERRITORY['default'])\n    scored.append({**lead, 'score': score, 'assigned_to': rep, 'company_data': company, 'tier': 'hot' if score >= 70 else 'warm' if score >= 40 else 'cold'})\noutput = sorted(scored, key=lambda x: x['score'], reverse=True)"}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Update CRM", "type": "loop", "config": {"items": "{{ steps.step_3 }}", "step": {"type": "http_request", "config": {"url": "{{ config.crm_api }}/leads/{{ item.id }}", "method": "PATCH", "body": {"score": "{{ item.score }}", "tier": "{{ item.tier }}", "assigned_to": "{{ item.assigned_to }}", "company_size": "{{ item.company_data.metrics.employees }}", "industry": "{{ item.company_data.category.industry }}", "enriched": True}}}}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Create Follow-up Tasks for Hot Leads", "type": "loop", "config": {"items": "{{ steps.step_3 | selectattr('tier', 'eq', 'hot') }}", "step": {"type": "http_request", "config": {"url": "{{ config.crm_api }}/tasks", "method": "POST", "body": {"title": "Follow up with {{ item.first_name }} {{ item.last_name }} (Score: {{ item.score }})", "assigned_to": "{{ item.assigned_to }}", "due_date": "{{ today + 1d }}", "priority": "high", "lead_id": "{{ item.id }}"}}}}, "depends_on": ["step-4"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # SCHEDULED MAINTENANCE
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-cleanup-automation",
        "name": "System Cleanup & Maintenance",
        "description": "Automated system maintenance: clean temp files, purge old logs (>90 days), vacuum databases, check disk space, restart services if needed, and send health report.",
        "category": "devops",
        "icon": "🧹",
        "tags": ["cleanup", "maintenance", "logs", "disk", "devops", "scheduled"],
        "difficulty": "intermediate",
        "estimated_duration": "5-20 min",
        "steps": [
            {"id": "step-1", "name": "Check Disk Space", "type": "custom_script", "config": {"language": "bash", "script": "df -h / /var/log /tmp --output=target,pcent,avail | tail -n +2"}},
            {"id": "step-2", "name": "Clean Temp Files", "type": "custom_script", "config": {"language": "bash", "script": "find /tmp -type f -mtime +7 -delete 2>/dev/null\nfind /var/tmp -type f -mtime +30 -delete 2>/dev/null\necho \"Temp files cleaned\""}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Purge Old Logs", "type": "custom_script", "config": {"language": "bash", "script": "find /var/log -name '*.log.*' -mtime +90 -delete\nfind /var/log -name '*.gz' -mtime +90 -delete\njournalctl --vacuum-time=90d 2>/dev/null\necho \"Old logs purged\""}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Vacuum Database", "type": "database_query", "config": {"connection": "{{ credentials.main_db }}", "query": "VACUUM ANALYZE; SELECT pg_database_size(current_database()) as db_size;"}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Check Disk After", "type": "custom_script", "config": {"language": "bash", "script": "df -h / /var/log /tmp --output=target,pcent,avail | tail -n +2"}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Send Health Report", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "🧹 *System Maintenance Complete*\n\nDisk before:\n```{{ steps.step_1.output }}```\n\nDisk after:\n```{{ steps.step_5.output }}```\n\nDB size: {{ steps.step_4.rows[0].db_size | filesizeformat }}"}}, "depends_on": ["step-5"]},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════
    # SMART AMAZON TRACKER (Browser-based)
    # ═══════════════════════════════════════════════════════════════════
    {
        "id": "tpl-amazon-price-tracker",
        "name": "Smart Amazon Best Sellers Tracker",
        "description": "Browser-based RPA that tracks top 10,000 best-selling products on Amazon.de daily. Collects ASIN, title, price, rating, review count, availability, and category. Features auto-restart on failure, network checks, CAPTCHA detection, exponential backoff, progress checkpoints, and error reporting via Slack/email.",
        "category": "e-commerce",
        "icon": "🛒",
        "tags": ["amazon", "price-tracker", "browser", "best-sellers", "e-commerce", "scraping", "monitoring"],
        "difficulty": "advanced",
        "estimated_duration": "60-180 min",
        "steps": [
            {"id": "step-1", "name": "Health Check & Init", "type": "custom_script", "config": {"language": "python", "script": "import urllib.request, json\nfrom datetime import datetime\n\n# Check internet\ntry:\n    urllib.request.urlopen('https://www.amazon.de', timeout=10)\n    net_ok = True\nexcept:\n    net_ok = False\n\n# Load checkpoint if exists (resume after crash)\ncheckpoint = None\ntry:\n    with open('/tmp/amazon_tracker_checkpoint.json') as f:\n        checkpoint = json.load(f)\nexcept:\n    pass\n\n# Amazon.de Best Seller categories\ncategories = [\n    {'name': 'All', 'url': 'https://www.amazon.de/gp/bestsellers/'},\n    {'name': 'Electronics', 'url': 'https://www.amazon.de/gp/bestsellers/ce-de/'},\n    {'name': 'Books', 'url': 'https://www.amazon.de/gp/bestsellers/books-de/'},\n    {'name': 'Home & Kitchen', 'url': 'https://www.amazon.de/gp/bestsellers/kitchen/'},\n    {'name': 'Clothing', 'url': 'https://www.amazon.de/gp/bestsellers/apparel/'},\n    {'name': 'Beauty', 'url': 'https://www.amazon.de/gp/bestsellers/beauty/'},\n    {'name': 'Sports', 'url': 'https://www.amazon.de/gp/bestsellers/sports/'},\n    {'name': 'Toys', 'url': 'https://www.amazon.de/gp/bestsellers/toys/'},\n    {'name': 'Garden', 'url': 'https://www.amazon.de/gp/bestsellers/garden/'},\n    {'name': 'Automotive', 'url': 'https://www.amazon.de/gp/bestsellers/automotive/'},\n    {'name': 'Pet Supplies', 'url': 'https://www.amazon.de/gp/bestsellers/pet-supplies/'},\n    {'name': 'Health', 'url': 'https://www.amazon.de/gp/bestsellers/drugstore/'},\n    {'name': 'Baby', 'url': 'https://www.amazon.de/gp/bestsellers/baby-de/'},\n    {'name': 'PC & Video Games', 'url': 'https://www.amazon.de/gp/bestsellers/videogames/'},\n    {'name': 'Office', 'url': 'https://www.amazon.de/gp/bestsellers/officeproduct/'},\n]\n\nstart_from = 0\nif checkpoint and checkpoint.get('date') == datetime.utcnow().strftime('%Y-%m-%d'):\n    start_from = checkpoint.get('last_category_index', 0)\n    print(f'Resuming from category {start_from}')\n\noutput = {\n    'network_ok': net_ok,\n    'categories': categories,\n    'start_from': start_from,\n    'run_id': datetime.utcnow().strftime('%Y%m%d_%H%M%S'),\n    'date': datetime.utcnow().strftime('%Y-%m-%d'),\n    'all_products': [],\n    'errors': [],\n    'retry_count': 0,\n    'max_retries': 5\n}", "outputs": ["state"]}},
            {"id": "step-2", "name": "Abort if No Network", "type": "condition", "config": {"condition": "{{ not steps.step_1.network_ok }}", "on_true": "step-10-error", "on_false": "step-3"}, "depends_on": ["step-1"]},
            {"id": "step-3", "name": "Open Browser & Set Config", "type": "page_interaction", "config": {"browser": "chromium", "headless": True, "user_agent_rotation": True, "viewport": {"width": 1920, "height": 1080}, "steps": [{"action": "navigate", "url": "https://www.amazon.de"}, {"action": "wait", "timeout": 3}, {"action": "click", "selector": "#sp-cc-accept", "optional": True, "description": "Accept cookies"}, {"action": "wait", "timeout": 2}]}, "depends_on": ["step-2"]},
            {"id": "step-4", "name": "Scrape Category Loop", "type": "loop", "config": {"items": "{{ steps.step_1.categories[steps.step_1.start_from:] }}", "max_parallel": 1, "delay_between": {"min": 3, "max": 7, "unit": "seconds"}, "on_error": "continue", "step": {"type": "custom_script", "config": {"language": "python", "script": "import random, time, json\nfrom datetime import datetime\n\ncategory = item\nproducts = []\npage = 1\nmax_pages = 5  # Amazon shows ~50 per page, 5 pages = 250 per category\n\nwhile page <= max_pages:\n    url = f\"{category['url']}?pg={page}\"\n    \n    # Navigate with retry\n    for attempt in range(3):\n        try:\n            browser.navigate(url)\n            browser.wait_for('.zg-grid-general-faceout', timeout=15)\n            break\n        except:\n            wait_time = (2 ** attempt) + random.uniform(1, 3)\n            time.sleep(wait_time)\n            if attempt == 2:\n                state['errors'].append({'category': category['name'], 'page': page, 'error': 'Navigation failed after 3 attempts', 'time': datetime.utcnow().isoformat()})\n                break\n    \n    # Check for CAPTCHA\n    if browser.find_element('#captchacharacters', optional=True):\n        state['errors'].append({'category': category['name'], 'error': 'CAPTCHA detected', 'time': datetime.utcnow().isoformat()})\n        time.sleep(random.uniform(30, 60))  # Wait before retry\n        continue\n    \n    # Extract products\n    items = browser.query_selector_all('.zg-grid-general-faceout')\n    for el in items:\n        try:\n            asin = el.get_attribute('data-asin') or ''\n            title_el = el.query_selector('.p13n-sc-truncate-desktop-type2, ._cDEzb_p13n-sc-css-line-clamp-1_1Fn1y')\n            price_el = el.query_selector('.p13n-sc-price, ._cDEzb_p13n-sc-price_3mJ9Z')\n            rating_el = el.query_selector('.a-icon-alt')\n            reviews_el = el.query_selector('.a-size-small .a-link-normal')\n            rank_el = el.query_selector('.zg-bdg-text')\n            \n            product = {\n                'asin': asin,\n                'title': title_el.text_content().strip() if title_el else '',\n                'price': price_el.text_content().strip() if price_el else 'N/A',\n                'rating': rating_el.text_content().split()[0] if rating_el else '0',\n                'reviews': reviews_el.text_content().strip().replace('.', '').replace(',', '') if reviews_el else '0',\n                'rank': rank_el.text_content().strip().replace('#', '') if rank_el else str(len(products) + 1),\n                'category': category['name'],\n                'url': f\"https://www.amazon.de/dp/{asin}\" if asin else '',\n                'scraped_at': datetime.utcnow().isoformat(),\n                'date': datetime.utcnow().strftime('%Y-%m-%d')\n            }\n            if product['title']:  # Only add if we got a title\n                products.append(product)\n        except Exception as e:\n            continue\n    \n    page += 1\n    # Random delay between pages (anti-bot)\n    time.sleep(random.uniform(2, 5))\n\n# Save checkpoint\ncat_idx = steps.step_1.categories.index(category)\ncheckpoint = {'date': datetime.utcnow().strftime('%Y-%m-%d'), 'last_category_index': cat_idx + 1, 'products_so_far': len(state.get('all_products', []))}\nwith open('/tmp/amazon_tracker_checkpoint.json', 'w') as f:\n    json.dump(checkpoint, f)\n\noutput = {'category': category['name'], 'products': products, 'count': len(products)}"}}}, "depends_on": ["step-3"]},
            {"id": "step-5", "name": "Aggregate & Deduplicate", "type": "custom_script", "config": {"language": "python", "script": "all_products = []\nseen_asins = set()\nfor result in steps.step_4.results:\n    for p in result.get('products', []):\n        if p['asin'] and p['asin'] not in seen_asins:\n            seen_asins.add(p['asin'])\n            # Clean price\n            import re\n            price_str = re.sub(r'[^\\d,.]', '', p.get('price', '0')).replace(',', '.')\n            try:\n                p['price_numeric'] = float(price_str)\n            except:\n                p['price_numeric'] = 0\n            # Clean rating\n            try:\n                p['rating_numeric'] = float(p.get('rating', '0').replace(',', '.'))\n            except:\n                p['rating_numeric'] = 0\n            # Clean reviews\n            try:\n                p['reviews_numeric'] = int(re.sub(r'[^\\d]', '', p.get('reviews', '0')) or '0')\n            except:\n                p['reviews_numeric'] = 0\n            all_products.append(p)\n\n# Sort by rating * reviews (popularity score)\nall_products.sort(key=lambda x: x['rating_numeric'] * x['reviews_numeric'], reverse=True)\n\nby_category = {}\nfor p in all_products:\n    cat = p['category']\n    if cat not in by_category:\n        by_category[cat] = 0\n    by_category[cat] += 1\n\noutput = {\n    'products': all_products[:10000],\n    'total_unique': len(all_products),\n    'by_category': by_category,\n    'top_10': all_products[:10]\n}"}, "depends_on": ["step-4"]},
            {"id": "step-6", "name": "Compare with Yesterday", "type": "custom_script", "config": {"language": "python", "script": "import json\nfrom datetime import datetime, timedelta\n\nyesterday_file = f\"/data/amazon_tracker/{(datetime.utcnow() - timedelta(days=1)).strftime('%Y-%m-%d')}.json\"\ntry:\n    with open(yesterday_file) as f:\n        yesterday = json.load(f)\n    yesterday_map = {p['asin']: p for p in yesterday.get('products', [])}\nexcept:\n    yesterday_map = {}\n\nprice_changes = []\nnew_products = []\nfor p in steps.step_5.products[:10000]:\n    asin = p['asin']\n    if asin in yesterday_map:\n        old_price = yesterday_map[asin].get('price_numeric', 0)\n        new_price = p.get('price_numeric', 0)\n        if old_price > 0 and new_price > 0:\n            change_pct = ((new_price - old_price) / old_price) * 100\n            if abs(change_pct) >= 5:  # 5% threshold\n                price_changes.append({\n                    'asin': asin,\n                    'title': p['title'][:60],\n                    'old_price': old_price,\n                    'new_price': new_price,\n                    'change_pct': round(change_pct, 1),\n                    'direction': '📈' if change_pct > 0 else '📉',\n                    'category': p['category']\n                })\n    else:\n        new_products.append({'asin': asin, 'title': p['title'][:60], 'price': p.get('price', 'N/A'), 'category': p['category']})\n\nprice_changes.sort(key=lambda x: abs(x['change_pct']), reverse=True)\n\noutput = {\n    'price_changes': price_changes[:50],\n    'new_products': new_products[:50],\n    'total_changes': len(price_changes),\n    'total_new': len(new_products)\n}"}, "depends_on": ["step-5"]},
            {"id": "step-7", "name": "Save to Database & File", "type": "custom_script", "config": {"language": "python", "script": "import json, os\nfrom datetime import datetime\n\n# Save JSON file\ndate_str = datetime.utcnow().strftime('%Y-%m-%d')\nos.makedirs('/data/amazon_tracker', exist_ok=True)\nwith open(f'/data/amazon_tracker/{date_str}.json', 'w') as f:\n    json.dump({'products': steps.step_5.products, 'metadata': {'date': date_str, 'total': steps.step_5.total_unique, 'by_category': steps.step_5.by_category}}, f)\n\n# Save CSV\nimport csv\nwith open(f'/data/amazon_tracker/{date_str}.csv', 'w', newline='') as f:\n    writer = csv.DictWriter(f, fieldnames=['rank', 'asin', 'title', 'price', 'rating', 'reviews', 'category', 'url', 'date'])\n    writer.writeheader()\n    for p in steps.step_5.products:\n        writer.writerow({k: p.get(k, '') for k in writer.fieldnames})\n\n# Clean old files (keep 90 days)\nimport glob\nfiles = sorted(glob.glob('/data/amazon_tracker/*.json'))\nif len(files) > 90:\n    for old in files[:-90]:\n        os.remove(old)\n        os.remove(old.replace('.json', '.csv'))\n\noutput = {'saved': True, 'json_path': f'/data/amazon_tracker/{date_str}.json', 'csv_path': f'/data/amazon_tracker/{date_str}.csv'}"}, "depends_on": ["step-5", "step-6"]},
            {"id": "step-8", "name": "Send Daily Report", "type": "http_request", "config": {"url": "{{ credentials.slack_webhook }}", "method": "POST", "body": {"text": "📊 *Amazon.de Daily Best Sellers Report*\n📅 {{ steps.step_1.date }}\n\n✅ *{{ steps.step_5.total_unique }}* unique products tracked\n\n📂 *By Category:*\n{% for cat, count in steps.step_5.by_category.items() %}• {{ cat }}: {{ count }} products\n{% endfor %}\n\n🏆 *Top 10 Products:*\n{% for p in steps.step_5.top_10 %}{{ loop.index }}. {{ p.title[:50] }} — {{ p.price }} ⭐{{ p.rating }} ({{ p.reviews }} reviews)\n{% endfor %}\n\n{% if steps.step_6.total_changes > 0 %}💰 *Price Changes (≥5%):* {{ steps.step_6.total_changes }} products\n{% for c in steps.step_6.price_changes[:10] %}{{ c.direction }} {{ c.title }} — €{{ c.old_price }} → €{{ c.new_price }} ({{ c.change_pct }}%)\n{% endfor %}{% endif %}\n\n{% if steps.step_6.total_new > 0 %}🆕 *New in Top:* {{ steps.step_6.total_new }} products{% endif %}\n\n{% if steps.step_1.errors %}⚠️ *Errors:* {{ len(steps.step_1.errors) }}{% endif %}"}}, "depends_on": ["step-7"]},
            {"id": "step-9", "name": "Cleanup & Clear Checkpoint", "type": "custom_script", "config": {"language": "python", "script": "import os\ntry:\n    os.remove('/tmp/amazon_tracker_checkpoint.json')\nexcept:\n    pass\noutput = {'status': 'completed', 'products': steps.step_5.total_unique, 'errors': len(steps.step_1.errors)}"}, "depends_on": ["step-8"]},
            {"id": "step-10-error", "name": "Error Recovery & Alert", "type": "custom_script", "config": {"language": "python", "script": "import json\nstate = steps.step_1\nstate['retry_count'] = state.get('retry_count', 0) + 1\nerror_msg = f\"Amazon Tracker failed. Retry {state['retry_count']}/{state['max_retries']}\"\nif not state.get('network_ok'):\n    error_msg += '. Reason: No network connectivity'\nelse:\n    error_msg += f\". Errors: {json.dumps(state.get('errors', [])[:5])}\"\n\n# If under max retries, schedule restart in 5 minutes\nif state['retry_count'] < state['max_retries']:\n    output = {'action': 'retry', 'message': error_msg, 'wait_seconds': 300}\nelse:\n    output = {'action': 'abort', 'message': f'CRITICAL: Amazon Tracker failed after {state[\"max_retries\"]} retries. Manual intervention needed.'}"}},
        ],
    },
]
