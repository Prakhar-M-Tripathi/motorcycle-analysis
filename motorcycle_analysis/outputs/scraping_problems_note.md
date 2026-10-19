# Scraping Problems — What Went Wrong and Why
**Project:** Indian Motorcycle Brand Network Bottleneck Analysis  
**Note date:** June 2026  
**Written for:** future reference, in plain English

---

## What this note is for

Building the web scraper for this project was harder than expected. This note documents every major problem that came up, explains why it happened in plain English, and records the fix. If you ever need to re-run the scraper, update the code, or debug a new failure, read this first — it will save you hours.

---

## Problem 1 — The website URLs were completely wrong at first

**What happened:**  
The first guess for the URL structure was something like `bikewale.com/dealers/royal-enfield/delhi/`. All of these URLs returned a "404 Not Found" error — the page didn't exist. Dozens of variations were tried and all failed.

**Why it happened:**  
BikeWale's actual URL structure is not obvious from the outside. You cannot guess it reliably. The real paths turned out to be:
- Service centers: `/service-centers/royalenfield/delhi/`
- Showrooms: `/dealer-showrooms/royalenfield/delhi/`

Note that "dealer-showrooms" (not "dealers") and "service-centers" (not "service") are the exact words used. These were discovered by downloading and reading BikeWale's own internal JavaScript file, which contained the URL construction logic the site itself uses.

**The fix:**  
Stop guessing. Write a script (`find_api.py`) that downloads the site's JavaScript bundle and searches for URL patterns inside it. This is called "reverse engineering the front-end," and it's the correct approach for any modern website.

---

## Problem 2 — The brand name in the URL is not what you'd expect

**What happened:**  
Even after finding the correct URL path structure, the brand part of the URL was wrong. Using "royal-enfield" as the brand identifier gave a 404. Using "ola-electric" for OLA also gave a 404.

**Why it happened:**  
BikeWale uses its own internal short codes (called "maskings") for brand names in URLs. These maskings are different from the brand's common name:

| What you'd expect | What BikeWale actually uses |
|---|---|
| royal-enfield | royalenfield |
| ola-electric | ola |
| hero | hero |
| bajaj | bajaj |

The maskings were discovered by calling BikeWale's internal API (`/api/servicecenter/cities/make/{id}/`) and inspecting the response.

**The fix:**  
A lookup table (`BIKEWALE_BRAND_SLUG`) is stored in `constants.py`. Every brand's masking was verified manually before being added. Never hardcode a brand name in a URL — always look it up from this table.

---

## Problem 3 — The scraper was reading the number 25, but it was the wrong 25

**What happened:**  
Early in testing, the scraper kept extracting the number "25" as the service center count for Royal Enfield — for every city. That's obviously wrong.

**Why it happened:**  
The scraper was loading a generic BikeWale landing page, not the Royal Enfield + Delhi specific page. That generic page contained the marketing text: "more than 25 motorcycle and scooter brands." The scraper found the number 25 in that text and mistakenly thought it was the count it was looking for.

This happened because the URL was still wrong at that stage — the page loaded without an error (HTTP 200), but it wasn't the right page.

**The fix:**  
Once the URLs were corrected (Problems 1 and 2), the correct count appeared immediately. The count is now extracted specifically from the `h1` or `h2` heading at the top of the page, which reads something like "31 Royal Enfield service centers in Delhi." A regex matches only a number at the very start of that heading text.

---

## Problem 4 — Any special character in a print statement crashes the script

**What happened:**  
Whenever the script tried to print a special character — like the Rupee symbol (₹), a checkmark (✓), a cross mark (✗), or a decorative line (─) — it crashed with an error like:

```
UnicodeEncodeError: 'charmap' codec can't encode character '₹'
```

This happened multiple times, requiring a full rewrite of the test script.

**Why it happened:**  
Windows uses an older text encoding called "cp1252" for the terminal/console. This encoding only supports Western European characters. Any character outside that set (which includes most symbols, most non-Latin scripts, and the Rupee symbol) cannot be printed to the Windows terminal without crashing.

