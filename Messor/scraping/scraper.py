import json
from datetime import datetime
from enum import Enum
from typing import Optional

from inkbytes.common.system.module_handler import get_module_name
from pydantic import BaseModel, Field

from inkbytes.models.articles import ArticleCollection

MODULE_NAME = get_module_name(2)

class SessionSavingMode(Enum):
    SAVE_TO_FILE = "save_to_file"
    SEND_TO_API = "send_to_api"


class JsonEncoderForDateTime(json.JSONEncoder):
    def encodeDatetimeObject(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().encodeDatetimeObject(obj)


class ScrapingStats(BaseModel):
    start_time: datetime = Field(default_factory=datetime.utcnow)
    outlet_name: str = Field(default_factory=str)
    results_staging_file_name: str = Field(default_factory=str)
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
        self.completed_session = True

    def increment_total_articles(self):
        self.total_articles += 1

    def increment_failed_articles(self):
        self.failed_articles += 1

    def increment_successful_articles(self):
        self.successful_articles += 1

    def set_results_staging_file_name(self, file_name: str):
        self.results_staging_file_name = file_name

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
                "results_staging_file_name": self.results_staging_file_name,
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
