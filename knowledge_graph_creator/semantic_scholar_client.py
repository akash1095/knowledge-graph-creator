import os
from typing import Any, Dict, Optional

import requests


class SemanticScholarClient:
    """Client for interacting with Semantic Scholar API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._get_api_key()
        self.base_url = "https://api.semanticscholar.org/graph/v1"
        self.headers = {"x-api-key": self.api_key}

    @staticmethod
    def _get_api_key() -> str:
        """Retrieve the API key from environment variables."""
        api_key = os.getenv("SS_API_KEY")
        if not api_key:
            raise ValueError(
                "API key not found. Please set the SS_API_KEY environment variable."
            )
        return api_key

    def get_paper_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """Fetch paper JSON from Semantic Scholar API based on the paper title."""
        try:
            url = f"{self.base_url}/paper/search/match"
            query_params = {
                "query": title,
                "fields": "paperId,corpusId,url,title,abstract,venue,publicationVenue,year,"
                "referenceCount,citationCount,influentialCitationCount,isOpenAccess,"
                "openAccessPdf,fieldsOfStudy,s2FieldsOfStudy,publicationTypes,"
                "publicationDate,journal,authors",
            }
            response = requests.get(
                url, params=query_params, headers=self.headers
            ).json()

            if "error" in response:
                print(f"API Error for query '{title}': {response['error']}")
                return None

            if not response.get("data"):
                return None

            return response["data"][0]
        except Exception as e:
            print(f"Error fetching paper JSON for query '{title}': {e}")
            return None
