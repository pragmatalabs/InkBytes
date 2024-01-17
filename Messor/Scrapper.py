import json
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from Articles import ArticleCollection


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class ScrapingStats(BaseModel):
    start_time: datetime = Field(default_factory=datetime.utcnow)
    outlet_name: str = Field(default_factory=str)
    end_time: Optional[datetime] = Field(default_factory=datetime.utcnow)
    completed_session: Optional[bool] = False
    successful_articles: int = Field(
        default=0, description="The total number of successful articles processed.")
    total_articles: int = Field(
        default=0, description="The total number of articles processed.")
    failed_articles: int = Field(
        default=0, description="The number of failed articles during processing.")


class ScrapingSession(ScrapingStats):

    def complete_session(self):
        self.end_time = datetime.utcnow()
        self.completed_session=True

    def increment_total_articles(self):
        self.total_articles += 1

    def increment_failed_articles(self):
        self.failed_articles += 1

    def increment_successful_articles(self):
        self.successful_articles += 1

    def calculate_duration(self) -> float:
        end_time = self.end_time or datetime.utcnow()
        return (end_time - self.start_time).total_seconds()

    def calculate_success_rate(self) -> float:
        if self.total_articles == 0:
            return 0
        return self.successful_articles / self.total_articles

    def to_json(self) -> str:
        duration = self.calculate_duration()
        success_rate = (self.calculate_success_rate())
        return {
            "data": {
                "start_time": self.start_time.isoformat(),
                "end_time": self.end_time.isoformat(),
                "total_articles": self.total_articles,
                "failed_articles": self.failed_articles,
                "successful_articles": self.successful_articles,
                "duration": duration,
                "success_rate": success_rate,
                "outlet": self.outlet_name,
                "completed_session": self.completed_session
            }
        }

    class Config:
        orm_mode = True


class ScraperResults(BaseModel):
    processed_articles: ArticleCollection
    session: ScrapingSession
