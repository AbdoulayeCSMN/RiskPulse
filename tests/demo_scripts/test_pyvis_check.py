"""Verifie que le HTML final est 100% offline."""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

from pyvis.network import Network
import networkx as nx

G = nx.Graph()
G.add_edge('A', 'B', weight=1.0)
G.add_edge('B', 'C', weight=2.0)

net = Network(cdn_resources='in_line', bgcolor='#0a0a0c', font_color='#e4e4e7')
net.from_nx(G)
html = net.generate_html(notebook=False)

# Apply the same strip as in analyse_view
html = re.sub(
    r'<link[^>]+href=["\']https://cdn\.jsdelivr\.net/[^"\']+["\'][^>]*>',
    "", html,
)
html = re.sub(
    r'<script[^>]+src=["\']https://cdn\.jsdelivr\.net/[^"\']+["\'][^>]*></script>',
    "", html,
)

remotes = re.findall(r'(?:src|href)=["\'](https?://[^"\']+)["\']', html)
print(f"HTML size : {len(html):,} chars")
print(f"Remote references restantes : {len(set(remotes))}")
for r in sorted(set(remotes)):
    print(f"  {r}")
print()
print('OK : HTML 100% offline' if not remotes else 'FAIL')
