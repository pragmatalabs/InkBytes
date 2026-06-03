export class SessionAttributes {
    createdAt: Date;
    updatedAt: Date;
    outlet: string;
    total_articles: number;
    failed_articles: number;
    duration: number;
    success_rate: number;
    completed_session: boolean;
    successful_articles: number;
    start_time: Date;
    end_time: Date;
    results_staging_file_name: null;

    constructor(
        data: SessionAttributes
    ) {
        this.createdAt = data.createdAt;
        this.updatedAt = data.updatedAt;
        this.outlet = data.outlet;
        this.total_articles = data.total_articles;
        this.failed_articles = data.failed_articles;
        this.duration = data.duration;
        this.success_rate = data.success_rate;
        this.completed_session = data.completed_session;
        this.successful_articles = data.successful_articles;
        this.start_time = data.start_time;
        this.end_time = data.end_time;
        this.results_staging_file_name = data.results_staging_file_name;
    }
}