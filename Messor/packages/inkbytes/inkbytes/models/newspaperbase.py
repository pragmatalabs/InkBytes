import logging

__name__ = "NewsPaper"

from .outlets import OutletsSource

logger = logging.getLogger(__name__)

import newspaper


def _sanitize_header_value(value):
    """Strip CR/LF and surrounding whitespace from a header/agent value.

    urllib3 raises "Invalid ... return character(s) in header value" for any
    header containing a newline. A YAML folded scalar (>) silently appends one,
    which fails every request and harvests 0 articles. This guard makes that
    class of config typo non-fatal. See incident 2026-06-02.
    """
    if isinstance(value, str):
        return value.replace("\r", " ").replace("\n", " ").strip()
    if isinstance(value, dict):
        return {k: _sanitize_header_value(v) for k, v in value.items()}
    return value


class NewsPaper:
    def __init__(self, agent="", headers="") -> None:
        super().__init__()
        self.agent = _sanitize_header_value(agent)
        self.headers = _sanitize_header_value(headers)
        self.paper = None
        self.newspaper = newspaper
        self.config = {}

    def __iter__(self):
        super().__iter__()

    def generate_paper(self, paper) -> object:
        """
        Generates the newspaper object
        :return: newspaper object
        """
        try:
            paper.download()
            paper.parse()
            paper.set_categories()
            paper.download_categories()  # mthread — can hang on slow/blocked sites
            paper.parse_categories()
            paper.generate_articles()
            self.paper = paper
            return self.paper
        except Exception as e:
            logger.error(f"Could not build Paper: {type(e).__name__}: {e}")

    def build(self, outlet: OutletsSource) -> object:
        """
        Builds the newspaper object
        :param outlet:
        :return: generated object
        """
        self.config = {
            "memoize_articles": False,
            "concurrent": True,
            "follow_meta_refresh": False,
            "http_success_only": False,
            "headers": self.headers,
            "agent": self.agent,
            # Prevent hung connections from freezing a scraper thread indefinitely.
            # newspaper3k passes this to requests; 30 s is generous for news articles.
            "request_timeout": 30,
            # Limit redirects — BBC-style infinite redirect loops hit this ceiling
            # cleanly instead of consuming a thread until Python's 30-redirect cap.
            "MAX_REDIRECTS": 10,
        }
        try:
            paper = self.newspaper.build(outlet.url, **self.config)
            return self.generate_paper(paper)
        except ValueError as e:
            print(e)
            return None


class NewsPaperBuilder:
    pass
