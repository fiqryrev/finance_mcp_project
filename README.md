# MCP Financial Document Bot

A Telegram bot for managing financial documents, extracting information from receipts and invoices, and analyzing spending patterns. This bot uses VertexAI's multimodal capabilities to process documents and provide insights.

## Features

- **Document Processing**: Upload receipts or invoices (as images or PDFs) and extract key information
- **Data Storage**: Store financial data in Google Sheets for easy access and analysis
- **Financial Reports**: Generate daily, weekly, or monthly financial reports
- **Spending Analysis**: Analyze spending by category, merchant, or time period
- **Budget Tracking**: Track expenses against budget categories
- **Email Reports**: Schedule automated reports to be sent via email

## Project Structure

```
financial-mcp-bot/
├── config/
│   ├── config.py             # Configuration variables
│   └── secrets.py            # API keys and credentials
├── bot/
│   ├── handlers.py           # Telegram message handlers
│   ├── commands.py           # Bot command implementations
│   └── keyboards.py          # Custom keyboard layouts
├── services/
│   ├── ocr_service.py        # Document parsing functions
│   ├── sheets_service.py     # Google Sheets integration
│   ├── llm_service.py        # VertexAI integration
│   ├── scheduler_service.py  # Scheduling functionality
│   ├── email_service.py      # Email sending functionality
│   └── analysis_service.py   # Financial analysis logic
├── models/
│   ├── receipt.py            # Receipt data model
│   ├── user.py               # User data model
│   └── report.py             # Report data model
├── utils/
│   ├── image_processing.py   # Image preprocessing
│   ├── text_processing.py    # Text extraction helper
│   └── formatters.py         # Report formatting functions
├── main.py                   # Main application entry point
└── requirements.txt          # Dependencies
```

## Setup Instructions

### Prerequisites

- Python 3.9+
- Telegram Bot Token (from BotFather)
- Google Cloud project with VertexAI and Google Sheets API enabled
- Google Cloud service account credentials

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/financial-mcp-bot.git
   cd financial-mcp-bot
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows, use: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create an `.env` file with your credentials:
   ```
   # Telegram Bot
   TELEGRAM_BOT_TOKEN=your_bot_token_here

   # VertexAI Configuration
   GOOGLE_APPLICATION_CREDENTIALS=path/to/your/credentials.json
   PROJECT_ID=your_gcp_project_id
   LOCATION=us-central1
   MODEL_ID=gemini-flash-2.5-001  # or claude-3.5-sonnet etc.

   # Google Sheets
   SPREADSHEET_ID=your_spreadsheet_id_here

   # Email Configuration
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   EMAIL_RECIPIENTS=recipient1@example.com,recipient2@example.com
   ```

4. Configure Google Sheets:
   - Create a new Google Spreadsheet
   - Share it with the email from your service account
   - Copy the spreadsheet ID (from the URL) to your .env file

### Running the Bot

Start the bot with:

```
python main.py
```

## Usage

1. Start a chat with your bot on Telegram
2. Send a photo of a receipt or invoice
3. The bot will extract the information and save it to Google Sheets
4. Use commands to generate reports and analyze your spending:
   - `/start` - Start the bot
   - `/help` - Show help message
   - `/report` - Generate a financial report
   - `/analyze` - Analyze your financial data

## Model Context Protocol (MCP)

This bot implements the Model Context Protocol (MCP) design pattern, allowing it to:

1. Switch between different execution contexts (document processing, report generation, etc.)
2. Maintain state across interactions
3. Use structured data formats for communication with LLMs
4. Process multimodal inputs (text, images, PDFs)

The core MCP implementation is in the various service files, with the main interface in `main.py`.

## Development

### Adding New Features

To add new features:

1. Create appropriate handlers in `bot/handlers.py`
2. Implement the business logic in service classes
3. Update the models if needed
4. Register new command handlers in `main.py`

### Testing

Run tests with:

```
pytest
```

## License

[MIT License](LICENSE)

## Acknowledgements

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [VertexAI](https://cloud.google.com/vertex-ai)
- [Google Sheets API](https://developers.google.com/sheets/api)