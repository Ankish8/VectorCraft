# VectorCraft API Documentation

## Overview

VectorCraft provides both synchronous and asynchronous APIs for image vectorization. The async API is recommended for production use as it provides better scalability and doesn't block the request thread.

## Base URL

```
http://localhost:8080/api
```

## Authentication

All API endpoints require authentication. Login to get session cookies:

```bash
POST /login
Content-Type: application/x-www-form-urlencoded

username=your_username&password=your_password
```

## Synchronous API (Legacy)

### Vectorize Image

```bash
POST /api/vectorize
Content-Type: multipart/form-data

file: <image_file>
strategy: vtracer_high_fidelity | experimental_v2 | vtracer_experimental
target_time: 60.0
filter_speckle: 4
color_precision: 8
layer_difference: 8
corner_threshold: 90
length_threshold: 1.0
splice_threshold: 20
curve_fitting: spline
use_palette: false
selected_palette: [optional palette JSON]
```

**Response:**
```json
{
  "success": true,
  "processing_time": 45.2,
  "strategy_used": "vtracer_high_fidelity",
  "quality_score": 0.92,
  "svg_content": "<svg>...</svg>",
  "svg_b64": "base64_encoded_svg",
  "download_url": "/download/result.svg"
}
```

### Extract Palettes

```bash
POST /api/extract-palettes
Content-Type: multipart/form-data

file: <image_file>
```

**Response:**
```json
{
  "success": true,
  "palettes": {
    "vibrant": [[255, 0, 0], [0, 255, 0], [0, 0, 255]],
    "muted": [[128, 64, 64], [64, 128, 64], [64, 64, 128]]
  }
}
```

## Asynchronous API (Recommended)

### Submit Vectorization Task

```bash
POST /api/async/vectorize
Content-Type: multipart/form-data

file: <image_file>
strategy: vtracer_high_fidelity | experimental_v2 | vtracer_experimental
target_time: 60.0
filter_speckle: 4
color_precision: 8
layer_difference: 8
corner_threshold: 90
length_threshold: 1.0
splice_threshold: 20
curve_fitting: spline
use_palette: false
selected_palette: [optional palette JSON]
```

**Response:**
```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "status": "submitted",
  "message": "Vectorization task submitted successfully",
  "estimated_time": 60.0,
  "tracking_url": "/api/async/status/abc123-def456-ghi789"
}
```

### Submit Batch Vectorization Task

```bash
POST /api/async/batch-vectorize
Content-Type: multipart/form-data

files: <multiple_image_files>
strategy: vtracer_high_fidelity
target_time: 60.0
[... other parameters ...]
```

**Response:**
```json
{
  "success": true,
  "task_id": "batch123-def456-ghi789",
  "status": "submitted",
  "message": "Batch vectorization task submitted successfully",
  "total_files": 5,
  "estimated_time": 300.0,
  "tracking_url": "/api/async/status/batch123-def456-ghi789"
}
```

### Submit Palette Extraction Task

```bash
POST /api/async/extract-palettes
Content-Type: multipart/form-data

file: <image_file>
```

**Response:**
```json
{
  "success": true,
  "task_id": "palette123-def456-ghi789",
  "status": "submitted",
  "message": "Palette extraction task submitted successfully",
  "tracking_url": "/api/async/status/palette123-def456-ghi789"
}
```

### Check Task Status

```bash
GET /api/async/status/{task_id}
```

**Response:**
```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "status": "PROCESSING",
  "progress": {
    "status": "Vectorizing image...",
    "progress": 45,
    "current_step": "edge_detection"
  },
  "created_at": "2023-12-01T10:00:00Z",
  "started_at": "2023-12-01T10:00:05Z",
  "completed_at": null,
  "error": null,
  "runtime": 25.5
}
```

### Get Task Result

```bash
GET /api/async/result/{task_id}
GET /api/async/result/{task_id}?timeout=30
```

**Response:**
```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "result": {
    "success": true,
    "processing_time": 45.2,
    "strategy_used": "vtracer_high_fidelity",
    "quality_score": 0.92,
    "svg_content": "<svg>...</svg>",
    "svg_b64": "base64_encoded_svg",
    "download_url": "/download/result.svg"
  }
}
```

### Cancel Task

```bash
POST /api/async/cancel/{task_id}
```

**Response:**
```json
{
  "success": true,
  "task_id": "abc123-def456-ghi789",
  "message": "Task cancelled successfully"
}
```

### Get Queue Statistics

```bash
GET /api/async/queue-stats
GET /api/async/queue-stats?queue=vectorization
```

**Response:**
```json
{
  "success": true,
  "queue_stats": {
    "active_tasks": 3,
    "scheduled_tasks": 1,
    "reserved_tasks": 0,
    "workers": [
      {
        "worker": "worker@hostname",
        "active_tasks": 2,
        "tasks": [...]
      }
    ]
  },
  "timestamp": "2023-12-01T10:00:00Z"
}
```

### Get API Metrics (Admin Only)

```bash
GET /api/async/metrics
```

**Response:**
```json
{
  "success": true,
  "metrics": {
    "tasks": {
      "total_tasks": 1250,
      "successful_tasks": 1200,
      "failed_tasks": 45,
      "cancelled_tasks": 5,
      "success_rate": 96.0,
      "avg_processing_time": 42.5
    },
    "queues": {
      "active_tasks": 3,
      "scheduled_tasks": 1,
      "reserved_tasks": 0
    },
    "workers": {
      "worker@hostname": {
        "info": {...},
        "stats": {...}
      }
    },
    "redis": {
      "connected_clients": 5,
      "used_memory": 1024000,
      "used_memory_human": "1.0M"
    }
  }
}
```

