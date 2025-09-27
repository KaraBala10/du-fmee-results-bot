# 🎓 علاماتي - Damascus University Results Bot

A professional Telegram bot for retrieving academic results for students at Damascus University - Faculty of Mechanical and Electrical Engineering.

## ✨ Features

- 📊 **Academic Year Filtering**: View results by specific academic year
- 🎯 **Specialization Support**: Separate tracks for Computer Engineering and Control Engineering
- 📈 **GPA Calculation**: Automatic calculation of final GPA from successful subjects
- ✅ **Comprehensive Results**: Display both successful and failed subjects
- 🔄 **Latest Attempts**: Show only the most recent attempt for each subject
- 📋 **Missing Subjects**: Identify subjects not yet attempted
- 👤 **Student Information**: Display student name and academic details
- 🚀 **Fast & Reliable**: Optimized web scraping with retry mechanisms

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Telegram Bot Token
- Internet connection

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd university_percentage
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**
   - Copy `.env.example` to `.env`: `cp .env.example .env`
   - Update the `BOT_TOKEN` in `.env` with your Telegram bot token
   - Ensure `subjects.txt` contains the subject lists for each academic year

4. **Run the bot**
   ```bash
   ./start_bot.sh
   ```
   
   Or directly:
   ```bash
   python telegram_bot.py
   ```

## 📱 Usage Guide

### For Students

1. **Start the bot**: Send `/start` to begin
2. **Enter student number**: Provide your 10-digit university ID
3. **Select academic year**: Choose from the available options:
   - Year 1, 2, 3 (General)
   - Year 4 - Computer Engineering
   - Year 4 - Control Engineering  
   - Year 5 - Computer Engineering
   - Year 5 - Control Engineering
4. **View results**: The bot will display your academic results with detailed statistics

### Available Commands

- `/start` - Initialize the bot and show welcome message
- `/help` - Display usage instructions
- `/get_marks` - Start the marks retrieval process

## 📊 Supported Academic Years

| Year | Specialization | Subjects Count |
|------|----------------|----------------|
| 1st Year | General | 14 subjects |
| 2nd Year | General | 14 subjects |
| 3rd Year | General | 12 subjects |
| 4th Year | Computer Engineering | 11 subjects |
| 4th Year | Control Engineering | 12 subjects |
| 5th Year | Computer Engineering | 8 subjects |
| 5th Year | Control Engineering | 8 subjects |

## 🏗️ Project Structure

```
university_percentage/
├── telegram_bot.py          # Main bot application
├── subjects.txt                 # Subject lists for each academic year
├── requirements.txt         # Python dependencies
├── start_bot.sh            # Bot startup script
├── deploy.sh               # Deployment script
└── README.md               # This file
```

## 🔧 Technical Details

### Core Components

- **Web Scraping**: Automated data extraction from university website
- **Session Management**: Persistent HTTP sessions with retry logic
- **Data Processing**: Intelligent filtering and deduplication
- **Error Handling**: Comprehensive error management and user feedback
- **Logging**: Detailed logging for debugging and monitoring

### Key Features

- **Smart Filtering**: Automatically filters subjects by academic year and specialization
- **Duplicate Handling**: Keeps only the latest attempt for repeated subjects
- **Result Validation**: Skips subjects without valid marks or results
- **Specialization Detection**: Handles both Computer and Control Engineering tracks
- **Arabic Support**: Full RTL support for Arabic text and numbers

## 🛠️ Development

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements.txt

# Run the bot in development mode
python telegram_bot.py
```

### Configuration

The bot requires the following configuration:

1. **Environment Setup**: 
   ```bash
   cp .env.example .env
   # Edit .env and add your bot token
   ```

2. **Telegram Bot Token**: Obtain from [@BotFather](https://t.me/botfather)
3. **University Website Access**: Ensure connectivity to the university results portal
4. **Subject Data**: Maintain `subjects.txt` with current subject lists

### Dependencies

- `python-telegram-bot`: Telegram Bot API wrapper
- `requests`: HTTP library for web scraping
- `beautifulsoup4`: HTML parsing
- `urllib3`: HTTP client with retry support

## 📈 Performance

- **Response Time**: < 5 seconds for result retrieval
- **Reliability**: 99%+ uptime with automatic retry mechanisms
- **Scalability**: Handles multiple concurrent users
- **Error Recovery**: Automatic retry on network failures

## 🔒 Security & Privacy

- **No Data Storage**: Student data is not permanently stored
- **Secure Communication**: All data transmission uses HTTPS
- **Input Validation**: Comprehensive validation of student numbers
- **Error Handling**: Secure error messages without sensitive information

## 🐛 Troubleshooting

### Common Issues

1. **"No results found"**
   - Verify student number is correct (10 digits)
   - Check if results are available for the selected year
   - Ensure university website is accessible

2. **"Connection error"**
   - Check internet connectivity
   - Verify university website is online
   - Bot will automatically retry

3. **"Invalid student number"**
   - Ensure the number is exactly 10 digits
   - Use university ID, not exam number

### Debug Mode

Enable detailed logging by setting the log level in `telegram_bot.py`:

```python
logging.basicConfig(level=logging.DEBUG)
```

## 📞 Support

For technical support or feature requests:

- **Developer**: [@karabala10](https://t.me/karabala10)
- **Issues**: Report bugs through the issue tracker
- **Documentation**: Check this README for common solutions

## 📄 License

This project is developed for educational purposes at Damascus University.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📊 Statistics

- **Supported Years**: 5 academic years
- **Specializations**: 2 (Computer & Control Engineering)
- **Total Subjects**: 79 unique subjects
- **Response Time**: < 5 seconds average
- **Uptime**: 99%+ reliability

---

**Note**: This bot is specifically designed for Damascus University - Faculty of Mechanical and Electrical Engineering students. Ensure you have the correct student number and are enrolled in the supported department.