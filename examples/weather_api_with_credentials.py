#!/usr/bin/env python3
"""
Weather API Integration with Secure Credential Management
========================================================

Example implementation showing how to integrate the secure credential
management system with the Adelaide weather forecasting API components.

This demonstrates real-world usage patterns for:
- API authentication with stored credentials
- Database connections using secure passwords
- Service-to-service authentication
- Credential rotation in production systems
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from core.secure_credential_manager import (
    SecureCredentialManager,
    CredentialType,
    SecurityLevel,
    CredentialNotFoundError
)


class WeatherAPIClient:
    """
    Weather API client with secure credential management integration.
    
    Demonstrates how to integrate the credential manager with actual
    weather data fetching and API authentication.
    """
    
    def __init__(self, credential_manager: SecureCredentialManager, environment: str = "production"):
        self.credential_manager = credential_manager
        self.environment = environment
        self.logger = logging.getLogger(f"weather_api_{environment}")
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    async def fetch_gfs_data(self, variables: list, forecast_hour: int) -> Dict[str, Any]:
        """
        Fetch GFS weather data using securely stored API credentials.
        
        Args:
            variables: List of weather variables to fetch
            forecast_hour: Forecast hour (0, 6, 12, 18, 24, etc.)
            
        Returns:
            Dictionary containing weather data
        """
        try:
            # Retrieve GFS API credentials securely
            with self.credential_manager.secure_context("gfs_api_key", "weather_service") as api_key:
                self.logger.info(f"Fetching GFS data for variables: {variables}")
                
                # Simulate GFS API call (in real implementation, use requests/httpx)
                gfs_url = f"https://api.weather.gov/gfs/forecast"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "Adelaide-Weather-Service/1.0"
                }
                
                # Mock data structure (real implementation would make HTTP request)
                weather_data = {
                    "source": "GFS",
                    "forecast_hour": forecast_hour,
                    "variables": {},
                    "metadata": {
                        "fetch_time": datetime.utcnow().isoformat(),
                        "model_run": "12Z"
                    }
                }
                
                # Simulate variable data
                for var in variables:
                    weather_data["variables"][var] = {
                        "value": 20.5 + forecast_hour * 0.1,  # Mock temperature-like data
                        "units": "celsius" if var.startswith("t") else "m/s",
                        "quality": "good"
                    }
                
                self.logger.info(f"Successfully fetched GFS data for {len(variables)} variables")
                return weather_data
                
        except CredentialNotFoundError:
            self.logger.error("GFS API credentials not found")
            raise
        except Exception as e:
            self.logger.error(f"Failed to fetch GFS data: {e}")
            raise
    
    async def fetch_era5_data(self, variables: list, date: str) -> Dict[str, Any]:
        """
        Fetch ERA5 reanalysis data using securely stored credentials.
        
        Args:
            variables: List of weather variables to fetch
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing ERA5 data
        """
        try:
            # Retrieve ERA5 API credentials
            with self.credential_manager.secure_context("era5_api_key", "weather_service") as api_key:
                self.logger.info(f"Fetching ERA5 data for date: {date}")
                
                # Simulate ERA5 API call
                era5_data = {
                    "source": "ERA5",
                    "date": date,
                    "variables": {},
                    "metadata": {
                        "fetch_time": datetime.utcnow().isoformat(),
                        "data_type": "reanalysis"
                    }
                }
                
                # Simulate variable data
                for var in variables:
                    era5_data["variables"][var] = {
                        "value": 18.3,  # Mock historical data
                        "units": "celsius" if var.startswith("t") else "m/s",
                        "quality": "reanalysis"
                    }
                
                self.logger.info(f"Successfully fetched ERA5 data for {len(variables)} variables")
                return era5_data
                
        except CredentialNotFoundError:
            self.logger.error("ERA5 API credentials not found")
            raise
        except Exception as e:
            self.logger.error(f"Failed to fetch ERA5 data: {e}")
            raise


class DatabaseManager:
    """
    Database manager with secure credential integration.
    
    Demonstrates secure database connection management using
    the credential management system.
    """
    
    def __init__(self, credential_manager: SecureCredentialManager):
        self.credential_manager = credential_manager
        self.logger = logging.getLogger("database_manager")
        self.connection_pool = None
    
    async def initialize_connection_pool(self):
        """Initialize database connection pool with secure credentials."""
        try:
            # Retrieve database credentials
            with self.credential_manager.secure_context("postgres_password", "database_service") as db_password:
                # Get additional database configuration
                db_config = {
                    "host": os.environ.get("DB_HOST", "localhost"),
                    "port": int(os.environ.get("DB_PORT", "5432")),
                    "database": os.environ.get("DB_NAME", "weather_data"),
                    "username": os.environ.get("DB_USER", "weather_app"),
                    "password": db_password
                }
                
                self.logger.info(f"Initializing database connection to {db_config['host']}:{db_config['port']}")
                
                # In real implementation, would create actual connection pool
                # Example with asyncpg:
                # import asyncpg
                # self.connection_pool = await asyncpg.create_pool(
                #     host=db_config["host"],
                #     port=db_config["port"],
                #     database=db_config["database"],
                #     user=db_config["username"],
                #     password=db_config["password"],
                #     min_size=5,
                #     max_size=20
                # )
                
                # Mock connection pool for demo
                self.connection_pool = {
                    "status": "connected",
                    "config": {k: v for k, v in db_config.items() if k != "password"}
                }
                
                self.logger.info("Database connection pool initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    async def store_weather_data(self, weather_data: Dict[str, Any]) -> bool:
        """
        Store weather data in database using secure connection.
        
        Args:
            weather_data: Weather data to store
            
        Returns:
            True if successful
        """
        if not self.connection_pool:
            await self.initialize_connection_pool()
        
        try:
            self.logger.info(f"Storing weather data from {weather_data.get('source', 'unknown')}")
            
            # In real implementation, would execute SQL queries
            # Example:
            # async with self.connection_pool.acquire() as connection:
            #     await connection.execute(
            #         "INSERT INTO weather_observations (source, data, created_at) VALUES ($1, $2, $3)",
            #         weather_data["source"],
            #         json.dumps(weather_data),
            #         datetime.utcnow()
            #     )
            
            # Mock storage for demo
            self.logger.info("Weather data stored successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store weather data: {e}")
            raise


class ForecastService:
    """
    Complete forecast service integrating all secure credential usage.
    
    Demonstrates end-to-end integration of the credential management
    system in a real weather forecasting service.
    """
    
    def __init__(self, environment: str = "production"):
        self.environment = environment
        self.logger = logging.getLogger(f"forecast_service_{environment}")
        
        # Initialize credential manager
        master_key_env = f"ADELAIDE_WEATHER_MASTER_KEY_{environment.upper()}"
        self.credential_manager = SecureCredentialManager(
            environment=environment,
            master_key_env=master_key_env
        )
        
        # Initialize service components
        self.weather_client = WeatherAPIClient(self.credential_manager, environment)
        self.database_manager = DatabaseManager(self.credential_manager)
        
        self.logger.info(f"ForecastService initialized for {environment} environment")
    
    async def setup_credentials(self):
        """Setup initial credentials for the service."""
        self.logger.info("Setting up service credentials...")
        
        # Development credentials (these would be different in production)
        if self.environment == "development":
            development_credentials = [
                {
                    "id": "gfs_api_key",
                    "value": "dev-gfs-api-key-12345",
                    "type": CredentialType.API_KEY,
                    "security_level": SecurityLevel.STANDARD,
                    "tags": {"service": "gfs", "env": "dev"}
                },
                {
                    "id": "era5_api_key",
                    "value": "dev-era5-api-key-67890",
                    "type": CredentialType.API_KEY,
                    "security_level": SecurityLevel.STANDARD,
                    "tags": {"service": "era5", "env": "dev"}
                },
                {
                    "id": "postgres_password",
                    "value": "dev-postgres-password-secure",
                    "type": CredentialType.DATABASE_PASSWORD,
                    "security_level": SecurityLevel.HIGH,
                    "tags": {"service": "postgresql", "env": "dev"}
                },
                {
                    "id": "redis_password",
                    "value": "dev-redis-password-cache",
                    "type": CredentialType.DATABASE_PASSWORD,
                    "security_level": SecurityLevel.STANDARD,
                    "tags": {"service": "redis", "env": "dev"}
                },
                {
                    "id": "jwt_secret",
                    "value": "dev-jwt-signing-secret-key",
                    "type": CredentialType.JWT_SECRET,
                    "security_level": SecurityLevel.CRITICAL,
                    "tags": {"service": "authentication", "env": "dev"}
                }
            ]
            
            for cred in development_credentials:
                try:
                    self.credential_manager.store_credential(
                        credential_id=cred["id"],
                        credential_value=cred["value"],
                        credential_type=cred["type"],
                        security_level=cred["security_level"],
                        tags=cred["tags"],
                        user_id="system_setup"
                    )
                    self.logger.info(f"Setup credential: {cred['id']}")
                except Exception as e:
                    if "already exists" in str(e):
                        self.logger.info(f"Credential {cred['id']} already exists")
                    else:
                        self.logger.error(f"Failed to setup credential {cred['id']}: {e}")
    
    async def generate_forecast(self, location: str, forecast_hours: list) -> Dict[str, Any]:
        """
        Generate weather forecast using secure credentials for data access.
        
        Args:
            location: Location identifier (e.g., "Adelaide")
            forecast_hours: List of forecast hours to generate
            
        Returns:
            Complete forecast data
        """
        self.logger.info(f"Generating forecast for {location}, hours: {forecast_hours}")
        
        try:
            # Variables to fetch
            weather_variables = ["t2m", "u10", "v10", "msl", "cape"]
            
            # Fetch current conditions from multiple sources
            forecast_data = {
                "location": location,
                "generated_at": datetime.utcnow().isoformat(),
                "forecasts": {},
                "sources": {}
            }
            
            # Fetch GFS forecast data
            for hour in forecast_hours:
                gfs_data = await self.weather_client.fetch_gfs_data(weather_variables, hour)
                forecast_data["forecasts"][f"hour_{hour}"] = gfs_data
            
            # Fetch historical ERA5 data for analog search
            era5_data = await self.weather_client.fetch_era5_data(
                weather_variables, 
                "2023-11-01"  # Example historical date
            )
            forecast_data["sources"]["era5_analog"] = era5_data
            
            # Store forecast data in database
            await self.database_manager.store_weather_data(forecast_data)
            
            self.logger.info(f"Forecast generation completed for {location}")
            return forecast_data
            
        except Exception as e:
            self.logger.error(f"Forecast generation failed: {e}")
            raise
    
    async def authenticate_request(self, token: str) -> Dict[str, Any]:
        """
        Authenticate API request using JWT secret from credential manager.
        
        Args:
            token: JWT token to validate
            
        Returns:
            Authentication result
        """
        try:
            # Retrieve JWT signing secret
            with self.credential_manager.secure_context("jwt_secret", "auth_service") as jwt_secret:
                # In real implementation, would validate JWT token
                # Example with PyJWT:
                # import jwt
                # payload = jwt.decode(token, jwt_secret, algorithms=["HS256"])
                
                # Mock authentication for demo
                auth_result = {
                    "authenticated": True,
                    "user_id": "demo_user",
                    "permissions": ["read_forecasts", "write_forecasts"],
                    "expires_at": (datetime.utcnow()).isoformat()
                }
                
                self.logger.info(f"Request authenticated for user: {auth_result['user_id']}")
                return auth_result
                
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return {"authenticated": False, "error": str(e)}
    
    async def rotate_credentials(self, credential_ids: list):
        """
        Rotate multiple credentials as part of security maintenance.
        
        Args:
            credential_ids: List of credential IDs to rotate
        """
        self.logger.info(f"Starting credential rotation for: {credential_ids}")
        
        rotation_results = {}
        
        for cred_id in credential_ids:
            try:
                # Mark for rotation
                self.credential_manager.mark_for_rotation(cred_id, "security_admin")
                
                # Generate new credential value (in production, this would be more sophisticated)
                import secrets
                new_value = f"rotated-{cred_id}-{secrets.token_urlsafe(16)}"
                
                # Perform rotation
                self.credential_manager.rotate_credential(cred_id, new_value, "security_admin")
                
                rotation_results[cred_id] = {"status": "success", "rotated_at": datetime.utcnow().isoformat()}
                self.logger.info(f"Successfully rotated credential: {cred_id}")
                
            except Exception as e:
                rotation_results[cred_id] = {"status": "failed", "error": str(e)}
                self.logger.error(f"Failed to rotate credential {cred_id}: {e}")
        
        return rotation_results
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health including credential management."""
        health = self.credential_manager.health_check()
        
        # Add service-specific health information
        health["service"] = "forecast_service"
        health["environment"] = self.environment
        health["components"] = {
            "credential_manager": "healthy" if health["status"] == "healthy" else "degraded",
            "weather_client": "healthy",
            "database_manager": "healthy"
        }
        
        return health


