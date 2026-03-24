# Network Interception

Monitor and intercept HTTP requests and responses.

## Enable Network Monitoring

```python
# Network interception requires enabling Network domain
browser = Browser()
tab = browser.new_tab("https://example.com")

# Network domain is automatically enabled when you use on_request/on_response
```

## Monitor Requests

```python
# Log all requests
def log_request(request):
    print(f"-> {request['request']['method']} {request['request']['url']}")

browser.on_request(log_request)

# Filter specific requests
def log_api_calls(request):
    url = request['request']['url']
    if '/api/' in url:
        print(f"API call: {url}")

browser.on_request(log_api_calls)
```

## Monitor Responses

```python
# Log all responses
def log_response(response):
    status = response['response']['status']
    url = response['response']['url']
    print(f"<- {status} {url}")

browser.on_response(log_response)

# Filter by status code
def log_errors(response):
    status = response['response']['status']
    if status >= 400:
        print(f"Error: {status} {response['response']['url']}")

browser.on_response(log_errors)
```

## Monitor Failed Requests

```python
# Log failed requests (network errors, timeouts)
def log_failed(request):
    url = request['request']['url']
    error = request.get('errorText', 'Unknown error')
    print(f"X Failed: {url} - {error}")

browser.on_request_failed(log_failed)
```

## Use Case: Track API Calls

```python
api_calls = []

def track_api(response):
    url = response['response']['url']
    if '/api/' in url:
        api_calls.append({
            'url': url,
            'status': response['response']['status'],
            'type': response['response'].get('mimeType', '')
        })

browser.on_response(track_api)

# Navigate and interact...

print(f"Made {len(api_calls)} API calls:")
for call in api_calls:
    print(f"  {call['status']} {call['url']}")
```

## Use Case: Wait for XHR

```python
import time

pending_requests = set()

def track_start(request):
    request_id = request['requestId']
    pending_requests.add(request_id)

def track_end(response):
    request_id = response['requestId']
    pending_requests.discard(request_id)

browser.on_request(track_start)
browser.on_response(track_end)

# Wait for all XHR to complete
while pending_requests:
    time.sleep(0.1)
```

## Note

Network interception is for **monitoring** only. To **modify** requests, you need a proxy or use Chrome extensions.
