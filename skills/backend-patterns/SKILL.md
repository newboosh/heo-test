---
name: backend-patterns
description: Backend architecture patterns, API design, database optimization, and server-side best practices for Flask, SQLAlchemy, and Celery.
model: opus
---

# Backend Development Patterns

Backend architecture patterns and best practices for scalable Flask applications.

## API Design Patterns

### RESTful API Structure

```python
# Flask Blueprint structure
# app/api/markets.py

from flask import Blueprint, request, jsonify
from app.models import Market
from app.services.market_service import MarketService

bp = Blueprint('markets', __name__, url_prefix='/api/markets')

@bp.route('', methods=['GET'])
def list_markets():
    """GET /api/markets - List all markets"""
    status = request.args.get('status')
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)

    markets = MarketService.get_all(status=status, limit=limit, offset=offset)
    return jsonify({'success': True, 'data': markets})

@bp.route('/<int:market_id>', methods=['GET'])
def get_market(market_id: int):
    """GET /api/markets/:id - Get specific market"""
    market = MarketService.get_by_id(market_id)
    if market is None:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({'success': True, 'data': market})

@bp.route('', methods=['POST'])
def create_market():
    """POST /api/markets - Create new market"""
    data = request.get_json()
    market = MarketService.create(data)
    return jsonify({'success': True, 'data': market}), 201

@bp.route('/<int:market_id>', methods=['PUT'])
def update_market(market_id: int):
    """PUT /api/markets/:id - Update market"""
    data = request.get_json()
    market = MarketService.update(market_id, data)
    return jsonify({'success': True, 'data': market})

@bp.route('/<int:market_id>', methods=['DELETE'])
def delete_market(market_id: int):
    """DELETE /api/markets/:id - Delete market"""
    MarketService.delete(market_id)
    return jsonify({'success': True}), 204
```

### Repository Pattern

```python
# app/repositories/market_repository.py

from typing import Optional
from sqlalchemy.orm import Session
from app.models import Market
from app.schemas import MarketFilters

class MarketRepository:
    def __init__(self, session: Session):
        self._session = session

    def find_all(
        self,
        *,
        filters: Optional[MarketFilters] = None,
        limit: int = 20,
        offset: int = 0
    ) -> list[Market]:
        query = self._session.query(Market)

        if filters is not None and filters.status is not None:
            query = query.filter(Market.status == filters.status)

        return query.offset(offset).limit(limit).all()

    def find_by_id(self, market_id: int) -> Optional[Market]:
        return self._session.query(Market).get(market_id)

    def create(self, data: dict) -> Market:
        market = Market(**data)
        self._session.add(market)
        self._session.commit()
        return market

    def update(self, market_id: int, data: dict) -> Optional[Market]:
        market = self.find_by_id(market_id)
        if market is None:
            return None

        for key, value in data.items():
            setattr(market, key, value)

        self._session.commit()
        return market

    def delete(self, market_id: int) -> bool:
        market = self.find_by_id(market_id)
        if market is None:
            return False

        self._session.delete(market)
        self._session.commit()
        return True
```

### Service Layer Pattern

```python
# app/services/market_service.py

from typing import Optional
from app.repositories import MarketRepository
from app.rag import generate_embedding, vector_search

class MarketService:
    def __init__(self, repo: MarketRepository):
        self._repo = repo

    def search_markets(
        self,
        query: str,
        *,
        limit: int = 10
    ) -> list[dict]:
        """Semantic search for markets."""
        # Generate embedding for query
        embedding = generate_embedding(query)

        # Vector search
        results = vector_search(embedding, limit=limit)

        # Fetch full market data
        market_ids = [r['id'] for r in results]
        markets = self._repo.find_by_ids(market_ids)

        # Sort by similarity score
        score_map = {r['id']: r['score'] for r in results}
        markets.sort(key=lambda m: score_map.get(m.id, 0), reverse=True)

        return markets
```

### Middleware Pattern (Flask Decorators)

```python
# app/middleware/auth.py

from functools import wraps
from flask import request, g, jsonify
from app.auth import verify_token

def require_auth(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        if not token:
            return jsonify({'error': 'Unauthorized'}), 401

        user = verify_token(token)
        if user is None:
            return jsonify({'error': 'Invalid token'}), 401

        g.current_user = user
        return f(*args, **kwargs)

    return decorated

def require_role(role: str):
    """Decorator to require specific role."""
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            if g.current_user.role != role:
                return jsonify({'error': 'Forbidden'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

# Usage
@bp.route('/admin/users', methods=['GET'])
@require_role('admin')
def list_users():
    return jsonify({'users': User.query.all()})
```

