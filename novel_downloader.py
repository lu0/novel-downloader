import logging
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple

import requests
from jinja2 import Template
from requests.adapters import HTTPAdapter
from selenium import webdriver
from selenium.webdriver.common.by import By
from urllib3.util.retry import Retry


class StringEnum(Enum):
    def __str__(self) -> str:
        return self._value_


class RegEx(StringEnum):
    ANYTHING = r".*"
    ANY_NUMBERS = r"\d+"
    ANY_WHITE_LINES = r"\n+"
    LAST_PAGE_CONTAINER = rf'data-page="{ANY_NUMBERS}{ANYTHING}Final'


class Html(StringEnum):
    DOUBLE_LINE_BREAK = "<br><br>"
    CHAPTER_BODY_ID = "chapter-content"
    CHAPTER_TITLE_CLASS = "chapter-title"


class FolderName(StringEnum):
    OUTPUT = "output"
    CHAPTERS = "chapters"
    TEMPLATES = "templates"


class FilePath(StringEnum):
    LOG_FILE = "novel_downloader.log"
    HOME_PAGE = f"{FolderName.OUTPUT}/home.html"
    CHAPTER_TEMPLATE = f"{FolderName.TEMPLATES}/chapter_template.html"
    NOVEL_TEMPLATE = f"{FolderName.TEMPLATES}/novel_template.html"


@dataclass
class Chapter:
    number_padded: str
    title: str
    html: str


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(FilePath.LOG_FILE.value), logging.StreamHandler()
    ],
)


def get_novel_dir(novel_title: str) -> str:
    return f"{FolderName.OUTPUT}/{novel_title}"


def get_chapters_dir(novel_dir: str) -> str:
    return f"{novel_dir}/{FolderName.CHAPTERS}"


def create_directories(novel_title: str) -> Tuple[str, str]:
    """Creates directories (and parents) where chapters will be stored in"""
    novel_dir: str = get_novel_dir(novel_title)
    chapters_dir: str = get_chapters_dir(novel_dir)
    os.makedirs(chapters_dir, exist_ok=True)
    return (novel_dir, chapters_dir)


driver = webdriver.Chrome()

session = requests.Session()
retry_policy = Retry(connect=3, backoff_factor=0.5)
http_adapter = HTTPAdapter(max_retries=retry_policy)
session.mount("http://", http_adapter)
session.mount("https://", http_adapter)


def text_to_file(text: str, file_path: str) -> None:
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text)


def url_to_file(url: str, file_path: str) -> None:
    response = session.get(url)
    text_to_file(text=response.text, file_path=file_path)


def download_home_page(home_url: str) -> None:
    url_to_file(url=home_url, file_path=FilePath.HOME_PAGE.value)


def get_total_pages_in_chapter_pager() -> int:
    """
    The home page contains the following element:
        `<a href="/novel-name/?page=I" data-page="I">Final »</a>`
    where `I` is the number of the last page of the chapter paginator.

    Returns:
        int: Number of pages in the chapter pager.
    """
    with open(FilePath.HOME_PAGE.value, "r") as f:
        file_content = f.read()
        container: str = re.search(
            RegEx.LAST_PAGE_CONTAINER.value, file_content
        ).group()
        page_number = int(re.search(RegEx.ANY_NUMBERS.value, container).group())
    logging.info("Number of pages in chapter paged: %s", page_number)
    return page_number


def _pad_number(number: int, pad_length: int) -> str:
    """Pad a number with leading zeros"""
    return str(number).zfill(pad_length)


def extract_chapter_urls(chapter_pager_last: int, home_url: str) -> List[str]:
    """Extract URLs of chapters from each page of the chapter pager

    Args:
        chapter_pager_last (int): Total number of pages in the chapter pager
        home_url (str): URL of the novel

    Returns:
        List[str]: List of chapter URLs
    """
    chapter_urls: List = []
    for page_number in range(1, chapter_pager_last + 1):
        logging.info("Extracting URLs from page %s of chapter pager", page_number)
        page_url: str = f"{home_url}?page={page_number}"
        page = session.get(page_url)
        page_content: str = page.text
        chapter_urls_in_page: List[str] = parse_chapter_urls(page_content, home_url)
        # Slicing since the page also lists 6 random chapters on top of the actual ones...
        # this is a temporary workaround to keep using ReGex (which I'm kinda fast with),
        # but it would be better to use bs4 or some other HTML Parser library.
        chapter_urls_in_page = chapter_urls_in_page[6:]
        logging.info("Number of chapter URLs retrieved: %s", len(chapter_urls_in_page))
        chapter_urls.extend(chapter_urls_in_page)
    return chapter_urls


def _split_home_url(home_url: str) -> Tuple[str, str]:
    """Split the home URL into the base domain and the novel name

    Args:
        home_url (str): URL of the novel

    Returns:
        Tuple[str, str]: Tuple containing the base Domain
            and the novel name (as is in the URL).
    """
    base_domain, novel_title, _ = home_url.rsplit(sep="/", maxsplit=2)
    return (base_domain, novel_title)


