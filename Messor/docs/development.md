# Development Guide

A comprehensive guide for developers contributing to or extending Messor News Harvester.

## 🛠️ Development Environment Setup

### **Prerequisites**
- **Python 3.11+** with pip and venv
- **Node.js 16+** with npm
- **Git** for version control
- **Docker** for testing containerization
- **IDE** with Python support (VS Code, PyCharm)

### **Initial Setup**
```bash
# Clone repository
git clone <repository-url>
cd Messor

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # If exists

# Install InkBytes libraries
chmod +x scripts/install_inkbytes_libraries.sh
./scripts/install_inkbytes_libraries.sh

# Install pre-commit hooks
pre-commit install

# Setup client development
cd client
npm install
cd ..
```

### **IDE Configuration**

#### **VS Code Settings** (`.vscode/settings.json`)
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests/"],
  "editor.formatOnSave": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/venv": true,
    "**/node_modules": true
  }
}
```

#### **PyCharm Configuration**
- **Interpreter**: Set to `./venv/bin/python`
- **Code Style**: Follow PEP 8
- **Run Configurations**: Create for main.py with different args
- **Test Runner**: Configure pytest

## 🏗️ Project Structure

### **Directory Layout**
```
Messor/
├── api/                    # FastAPI REST endpoints
│   ├── main.py            # API server entry point
│   ├── routers/           # API route handlers
│   └── utils/             # API utilities
├── client/                # React dashboard
│   ├── src/               # Frontend source code
│   ├── public/            # Static assets
│   └── package.json       # Node.js dependencies
├── core/                  # Core application logic
│   ├── application.py     # Main orchestrator
│   ├── command_processor.py # CLI handling
│   └── config.py          # Configuration management
├── data/                  # Data storage (mounted in Docker)
│   ├── outlets/           # News source configurations
│   ├── scrapes/           # Raw scraped content
│   └── history/           # Processing history
├── docker/                # Docker configurations
│   ├── Dockerfile         # Container definition
│   └── docker-compose.yaml # Service orchestration
├── docs/                  # Documentation
├── logs/                  # Application logs
├── services/              # Business logic services
│   ├── scraper_service.py # Web scraping
│   ├── outlet_service.py  # Source management
│   └── storage_service.py # Data persistence
├── scripts/               # Utility scripts
├── tests/                 # Test suite
├── main.py               # Application entry point
├── env.yaml              # Configuration file
└── requirements.txt      # Python dependencies
```

### **Code Organization Principles**

#### **Separation of Concerns**
- **Core**: Application lifecycle and orchestration
- **Services**: Business logic and external integrations
- **API**: HTTP interface and routing
- **Client**: User interface and visualization

#### **Dependency Injection**
```python
# Services receive dependencies via constructor
class ScraperService:
    def __init__(self, config, logger, outlet_service, storage_service):
        self.config = config
        self.logger = logger
        self.outlet_service = outlet_service
        self.storage_service = storage_service

# Application injects dependencies
scraper_service = ScraperService(
    config, logger, outlet_service, storage_service
)
```

#### **Configuration Management**
```python
# Centralized configuration access
class Config:
    def __init__(self, config_path: str):
        self._config = ConfigLoader(config_path)
    
    @property
    def scraping(self):
        return self._config.scraping
    
    def get_schedule_interval_minutes(self):
        return getattr(self._config.scraping, 'schedule_interval_minutes', 60)
```

## 📝 Coding Standards

### **Python Style Guide**
- **PEP 8**: Standard Python style guidelines
- **PEP 257**: Docstring conventions
- **Type Hints**: Use for all function parameters and returns
- **Line Length**: Maximum 88 characters (Black formatter)

#### **Docstring Format** (Google Style)
```python
def scrape_outlet(self, outlet: OutletsSource, limit: Optional[int] = None) -> List[Article]:
    """Scrape articles from a specific news outlet.
    
    Args:
        outlet: The news outlet configuration to scrape
        limit: Maximum number of articles to extract
        
    Returns:
        List of successfully scraped articles
        
    Raises:
        ConnectionError: When outlet is unreachable
        ValidationError: When outlet configuration is invalid
        
    Example:
        >>> articles = scraper.scrape_outlet(bbc_outlet, limit=10)
        >>> print(f"Found {len(articles)} articles")
    """
```

#### **Error Handling**
```python
# Specific exception handling with logging
try:
    articles = self.scrape_outlet(outlet)
except ConnectionError as e:
    self.logger.error(f"Failed to connect to {outlet.name}: {e}")
    return []
except Exception as e:
    self.logger.error(f"Unexpected error scraping {outlet.name}: {e}", 
                     exc_info=True)
    raise
```

### **JavaScript/TypeScript Standards**
- **ES6+**: Modern JavaScript features
- **TypeScript**: Strict type checking enabled
- **Functional Components**: React hooks pattern
- **ESLint**: Code quality enforcement

#### **Component Structure**
```typescript
interface DashboardProps {
  scrapingStatus: ScrapingStatus;
  onStartScraping: () => void;
}

