"""Fake HTML pages and a fake HTTP client so tests never touch the internet."""
from bs4 import BeautifulSoup


class FakeClient:
    """Mimics HttpClient.get_soup using an in-memory {url: html} mapping."""

    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get_soup(self, url):
        self.requested.append(url)
        html = self.pages.get(url)
        return BeautifulSoup(html, "lxml") if html else None


def book_item(title, href, price="\u00a351.77", rating="Three", avail="In stock"):
    price_html = f'<p class="price_color">{price}</p>' if price else ""
    return (
        '<article class="product_pod">'
        f'<p class="star-rating {rating}"></p>'
        f'<h3><a href="{href}" title="{title}">{title[:12]}...</a></h3>'
        f'<div class="product_price">{price_html}'
        f'<p class="instock availability">\n  {avail}\n</p></div></article>'
    )


def books_page(items, next_href=None, sidebar=""):
    nxt = f'<li class="next"><a href="{next_href}">next</a></li>' if next_href else ""
    return (
        f"<html><body>{sidebar}<ol>{''.join(items)}</ol>"
        f'<ul class="pager">{nxt}</ul></body></html>'
    )


def quote_item(text, author, tags):
    tag_html = "".join(f'<a class="tag" href="/tag/{t}/">{t}</a>' for t in tags)
    return (
        '<div class="quote">'
        f'<span class="text">\u201c{text}\u201d</span>'
        f'<span>by <small class="author">{author}</small></span>'
        f'<div class="tags">{tag_html}</div></div>'
    )


def quotes_page(items, next_href=None):
    nxt = f'<li class="next"><a href="{next_href}">Next</a></li>' if next_href else ""
    return f'<html><body>{"".join(items)}<ul class="pager">{nxt}</ul></body></html>'
