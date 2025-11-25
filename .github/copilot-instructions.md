# ZZ-API Copilot Instructions

## Architecture Overview

**Stock Trading & T-Bill Management REST API** built with Flask and Flask-RESTful, supporting WeChat mini-program authentication and MongoDB data persistence.

### Core Components
- **`app.py`**: Main Flask application with error handling, CORS middleware, health check, and WeChat OAuth routes
- **`routes/`**: Three separate resource endpoints handling domain-specific operations
  - `trade_routes.py`: Buy/sell trade operations with pagination and filtering
  - `tbill_routes.py`: T-bill (treasury bill) creation, updates, and queries
  - `stock_routes.py`: Stock code lookup service with multi-market support (A-shares, HK, US)
- **`utils/`**: Shared utilities for database, authentication, and data generation
  - `db.py`: MongoDB connection management with optional authentication
  - `wechat_utils.py`: WeChat mini-program OAuth2 integration
  - `id_generator.py`: MD5-based business ID generation (trades, T-bills)
  - `stock_utils.py`: Multi-market stock code validation and lookup

### Data Model Pattern
All trade/T-bill documents store `_openid` field for user isolation. Operations are scoped to authenticated user's `openid`.

```python
# Example: Trade document structure
{
  '_id': ObjectId,
  '_openid': 'wechat_openid',
  'tradeId': 'md5_hash',
  'createTime': datetime,
  'matchStatus': 'matched|pending',
  'stockCode': '000001.SZ',
  'type': 'buy|sell'
}
```

## Critical Workflows

### Setup & Development
```powershell
# Windows startup (handles .env loading)
.\start.bat

# Linux/Mac startup
bash start.sh
```

Environment variables required (set in `.env`):
- `MONGO_URI`: MongoDB connection string (default: `mongodb://localhost:27017/stock_trade_db`)
- `MONGO_USERNAME`, `MONGO_PASSWORD`: Optional authentication
- `WX_APP_ID`, `WX_APP_SECRET`: WeChat mini-program credentials
- `PORT`: Server port (default: 5000)
- `DEBUG`: Set to 'True' to enable Flask debug mode

### API Response Format
All endpoints return consistent JSON structure:
```python
{
  'success': True|False,
  'data': {...},  # Present on success
  'message': 'error description',  # Present on error
  'error': 'technical details'  # Optional in error responses
}
```

Pagination pattern (trades/T-bills):
```python
'pagination': {
  'page': 1,
  'pageSize': 20,
  'total': 150,
  'hasMore': True
}
```

## Project-Specific Conventions

### Route Operation Pattern
Operations use a **single POST endpoint with `operation` parameter** in request body:
```python
{
  'operation': 'getAllTrades|addTrade|deleteTrade|getTradeById',
  'data': { /* operation-specific parameters */ },
  'openId': 'wechat_openid'  # Optional; defaults to 'test_openid'
}
```

This differs from REST conventions but enables flexible business logic in single resources.

### Database Query Conventions
- **User isolation**: Always filter by `{'_openid': openid}` to prevent cross-user data access
- **Sorting**: Default to `createTime` descending (newest first)
- **ID conversions**: MongoDB `ObjectId` must be converted to string for JSON serialization: `trade['_id'] = str(trade['_id'])`

### Stock Code Format Recognition
- **A-share (Shanghai)**: `000001.SH` (leading zeros, `.SH` suffix)
- **A-share (Shenzhen)**: `000001.SZ` (leading zeros, `.SZ` suffix)
- **Hong Kong**: `00001.HK` (5-digit code, `.HK` suffix)
- **US**: `AAPL` (uppercase letters, no suffix)

Validation uses regex patterns in `stock_utils.py._get_api_url_and_market()`.

### Error Handling Pattern
- Return `400` for invalid request data (missing params, format errors)
- Return `404` for not found (trade/T-bill not found, unsupported stock code)
- Return `500` for server errors with logged traceback
- All errors logged via `logger.error()` with context

### ID Generation
Business IDs are deterministic MD5 hashes: `MD5(prefix:openid:timestamp)`
- Enables ID reproduction for reconciliation
- Used for trades, T-bills, and other business entities
- See `id_generator.py` for format and usage

## Integration Points

### WeChat Mini-Program Flow
1. Frontend sends login `code` → `/api/getOpenId` endpoint
2. Endpoint calls `WeChatAPI.get_open_id(code)` 
3. Returns `openId` + `unionId` to frontend
4. Frontend includes `openId` in all subsequent operation requests

### Cross-Component Communication
- Routes import database access via `from utils.db import get_db()`
- Stock lookup is called from `stock_routes.py` → `stock_utils.StockCodeLookup.get_stock_info()`
- All business ID generation flows through `BusinessIdGenerator` utility

## Key Files Reference

| File | Purpose | Key Pattern |
|------|---------|-------------|
| `app.py` | Entry point, middleware, health check | Flask initialization, error handlers |
| `routes/trade_routes.py` | Trade CRUD operations | Operation dispatcher, pagination |
| `routes/tbill_routes.py` | T-bill management | Similar structure to trades |
| `routes/stock_routes.py` | Stock lookup | Error code routing based on result |
| `utils/db.py` | MongoDB lifecycle | Global client pattern, lazy initialization |
| `utils/wechat_utils.py` | WeChat OAuth | Static method class, timeout=10s |
| `utils/id_generator.py` | ID generation | Deterministic MD5 hashing |
| `utils/stock_utils.py` | Stock validation | Regex-based market detection |

## Common Tasks

**Adding a new operation to trades:**
1. Add method `_<operation_name>` in `TradeOperations` class
2. Wire it in the `post()` dispatcher: `elif operation == '<operationName>': return self._<operation_name>(...)`
3. Query/modify `db.trades` collection with user isolation
4. Convert ObjectIds to strings before returning
5. Follow pagination pattern for list operations

**Debugging database issues:**
- Check `.env` for `MONGO_URI` correctness
- Verify credentials with `MONGO_USERNAME`/`MONGO_PASSWORD`
- Connection test occurs at `db.py:get_db()` with `db.command('ping')`
- Logs indicate success: `"MongoDB连接成功"` or failure reason

**Testing stock code lookup:**
- Use `/api/stockCodeLookup` POST endpoint with body: `{"stockCode": "000001.SZ"}`
- Supports GET requests for quick testing (see `stock_routes.py:get()`)
