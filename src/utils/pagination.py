"""分页工具类"""


class Pagination:
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page
        self.has_next = page < self.pages
        self.has_prev = page > 1
        self.next_num = page + 1 if self.has_next else None
        self.prev_num = page - 1 if self.has_prev else None

    def iter_pages(self, left_edge=2, right_edge=2, left_current=2, right_current=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (num <= left_edge or
                (self.page - left_current - 1 < num < self.page + right_current + 1) or
                num > self.pages - right_edge):

                if last + 1 != num:
                    yield None  # 表示省略号
                yield num
                last = num