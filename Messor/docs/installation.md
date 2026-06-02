# Installation Guide

This guide covers all installation methods for Messor News Harvester.

## 📋 Prerequisites

### **System Requirements**
- **Python**: 3.11 or higher
- **Node.js**: 16+ (for client dashboard)
- **Docker**: Latest version (for containerized deployment)
- **Git**: For source code management

### **External Services**
- **RabbitMQ Server**: Message queuing
- **Digital Ocean Spaces**: Cloud storage (optional)
- **Strapi CMS**: Configuration management (optional)

## 🐍 Python Installation (Development)

### **1. Clone Repository**
```bash
git clone <repository-url>
cd Messor
```

### **2. Setup Python Environment**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **3. Install InkBytes Libraries**
```bash
# Make script executable
chmod +x scripts/install_inkbytes_libraries.sh

# Install libraries
./scripts/install_inkbytes_libraries.sh
```

### **4. Configure Application**
```bash
# Copy configuration template
cp env.yaml.example env.yaml

# Edit configuration (see Configuration Guide)
nano env.yaml
```

### **5. Verify Installation**
```bash
# Run basic validation
python main.py --help

# Test with dry run
python main.py --scrape --limit=1
```

## 🐳 Docker Installation (Recommended)

### **1. Prerequisites**
```bash
# Ensure Docker is installed and running
docker --version
docker-compose --version
```

### **2. Setup Project Structure**
```bash
# Clone repository
git clone <repository-url>
cd Messor

# Verify project structure
cd docker
./setup-host-directories.sh
```

### **3. Configure Environment**
```bash
# Copy environment template
cd docker
cp example.changeme.env .env

# Edit container settings
nano .env

# Configure application (in project root)
cd ..
cp env.yaml.example env.yaml
nano env.yaml
```

### **4. Deploy Container**
```bash
# Development deployment
cd docker
docker-compose -f docker-compose.local.yaml up -d

# Production deployment
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs messor
```

### **5. Verify Docker Installation**
```bash
# Check container health
docker exec messor python main.py --help

# View logs
docker-compose logs -f messor

# Access container shell
docker exec -it messor bash
```

## 🌐 Client Dashboard Setup (Optional)

### **1. Install Node.js Dependencies**
```bash
cd client
npm install
```

### **2. Development Mode**
```bash
# Start development server
npm run dev

# Access dashboard at http://localhost:5173
```

### **3. Production Build**
```bash
# Build for production
npm run build

# Serve production build
npm run preview
```

## ⚙️ Configuration

### **1. Basic Configuration** (`env.yaml`)
```yaml
application:
  name: Messor
  mode: development
  max_threads: 10

scraping:
  schedule_interval_minutes: 60
  min_word_count: 40

logging:
  level: INFO
  destinations:
    - console
    - file
```

### **2. Docker Environment** (`.env`)
```env
CONTAINER_NAME=messor
MODE=development
LOG_LEVEL=INFO
```

### **3. External Services**
Configure external service connections in `env.yaml`:
- RabbitMQ connection settings
- Digital Ocean Spaces credentials
- Strapi CMS endpoints

## 🔧 Verification Steps

### **1. Basic Functionality**
```bash
# Test configuration loading
python main.py

# Test scraping (dry run)
python main.py --scrape --limit=1

# Test API server
curl http://localhost:8050/health
```

### **2. Docker Functionality**
```bash
# Test scheduled mode
docker-compose logs messor | grep "SCHEDULED MODE"

# Test volume mounting
docker exec messor ls -la /app/data

# Test configuration
docker exec messor cat /app/env.yaml
```

### **3. Client Dashboard**
```bash
# Verify client build
cd client && npm run build

# Test client server
npm run dev
# Visit http://localhost:5173
```

## 🐛 Troubleshooting

### **Common Issues**

#### **Python Environment**
```bash
# Issue: Module not found
# Solution: Verify virtual environment activation
source venv/bin/activate
pip list | grep inkbytes

# Issue: Permission denied on scripts
# Solution: Make scripts executable
chmod +x scripts/*.sh
```

#### **Docker Issues**
```bash
# Issue: Volume mount failures
# Solution: Verify project structure
./docker/setup-host-directories.sh

# Issue: Container won't start
# Solution: Check logs and configuration
docker-compose logs messor
docker exec messor python -c "import core.config"
```

#### **Network Connectivity**
```bash
# Issue: Cannot connect to external services
# Solution: Test connectivity
ping kloudsix.io
telnet kloudsix.io 5672

# Issue: API not accessible
# Solution: Check port bindings
docker-compose ps
netstat -tulpn | grep 8050
```

### **Log Analysis**
```bash
# View application logs
tail -f logs/messor.log

# View Docker logs
docker-compose logs -f messor

# Debug mode
LOG_LEVEL=DEBUG python main.py
```

## 📚 Next Steps

After successful installation:

1. **[Configuration Guide](./configuration.md)** - Detailed configuration options
2. **[User Guide](./user-guide.md)** - How to use Messor
3. **[Docker Guide](./docker.md)** - Advanced Docker usage
4. **[Development Guide](./development.md)** - Contributing to the project

## 🆘 Getting Help

- **Documentation**: Check the full documentation in `/docs`
- **Issues**: Report problems via the issue tracker
- **Logs**: Always include relevant log files when reporting issues
- **Configuration**: Verify your `env.yaml` matches the expected format