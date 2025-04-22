from bs4 import BeautifulSoup
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator


# --- HTML Link Removal Logic ---
def remove_links(html):
    """Remove navigation elements, links and related structures from HTML"""
    soup = BeautifulSoup(html, "html.parser")

    # Remove navigation elements
    for element in soup.find_all(["nav", "header", "footer"]):
        element.decompose()

    # Remove all link tags and their content
    for a in soup.find_all("a"):
        a.decompose()

    # Find and remove navigation lists (common in site menus)
    for ul in soup.find_all("ul"):
        # Check if this list is likely a navigation menu
        link_count = len(ul.find_all("li"))
        if link_count > 3:  # If it has multiple list items, likely a menu
            ul.decompose()

    # Remove empty list items
    for li in soup.find_all("li"):
        if not li.get_text(strip=True):
            li.decompose()

    # Remove elements with navigation-related classes or IDs
    nav_indicators = ["nav", "menu", "sidebar", "navigation", "toc", "breadcrumb"]
    for cls in nav_indicators:
        for element in soup.find_all(class_=lambda c: c and cls in c.lower()):
            element.decompose()
        for element in soup.find_all(id=lambda i: i and cls in i.lower()):
            element.decompose()

    return str(soup)


class LinkRemovingMarkdownGenerator(DefaultMarkdownGenerator):
    """Custom markdown generator that removes links and nav elements before processing"""

    def generate_markdown(self, cleaned_html, source_url=None, *args, **kwargs):
        # Pre-process the HTML to remove links and nav elements
        cleaned_html = remove_links(cleaned_html)
        markdown = super().generate_markdown(cleaned_html *args, **kwargs)
        if source_url:
            markdown = f"Source: {source_url}\n\n" + markdown
        return markdown
        # Call the parent implementation with the modified HTML
        # return super().generate_markdown(cleaned_html, *args, **kwargs)
