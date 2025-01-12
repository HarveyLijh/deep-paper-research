# src/monitoring/metrics.py
from prometheus_client import Counter, Gauge, Histogram, Summary
import functools
import time

# API Metrics
api_calls = Counter(
    'paper_discovery_api_calls_total',
    'Number of API calls made',
    ['api', 'endpoint', 'status']
)

api_latency = Histogram(
    'paper_discovery_api_latency_seconds',
    'API call latency',
    ['api', 'endpoint'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Paper Processing Metrics
papers_processed = Counter(
    'paper_discovery_papers_processed_total',
    'Number of papers processed'
)

papers_by_relevance = Histogram(
    'paper_discovery_paper_relevance_score',
    'Distribution of paper relevance scores',
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

reference_depth = Histogram(
    'paper_discovery_reference_depth',
    'Distribution of reference processing depth',
    buckets=[1, 2, 3, 4, 5]
)

# Queue Metrics
queue_depth = Gauge(
    'paper_discovery_queue_depth',
    'Number of papers waiting to be processed',
    ['queue']
)

queue_processing_time = Summary(
    'paper_discovery_queue_processing_seconds',
    'Time spent processing queue items',
    ['queue']
)

# Resource Metrics
memory_usage = Gauge(
    'paper_discovery_memory_bytes',
    'Memory usage in bytes'
)

db_connections = Gauge(
    'paper_discovery_db_connections',
    'Number of active database connections'
)

# Decorators for automatic metric collection
def track_api_call(api, endpoint):
    """Decorator to track API calls with metrics"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                api_calls.labels(api=api, endpoint=endpoint, status='success').inc()
                api_latency.labels(api=api, endpoint=endpoint).observe(
                    time.time() - start_time
                )
                return result
            except Exception as e:
                api_calls.labels(api=api, endpoint=endpoint, status='error').inc()
                raise
            finally:
                # Track request size for batch operations
                if kwargs.get('batch_size'):
                    request_size.labels(api=api, endpoint=endpoint).observe(
                        kwargs['batch_size']
                    )
        return wrapper
    return decorator

# Paper Discovery Metrics
def track_paper_processing():
    """Decorator to track paper processing metrics"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            papers_processed.inc()
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                # Track paper metadata
                if isinstance(result, dict):
                    if 'relevance_score' in result:
                        papers_by_relevance.observe(result['relevance_score'])
                    if 'depth' in result:
                        reference_depth.observe(result['depth'])
                return result
            finally:
                processing_time = time.time() - start_time
                queue_processing_time.labels(queue='paper_processing').observe(
                    processing_time
                )
        return wrapper
    return decorator

# Business Intelligence Metrics
class BusinessMetrics:
    """Track high-level business metrics"""
    def __init__(self):
        self.papers_per_topic = Counter(
            'paper_discovery_papers_per_topic_total',
            'Number of papers discovered per topic',
            ['topic']
        )
        
        self.citation_network_size = Gauge(
            'paper_discovery_citation_network_size',
            'Total size of the citation network'
        )
        
        self.topic_coverage = Gauge(
            'paper_discovery_topic_coverage_percent',
            'Estimated coverage of research topics',
            ['topic']
        )
        
        self.discovery_efficiency = Gauge(
            'paper_discovery_efficiency_ratio',
            'New papers found per API call'
        )
    
    def update_metrics(self, db_manager):
        """Update all business metrics"""
        # Update citation network size
        papers = db_manager.get_processed_papers()
        total_nodes = len(papers)
        total_edges = sum(
            len(p.references or []) + len(p.citations or [])
            for p in papers
        )
        self.citation_network_size.set(total_nodes + total_edges)
        
        # Update topic coverage
        for topic in settings.SEARCH_TOPICS:
            relevant_papers = sum(
                1 for p in papers
                if hasattr(p, 'relevance_score') and p.relevance_score >= 0.7
            )
            self.topic_coverage.labels(topic=topic).set(
                (relevant_papers / total_nodes) * 100
            )
        
        # Update discovery efficiency
        total_calls = sum(
            c.value
            for c in api_calls._metrics
        )
        if total_calls > 0:
            self.discovery_efficiency.set(total_nodes / total_calls)

# Resource Monitoring
def track_resource_usage():
    """Update resource usage metrics"""
    import psutil
    
    def get_metrics():
        process = psutil.Process()
        memory_usage.set(process.memory_info().rss)
        
        # Track database connections
        db_stats = psutil.net_connections('tcp')
        postgres_conns = sum(
            1 for conn in db_stats
            if conn.laddr.port == 5432 and conn.status == 'ESTABLISHED'
        )
        db_connections.set(postgres_conns)
    
    return get_metrics

# Celery Task Monitoring
from celery.events import EventReceiver
from celery.events.state import State

class CeleryMonitor:
    """Monitor Celery tasks and queues"""
    def __init__(self, app):
        self.app = app
        self.state = State()
        
        # Metrics
        self.task_status = Counter(
            'celery_task_status_total',
            'Number of tasks by status',
            ['task_name', 'status']
        )
        
        self.task_runtime = Histogram(
            'celery_task_runtime_seconds',
            'Task runtime in seconds',
            ['task_name']
        )
        
        self.queue_length = Gauge(
            'celery_queue_length',
            'Number of tasks in queue',
            ['queue_name']
        )
    
    def start(self):
        """Start monitoring Celery events"""
        receiver = self.app.events.Receiver(
            self.app.connection(),
            handlers={
                'task-sent': self._handle_sent,
                'task-received': self._handle_received,
                'task-started': self._handle_started,
                'task-succeeded': self._handle_succeeded,
                'task-failed': self._handle_failed,
                'task-rejected': self._handle_rejected,
                'task-revoked': self._handle_revoked,
            }
        )
        receiver.capture(limit=None, timeout=None, wakeup=True)
    
    def _handle_sent(self, event):
        self.queue_length.labels(
            queue_name=event['queue']
        ).inc()
    
    def _handle_received(self, event):
        self.state.event(event)
        task = self.state.tasks.get(event['uuid'])
        
        self.task_status.labels(
            task_name=event['name'],
            status='received'
        ).inc()
    
    def _handle_started(self, event):
        self.state.event(event)
        task = self.state.tasks.get(event['uuid'])
        
        self.task_status.labels(
            task_name=event['name'],
            status='started'
        ).inc()
    
    def _handle_succeeded(self, event):
        self.state.event(event)
        task = self.state.tasks.get(event['uuid'])
        
        self.task_status.labels(
            task_name=event['name'],
            status='succeeded'
        ).inc()
        
        if task and task.started:
            runtime = task.runtime
            self.task_runtime.labels(
                task_name=event['name']
            ).observe(runtime)