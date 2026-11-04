import sys

path = sys.argv[1] if len(sys.argv) > 1 else "index.html"

with open(path, encoding="utf-8") as f:
    html = f.read()

if 'class="slogan"' in html:
    print("Slogan is already in this file. Nothing changed.")
    raise SystemExit

edits = [
    (
        '<h1>Welcome to <span class="hl">Apex Transporte</span></h1>',
        '<h1>Welcome to <span class="hl">Apex Transporte</span></h1>\n'
        '        <p class="slogan">The solution of logistics</p>',
    ),
    (
        ".dh,.dbar,#dlist,#dnone{display:none!important}",
        ".dh,.dbar,#dlist,#dnone{display:none!important}\n"
        ".slip .top p.slogan{color:var(--red)}\n"
        ".slip .top p.slogan{font-family:var(--head)}\n"
        ".slip .top p.slogan{font-size:30px}",
    ),
    (
        "<title>Apex Transporte | Virtual Trucking Company</title>",
        "<title>Apex Transporte | The solution of logistics</title>",
    ),
]

for old, new in edits:
    if html.count(old) != 1:
        print("Could not find this line, so nothing was changed:")
        print(old)
        raise SystemExit
    html = html.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(html)

print("Done. The slogan is now in " + path)