**The fix:**  
Replace every special character in `print()` statements with plain ASCII equivalents. For example:
- ✓ → `OK`
- ✗ → `!!`
- ₹ → `Rs.`
- ─ → `-`
- ═ → `=`

The rule is: **if it is not a standard keyboard character, it cannot be in a `print()` statement on Windows.** File writes and log files are safe because they use UTF-8 encoding explicitly — only the terminal is affected.

---

## Problem 5 — Opening a visible browser window failed completely

**What happened:**  
The first version of the scraper tried to open a real, visible browser window so you could watch it work. This failed immediately with:

```
BrowserType.launch: spawn UNKNOWN
```

**Why it happened:**  
The scraper uses a tool called Playwright, which controls a browser automatically. There are two modes: headless (invisible, runs in the background) and non-headless (visible window). The visible window mode failed because this particular Windows environment does not have a graphical display environment set up in a way that allows Playwright to spawn a Chromium window.

**The fix:**  
Always use `headless=True` — the invisible mode. The scraper runs fine this way; you just cannot watch it. All results are saved to files regardless, so there is no functional difference.

---

## Problem 6 — The count extractor found nothing at all for a long time

**What happened:**  
Even when the correct page loaded, the scraper extracted no count. It returned `None` for every city, which would have filled the dataset with zeros and ruined the analysis.

**Why it happened:**  
The first version of `extract_count()` looked for HTML elements with class names like `heading`, `title`, `count`, or `listing-count`. BikeWale does not use any of these class names. The count is in a plain `<h2>` tag with no special class at all.

**The fix:**  
Simplify the extractor to check every `<h1>` and `<h2>` element on the page — no class filtering. Then use a regular expression to check if the text starts with a number. The heading "31 Royal Enfield service centers in Delhi" starts with 31, so `re.match(r"^(\d+)", text)` catches it. This approach is robust because BikeWale always puts the count as the first word of the heading.

---

## Problem 7 — Dashboard chart colours caused a crash

**What happened:**  
The dashboard script (`test_dashboard.py`) crashed with a Plotly error about invalid colour values when trying to draw the table and the summary annotation box.

**Why it happened:**  
The code used 8-character hex colour strings like `#4C72B044`. Standard hex colours are 6 characters (e.g., `#4C72B0`). The extra two characters (`44`) are supposed to add transparency (alpha), but Plotly's table and annotation components do not accept this format — they only accept standard 6-character hex, or `rgba(r, g, b, a)` format.

**The fix:**  
Replace all 8-character hex+alpha strings with plain 6-character hex values. For subtle backgrounds, just use light grey (`#eeeeee` or `#f5f5f5`) instead of a transparent version of the zone colour.

---

## Summary table

| # | Problem | Root cause | Fix |
|---|---|---|---|
| 1 | All URLs returned 404 | Wrong URL path structure | Read BikeWale's own JS to find real paths |
| 2 | Brand name in URL was wrong | BikeWale uses internal "maskings" | Lookup table in `constants.py` |
| 3 | Extracted number 25 everywhere | Wrong URL loaded generic page | Fix URLs; extract from h1/h2 heading only |
| 4 | Any symbol crashes the script | Windows terminal uses cp1252 encoding | ASCII-only in `print()` statements |
| 5 | Visible browser fails to launch | No graphical display in this environment | Always use `headless=True` |
| 6 | Count extractor returned nothing | Looked for CSS classes that don't exist | Check all h1/h2, match leading integer |
| 7 | Dashboard crashed on colours | 8-char hex+alpha not supported by Plotly | Use plain 6-char hex colours |

---

## One rule to remember

> **BikeWale is a JavaScript-rendered website.** The data does not exist in the raw HTML that a simple `requests.get()` call returns — it is injected by JavaScript after the page loads. This is why the scraper uses Playwright (a full browser engine) rather than a simple HTTP library. Any future scraper that replaces Playwright with `requests` or `urllib` will get empty pages.
