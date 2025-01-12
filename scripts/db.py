import os
import sys
import logging
from pathlib import Path
import urllib.parse
from sqlalchemy import create_engine, text
import click

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from src.database.models import Base
from src.config.settings import settings

def create_neon_engine(url: str):
    """Create SQLAlchemy engine with Neon DB configuration"""
    parsed = urllib.parse.urlparse(url)
    query_params = urllib.parse.parse_qs(parsed.query)
    query_params.update({
        'sslmode': ['require'],
        'connect_timeout': ['10'],
        'application_name': ['paper_discovery_init']
    })
    
    new_url = urllib.parse.urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        urllib.parse.urlencode(query_params, doseq=True),
        parsed.fragment
    ))
    
    return create_engine(
        new_url,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True
    )

def init_db():
    """Initialize database schema"""
    logging.info("Creating database engine...")
    engine = create_neon_engine(settings.DATABASE_URL)
    
    # Test connection
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logging.info("Database connection successful")
    except Exception as e:
        logging.error(f"Database connection failed: {str(e)}")
        sys.exit(1)
    
    # Create tables
    logging.info("Creating database tables...")
    try:
        Base.metadata.create_all(engine)
        logging.info("Database tables created successfully")
    except Exception as e:
        logging.error(f"Failed to create tables: {str(e)}")
        sys.exit(1)

@click.group()
def cli():
    pass

def ensure_migrations_initialized():
    """Ensure migrations directory and files exist"""
    migrations_dir = project_root / 'migrations'
    versions_dir = migrations_dir / 'versions'
    alembic_ini = project_root / 'alembic.ini'
    
    if not migrations_dir.exists() or not (migrations_dir / 'script.py.mako').exists():
        if migrations_dir.exists():
            import shutil
            shutil.rmtree(migrations_dir)
        os.system("alembic init migrations")
        
        # Update alembic.ini with correct script_location
        with open(alembic_ini, 'r') as f:
            config = f.read()
        config = config.replace('sqlalchemy.url = driver://user:pass@localhost/dbname',
                              f'sqlalchemy.url = {settings.DATABASE_URL}')
        with open(alembic_ini, 'w') as f:
            f.write(config)

@cli.command()
def init():
    """Initialize database tables"""
    os.system("alembic upgrade head")

@cli.command()
@click.argument('message')
def migrate(message):
    """Create new migration"""
    ensure_migrations_initialized()
    os.system(f"alembic revision --autogenerate -m '{message}'")

@cli.command()
def upgrade():
    """Upgrade to latest migration"""
    os.system("alembic upgrade head")

@cli.command()
def downgrade():
    """Downgrade last migration"""
    os.system("alembic downgrade -1")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli()