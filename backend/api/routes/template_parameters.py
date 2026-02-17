"""
Required parameters for each workflow template.
Maps template_id → list of parameter definitions.
Each parameter specifies what the user must fill in before a template can be used.

Fields:
  - key: unique identifier for the parameter
  - label: display name
  - type: url|string|number|email|select|boolean|credential|textarea
  - required: whether the field must be filled
  - placeholder: example value
  - description: help text
  - maps_to: dot-notation path for merging into template steps
  - auto_fillable: AI can suggest values for this field (default False)
  - ai_hint: hint for AI on what values work well
  - credential_type: for credential fields, what kind
  - options: for select fields, available choices
  - default: default value if not provided
"""

TEMPLATE_PARAMETERS = {
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DATA EXTRACTION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-web-scraper": [
        {"key": "target_url", "label": "Target URL", "type": "url", "required": True,
         "placeholder": "https://example.com/products", "description": "The web page URL to scrape data from",
         "maps_to": "steps.0.config.url",
         "auto_fillable": True, "ai_hint": "Construct the URL from the user's description of the target site and page"},
        {"key": "css_selector", "label": "CSS Selector", "type": "string", "required": True,
         "placeholder": "div.product h2", "description": "CSS selector to extract data elements",
         "maps_to": "steps.0.config.selectors.0.selector",
         "auto_fillable": True, "ai_hint": "For known sites suggest common selectors: emag.bg prices use .product-new-price, amazon uses .a-price-whole"},
    ],
    "tpl-multi-page-scraper": [
        {"key": "start_url", "label": "Start URL", "type": "url", "required": True,
         "placeholder": "https://example.com/listings?page=1", "description": "First page URL to begin crawling",
         "maps_to": "steps.0.config.url",
         "auto_fillable": True, "ai_hint": "Add ?page=1 or similar pagination parameter to the URL"},
        {"key": "max_pages", "label": "Max Pages", "type": "number", "required": True,
         "placeholder": "10", "description": "Maximum number of pages to crawl",
         "default": 10,
         "auto_fillable": True, "ai_hint": "Extract number from instruction or default to 10"},
        {"key": "output_email", "label": "Results Email", "type": "email", "required": False,
         "placeholder": "you@company.com", "description": "Email to send scraped results to (optional)",
         "maps_to": "steps.7.config.to"},
    ],
    "tpl-competitor-price-tracker": [
        {"key": "competitor_url_1", "label": "Competitor URL 1", "type": "url", "required": True,
         "placeholder": "https://competitor1.com/products", "description": "First competitor product page",
         "auto_fillable": True, "ai_hint": "Extract competitor site URLs from instruction"},
        {"key": "competitor_url_2", "label": "Competitor URL 2", "type": "url", "required": False,
         "placeholder": "https://competitor2.com/products", "description": "Second competitor product page (optional)",
         "auto_fillable": True},
        {"key": "competitor_url_3", "label": "Competitor URL 3", "type": "url", "required": False,
         "placeholder": "https://competitor3.com/products", "description": "Third competitor product page (optional)",
         "auto_fillable": True},
        {"key": "alert_webhook", "label": "Alert Webhook", "type": "url", "required": False,
         "placeholder": "https://hooks.slack.com/services/...", "description": "Slack/Teams webhook for price change alerts"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MONITORING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-api-monitor": [
        {"key": "api_url", "label": "API Endpoint URL", "type": "url", "required": True,
         "placeholder": "https://api.example.com/health", "description": "API endpoint to monitor",
         "maps_to": "steps.0.config.url",
         "auto_fillable": True, "ai_hint": "If user mentions a service, suggest its common health endpoint"},
        {"key": "alert_webhook", "label": "Alert Webhook", "type": "url", "required": False,
         "placeholder": "https://hooks.slack.com/services/...", "description": "Webhook URL for failure alerts",
         "maps_to": "steps.2.config.url"},
        {"key": "expected_status", "label": "Expected Status Code", "type": "number", "required": False,
         "placeholder": "200", "description": "Expected HTTP status code", "default": 200,
         "auto_fillable": True, "ai_hint": "Usually 200 unless user specifies otherwise"},
    ],
    "tpl-uptime-multi-endpoint": [
        {"key": "endpoints", "label": "Endpoint URLs (one per line)", "type": "textarea", "required": True,
         "placeholder": "https://api.example.com/health\nhttps://web.example.com\nhttps://admin.example.com",
         "description": "List of URLs to monitor, one per line",
         "auto_fillable": True, "ai_hint": "Extract all URLs or services mentioned in instruction"},
        {"key": "alert_webhook", "label": "Alert Webhook", "type": "url", "required": False,
         "placeholder": "https://hooks.slack.com/services/...", "description": "Webhook for downtime alerts"},
    ],
    "tpl-ssl-certificate-monitor": [
        {"key": "domains", "label": "Domains (one per line)", "type": "textarea", "required": True,
         "placeholder": "example.com\napi.example.com\nshop.example.com",
         "description": "Domain names to check SSL certificates for",
         "auto_fillable": True, "ai_hint": "Extract domain names from instruction"},
        {"key": "alert_days", "label": "Alert Before Expiry (days)", "type": "number", "required": False,
         "placeholder": "30", "description": "Send alert this many days before certificate expiry", "default": 30,
         "auto_fillable": True, "ai_hint": "Extract number of days from instruction or default 30"},
        {"key": "alert_webhook", "label": "Alert Webhook", "type": "url", "required": False,
         "placeholder": "https://hooks.slack.com/services/...", "description": "Webhook for expiry alerts"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FORM & BROWSER AUTOMATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-form-automation": [
        {"key": "form_url", "label": "Form URL", "type": "url", "required": True,
         "placeholder": "https://example.com/contact-form", "description": "The web page containing the form",
         "maps_to": "steps.0.config.url",
         "auto_fillable": True, "ai_hint": "Extract form URL from instruction"},
        {"key": "form_data", "label": "Form Field Values (JSON)", "type": "textarea", "required": True,
         "placeholder": '{"name": "John", "email": "john@example.com", "message": "Hello"}',
         "description": "JSON object with form field names and values to fill in",
         "auto_fillable": True, "ai_hint": "Build JSON from field names and values mentioned in instruction"},
    ],
    "tpl-invoice-download": [
        {"key": "portal_url", "label": "Supplier Portal URL", "type": "url", "required": True,
         "placeholder": "https://supplier-portal.com/login", "description": "Login page of the supplier portal",
         "maps_to": "steps.0.config.url",
         "auto_fillable": True, "ai_hint": "Extract portal URL from instruction"},
        {"key": "portal_credential", "label": "Portal Login Credential", "type": "credential", "required": True,
         "credential_type": "web_login", "description": "Username/password credential for portal login"},
        {"key": "download_path", "label": "Save To Folder", "type": "string", "required": False,
         "placeholder": "/invoices/2026/", "description": "Folder path to save downloaded invoices",
         "auto_fillable": True, "ai_hint": "Suggest /invoices/YYYY/ based on current year"},
        {"key": "notify_email", "label": "Notification Email", "type": "email", "required": False,
         "placeholder": "accounting@company.com", "description": "Email to notify when invoices are downloaded"},
    ],
    "tpl-screenshot-monitor": [
        {"key": "target_url", "label": "Page URL", "type": "url", "required": True,
         "placeholder": "https://example.com", "description": "Web page to capture screenshots of",
         "auto_fillable": True, "ai_hint": "Extract target URL from instruction"},
        {"key": "check_interval", "label": "Check Interval (minutes)", "type": "number", "required": False,
         "placeholder": "60", "description": "How often to take a screenshot", "default": 60,
         "auto_fillable": True, "ai_hint": "Parse interval from instruction: 'every hour'=60, 'every 5 min'=5"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # REPORTS & NOTIFICATIONS
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-report-generator": [
        {"key": "data_source_url", "label": "Data Source URL", "type": "url", "required": True,
         "placeholder": "https://api.example.com/data", "description": "API endpoint to pull report data from",
         "auto_fillable": True, "ai_hint": "Extract data source URL from instruction"},
        {"key": "report_email", "label": "Report Recipient Email", "type": "email", "required": True,
         "placeholder": "manager@company.com", "description": "Email to send the generated report to"},
        {"key": "report_title", "label": "Report Title", "type": "string", "required": False,
         "placeholder": "Weekly Performance Report", "description": "Title for the generated report",
         "auto_fillable": True, "ai_hint": "Generate a descriptive title from the instruction"},
    ],
    "tpl-daily-kpi-report": [
        {"key": "kpi_api_url", "label": "KPI Data API URL", "type": "url", "required": True,
         "placeholder": "https://analytics.example.com/api/kpi", "description": "API endpoint for KPI data",
         "auto_fillable": True},
        {"key": "db_credential", "label": "Database Credential", "type": "credential", "required": False,
         "credential_type": "database", "description": "Database credential for direct KPI queries (optional)"},
        {"key": "report_recipients", "label": "Report Recipients", "type": "string", "required": True,
         "placeholder": "ceo@company.com, cto@company.com", "description": "Comma-separated email addresses"},
        {"key": "slack_webhook", "label": "Slack Webhook", "type": "url", "required": False,
         "placeholder": "https://hooks.slack.com/services/...", "description": "Slack webhook for KPI summary"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # AI / MACHINE LEARNING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-ai-classifier": [
        {"key": "api_key", "label": "OpenAI API Key", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "OpenAI API key for classification"},
        {"key": "input_source", "label": "Input Data URL/Path", "type": "string", "required": True,
         "placeholder": "/data/documents/ or https://api.example.com/docs", "description": "Source of documents to classify",
         "auto_fillable": True, "ai_hint": "Extract source path or URL from instruction"},
        {"key": "categories", "label": "Classification Categories", "type": "textarea", "required": True,
         "placeholder": "Invoice\nReceipt\nContract\nLetter", "description": "Categories to classify into, one per line",
         "auto_fillable": True, "ai_hint": "Extract category names from instruction"},
    ],
    "tpl-ai-email-responder": [
        {"key": "email_credential", "label": "Email Account Credential", "type": "credential", "required": True,
         "credential_type": "email_imap", "description": "IMAP email credential for reading incoming emails"},
        {"key": "ai_api_key", "label": "AI API Key", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "OpenAI/Claude API key for generating responses"},
        {"key": "response_rules", "label": "Response Rules", "type": "textarea", "required": False,
         "placeholder": "Be professional and concise\nAlways include a greeting\nNever promise deadlines",
         "description": "Guidelines for AI-generated responses",
         "auto_fillable": True, "ai_hint": "Generate response rules based on tone/style described in instruction"},
    ],
    "tpl-ai-document-processor": [
        {"key": "ai_api_key", "label": "AI API Key", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "API key for document processing AI"},
        {"key": "input_folder", "label": "Input Document Folder", "type": "string", "required": True,
         "placeholder": "/documents/incoming/", "description": "Folder to watch for new documents",
         "auto_fillable": True, "ai_hint": "Extract folder path from instruction"},
        {"key": "output_folder", "label": "Output Folder", "type": "string", "required": False,
         "placeholder": "/documents/processed/", "description": "Folder for processed results",
         "auto_fillable": True, "ai_hint": "Suggest /documents/processed/ or derive from input folder"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # FINANCE & ACCOUNTING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-bank-reconciliation": [
        {"key": "bank_credential", "label": "Bank API Credential", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "Bank or financial API credential"},
        {"key": "accounting_system_url", "label": "Accounting System URL", "type": "url", "required": True,
         "placeholder": "https://accounting.company.com/api", "description": "URL of your accounting system API",
         "auto_fillable": True, "ai_hint": "Extract accounting system URL from instruction"},
        {"key": "account_id", "label": "Bank Account ID", "type": "string", "required": True,
         "placeholder": "ACC-12345", "description": "Bank account identifier for reconciliation"},
    ],
    "tpl-expense-processor": [
        {"key": "expense_email", "label": "Expense Receipts Email", "type": "email", "required": True,
         "placeholder": "expenses@company.com", "description": "Email address that receives expense receipts"},
        {"key": "email_credential", "label": "Email Credential", "type": "credential", "required": True,
         "credential_type": "email_imap", "description": "IMAP credential to read the expense email inbox"},
        {"key": "approval_email", "label": "Manager Approval Email", "type": "email", "required": True,
         "placeholder": "manager@company.com", "description": "Manager email for expense approval notifications"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # HR
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-employee-onboarding": [
        {"key": "hr_system_url", "label": "HR System URL", "type": "url", "required": True,
         "placeholder": "https://hr.company.com/api", "description": "URL of your HR management system",
         "auto_fillable": True},
        {"key": "hr_credential", "label": "HR System Credential", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "API credential for the HR system"},
        {"key": "it_email", "label": "IT Team Email", "type": "email", "required": True,
         "placeholder": "it-support@company.com", "description": "IT team email for account setup requests"},
        {"key": "welcome_template", "label": "Welcome Email Template Name", "type": "string", "required": False,
         "placeholder": "new_employee_welcome", "description": "Name of the welcome email template to use",
         "auto_fillable": True, "ai_hint": "Suggest descriptive template name based on instruction"},
    ],
    "tpl-resume-screener": [
        {"key": "ai_api_key", "label": "AI API Key", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "AI API key for resume analysis"},
        {"key": "resume_folder", "label": "Resume Input Folder", "type": "string", "required": True,
         "placeholder": "/resumes/incoming/", "description": "Folder where new resumes are uploaded",
         "auto_fillable": True, "ai_hint": "Suggest /resumes/incoming/ or extract from instruction"},
        {"key": "job_requirements", "label": "Job Requirements", "type": "textarea", "required": True,
         "placeholder": "5+ years Python experience\nBachelor's degree in CS\nExperience with distributed systems",
         "description": "Job requirements to screen resumes against, one per line",
         "auto_fillable": True, "ai_hint": "Extract job requirements from instruction"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # E-COMMERCE & SUPPLY CHAIN
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-order-fulfillment": [
        {"key": "shop_api_url", "label": "Shop/ERP API URL", "type": "url", "required": True,
         "placeholder": "https://shop.example.com/api/v1", "description": "E-commerce platform or ERP API endpoint",
         "auto_fillable": True, "ai_hint": "Extract shop/ERP URL from instruction"},
        {"key": "shop_credential", "label": "Shop API Credential", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "API credential for your shop/ERP system"},
        {"key": "shipping_api_url", "label": "Shipping Provider API", "type": "url", "required": False,
         "placeholder": "https://api.shipping-provider.com/v2", "description": "Shipping carrier API endpoint",
         "auto_fillable": True, "ai_hint": "If shipping provider mentioned (Speedy, Econt, DHL), suggest their API URL"},
    ],
    "tpl-inventory-sync": [
        {"key": "primary_system_url", "label": "Primary Inventory System URL", "type": "url", "required": True,
         "placeholder": "https://erp.company.com/api/inventory", "description": "Main inventory system API",
         "auto_fillable": True},
        {"key": "secondary_system_url", "label": "Secondary System URL", "type": "url", "required": True,
         "placeholder": "https://shop.company.com/api/stock", "description": "Secondary system to sync with",
         "auto_fillable": True},
        {"key": "sync_interval", "label": "Sync Interval (minutes)", "type": "number", "required": False,
         "placeholder": "15", "description": "How often to sync inventory", "default": 15,
         "auto_fillable": True, "ai_hint": "Parse interval from instruction: 'every 15 min'=15, 'hourly'=60"},
    ],
    "tpl-amazon-price-tracker": [
        {"key": "product_urls", "label": "Amazon Product URLs (one per line)", "type": "textarea", "required": True,
         "placeholder": "https://amazon.com/dp/B08N5WRWNW\nhttps://amazon.com/dp/B09V3KXJPB",
         "description": "Amazon product page URLs to track prices for",
         "auto_fillable": True, "ai_hint": "Extract Amazon URLs from instruction if provided"},
        {"key": "price_drop_threshold", "label": "Alert on Price Drop (%)", "type": "number", "required": False,
         "placeholder": "10", "description": "Minimum percentage drop to trigger alert", "default": 10,
         "auto_fillable": True, "ai_hint": "Extract percentage from instruction or default 10"},
        {"key": "alert_email", "label": "Alert Email", "type": "email", "required": False,
         "placeholder": "you@example.com", "description": "Email for price drop notifications"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # DEVOPS & DATA
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-db-backup": [
        {"key": "db_credential", "label": "Database Credential", "type": "credential", "required": True,
         "credential_type": "database", "description": "Database connection credential"},
        {"key": "backup_path", "label": "Backup Destination", "type": "string", "required": True,
         "placeholder": "/backups/daily/ or s3://bucket/backups/", "description": "Local path or S3 URL for backups",
         "auto_fillable": True, "ai_hint": "Extract backup path from instruction or suggest /backups/daily/"},
        {"key": "retention_days", "label": "Retention Period (days)", "type": "number", "required": False,
         "placeholder": "30", "description": "Days to keep old backups", "default": 30,
         "auto_fillable": True, "ai_hint": "Extract retention period from instruction or default 30"},
    ],
    "tpl-log-analyzer": [
        {"key": "log_source", "label": "Log Source Path/URL", "type": "string", "required": True,
         "placeholder": "/var/log/app/ or https://logging-api.com/v1/logs", "description": "Path or API URL for log files",
         "auto_fillable": True, "ai_hint": "Extract log path from instruction"},
        {"key": "alert_patterns", "label": "Alert Patterns (regex, one per line)", "type": "textarea", "required": True,
         "placeholder": "ERROR|FATAL\nOutOfMemory\nConnection refused",
         "description": "Regex patterns that should trigger alerts",
         "auto_fillable": True, "ai_hint": "Generate regex patterns based on error types mentioned in instruction"},
        {"key": "alert_webhook", "label": "Alert Webhook", "type": "url", "required": False,
         "placeholder": "https://hooks.slack.com/services/...", "description": "Webhook for log alerts"},
    ],
    "tpl-data-pipeline": [
        {"key": "source_db_credential", "label": "Source Database Credential", "type": "credential", "required": True,
         "credential_type": "database", "description": "Source database connection"},
        {"key": "dest_db_credential", "label": "Destination Database Credential", "type": "credential", "required": True,
         "credential_type": "database", "description": "Destination database connection"},
        {"key": "source_query", "label": "Source SQL Query", "type": "textarea", "required": True,
         "placeholder": "SELECT * FROM orders WHERE created_at > NOW() - INTERVAL '1 day'",
         "description": "SQL query to extract data from source",
         "auto_fillable": True, "ai_hint": "Generate SQL query based on data described in instruction"},
        {"key": "dest_table", "label": "Destination Table", "type": "string", "required": True,
         "placeholder": "warehouse.daily_orders", "description": "Target table to load data into",
         "auto_fillable": True, "ai_hint": "Suggest table name based on data type in instruction"},
    ],
    "tpl-csv-etl-pipeline": [
        {"key": "input_path", "label": "CSV Input Path", "type": "string", "required": True,
         "placeholder": "/data/imports/daily.csv or https://api.example.com/export.csv",
         "description": "Path or URL to the CSV file",
         "auto_fillable": True, "ai_hint": "Extract CSV file path or URL from instruction"},
        {"key": "output_db_credential", "label": "Output Database Credential", "type": "credential", "required": False,
         "credential_type": "database", "description": "Database credential if loading into a database"},
        {"key": "output_path", "label": "Output Path (if file)", "type": "string", "required": False,
         "placeholder": "/data/processed/clean.csv", "description": "Output file path (if not using database)",
         "auto_fillable": True, "ai_hint": "Suggest output path based on input path"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SUPPORT & COMMUNICATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-ticket-sla-monitor": [
        {"key": "ticketing_api_url", "label": "Ticketing System API URL", "type": "url", "required": True,
         "placeholder": "https://support.company.com/api/v2", "description": "Your ticketing system API endpoint",
         "auto_fillable": True, "ai_hint": "If system name mentioned (Zendesk, Freshdesk), suggest their API URL format"},
        {"key": "ticketing_credential", "label": "Ticketing API Credential", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "API credential for your ticketing system"},
        {"key": "sla_hours", "label": "SLA Response Time (hours)", "type": "number", "required": True,
         "placeholder": "4", "description": "Maximum hours before SLA breach", "default": 4,
         "auto_fillable": True, "ai_hint": "Extract SLA hours from instruction or default 4"},
        {"key": "escalation_email", "label": "Escalation Email", "type": "email", "required": True,
         "placeholder": "support-lead@company.com", "description": "Email for SLA breach escalation"},
    ],
    "tpl-social-media-scheduler": [
        {"key": "social_credential", "label": "Social Media API Credential", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "API credential for social media platform"},
        {"key": "content_source", "label": "Content Source (URL/folder)", "type": "string", "required": True,
         "placeholder": "/content/social/ or https://cms.example.com/api/posts",
         "description": "Source of content to post",
         "auto_fillable": True, "ai_hint": "Extract content source from instruction"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # SEO & MARKETING
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-seo-audit": [
        {"key": "site_url", "label": "Website URL", "type": "url", "required": True,
         "placeholder": "https://www.example.com", "description": "Root URL of the website to audit",
         "auto_fillable": True, "ai_hint": "Extract website URL from instruction"},
        {"key": "max_pages", "label": "Max Pages to Crawl", "type": "number", "required": False,
         "placeholder": "100", "description": "Maximum pages to check during the audit", "default": 100,
         "auto_fillable": True, "ai_hint": "Extract page limit from instruction or default 100"},
        {"key": "report_email", "label": "Report Email", "type": "email", "required": False,
         "placeholder": "seo@company.com", "description": "Email to send the SEO audit report"},
    ],
    "tpl-lead-enrichment": [
        {"key": "crm_api_url", "label": "CRM API URL", "type": "url", "required": True,
         "placeholder": "https://crm.company.com/api/v1", "description": "Your CRM system API endpoint",
         "auto_fillable": True, "ai_hint": "If CRM name mentioned (HubSpot, Salesforce), suggest their API format"},
        {"key": "crm_credential", "label": "CRM API Credential", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "API credential for your CRM"},
        {"key": "enrichment_api_key", "label": "Enrichment Service API Key", "type": "credential", "required": True,
         "credential_type": "api_key", "description": "API key for data enrichment service (Clearbit, etc.)"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # COMPLIANCE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-gdpr-data-request": [
        {"key": "database_credential", "label": "User Database Credential", "type": "credential", "required": True,
         "credential_type": "database", "description": "Database credential to search for user data"},
        {"key": "dpo_email", "label": "DPO Email", "type": "email", "required": True,
         "placeholder": "dpo@company.com", "description": "Data Protection Officer email for notifications"},
        {"key": "response_deadline_days", "label": "Response Deadline (days)", "type": "number", "required": False,
         "placeholder": "30", "description": "Days allowed for GDPR response", "default": 30,
         "auto_fillable": True, "ai_hint": "Default 30 days per GDPR requirements"},
    ],

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # MAINTENANCE
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    "tpl-cleanup-automation": [
        {"key": "target_path", "label": "Cleanup Target Path", "type": "string", "required": True,
         "placeholder": "/tmp/ or /data/temp/", "description": "Directory path to clean up old files from",
         "auto_fillable": True, "ai_hint": "Extract target path from instruction"},
        {"key": "max_age_days", "label": "Max File Age (days)", "type": "number", "required": True,
         "placeholder": "30", "description": "Delete files older than this many days", "default": 30,
         "auto_fillable": True, "ai_hint": "Extract age in days from instruction or default 30"},
        {"key": "file_pattern", "label": "File Pattern", "type": "string", "required": False,
         "placeholder": "*.log, *.tmp", "description": "Glob pattern for files to clean (default: all files)",
         "auto_fillable": True, "ai_hint": "Extract file patterns from instruction: 'log files'='*.log'"},
    ],
}


def get_template_parameters(template_id: str) -> list:
    """Get required parameters for a template, or empty list if none defined."""
    return TEMPLATE_PARAMETERS.get(template_id, [])
