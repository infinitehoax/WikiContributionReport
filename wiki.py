import mwclient
import pandas as pd
from datetime import datetime
from collections import defaultdict
import html

# --- 1. Fetch Revision Data (Corrected) ---
def get_revision_data(page_title):
    """Fetches and processes revision history for a given Wikipedia page."""
    print("Connecting to English Wikipedia...")
    site = mwclient.Site('en.wikipedia.org', clients_useragent='ContributionAnalyzer/1.0 (your@email.com)')

    print(f"Fetching page: '{page_title}'")
    
    try:
        page = site.pages[page_title]
        
        if not page.exists:
            print(f"Error: Page '{page_title}' not found.")
            return None, None

        print("Fetching all revisions (this may take a moment)...")
        
        contribution_data = []
        previous_size = 0
        
        # Get revisions in chronological order (oldest first)
        for rev in page.revisions(dir='newer', prop='user|size'):
            current_size = rev.get('size', 0)
            size_difference = current_size - previous_size
            contribution_data.append({
                'user': rev.get('user', 'Unknown'),
                'change': size_difference,
            })
            previous_size = current_size
        
        print(f"Processed {len(contribution_data)} revisions.")
        return contribution_data, page.name
        
    except Exception as e:
        print(f"Error fetching page data: {e}")
        return None, None

# --- 2. Aggregate Data by User ---
def aggregate_user_stats(contribution_data):
    """Calculates statistics for each user from the revision data."""
    user_stats = defaultdict(lambda: {'edits': 0, 'text_added': 0, 'text_removed': 0})
    
    for rev in contribution_data:
        user = rev['user']
        change = rev['change']
        
        user_stats[user]['edits'] += 1
        if change > 0:
            user_stats[user]['text_added'] += change
        else:
            user_stats[user]['text_removed'] += abs(change)
            
    total_text_added = sum(stats['text_added'] for stats in user_stats.values())
    
    if total_text_added == 0:
        print("Warning: No text was added to this page, cannot calculate percentages.")
        return []

    processed_stats = []
    for user, stats in user_stats.items():
        percentage = (stats['text_added'] / total_text_added) * 100 if total_text_added > 0 else 0
        processed_stats.append({
            'user': user,
            'percentage': percentage,
            **stats
        })
        
    processed_stats.sort(key=lambda x: x['percentage'], reverse=True)
    
    return processed_stats

# --- 3. Generate the HTML Report ---
def create_html_report(stats, page_title):
    """Generates a self-contained HTML file from the user statistics."""
    
    table_rows = ""
    for user_data in stats:
        user_name_safe = html.escape(user_data['user'])
        edits = f"{user_data['edits']:,}"
        text_added = f"+{user_data['text_added']:,}"
        text_removed = f"-{user_data['text_removed']:,}"
        percentage = user_data['percentage']
        
        table_rows += f"""
        <tr>
            <td><a href="https://en.wikipedia.org/wiki/User:{user_name_safe}" target="_blank">{user_name_safe}</a></td>
            <td>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width: {percentage:.2f}%;"></div>
                </div>
            </td>
            <td class="percentage-label">{percentage:.2f}%</td>
            <td class="number">{edits}</td>
            <td class="number added">{text_added}</td>
            <td class="number removed">{text_removed}</td>
        </tr>
        """

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Wikipedia Contribution Report: {html.escape(page_title)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f8f9fa;
            color: #212529;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 960px;
            margin: auto;
            background-color: #ffffff;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.05);
            padding: 30px;
        }}
        h1 {{
            color: #343a40;
            border-bottom: 2px solid #dee2e6;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        p.summary {{
            font-size: 1.1em;
            color: #6c757d;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #dee2e6;
        }}
        thead th {{
            background-color: #e9ecef;
            font-weight: 600;
            color: #495057;
        }}
        tbody tr:nth-of-type(even) {{
            background-color: #f8f9fa;
        }}
        tbody tr:hover {{
            background-color: #e9ecef;
        }}
        a {{
            color: #007bff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .progress-bar-container {{
            width: 100%;
            background-color: #e9ecef;
            border-radius: 5px;
            height: 20px;
            overflow: hidden;
        }}
        .progress-bar {{
            background: linear-gradient(90deg, #28a745, #218838);
            height: 100%;
            text-align: right;
            color: white;
            line-height: 20px;
            border-radius: 5px;
            transition: width 0.5s ease-in-out;
        }}
        .percentage-label {{
            font-weight: bold;
            min-width: 70px;
            text-align: right;
        }}
        .number {{
            text-align: right;
            font-family: "Courier New", Courier, monospace;
        }}
        .added {{ color: #28a745; }}
        .removed {{ color: #dc3545; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Contribution Report</h1>
        <p class="summary">Analysis of user contributions for the Wikipedia article: <strong>{html.escape(page_title)}</strong></p>
        
        <table>
            <thead>
                <tr>
                    <th>User</th>
                    <th style="width: 30%;">Contribution (% of Text Added)</th>
                    <th></th>
                    <th>Edits</th>
                    <th>Bytes Added</th>
                    <th>Bytes Removed</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
    """

    filename = "contribution_report.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"\nSuccess! Report saved to '{filename}'")

# --- Main Execution ---
if __name__ == "__main__":
    target_page_title = 'Samsung Galaxy XR'
    
    revision_history, page_title = get_revision_data(target_page_title)
    
    if revision_history:
        user_statistics = aggregate_user_stats(revision_history)
        create_html_report(user_statistics, page_title)
