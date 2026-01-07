"""
Azure AI Search Integration for Threat Intelligence RAG
Provides semantic search over historical threat data
"""

import json
import logging
from datetime import datetime
from typing import Any

from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchableField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
)

from config import settings

logger = logging.getLogger(__name__)


class ThreatIntelligenceSearch:
    """
    Azure AI Search client for threat intelligence RAG
    Enables semantic search over historical security incidents
    """
    
    def __init__(self):
        """Initialize Azure Search clients"""
        self.search_client = None
        self.index_client = None
        
        if settings.AZURE_SEARCH_KEY and settings.AZURE_SEARCH_ENDPOINT:
            try:
                credential = AzureKeyCredential(settings.AZURE_SEARCH_KEY)
                
                # Search client for querying
                self.search_client = SearchClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    index_name=settings.AZURE_SEARCH_INDEX_NAME,
                    credential=credential
                )
                
                # Index client for schema management
                self.index_client = SearchIndexClient(
                    endpoint=settings.AZURE_SEARCH_ENDPOINT,
                    credential=credential
                )
                
                logger.info("✅ Azure AI Search client initialized")
            except Exception as e:
                logger.warning(f"⚠️ Azure Search initialization failed: {e}")
                self.search_client = None
                self.index_client = None
        else:
            logger.info("ℹ️ Azure Search disabled - no credentials provided")
    
    async def ensure_index_exists(self) -> bool:
        """
        Ensure the threat intelligence index exists with proper schema
        Creates it if not present
        """
        if not self.index_client:
            logger.warning("Index client not available")
            return False
        
        try:
            # Check if index exists
            try:
                self.index_client.get_index(settings.AZURE_SEARCH_INDEX_NAME)
                logger.info(f"Index '{settings.AZURE_SEARCH_INDEX_NAME}' already exists")
                return True
            except ResourceNotFoundError:
                logger.info(f"Creating index '{settings.AZURE_SEARCH_INDEX_NAME}'...")
                
                # Define index schema
                index = SearchIndex(
                    name=settings.AZURE_SEARCH_INDEX_NAME,
                    fields=[
                        SimpleField(
                            name="threat_id",
                            type=SearchFieldDataType.String,
                            key=True,
                            filterable=True,
                        ),
                        SearchableField(
                            name="alert_type",
                            type=SearchFieldDataType.String,
                            filterable=True,
                            facetable=True,
                        ),
                        SearchableField(
                            name="severity",
                            type=SearchFieldDataType.String,
                            filterable=True,
                            facetable=True,
                        ),
                        SearchableField(
                            name="title",
                            type=SearchFieldDataType.String,
                            analyzer_name="en.microsoft",
                        ),
                        SearchableField(
                            name="description",
                            type=SearchFieldDataType.String,
                            analyzer_name="en.microsoft",
                        ),
                        SearchableField(
                            name="resolution",
                            type=SearchFieldDataType.String,
                            analyzer_name="en.microsoft",
                        ),
                        SearchableField(
                            name="indicators",
                            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                        ),
                        SearchableField(
                            name="attack_patterns",
                            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                        ),
                        SimpleField(
                            name="threat_score",
                            type=SearchFieldDataType.Double,
                            filterable=True,
                            sortable=True,
                        ),
                        SimpleField(
                            name="confidence_score",
                            type=SearchFieldDataType.Double,
                            filterable=True,
                            sortable=True,
                        ),
                        SimpleField(
                            name="first_seen",
                            type=SearchFieldDataType.DateTimeOffset,
                            filterable=True,
                            sortable=True,
                        ),
                        SimpleField(
                            name="last_seen",
                            type=SearchFieldDataType.DateTimeOffset,
                            filterable=True,
                            sortable=True,
                        ),
                        SearchableField(
                            name="kill_chain_stage",
                            type=SearchFieldDataType.String,
                            filterable=True,
                            facetable=True,
                        ),
                        SearchableField(
                            name="network_context",
                            type=SearchFieldDataType.String,
                        ),
                        SimpleField(
                            name="occurrences",
                            type=SearchFieldDataType.Int32,
                            filterable=True,
                            sortable=True,
                        ),
                    ]
                )
                
                # Create the index
                self.index_client.create_index(index)
                logger.info(f"✅ Index '{settings.AZURE_SEARCH_INDEX_NAME}' created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to ensure index exists: {e}")
            return False
    
    async def index_threat(self, threat_data: dict[str, Any]) -> bool:
        """
        Index a threat document into Azure Search
        
        Args:
            threat_data: Threat intelligence data to index
            
        Returns:
            True if successful, False otherwise
        """
        if not self.search_client:
            logger.debug("Search client not available, skipping indexing")
            return False
        
        try:
            # Prepare document for indexing
            document = {
                "threat_id": threat_data.get("threat_id"),
                "alert_type": threat_data.get("alert_type"),
                "severity": threat_data.get("severity"),
                "title": threat_data.get("title", ""),
                "description": threat_data.get("description", ""),
                "resolution": threat_data.get("resolution", ""),
                "indicators": threat_data.get("indicators", []),
                "attack_patterns": threat_data.get("attack_patterns", []),
                "threat_score": threat_data.get("threat_score", 0.0),
                "confidence_score": threat_data.get("confidence_score", 0.0),
                "first_seen": threat_data.get("first_seen", datetime.now(datetime.UTC)).isoformat(),
                "last_seen": threat_data.get("last_seen", datetime.now(datetime.UTC)).isoformat(),
                "kill_chain_stage": threat_data.get("kill_chain_stage", "Unknown"),
                "network_context": json.dumps(threat_data.get("network_context", {})),
                "occurrences": threat_data.get("occurrences", 1),
            }
            
            # Upload document
            result = self.search_client.upload_documents(documents=[document])
            
            if result[0].succeeded:
                logger.info(f"✅ Indexed threat: {document['threat_id']}")
                return True
            else:
                logger.error(f"Failed to index threat: {result[0].error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error indexing threat: {e}")
            return False
    
    async def search_similar_threats(
        self,
        query: str,
        alert_type: str | None = None,
        severity: str | None = None,
        top: int = 5,
        min_score: float = 0.5
    ) -> list[dict[str, Any]]:
        """
        Search for similar historical threats
        
        Args:
            query: Search query (alert description, indicators, etc.)
            alert_type: Filter by alert type
            severity: Filter by severity
            top: Number of results to return
            min_score: Minimum relevance score threshold
            
        Returns:
            List of similar threat documents
        """
        if not self.search_client:
            logger.debug("Search client not available")
            return []
        
        try:
            # Build filter expression
            filters = []
            if alert_type:
                filters.append(f"alert_type eq '{alert_type}'")
            if severity:
                filters.append(f"severity eq '{severity}'")
            
            filter_expression = " and ".join(filters) if filters else None
            
            # Perform search
            results = self.search_client.search(
                search_text=query,
                filter=filter_expression,
                top=top,
                select=[
                    "threat_id", "alert_type", "severity", "title",
                    "description", "resolution", "indicators",
                    "threat_score", "confidence_score", "kill_chain_stage",
                    "attack_patterns", "network_context", "occurrences"
                ],
                include_total_count=True
            )
            
            # Process results
            threats = []
            for result in results:
                # Filter by minimum score
                if hasattr(result, '@search.score') and result['@search.score'] < min_score:
                    continue
                
                threat = {
                    "threat_id": result.get("threat_id"),
                    "alert_type": result.get("alert_type"),
                    "severity": result.get("severity"),
                    "title": result.get("title"),
                    "description": result.get("description"),
                    "resolution": result.get("resolution"),
                    "indicators": result.get("indicators", []),
                    "threat_score": result.get("threat_score"),
                    "confidence_score": result.get("confidence_score"),
                    "kill_chain_stage": result.get("kill_chain_stage"),
                    "attack_patterns": result.get("attack_patterns", []),
                    "network_context": json.loads(result.get("network_context", "{}")),
                    "occurrences": result.get("occurrences", 1),
                    "relevance_score": getattr(result, '@search.score', 0.0)
                }
                threats.append(threat)
            
            logger.info(f"Found {len(threats)} similar threats for query: {query[:50]}...")
            return threats
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def get_threat_by_id(self, threat_id: str) -> dict[str, Any] | None:
        """
        Retrieve a specific threat by ID
        
        Args:
            threat_id: Unique threat identifier
            
        Returns:
            Threat document or None if not found
        """
        if not self.search_client:
            return None
        
        try:
            result = self.search_client.get_document(key=threat_id)
            
            threat = {
                "threat_id": result.get("threat_id"),
                "alert_type": result.get("alert_type"),
                "severity": result.get("severity"),
                "title": result.get("title"),
                "description": result.get("description"),
                "resolution": result.get("resolution"),
                "indicators": result.get("indicators", []),
                "threat_score": result.get("threat_score"),
                "confidence_score": result.get("confidence_score"),
                "kill_chain_stage": result.get("kill_chain_stage"),
                "attack_patterns": result.get("attack_patterns", []),
                "network_context": json.loads(result.get("network_context", "{}")),
                "occurrences": result.get("occurrences", 1),
            }
            
            return threat
            
        except ResourceNotFoundError:
            logger.warning(f"Threat not found: {threat_id}")
            return None
        except Exception as e:
            logger.error(f"Error retrieving threat: {e}")
            return None
    
    async def update_threat_occurrences(self, threat_id: str) -> bool:
        """
        Increment occurrence count for a threat
        
        Args:
            threat_id: Unique threat identifier
            
        Returns:
            True if successful, False otherwise
        """
        if not self.search_client:
            return False
        
        try:
            # Get existing document
            threat = await self.get_threat_by_id(threat_id)
            if not threat:
                return False
            
            # Increment occurrences
            threat["occurrences"] = threat.get("occurrences", 1) + 1
            threat["last_seen"] = datetime.now(datetime.UTC).isoformat()
            
            # Update document
            result = self.search_client.merge_or_upload_documents(documents=[threat])
            
            if result[0].succeeded:
                logger.info(f"Updated threat occurrences: {threat_id}")
                return True
            else:
                logger.error(f"Failed to update threat: {result[0].error_message}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating threat occurrences: {e}")
            return False
    
    async def get_threat_statistics(self) -> dict[str, Any]:
        """
        Get statistics about indexed threats
        
        Returns:
            Dictionary with threat statistics
        """
        if not self.search_client:
            return {"error": "Search client not available"}
        
        try:
            # Get faceted results for statistics
            results = self.search_client.search(
                search_text="*",
                facets=["alert_type,count:10", "severity,count:10", "kill_chain_stage,count:10"],
                top=0,  # We only want facets, not documents
                include_total_count=True
            )
            
            stats = {
                "total_threats": results.get_count(),
                "by_alert_type": {},
                "by_severity": {},
                "by_kill_chain_stage": {},
            }
            
            # Extract facets
            facets = results.get_facets()
            if facets:
                if "alert_type" in facets:
                    stats["by_alert_type"] = {
                        item["value"]: item["count"] for item in facets["alert_type"]
                    }
                if "severity" in facets:
                    stats["by_severity"] = {
                        item["value"]: item["count"] for item in facets["severity"]
                    }
                if "kill_chain_stage" in facets:
                    stats["by_kill_chain_stage"] = {
                        item["value"]: item["count"] for item in facets["kill_chain_stage"]
                    }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {"error": str(e)}
