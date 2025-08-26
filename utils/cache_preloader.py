"""
Cache Preloader for Common Queries
Preloads frequently accessed data to improve response times
"""

import json
import logging
import asyncio
from typing import List, Dict, Tuple
from pathlib import Path
import pandas as pd
from dataclasses import dataclass

from backend.api_client import OakvilleAPIClient
from services.geocoding_service import GeocodingService
from utils.cache_manager import get_global_cache_manager

logger = logging.getLogger(__name__)


@dataclass
class PreloadTask:
    """Represents a cache preload task"""
    name: str
    priority: int  # 1=highest, 5=lowest
    category: str
    data: Dict
    
    def __lt__(self, other):
        return self.priority < other.priority


class CachePreloader:
    """Preloads common queries into cache for faster response times"""
    
    def __init__(self):
        self.api_client = OakvilleAPIClient()
        self.geocoding_service = GeocodingService()
        self.cache_manager = get_global_cache_manager()
        self.sample_properties = self._load_sample_properties()
        
    def _load_sample_properties(self) -> List[Dict]:
        """Load sample properties for preloading"""
        sample_file = Path(__file__).parent.parent / 'data' / 'sample_properties.csv'
        
        if sample_file.exists():
            try:
                df = pd.read_csv(sample_file)
                return df.to_dict('records')
            except Exception as e:
                logger.warning(f"Could not load sample properties: {e}")
        
        # Fallback to hardcoded samples
        return [
            {
                'address': '2320 Lakeshore Rd W, Oakville, ON',
                'expected_zone': 'RL2',
                'priority': 1
            },
            {
                'address': '383 Maplehurst Avenue, Oakville, ON',
                'expected_zone': 'RL2 SP:1',
                'priority': 1
            },
            {
                'address': '1500 Rebecca Street, Oakville, ON',
                'expected_zone': 'RL3',
                'priority': 2
            },
            {
                'address': '100 Lakeshore Road East, Oakville, ON',
                'expected_zone': 'RL2',
                'priority': 2
            },
            {
                'address': '500 Dundas Street West, Oakville, ON',
                'expected_zone': 'RM1',
                'priority': 3
            }
        ]
    
    def create_preload_tasks(self) -> List[PreloadTask]:
        """Create list of preload tasks ordered by priority"""
        tasks = []
        
        # High priority: Sample properties
        for i, prop in enumerate(self.sample_properties[:5]):  # Top 5 properties
            tasks.append(PreloadTask(
                name=f"geocode_{i}",
                priority=1,
                category="geocoding",
                data={'address': prop['address']}
            ))
        
        # Medium priority: Common area coordinates
        common_areas = [
            {'name': 'Oakville City Hall', 'lat': 43.4675, 'lon': -79.6877, 'priority': 2},
            {'name': 'Glen Abbey Golf Club', 'lat': 43.4389, 'lon': -79.7436, 'priority': 2},
            {'name': 'Lakeshore & Dorval', 'lat': 43.4685, 'lon': -79.7071, 'priority': 2},
            {'name': 'Upper Middle & Third Line', 'lat': 43.4512, 'lon': -79.7123, 'priority': 3},
            {'name': 'Dundas & Trafalgar', 'lat': 43.4234, 'lon': -79.7289, 'priority': 3}
        ]
        
        for area in common_areas:
            tasks.append(PreloadTask(
                name=f"zoning_{area['name'].replace(' ', '_').lower()}",
                priority=area['priority'],
                category="zoning",
                data={'lat': area['lat'], 'lon': area['lon'], 'name': area['name']}
            ))
            
            tasks.append(PreloadTask(
                name=f"parks_{area['name'].replace(' ', '_').lower()}",
                priority=area['priority'] + 1,
                category="parks",
                data={'lat': area['lat'], 'lon': area['lon'], 'radius': 1000}
            ))
        
        # Sort by priority
        return sorted(tasks)
    
    async def preload_geocoding(self, address: str) -> bool:
        """Preload geocoding data"""
        try:
            logger.debug(f"Preloading geocoding: {address}")
            result = self.geocoding_service.geocode_address(address)
            return result is not None
        except Exception as e:
            logger.error(f"Failed to preload geocoding for {address}: {e}")
            return False
    
    async def preload_zoning(self, lat: float, lon: float, name: str = None) -> bool:
        """Preload zoning data"""
        try:
            logger.debug(f"Preloading zoning: {lat:.6f}, {lon:.6f} ({name or 'Unknown'})")
            result = self.api_client.get_zoning_info(lat, lon)
            return result is not None
        except Exception as e:
            logger.error(f"Failed to preload zoning for {lat}, {lon}: {e}")
            return False
    
    async def preload_parks(self, lat: float, lon: float, radius: int = 1000) -> bool:
        """Preload parks data"""
        try:
            logger.debug(f"Preloading parks: {lat:.6f}, {lon:.6f} (radius: {radius}m)")
            result = self.api_client.get_nearby_parks(lat, lon, radius)
            return True  # Empty list is still a valid result
        except Exception as e:
            logger.error(f"Failed to preload parks for {lat}, {lon}: {e}")
            return False
    
    async def execute_task(self, task: PreloadTask) -> bool:
        """Execute a single preload task"""
        try:
            if task.category == "geocoding":
                return await self.preload_geocoding(task.data['address'])
            elif task.category == "zoning":
                return await self.preload_zoning(
                    task.data['lat'], 
                    task.data['lon'], 
                    task.data.get('name')
                )
            elif task.category == "parks":
                return await self.preload_parks(
                    task.data['lat'],
                    task.data['lon'],
                    task.data.get('radius', 1000)
                )
            else:
                logger.warning(f"Unknown task category: {task.category}")
                return False
        except Exception as e:
            logger.error(f"Failed to execute task {task.name}: {e}")
            return False
    
    async def preload_cache(self, max_tasks: int = 20) -> Dict:
        """
        Preload cache with common queries
        
        Args:
            max_tasks: Maximum number of tasks to execute
            
        Returns:
            Dictionary with preload statistics
        """
        logger.info("Starting cache preloading...")
        
        tasks = self.create_preload_tasks()[:max_tasks]
        
        stats = {
            'total_tasks': len(tasks),
            'successful': 0,
            'failed': 0,
            'start_time': asyncio.get_event_loop().time(),
            'categories': {}
        }
        
        # Execute tasks in priority order with concurrency control
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent tasks
        
        async def execute_with_semaphore(task):
            async with semaphore:
                success = await self.execute_task(task)
                
                # Update stats
                category = task.category
                if category not in stats['categories']:
                    stats['categories'][category] = {'successful': 0, 'failed': 0}
                
                if success:
                    stats['successful'] += 1
                    stats['categories'][category]['successful'] += 1
                else:
                    stats['failed'] += 1
                    stats['categories'][category]['failed'] += 1
                
                return success
        
        # Execute all tasks concurrently
        results = await asyncio.gather(
            *[execute_with_semaphore(task) for task in tasks],
            return_exceptions=True
        )
        
        # Calculate timing
        stats['end_time'] = asyncio.get_event_loop().time()
        stats['duration'] = stats['end_time'] - stats['start_time']
        stats['success_rate'] = (stats['successful'] / stats['total_tasks'] * 100 
                                if stats['total_tasks'] > 0 else 0)
        
        logger.info(f"Cache preloading completed: {stats['successful']}/{stats['total_tasks']} "
                   f"successful ({stats['success_rate']:.1f}%) in {stats['duration']:.2f}s")
        
        return stats
    
    def preload_sync(self, max_tasks: int = 20) -> Dict:
        """Synchronous version of cache preloading"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(self.preload_cache(max_tasks))
    
    def get_cache_stats(self) -> Dict:
        """Get current cache statistics"""
        return self.cache_manager.get_stats()
    
    def warm_up_common_queries(self):
        """Quick warm-up for the most common queries (synchronous)"""
        logger.info("Warming up cache with common queries...")
        
        # Preload top 3 most common addresses
        common_addresses = [
            "2320 Lakeshore Rd W, Oakville, ON",
            "383 Maplehurst Avenue, Oakville, ON", 
            "1500 Rebecca Street, Oakville, ON"
        ]
        
        for address in common_addresses:
            try:
                # Geocode the address
                geo_result = self.geocoding_service.geocode_address(address)
                if geo_result:
                    lat, lon = geo_result['latitude'], geo_result['longitude']
                    
                    # Get zoning info
                    self.api_client.get_zoning_info(lat, lon, address)
                    
                    # Get nearby parks
                    self.api_client.get_nearby_parks(lat, lon)
                    
                    logger.debug(f"Warmed up cache for: {address}")
                    
            except Exception as e:
                logger.warning(f"Failed to warm up cache for {address}: {e}")
        
        logger.info("Cache warm-up completed")


def preload_on_startup():
    """Function to call on application startup (disabled for now)"""
    try:
        logger.info("Cache preloading disabled for faster startup")
        return True
    except Exception as e:
        logger.warning(f"Cache preload skipped: {e}")
        return False


if __name__ == "__main__":
    # Test preloader
    logging.basicConfig(level=logging.INFO)
    
    preloader = CachePreloader()
    
    # Quick warm-up
    preloader.warm_up_common_queries()
    
    # Full preload (async)
    stats = preloader.preload_sync(max_tasks=10)
    print(f"\nPreload Results:")
    print(f"- Total tasks: {stats['total_tasks']}")
    print(f"- Successful: {stats['successful']}")
    print(f"- Failed: {stats['failed']}")
    print(f"- Success rate: {stats['success_rate']:.1f}%")
    print(f"- Duration: {stats['duration']:.2f}s")
    
    # Cache stats
    cache_stats = preloader.get_cache_stats()
    print(f"\nCache Statistics:")
    print(json.dumps(cache_stats, indent=2))