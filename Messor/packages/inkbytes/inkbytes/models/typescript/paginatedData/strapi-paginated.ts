export interface Pagination {
    page: number;
    pageSize: number;
    pageCount: number;
    total: number;
}

export interface PaginatedResponse {
    data: any[];
    meta: {
        pagination: Pagination;
    };
}
