# API Reference

Messor provides a RESTful API built with FastAPI for programmatic access to news scraping functionality.

## 🌐 Base URL

**Local Development**: `http://localhost:8050`  
**Docker Container**: `http://localhost:8585`

## 🔐 Authentication

Currently, the API uses basic authentication mechanisms. Future versions will implement JWT tokens.

```http
Authorization: Bearer <token>
Content-Type: application/json
```

## 📋 API Endpoints

### **Health Check**

#### `GET /health`
Returns the health status of the application.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-04T10:30:00Z",
  "version": "1.0.0"
}
```

**Status Codes**:
- `200` - Service is healthy
- `503` - Service unavailable

---

### **Scraping Operations**

#### `POST /scrape`
Initiates a news scraping operation.

**Request Body**:
```json
{
  "limit": 10,
  "outlets": ["bbc", "reuters"],
  "custom_outlet": {
    "name": "example",
    "url": "https://example.com"
  }
}
```

**Parameters**:
- `limit` (optional): Maximum number of outlets to scrape
- `outlets` (optional): Specific outlet names to scrape
- `custom_outlet` (optional): Custom outlet configuration

**Response**:
```json
{
  "status": "started",
  "session_id": "sess_20250804_103000",
  "outlets_count": 5,
  "estimated_duration": "2-5 minutes"
}
```

**Status Codes**:
- `200` - Scraping started successfully
- `400` - Invalid parameters
- `409` - Scraping already in progress
- `500` - Internal server error

#### `GET /scrape/status`
Returns the current scraping status.

**Response**:
```json
{
  "active": true,
  "session_id": "sess_20250804_103000",
  "progress": {
    "outlets_processed": 3,
    "outlets_total": 5,
    "articles_found": 127,
    "start_time": "2025-08-04T10:30:00Z",
    "elapsed_seconds": 145
  }
}
```

**Status Codes**:
- `200` - Status retrieved successfully
- `404` - No active scraping session

#### `POST /scrape/stop`
Stops the current scraping operation.

**Response**:
```json
{
  "status": "stopped",
  "session_id": "sess_20250804_103000",
  "reason": "user_requested"
}
```

**Status Codes**:
- `200` - Scraping stopped successfully
- `404` - No active scraping session

---

### **Analytics & Reporting**

#### `GET /analytics/summary`
Returns scraping analytics and statistics.

**Query Parameters**:
- `period` (optional): `day`, `week`, `month` (default: `day`)
- `outlet` (optional): Filter by specific outlet

**Response**:
```json
{
  "period": "day",
  "total_articles": 1534,
  "total_outlets": 25,
  "average_articles_per_outlet": 61.36,
  "scraping_sessions": 12,
  "last_updated": "2025-08-04T10:30:00Z",
  "outlets": [
    {
      "name": "bbc",
      "articles_count": 89,
      "last_scraped": "2025-08-04T09:15:00Z",
      "success_rate": 98.5
    }
  ]
}
```

#### `GET /analytics/outlets`
Returns detailed outlet performance statistics.

**Response**:
```json
{
  "outlets": [
    {
      "name": "bbc",
      "url": "https://www.bbc.com/",
      "status": "active",
      "total_articles": 1250,
      "last_successful_scrape": "2025-08-04T09:15:00Z",
      "success_rate": 98.5,
      "average_response_time": 1.2,
      "error_count": 3
    }
  ],
  "summary": {
    "total_outlets": 25,
    "active_outlets": 23,
    "failed_outlets": 2
  }
}
```

---

### **System Information**

#### `GET /system/info`
Returns system information and configuration.

**Response**:
```json
{
  "application": {
    "name": "Messor",
    "version": "1.0.0",
    "mode": "development",
    "uptime_seconds": 3600
  },
  "system": {
    "python_version": "3.11.0",
    "platform": "linux",
    "docker_container": true,
    "memory_usage": "245MB",
    "cpu_usage": "15%"
  },
  "services": {
    "rabbitmq_connected": true,
    "storage_available": true,
    "api_server_running": true
  }
}
```

#### `GET /system/logs`
Returns recent application logs.

**Query Parameters**:
- `lines` (optional): Number of log lines to return (default: 100)
- `level` (optional): Log level filter (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

**Response**:
```json
{
  "logs": [
    {
      "timestamp": "2025-08-04T10:30:00Z",
      "level": "INFO",
      "message": "Scraping session completed successfully",
      "component": "scraper_service"
    }
  ],
  "total_lines": 100,
  "filtered": false
}
```

---

### **Configuration Management**

#### `GET /config/outlets`
Returns configured news outlets.

**Response**:
```json
{
  "outlets": [
    {
      "name": "bbc",
      "url": "https://www.bbc.com/",
      "active": true,
      "last_modified": "2025-08-04T08:00:00Z"
    }
  ],
  "source": "api",
  "fallback_available": true
}
```

#### `POST /config/outlets`
Adds or updates outlet configuration.

**Request Body**:
```json
{
  "name": "example_news",
  "url": "https://example-news.com/",
  "active": true
}
```

**Response**:
```json
{
  "status": "updated",
  "outlet": {
    "name": "example_news",
    "url": "https://example-news.com/",
    "active": true,
    "created": "2025-08-04T10:30:00Z"
  }
}
```

## 🔄 WebSocket Endpoints

### **Real-time Updates**

#### `WS /ws/scraping`
WebSocket connection for real-time scraping updates.

**Connection**: `ws://localhost:8050/ws/scraping`

