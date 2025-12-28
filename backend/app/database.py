from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from app.config import get_settings

settings = get_settings()

# Ensure the URL uses asyncpg driver and handle SSL properly
db_url = settings.DATABASE_URL
if not db_url.startswith("postgresql+asyncpg://"):
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)

# Parse URL to handle sslmode parameter for asyncpg
parsed = urlparse(db_url)
query_params = parse_qs(parsed.query)

# Check if sslmode is set and convert to asyncpg SSL format
ssl_required = False
if 'sslmode' in query_params:
    sslmode = query_params['sslmode'][0].lower()
    if sslmode in ('require', 'prefer', 'allow', 'verify-ca', 'verify-full'):
        ssl_required = True
    # Remove sslmode from query params as asyncpg doesn't use it
    del query_params['sslmode']

# Reconstruct URL without sslmode
new_query = urlencode(query_params, doseq=True) if query_params else ''
new_parsed = parsed._replace(query=new_query)
db_url = urlunparse(new_parsed)

# Prepare connection arguments for asyncpg
connect_args = {}
if ssl_required:
    connect_args['ssl'] = True

engine = create_async_engine(
    db_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

