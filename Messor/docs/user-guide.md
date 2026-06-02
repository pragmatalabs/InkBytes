# User Guide

A comprehensive guide to using Messor News Harvester for news scraping and content management.

## 🚀 Getting Started

### **Quick Start**
```bash
# Basic scraping (interactive mode)
python main.py

# Automated scraping with parameters
python main.py --scrape --limit=10

# Docker scheduled mode
docker-compose up -d
```

## 🎯 Usage Modes

### **1. Interactive CLI Mode**
The default mode that provides a command-line interface for manual control.

```bash
# Start interactive mode
python main.py

# Available commands:
# SCRAPE - Start scraping operation
# STATUS - Check system status
# ANALYTICS - View scraping statistics
# HELP - Show available commands
# EXIT - Quit application
```

**Example Session**:
```
Enter command: SCRAPE --limit=5
✅ Scraping 5 outlets...
📰 Found 127 articles from BBC
📰 Found 89 articles from Reuters
✅ Scraping completed in 2.3 minutes

Enter command: ANALYTICS
📊 Total articles scraped today: 1,234
📊 Active outlets: 25/27
📊 Success rate: 98.5%

Enter command: EXIT
```

### **2. One-Shot Mode**
Execute specific operations and exit.

```bash
# Scrape all configured outlets
python main.py --scrape

# Scrape with limit
python main.py --scrape --limit=10

# Scrape specific outlets
python main.py --scrape --outlet="bbc|https://www.bbc.com"

# Start with client dashboard
python main.py --client --scrape
```

### **3. Scheduled Mode (Docker)**
Continuous operation with automatic scheduling.

```bash
# Start scheduled mode
docker-compose up -d

# Check logs
docker-compose logs -f messor

# The container will:
# - Run scraping every 60 minutes (configurable)
# - Skip cycles if scraping is already running
# - Provide web dashboard at http://localhost:8585
```

## 📊 Web Dashboard

Access the web dashboard for real-time monitoring and control.

### **Starting the Dashboard**
```bash
# With Python installation
python main.py --client

# Access at http://localhost:5173 (development)
# Access at http://localhost:8585 (Docker)
```

### **Dashboard Features**

#### **Main Dashboard**
- **Real-time Status**: Current scraping progress
- **Article Counter**: Live count of articles found
- **Outlet Status**: Health of each news source
- **System Metrics**: Memory usage, uptime, errors

#### **Analytics View**
- **Historical Data**: Scraping trends over time
- **Outlet Performance**: Success rates and response times
- **Article Statistics**: Word counts, categories, languages
- **Error Tracking**: Failed scrapes and reasons

#### **Configuration Panel**
- **Outlet Management**: Add/remove news sources
- **Schedule Settings**: Modify scraping intervals
- **System Settings**: Logging levels, thread counts
- **Export Options**: Download scraped data

## 🔧 Command Reference

### **CLI Commands**

#### **SCRAPE Command**
```bash
# Basic scraping
SCRAPE

# With parameters
SCRAPE --limit=10
SCRAPE --outlet="name|url"
SCRAPE --limit=5 --outlet="custom|https://example.com"
```

**Parameters**:
- `--limit=N`: Scrape only N outlets
- `--outlet="name|url"`: Add custom outlet

#### **STATUS Command**
```bash
STATUS
```
Shows:
- System health
- Active scraping status
- Service connectivity (RabbitMQ, Storage)
- Memory and CPU usage

#### **ANALYTICS Command**
```bash
ANALYTICS
```
Displays:
- Today's scraping statistics
- Outlet success rates
- Article counts and trends
- Error summaries

#### **QUEUE Command**
```bash
QUEUE
```
Shows RabbitMQ queue status:
- Articles awaiting processing
- Message counts
- Queue health

### **Command Line Arguments**

#### **Basic Arguments**
```bash
python main.py [config_path] [options]
```

**Arguments**:
- `config_path`: Path to env.yaml (default: env.yaml)

**Options**:
- `--scrape`: Run scraping immediately
- `--client`: Start web dashboard
- `--schedule`: Run in scheduled mode
- `--no-browser`: Don't open browser automatically

#### **Usage Examples**
```bash
# Use default config
python main.py

# Use custom config
python main.py /path/to/custom.yaml

# Scrape and start dashboard
python main.py --scrape --client

# Scheduled mode (Docker)
python main.py --schedule

# Scrape without opening browser
python main.py --scrape --client --no-browser
```

## 📰 Understanding Scraping Results

### **Article Data Structure**
Each scraped article contains:
```json
{
  "title": "Article headline",
  "url": "https://source.com/article",
  "content": "Full article text",
  "outlet": "bbc",
  "timestamp": "2025-08-04T10:30:00Z",
  "word_count": 245,
  "language": "en",
  "categories": ["politics", "international"]
}
```

### **Storage Locations**

#### **Local Storage**
- **Articles Database**: `data/articles.db.json`
- **Raw Scrapes**: `data/scrapes/`
- **Processing History**: `data/history/`
- **Content Clusters**: `data/clusters/`

#### **Cloud Storage** (if configured)
- **Digital Ocean Spaces**: Automatic upload
- **Backup Location**: Redundant storage
- **Archive**: Long-term retention