**Message Types**:

**Status Update**:
```json
{
  "type": "status_update",
  "data": {
    "outlets_processed": 3,
    "articles_found": 45,
    "current_outlet": "reuters"
  }
}
```

**Article Found**:
```json
{
  "type": "article_found",
  "data": {
    "title": "Breaking News Title",
    "url": "https://example.com/article",
    "outlet": "bbc",
    "timestamp": "2025-08-04T10:30:00Z"
  }
}
```

**Session Complete**:
```json
{
  "type": "session_complete",
  "data": {
    "session_id": "sess_20250804_103000",
    "total_articles": 234,
    "duration_seconds": 320
  }
}
```

## 📊 Response Format

### **Standard Response Structure**
```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed successfully",
  "timestamp": "2025-08-04T10:30:00Z",
  "request_id": "req_abc123"
}
```

### **Error Response Structure**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid parameter: limit must be between 1 and 100",
    "details": {
      "field": "limit",
      "value": 150,
      "constraint": "max_value"
    }
  },
  "timestamp": "2025-08-04T10:30:00Z",
  "request_id": "req_xyz789"
}
```

## 🚨 Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `VALIDATION_ERROR` | Invalid request parameters | 400 |
| `SCRAPING_IN_PROGRESS` | Another scraping operation is active | 409 |
| `SERVICE_UNAVAILABLE` | External service connection failed | 503 |
| `STORAGE_ERROR` | Data storage operation failed | 500 |
| `AUTHENTICATION_FAILED` | Invalid or missing authentication | 401 |
| `RATE_LIMIT_EXCEEDED` | Too many requests | 429 |

## 🔧 Rate Limiting

- **Scraping Operations**: 1 request per minute
- **Analytics Queries**: 60 requests per hour
- **System Information**: 30 requests per minute

## 📝 Usage Examples

### **Python**
```python
import requests
import json

# Start scraping
response = requests.post('http://localhost:8050/scrape', 
                        json={'limit': 5})
session = response.json()

# Check status
status = requests.get('http://localhost:8050/scrape/status')
print(status.json())

# Get analytics
analytics = requests.get('http://localhost:8050/analytics/summary')
print(analytics.json())
```

### **JavaScript**
```javascript
// Start scraping
const response = await fetch('http://localhost:8050/scrape', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ limit: 5 })
});
const session = await response.json();

// WebSocket connection
const ws = new WebSocket('ws://localhost:8050/ws/scraping');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data);
};
```

### **cURL**
```bash
# Start scraping
curl -X POST http://localhost:8050/scrape \
  -H "Content-Type: application/json" \
  -d '{"limit": 5}'

# Get status
curl http://localhost:8050/scrape/status

# Get system info
curl http://localhost:8050/system/info
```

## 📚 OpenAPI Documentation

The complete API specification is available at:
- **Swagger UI**: `http://localhost:8050/docs`
- **ReDoc**: `http://localhost:8050/redoc`
- **OpenAPI JSON**: `http://localhost:8050/openapi.json`