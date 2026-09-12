"""Generate the profile's native SVG identity from the portfolio register."""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'assets' / 'identity'
OUT.mkdir(exist_ok=True)
items = json.loads((ROOT / 'data/portfolio.json').read_text())['first_party']
public = sum(i['visibility'] == 'public' for i in items)
private = len(items) - public

def text(x, y, value, size=20, fill='#f3eee5', weight=400, spacing=0):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" font-weight="{weight}" letter-spacing="{spacing}">{escape(str(value))}</text>'

def svg(name, width, height, label, content):
    (OUT / name).write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title">
<title id="title">{escape(label)}</title>
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="#0b1721"/><stop offset="1" stop-color="#11101b"/></linearGradient></defs>
<rect width="{width}" height="{height}" rx="16" fill="url(#bg)"/>
<g font-family="DejaVu Sans, Arial, sans-serif">{content}</g></svg>\n''')

content = '<path d="M38 43H1162" stroke="#34414b"/><path d="M38 43H155" stroke="#64e5d2" stroke-width="3"/>'
content += text(38, 82, 'CONROY1988  /  INDEPENDENT PROJECTS', 18, '#64e5d2', 600, 2)
content += text(38, 173, 'DANIEL CONROY', 76, weight=700, spacing=-3)
content += text(40, 221, 'Useful software. Better game worlds.', 31)
content += text(40, 259, 'Built in Edinburgh. Shared everywhere.', 24, '#a9b8c6')
content += '<path d="M38 294H1162" stroke="#34414b"/>'
for x, n, label, accent in [(40,len(items),'PORTFOLIO SYSTEMS','#64e5d2'),(430,public,'PUBLIC PRODUCTS','#b9a5ff'),(820,private,'PRIVATE PLATFORMS','#edb77c')]:
    content += text(x, 359, f'{n:02}', 48, accent, 700)
    content += text(x+86, 352, label, 17, '#c5cdd6', 500)
svg('masthead.svg',1200,395,f'Daniel Conroy — independent projects from Edinburgh; {len(items)} systems, {public} public products, {private} private platforms',content)

cards = [
 ('games.svg','01','GAME WORLDS','Guides. Atlases. Original music.','TKB Gaming + CRNY','#64e5d2'),
 ('missionchief.svg','02','MISSIONCHIEF','Toolkit. Animated fleet. Mission icons.','Explore the command suite','#edb77c'),
 ('software.svg','03','INDEPENDENT SOFTWARE','Achievements. Browsers. Media.','Find your next useful tool','#b9a5ff'),
 ('collaboration.svg','04','BEHIND THE SYSTEMS','Infrastructure. Community. Collaboration.','People and projects, properly credited','#89bcf2')]
for filename,number,title,subtitle,cta,accent in cards:
    c=f'<path d="M24 26H556" stroke="#34414b"/><path d="M24 26H88" stroke="{accent}" stroke-width="3"/>'
    c+=text(24,63,number,20,accent,600)+text(72,63,title,23,weight=700)
    c+=text(24,105,subtitle,19,'#bdc9d4')
    c+=text(24,151,cta,17,accent,500)+text(545,151,'→',25,accent)
    svg(filename,580,181,title+' — '+subtitle,c)
