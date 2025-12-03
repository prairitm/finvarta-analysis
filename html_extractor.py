"""HTML extraction and financial data parsing."""

from typing import Optional

from bs4 import BeautifulSoup

from constants import DEFAULT_SECTIONS


def extract_financial_data(
    html_content: str,
    max_years: int = 5,
    max_quarters: int = 8,
    include_sections: Optional[list] = None,
    aggressive: bool = False
) -> str:
    """
    Extract only essential financial data and create minimal HTML structure.
    
    Args:
        html_content: Raw HTML content from screener.in or similar source
        max_years: Maximum number of years of historical data to include (default: 5)
        max_quarters: Maximum number of quarters to include (default: 8)
        include_sections: List of section IDs to include. If None, includes all sections.
                         Valid sections: 'quarters', 'profit-loss', 'balance-sheet', 
                         'cash-flow', 'ratios', 'shareholding'
        aggressive: If True, summarize older data instead of full tables
        
    Returns:
        Cleaned HTML string containing only financial data
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Default sections to keep
    sections_to_keep = include_sections if include_sections is not None else DEFAULT_SECTIONS
    
    # Build minimal HTML structure
    html_parts = ['<html><body>']
    
    # Company name
    h1 = soup.find('h1')
    if h1:
        html_parts.append(f'<h1>{h1.get_text(strip=True)}</h1>')
    
    # Key ratios
    ratios_ul = soup.find('ul', id='top-ratios')
    if ratios_ul:
        html_parts.append('<h2>Key Ratios</h2><ul>')
        for li in ratios_ul.find_all('li'):
            name = li.find('span', class_='name')
            value = li.find('span', class_='value')
            if name and value:
                html_parts.append(f'<li>{name.get_text(strip=True)}: {value.get_text(strip=True)}</li>')
        html_parts.append('</ul>')
    
    # About section
    about = soup.find('div', class_='about')
    if about:
        html_parts.append('<h2>About</h2>')
        html_parts.append(f'<p>{about.get_text(strip=True)}</p>')
    
    # Pros and Cons
    pros = soup.find('div', class_='pros')
    cons = soup.find('div', class_='cons')
    if pros or cons:
        html_parts.append('<h2>Analysis</h2>')
        if pros:
            html_parts.append('<h3>Pros</h3><ul>')
            for li in pros.find_all('li'):
                html_parts.append(f'<li>{li.get_text(strip=True)}</li>')
            html_parts.append('</ul>')
        if cons:
            html_parts.append('<h3>Cons</h3><ul>')
            for li in cons.find_all('li'):
                html_parts.append(f'<li>{li.get_text(strip=True)}</li>')
            html_parts.append('</ul>')
    
    # Extract financial tables with filtering
    for section_id in sections_to_keep:
        section = soup.find('section', id=section_id)
        if section:
            h2 = section.find('h2')
            if h2:
                html_parts.append(f'<h2>{h2.get_text(strip=True)}</h2>')
            
            # Extract tables
            tables = section.find_all('table', class_='data-table')
            for table in tables:
                html_parts.append('<table>')
                # Headers
                thead = table.find('thead')
                if thead:
                    html_parts.append('<thead><tr>')
                    ths = thead.find_all('th')
                    
                    # Filter columns based on section type
                    if section_id == 'quarters':
                        # Keep first column (row labels) + last N quarters
                        columns_to_keep = [0] + list(range(max(1, len(ths) - max_quarters), len(ths)))
                    elif section_id in ['profit-loss', 'balance-sheet', 'cash-flow', 'ratios']:
                        # Keep first column (row labels) + TTM + last N years
                        # TTM is typically the last column before the years
                        columns_to_keep = [0]  # Always keep first column
                        # Find TTM column if exists
                        ttm_index = None
                        for i, th in enumerate(ths):
                            if th.get_text(strip=True).upper() == 'TTM':
                                ttm_index = i
                                break
                        if ttm_index is not None:
                            columns_to_keep.append(ttm_index)
                        # Add last N years (excluding TTM)
                        year_cols = [i for i in range(1, len(ths)) if i != ttm_index]
                        columns_to_keep.extend(year_cols[-max_years:])
                        columns_to_keep = sorted(set(columns_to_keep))
                    else:
                        # For shareholding and other sections, keep all columns
                        columns_to_keep = list(range(len(ths)))
                    
                    for i in columns_to_keep:
                        if i < len(ths):
                            html_parts.append(f'<th>{ths[i].get_text(strip=True)}</th>')
                    html_parts.append('</tr></thead>')
                    
                    # Body - filter rows to match filtered columns
                    tbody = table.find('tbody')
                    if tbody:
                        html_parts.append('<tbody>')
                        for tr in tbody.find_all('tr'):
                            html_parts.append('<tr>')
                            tds = tr.find_all(['td', 'th'])
                            for i in columns_to_keep:
                                if i < len(tds):
                                    cell_text = tds[i].get_text(strip=True)
                                    # Skip empty cells in aggressive mode
                                    if not (aggressive and not cell_text):
                                        html_parts.append(f'<td>{cell_text}</td>')
                            html_parts.append('</tr>')
                        html_parts.append('</tbody>')
                html_parts.append('</table>')
            
            # Growth tables (ranges-table) - keep all, they're small
            growth_tables = section.find_all('table', class_='ranges-table')
            if growth_tables:
                html_parts.append('<h3>Growth Metrics</h3>')
                for table in growth_tables:
                    html_parts.append('<table>')
                    for tr in table.find_all('tr'):
                        html_parts.append('<tr>')
                        for td in tr.find_all(['td', 'th']):
                            html_parts.append(f'<td>{td.get_text(strip=True)}</td>')
                        html_parts.append('</tr>')
                    html_parts.append('</table>')
    
    html_parts.append('</body></html>')
    
    return ''.join(html_parts)