## Database Patterns

### Query Optimization

```python
# Select only needed columns
markets = db.session.query(
    Market.id,
    Market.name,
    Market.status,
    Market.volume
).filter(
    Market.status == 'active'
).order_by(
    Market.volume.desc()
).limit(10).all()

# Eager loading to prevent N+1
markets = Market.query.options(
    joinedload(Market.creator),
    selectinload(Market.positions)
).filter(Market.status == 'active').all()
```

### N+1 Query Prevention

```python
# BAD: N+1 query problem
markets = Market.query.all()
for market in markets:
    print(market.creator.name)  # N additional queries

# GOOD: Eager loading
markets = Market.query.options(
    joinedload(Market.creator)
).all()
for market in markets:
    print(market.creator.name)  # No additional queries
```

### Transaction Pattern

```python
from contextlib import contextmanager
from app import db

@contextmanager
def transaction():
    """Context manager for database transactions."""
    try:
        yield db.session
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

# Usage
with transaction() as session:
    market = Market(name='Test')
    session.add(market)
    position = Position(market_id=market.id, user_id=user.id)
    session.add(position)
# Commits on success, rolls back on error
```

## Caching Strategies

### Redis Caching Layer

```python
# app/cache.py

import json
from functools import wraps
from redis import Redis
from flask import current_app

redis_client = Redis.from_url(current_app.config['REDIS_URL'])

def cached(key_prefix: str, ttl: int = 300):
    """Decorator for caching function results."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"

            # Check cache
            cached_value = redis_client.get(cache_key)
            if cached_value is not None:
                return json.loads(cached_value)

            # Execute function
            result = f(*args, **kwargs)

            # Cache result
            redis_client.setex(cache_key, ttl, json.dumps(result))

            return result
        return decorated
    return decorator

def invalidate_cache(key_prefix: str, *args):
    """Invalidate a cached value."""
    cache_key = f"{key_prefix}:{':'.join(str(a) for a in args)}"
    redis_client.delete(cache_key)

# Usage
@cached('market', ttl=300)
def get_market(market_id: int) -> dict:
    market = Market.query.get(market_id)
    return market.to_dict()
```

## Error Handling Patterns

### Centralized Error Handler

```python
# app/errors.py

from flask import jsonify
from marshmallow import ValidationError

class ApiError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code
        super().__init__(message)

def register_error_handlers(app):
    @app.errorhandler(ApiError)
    def handle_api_error(error):
        return jsonify({
            'success': False,
            'error': error.message
        }), error.status_code

    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': error.messages
        }), 400

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        app.logger.exception('Unexpected error')
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
```

### Retry with Exponential Backoff

```python
import time
from functools import wraps
from typing import Callable, TypeVar

T = TypeVar('T')

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for retry with exponential backoff."""
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def decorated(*args, **kwargs) -> T:
            last_error = None

            for attempt in range(max_retries):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_error = e

                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        time.sleep(delay)

            raise last_error

        return decorated
    return decorator

# Usage
@retry_with_backoff(max_retries=3)
def call_external_api():
    response = requests.get('https://api.example.com/data')
    response.raise_for_status()
    return response.json()
```

## Background Jobs with Celery

### Task Pattern

```python
# app/tasks/market_tasks.py

from celery import shared_task
from app import create_app
from app.services import MarketService

@shared_task(bind=True, max_retries=3)
def index_market(self, market_id: int):
    """Background task to index a market for search."""
    try:
        app = create_app()
        with app.app_context():
            MarketService.index_for_search(market_id)
    except Exception as exc:
        self.retry(exc=exc, countdown=60)

@shared_task
def cleanup_expired_markets():
    """Periodic task to cleanup expired markets."""
    app = create_app()
    with app.app_context():
        MarketService.cleanup_expired()

# Trigger from API
@bp.route('/<int:market_id>/index', methods=['POST'])
@require_auth
def trigger_index(market_id: int):
    index_market.delay(market_id)
    return jsonify({'success': True, 'message': 'Indexing queued'})
```

## Logging & Monitoring

### Structured Logging

```python
import logging
import json
from flask import request, g

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
        }

        # Add request context if available
        if hasattr(g, 'request_id'):
            log_entry['request_id'] = g.request_id

        if hasattr(g, 'current_user'):
            log_entry['user_id'] = g.current_user.id

        return json.dumps(log_entry)

# Setup
handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
app.logger.addHandler(handler)
```

**Remember**: Backend patterns enable scalable, maintainable server-side applications. Choose patterns that fit your complexity level.