### **Data Processing Pipeline**
```
1. Source Discovery → 2. Content Extraction → 3. Text Processing → 4. Storage → 5. Cloud Upload

┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Outlets   │ -> │   Scraper   │ -> │  Processor  │ -> │   Local     │ -> │   Cloud     │
│   Config    │    │   Engine    │    │   Filter    │    │  Storage    │    │  Storage    │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

## 🛠️ Configuration

### **Basic Configuration** (`env.yaml`)

#### **Application Settings**
```yaml
application:
  name: Messor
  mode: development  # development | production
  max_threads: 10   # Scraping concurrency
  
scraping:
  schedule_interval_minutes: 60  # Scheduled scraping interval
  min_word_count: 40            # Minimum article length
  
logging:
  level: INFO                   # DEBUG | INFO | WARNING | ERROR
  destinations:
    - console                   # Log to console
    - file                      # Log to file
    - rabbit                    # Log to RabbitMQ
```

#### **News Outlets** (`data/outlets/news_outlets_sources.json`)
```json
[
  {
    "name": "bbc",
    "url": "https://www.bbc.com/"
  },
  {
    "name": "reuters", 
    "url": "https://www.reuters.com/"
  }
]
```

### **Docker Configuration** (`docker/.env`)
```env
CONTAINER_NAME=messor
MODE=production
LOG_LEVEL=INFO
DOCKER_CONTAINER=true
```

## 📈 Monitoring and Analytics

### **Real-time Monitoring**
- **Dashboard**: Visual status updates
- **Logs**: Detailed operation logs
- **WebSocket**: Live progress updates
- **API**: Programmatic status checks

### **Performance Metrics**
- **Throughput**: Articles per minute
- **Success Rate**: Successful vs failed scrapes
- **Response Time**: Average outlet response time
- **Resource Usage**: Memory and CPU consumption

### **Health Checks**
```bash
# Check application health
curl http://localhost:8050/health

# Check scraping status
curl http://localhost:8050/scrape/status

# View system information
curl http://localhost:8050/system/info
```

## 🐛 Troubleshooting

### **Common Issues**

#### **No Articles Found**
```
Issue: Scraping completes but finds 0 articles
Causes:
- External API connection failed
- Local outlets file missing/empty
- Network connectivity issues

Solutions:
1. Check logs: tail -f logs/messor.log
2. Verify outlets file: cat data/outlets/news_outlets_sources.json
3. Test connectivity: ping bbc.com
4. Check API status: curl http://kloudsix.io:1337/api/news-outlets
```

#### **Scraping Locks Up**
```
Issue: Scraping process becomes unresponsive
Causes:
- External site blocking requests
- Memory exhaustion
- Network timeouts

Solutions:
1. Check system resources: top, free -h
2. Restart application: docker-compose restart
3. Reduce thread count in env.yaml
4. Check outlet response times in logs
```

#### **Docker Volume Issues**
```
Issue: Data not persisting between container restarts
Causes:
- Incorrect volume mounting
- Permission issues
- Docker configuration errors

Solutions:
1. Run setup script: ./docker/setup-host-directories.sh
2. Check volumes: docker-compose ps
3. Verify permissions: ls -la data/
4. Check Docker logs: docker-compose logs messor
```

### **Log Analysis**
```bash
# View recent logs
tail -100 logs/messor.log

# Filter by error level
grep "ERROR" logs/messor.log

# Search for specific component
grep "scraper_service" logs/messor.log

# Monitor live logs
tail -f logs/messor.log | grep "Starting\|Completed\|Error"
```

### **Performance Tuning**
```yaml
# Optimize for performance
application:
  max_threads: 20              # Increase for faster scraping
  
scraping:
  min_word_count: 100          # Higher = fewer but quality articles
  
logging:
  level: WARNING               # Reduce log verbosity
```

## 📚 Advanced Usage

### **API Integration**
```python
import requests

# Start scraping via API
response = requests.post('http://localhost:8050/scrape', 
                        json={'limit': 10})

# Monitor progress
status = requests.get('http://localhost:8050/scrape/status')
print(f"Progress: {status.json()['progress']}")
```

### **Custom Outlets**
```bash
# Add custom news source
SCRAPE --outlet="techcrunch|https://techcrunch.com"

# Multiple custom outlets
SCRAPE --outlet="tech|https://techcrunch.com" --outlet="news|https://cnn.com"
```

### **Batch Operations**
```bash
# Process specific outlet list
for outlet in bbc reuters cnn; do
  python main.py --scrape --outlet="$outlet|https://$outlet.com"
done
```

## 🆘 Getting Help

### **Documentation Resources**
- **[Installation Guide](./installation.md)** - Setup instructions
- **[Configuration Guide](./configuration.md)** - Detailed configuration
- **[API Reference](./api-reference.md)** - Programmatic access
- **[Docker Guide](./docker.md)** - Container deployment

### **Support Channels**
- **Logs**: Always check `logs/messor.log` first
- **Health Check**: Use `/health` endpoint
- **Documentation**: Comprehensive guides in `/docs`
- **Issues**: Report bugs with log excerpts

### **Debug Mode**
```bash
# Enable verbose logging
LOG_LEVEL=DEBUG python main.py

# Docker debug mode
docker-compose logs -f messor

# API debug
curl -v http://localhost:8050/system/info
```