### System Health Check

```bash
GET /api/async/health
```

**Response:**
```json
{
  "success": true,
  "health": {
    "overall_healthy": true,
    "components": {
      "task_queue": {
        "healthy": true,
        "celery_healthy": true,
        "redis_healthy": true,
        "response_time_ms": 5.2,
        "active_workers": 1,
        "total_active_tasks": 3
      },
      "redis": {
        "connected": true,
        "status": "healthy",
        "response_time_ms": 1.2
      },
      "vectorization": {
        "healthy": true,
        "strategies_available": 3
      }
    },
    "timestamp": "2023-12-01T10:00:00Z"
  }
}
```

## Task States

- **PENDING**: Task is queued but not yet started
- **STARTED**: Task has been picked up by a worker
- **PROCESSING**: Task is currently being processed
- **SUCCESS**: Task completed successfully
- **FAILURE**: Task failed with an error
- **RETRY**: Task is being retried after failure
- **REVOKED**: Task was cancelled

## Rate Limits

### Synchronous API
- Vectorization: 30 requests per hour
- Palette extraction: 50 requests per hour

### Asynchronous API
- Vectorization: 20 requests per hour
- Batch vectorization: 5 requests per hour
- Palette extraction: 30 requests per hour
- Status checks: 100 requests per hour
- Result retrieval: 50 requests per hour

## Error Handling

All API endpoints return standardized error responses:

```json
{
  "success": false,
  "error": "Error message",
  "details": {
    "code": "ERROR_CODE",
    "message": "Detailed error description"
  }
}
```

Common HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid parameters)
- `401`: Unauthorized (login required)
- `403`: Forbidden (insufficient permissions)
- `404`: Not found (resource doesn't exist)
- `413`: Payload too large (file size exceeded)
- `429`: Too many requests (rate limit exceeded)
- `500`: Internal server error

## Usage Examples

### Python with requests

```python
import requests
import time

# Login
session = requests.Session()
login_response = session.post('http://localhost:8080/login', data={
    'username': 'your_username',
    'password': 'your_password'
})

# Submit async vectorization task
with open('image.jpg', 'rb') as f:
    response = session.post('http://localhost:8080/api/async/vectorize', files={
        'file': f
    }, data={
        'strategy': 'vtracer_high_fidelity',
        'target_time': 60.0
    })

task_data = response.json()
task_id = task_data['task_id']

# Poll for completion
while True:
    status_response = session.get(f'http://localhost:8080/api/async/status/{task_id}')
    status_data = status_response.json()
    
    if status_data['status'] in ['SUCCESS', 'FAILURE']:
        break
    
    time.sleep(2)  # Wait 2 seconds before checking again

# Get result
if status_data['status'] == 'SUCCESS':
    result_response = session.get(f'http://localhost:8080/api/async/result/{task_id}')
    result_data = result_response.json()
    print(f"Vectorization completed! Quality score: {result_data['result']['quality_score']}")
```

### JavaScript with fetch

```javascript
// Submit async vectorization task
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('strategy', 'vtracer_high_fidelity');
formData.append('target_time', '60.0');

const response = await fetch('/api/async/vectorize', {
    method: 'POST',
    body: formData
});

const taskData = await response.json();
const taskId = taskData.task_id;

// Poll for completion
const pollTask = async () => {
    const statusResponse = await fetch(`/api/async/status/${taskId}`);
    const statusData = await statusResponse.json();
    
    if (statusData.status === 'SUCCESS') {
        const resultResponse = await fetch(`/api/async/result/${taskId}`);
        const resultData = await resultResponse.json();
        console.log('Vectorization completed!', resultData.result);
    } else if (statusData.status === 'FAILURE') {
        console.error('Vectorization failed:', statusData.error);
    } else {
        // Still processing, check again
        setTimeout(pollTask, 2000);
    }
};

pollTask();
```

### curl Examples

```bash
# Submit async vectorization
curl -X POST http://localhost:8080/api/async/vectorize \
  -F "file=@image.jpg" \
  -F "strategy=vtracer_high_fidelity" \
  -F "target_time=60.0" \
  -b cookies.txt

# Check status
curl -X GET http://localhost:8080/api/async/status/abc123-def456-ghi789 \
  -b cookies.txt

# Get result
curl -X GET http://localhost:8080/api/async/result/abc123-def456-ghi789 \
  -b cookies.txt
```

## Best Practices

1. **Use Async API**: For production applications, use the async API to avoid blocking requests
2. **Poll Efficiently**: Don't poll too frequently; 2-5 second intervals are sufficient
3. **Handle Errors**: Always check the `success` field in responses
4. **Respect Rate Limits**: Implement exponential backoff for rate limit errors
5. **File Size**: Keep files under 16MB for optimal performance
6. **Batch Processing**: Use batch endpoints for multiple files to improve efficiency
7. **Cleanup**: Results are automatically cleaned up after 7 days

## Monitoring

### Flower Dashboard
Monitor Celery tasks at: http://localhost:5555

### Prometheus Metrics
Metrics available at: http://localhost:9090

### Grafana Dashboard
Visual monitoring at: http://localhost:3000

## Development

### Starting Services

```bash
# Start Redis
redis-server

# Start Celery worker and beat
./start_celery.sh start

# Start Flask application
python app.py
```

### Testing

```bash
# Run API tests
pytest tests/integration/test_api_endpoints.py

# Run performance tests
pytest tests/performance/test_performance.py
```