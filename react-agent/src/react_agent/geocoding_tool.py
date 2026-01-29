"""Geocoding 도구 - 장소명/주소를 좌표로 변환"""
import logging
from typing import Optional, Dict, Any
import httpx
from urllib.parse import quote

logger = logging.getLogger(__name__)


class GeocodingTool:
    """장소명이나 주소를 위도/경도 좌표로 변환하는 도구"""

    def __init__(self):
        """Geocoding 도구 초기화"""
        self.nominatim_url = "https://nominatim.openstreetmap.org/search"
        self.headers = {
            "User-Agent": "carbon-ai-chatbot/1.0"  # Nominatim requires User-Agent
        }

    def geocode(self, query: str, country_code: str = "kr") -> Optional[Dict[str, Any]]:
        """
        장소명이나 주소를 좌표로 변환

        Args:
            query: 검색할 장소명 또는 주소 (예: "한국교통공사", "서울시청")
            country_code: 국가 코드 (기본값: "kr" 한국)

        Returns:
            성공 시: {
                "latitude": float,
                "longitude": float,
                "display_name": str,
                "address": dict
            }
            실패 시: None
        """
        try:
            # URL 인코딩
            encoded_query = quote(query)

            # Nominatim API 호출
            params = {
                "q": query,
                "format": "json",
                "limit": 1,
                "countrycodes": country_code,
                "addressdetails": 1
            }

            response = httpx.get(
                self.nominatim_url,
                params=params,
                headers=self.headers,
                timeout=10.0
            )

            if response.status_code != 200:
                logger.error(f"Geocoding API 오류: {response.status_code}")
                return None

            results = response.json()

            if not results:
                logger.warning(f"'{query}'에 대한 geocoding 결과 없음")
                return None

            # 첫 번째 결과 사용
            result = results[0]

            return {
                "latitude": float(result["lat"]),
                "longitude": float(result["lon"]),
                "display_name": result["display_name"],
                "address": result.get("address", {})
            }

        except httpx.TimeoutException:
            logger.error(f"Geocoding API 타임아웃: {query}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Geocoding API 요청 실패: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Geocoding 응답 파싱 오류: {e}")
            return None

    def geocode_multiple(self, queries: list[str], country_code: str = "kr") -> list[Dict[str, Any]]:
        """
        여러 장소를 한번에 geocoding

        Args:
            queries: 장소명 리스트
            country_code: 국가 코드

        Returns:
            각 장소의 geocoding 결과 리스트
        """
        results = []
        for query in queries:
            result = self.geocode(query, country_code)
            if result:
                result["query"] = query  # 원본 쿼리 추가
                results.append(result)
        return results


# 싱글톤 인스턴스
_geocoding_tool: Optional[GeocodingTool] = None


def get_geocoding_tool() -> GeocodingTool:
    """Geocoding 도구 싱글톤 인스턴스 반환"""
    global _geocoding_tool
    if _geocoding_tool is None:
        _geocoding_tool = GeocodingTool()
    return _geocoding_tool