def parse_chapter_urls(listing_page_content: str, home_url: str) -> List[str]:
    """
    Parse chapter URLs from a page of the chapter pager

    A page in the chapter pager lists chapters following the below structure:
    ```html
    <a
        href="CHAPTER_REL_PATH"
        title="chapter title"><span
            class="chapter-text">chapter title</span></a>
    ```
    where `CHAPTER_REL_PATH` is the chapter URL relative to the Base Domain.

    This relative URL has the following structure:
        `/novel-name-CHAPTER_FILE_SUFFIX.html`

    Args:
        listing_page_content (str): HTML content of the chapter listing page
        home_url (str): URL to the home page

    Returns:
        List[str]: The list of URLs contained in the chapter listing.
    """
    base_domain, novel_title = _split_home_url(home_url)
    rel_url_pattern = rf"/{novel_title}-{RegEx.ANY_NUMBERS}.html"
    chapter_rel_urls: List[str] = re.findall(
        rel_url_pattern, listing_page_content, re.DOTALL
    )
    chapter_urls = [f"{base_domain}{rp}" for rp in chapter_rel_urls]
    return chapter_urls


def download_all_chapters(chapter_urls: List[str], chapters_dir) -> List[Chapter]:
    total_number_of_chapters: int = len(chapter_urls)
    pad_length: int = len(str(total_number_of_chapters))
    chapter_htmls: List[str] = []
    for chapter_number, chapter_url in enumerate(chapter_urls):
        padded_chapter_number: str = _pad_number(chapter_number + 1, pad_length)
        logging.info(
            "Downloading chapter %s/%s", padded_chapter_number, total_number_of_chapters
        )
        chapter_html: str = download_chapter(
            chapter_url, chapters_dir, padded_chapter_number
        )
        chapter_htmls.append(chapter_html)
    return chapter_htmls


def convert_line_breaks_to_html(s: str) -> str:
    """Replaces any number of white lines with HTML double line breaks"""
    return re.sub(RegEx.ANY_WHITE_LINES.value, Html.DOUBLE_LINE_BREAK.value, s)


def render_chapter_template(chapter_title: Chapter, chapter_body) -> str:
    with open(FilePath.CHAPTER_TEMPLATE.value) as f:
        chapter_template = Template(f.read())
        chapter_html = chapter_template.render(
            chapter_title=chapter_title, chapter_body=chapter_body
        )
    return chapter_html


def save_chapter(chapter: Chapter, chapters_dir=str) -> str:
    dashed_title: str = "-".join(chapter.title.split(sep=" ")).casefold()
    file_path = f"{chapters_dir}/{chapter.number_padded}_{dashed_title}.html"
    text_to_file(chapter.html, file_path)


def render_novel_template(chapter_htmls: List[str]) -> str:
    with open(FilePath.NOVEL_TEMPLATE.value, "r") as f:
        novel_template = Template(f.read())
        novel_html = novel_template.render(chapter_htmls=chapter_htmls)
    return novel_html


def save_novel(novel_html: str, novel_title: str, novel_dir: str) -> str:
    file_path = f"{novel_dir}/{novel_title}.html"
    text_to_file(novel_html, file_path)
    return file_path


def download_chapter(url: str, chapters_dir: str, padded_chapter_number: str) -> str:
    driver.get(url)
    chapter_title: str = driver.find_element(
        By.CLASS_NAME, Html.CHAPTER_TITLE_CLASS
    ).text.title()
    chapter_body_plain: str = driver.find_element(By.ID, Html.CHAPTER_BODY_ID).text
    chapter_body_html: str = convert_line_breaks_to_html(chapter_body_plain)
    chapter_html: str = render_chapter_template(chapter_title, chapter_body_html)
    chapter = Chapter(padded_chapter_number, chapter_title, chapter_html)
    save_chapter(chapter, chapters_dir)
    return chapter_html


def main(url: str) -> None:
    logging.info("Hello! New download process initialized")
    _, novel_title = _split_home_url(url)
    novel_dir, chapters_dir = create_directories(novel_title)
    download_home_page(home_url=url)
    chapter_pager_last: int = get_total_pages_in_chapter_pager()
    chapter_urls: List[str] = extract_chapter_urls(chapter_pager_last, url)
    logging.info(len(chapter_urls))
    chapter_htmls = download_all_chapters(chapter_urls, chapters_dir)
    novel_html: str = render_novel_template(chapter_htmls)
    novel_path: str = save_novel(novel_html, novel_title, novel_dir)
    # return chapter_title, chapter_html
    logging.info("Novel successfully downloaded and saved into %s", novel_path)
    session.close()
    driver.close()


if __name__ == "__main__":
    url = "https://www.novelabook.link/mi-esposo-es-un-billonario/"
    main(url)