const Dashboard: React.FC<DashboardProps> = ({ 
  scrapingStatus, 
  onStartScraping 
}) => {
  const [articles, setArticles] = useState<Article[]>([]);
  
  useEffect(() => {
    // Component logic
  }, [scrapingStatus]);
  
  return (
    <div className="dashboard">
      {/* JSX content */}
    </div>
  );
};

export default Dashboard;
```

## 🧪 Testing Strategy

### **Test Structure**
```
tests/
├── unit/                  # Unit tests
│   ├── test_services/     # Service layer tests
│   ├── test_core/         # Core logic tests
│   └── test_api/          # API endpoint tests
├── integration/           # Integration tests
│   ├── test_scraping_flow.py
│   └── test_storage_flow.py
├── e2e/                   # End-to-end tests
│   └── test_full_workflow.py
├── fixtures/              # Test data and mocks
└── conftest.py           # Pytest configuration
```

### **Unit Testing**
```python
# tests/unit/test_services/test_scraper_service.py
import pytest
from unittest.mock import Mock, patch
from services.scraper_service import ScraperService

class TestScraperService:
    @pytest.fixture
    def scraper_service(self):
        config = Mock()
        logger = Mock()
        outlet_service = Mock()
        storage_service = Mock()
        message_service = Mock()
        
        return ScraperService(
            config, logger, outlet_service, 
            storage_service, message_service
        )
    
    def test_execute_scraping_process_success(self, scraper_service):
        # Arrange
        scraper_service.outlet_service.get_outlets.return_value = [
            Mock(name="bbc", url="https://bbc.com")
        ]
        
        # Act
        result = scraper_service.execute_scraping_process(limit=1)
        
        # Assert
        assert result is not None
        scraper_service.outlet_service.get_outlets.assert_called_once()
    
    @patch('services.scraper_service.requests.get')
    def test_scrape_outlet_connection_error(self, mock_get, scraper_service):
        # Arrange
        mock_get.side_effect = ConnectionError("Network error")
        outlet = Mock(name="test", url="https://test.com")
        
        # Act & Assert
        with pytest.raises(ConnectionError):
            scraper_service.scrape_outlet(outlet)
```

### **Integration Testing**
```python
# tests/integration/test_scraping_flow.py
import pytest
import tempfile
import os
from core.application import Application

