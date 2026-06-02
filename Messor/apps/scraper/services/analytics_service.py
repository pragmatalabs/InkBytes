import json
from typing import List, Dict

class AnalyticsService:
    def __init__(self, logger):
        self.logger = logger
    
    def analyze_complexity(self, scraping_sessions: List[dict]) -> dict:
        """Analyze the complexity of the scraping process based on the scraping sessions."""
        self.logger.info("Starting analyze_complexity")
        try:
            if not scraping_sessions:
                self.logger.info("Completed analyze_complexity")
                return {
                    "total_sessions": 0,
                    "total_articles": 0,
                    "average_articles_per_session": 0,
                    "errors": 0
                }
                
            total_articles = sum(len(session.get("articles", [])) for session in scraping_sessions)
            
            complexity_data = {
                "total_sessions": len(scraping_sessions),
                "total_articles": total_articles,
                "average_articles_per_session": (
                    total_articles / len(scraping_sessions) if scraping_sessions else 0
                ),
                "errors": sum(1 for session in scraping_sessions if session.get("error"))
            }
            
            self.logger.info(f"Complexity analysis: {json.dumps(complexity_data, indent=2)}")
            self.logger.info("Completed analyze_complexity")
            return complexity_data
        except Exception as e:
            self.logger.error(f"Error in analyze_complexity: {e}")
            return {
                "total_sessions": 0,
                "total_articles": 0,
                "average_articles_per_session": 0,
                "errors": 1
            }