async def main():
    """Demonstrate complete weather service with secure credential management."""
    print("Adelaide Weather Service with Secure Credential Management")
    print("=" * 60)
    
    # Set up environment
    os.environ["ADELAIDE_WEATHER_MASTER_KEY_DEVELOPMENT"] = "demo-master-key-dev-12345"
    
    # Initialize forecast service
    forecast_service = ForecastService(environment="development")
    
    try:
        # Setup credentials
        await forecast_service.setup_credentials()
        print("✓ Credentials setup completed")
        
        # Generate a forecast
        forecast = await forecast_service.generate_forecast(
            location="Adelaide",
            forecast_hours=[0, 6, 12, 24]
        )
        print(f"✓ Forecast generated with {len(forecast['forecasts'])} time steps")
        
        # Test authentication
        mock_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test"
        auth_result = await forecast_service.authenticate_request(mock_token)
        print(f"✓ Authentication test: {auth_result['authenticated']}")
        
        # Test credential rotation
        rotation_result = await forecast_service.rotate_credentials(["gfs_api_key"])
        print(f"✓ Credential rotation test: {rotation_result}")
        
        # Check system health
        health = forecast_service.get_system_health()
        print(f"✓ System health: {health['status']}")
        print(f"  - Total credentials: {health['credential_count']}")
        print(f"  - Components: {health['components']}")
        
        if health['issues']:
            print("  - Issues detected:")
            for issue in health['issues']:
                print(f"    • {issue}")
        
        print("\n" + "=" * 60)
        print("✅ Weather service integration demonstration completed!")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))