class TestScrapingFlow:
    @pytest.fixture
    def temp_config(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
application:
  name: TestMessor
  mode: test
scraping:
  min_word_count: 10
logging:
  level: DEBUG
""")
            config_path = f.name
        
        yield config_path
        os.unlink(config_path)
    
    def test_full_scraping_workflow(self, temp_config):
        # Test complete scraping workflow
        app = Application(temp_config)
        
        # Mock external dependencies
        with patch('services.outlet_service.OutletsManagerAPI'):
            result = app.command_processor.execute_scraping()
            
        assert result is not None
```

### **API Testing**
```python
# tests/unit/test_api/test_scrape_endpoints.py
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_scrape_endpoint():
    response = client.post("/scrape", json={"limit": 5})
    assert response.status_code == 200
    assert "session_id" in response.json()

def test_scrape_status_endpoint():
    response = client.get("/scrape/status")
    assert response.status_code in [200, 404]  # 404 if no active session
```

### **Running Tests**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_services/test_scraper_service.py

# Run with verbose output
pytest -v

# Run integration tests only
pytest tests/integration/

# Run and stop on first failure
pytest -x
```

## 🔄 Development Workflow

### **Git Workflow**
```bash
# Create feature branch
git checkout -b feature/new-scraping-algorithm

# Make changes with descriptive commits
git add .
git commit -m "Add improved article extraction algorithm

- Implement BeautifulSoup-based content parser
- Add content quality scoring
- Include language detection
- Handle malformed HTML gracefully"

# Push and create pull request
git push origin feature/new-scraping-algorithm
```

### **Commit Message Format**
```
<type>(<scope>): <description>

[Optional body explaining the changes]

[Optional footer with breaking changes or issue references]
```

**Types**: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

**Examples**:
```
feat(scraper): add content quality scoring
fix(storage): handle null article content
docs(api): update endpoint documentation
test(services): add outlet service unit tests
```

### **Code Review Checklist**
- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New functionality has tests
- [ ] Documentation updated
- [ ] No secrets in code
- [ ] Error handling implemented
- [ ] Logging added where appropriate

## 🚀 Release Process

### **Version Management**
```python
# core/application.py
class Application:
    VERSION = "1.2.0"  # Semantic versioning
```

### **Release Steps**
1. **Update Version**: Bump version in `core/application.py`
2. **Update Changelog**: Document changes in `CHANGELOG.md`
3. **Run Tests**: Ensure all tests pass
4. **Build Docker**: Test container build
5. **Tag Release**: Create Git tag
6. **Deploy**: Update production environment

### **Semantic Versioning**
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## 🧩 Adding New Features

### **Service Development**
```python
# services/new_service.py
from typing import Optional
import logging

class NewService:
    """Template for new service implementation."""
    
    def __init__(self, config, logger: logging.Logger, **dependencies):
        """Initialize service with dependencies."""
        self.config = config
        self.logger = logger
        # Initialize dependencies
    
    def start(self) -> bool:
        """Start the service."""
        try:
            # Service initialization logic
            self.logger.info("NewService started successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to start NewService: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the service gracefully."""
        try:
            # Cleanup logic
            self.logger.info("NewService stopped successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to stop NewService: {e}")
            return False
    
    def health_check(self) -> dict:
        """Return service health status."""
        return {
            "service": "NewService",
            "status": "healthy",
            "details": {}
        }
```

### **API Endpoint Development**
```python
# api/routers/new_endpoint.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/new", tags=["new-feature"])

class RequestModel(BaseModel):
    parameter: str
    optional_param: Optional[int] = None

class ResponseModel(BaseModel):
    result: str
    status: str

@router.post("/endpoint", response_model=ResponseModel)
async def new_endpoint(request: RequestModel):
    """New API endpoint implementation."""
    try:
        # Endpoint logic
        return ResponseModel(
            result="success",
            status="completed"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### **Configuration Extensions**
```python
# core/config.py - Add new configuration section
@property
def new_feature(self):
    return self._config.new_feature

def get_new_feature_setting(self):
    """Get new feature configuration with fallback."""
    try:
        return getattr(self._config.new_feature, 'setting', 'default_value')
    except AttributeError:
        return 'default_value'
```

## 🐛 Debugging

### **Logging Configuration**
```python
# Enhanced logging for debugging
import logging

# Set debug level
logging.basicConfig(level=logging.DEBUG)

# Component-specific logging
logger = logging.getLogger('scraper_service')
logger.setLevel(logging.DEBUG)

# Structured logging
logger.info("Scraping started", extra={
    "component": "scraper_service",
    "session_id": session_id,
    "outlet_count": len(outlets)
})
```

### **Debug Mode**
```bash
# Run with debug logging
LOG_LEVEL=DEBUG python main.py

# Debug specific component
COMPONENT_DEBUG=scraper_service python main.py

# Profile performance
python -m cProfile -o profile.stats main.py --scrape
```

### **Common Debugging Techniques**
```python
# Add breakpoints for debugging
import pdb; pdb.set_trace()

# Temporary debug prints
print(f"DEBUG: Variable value = {variable}")

# Assert statements for validation
assert len(articles) > 0, "No articles were scraped"

# Exception context
try:
    risky_operation()
except Exception as e:
    logger.error(f"Context: {context_info}", exc_info=True)
    raise
```

## 📊 Performance Optimization

### **Profiling**
```python
# Profile specific functions
import cProfile
import pstats

def profile_scraping():
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Run scraping operation
    scraper.execute_scraping_process()
    
    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative').print_stats(10)
```

### **Memory Optimization**
```python
# Use generators for large datasets
def process_articles():
    for article in scrape_articles():  # Generator
        yield process_article(article)

# Clear large objects when done
del large_data_structure

# Monitor memory usage
import psutil
process = psutil.Process()
memory_mb = process.memory_info().rss / 1024 / 1024
logger.info(f"Memory usage: {memory_mb:.1f} MB")
```

## 🔐 Security Considerations

### **Input Validation**
```python
from pydantic import BaseModel, validator

class ScrapingRequest(BaseModel):
    limit: int
    outlets: List[str]
    
    @validator('limit')
    def validate_limit(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Limit must be between 1 and 100')
        return v
```

### **Secret Management**
```python
# Never commit secrets
API_KEY = os.getenv('STRAPI_API_KEY')
if not API_KEY:
    raise ValueError("STRAPI_API_KEY environment variable required")

# Use environment variables or secret management
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///default.db')
```

## 📚 Resources

### **Documentation**
- **[Architecture Overview](./architecture.md)** - System design
- **[API Reference](./api-reference.md)** - Endpoint documentation
- **[Component Docs](./components/)** - Detailed component info

### **External Resources**
- **Python**: [PEP 8](https://pep8.org/), [Type Hints](https://docs.python.org/3/library/typing.html)
- **FastAPI**: [Documentation](https://fastapi.tiangolo.com/)
- **React**: [Hooks Guide](https://reactjs.org/docs/hooks-intro.html)
- **Docker**: [Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### **Development Tools**
- **Black**: Code formatting
- **Pylint**: Code quality
- **Pytest**: Testing framework
- **Pre-commit**: Git hooks
- **Docker Compose**: Local development