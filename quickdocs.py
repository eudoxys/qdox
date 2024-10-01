"""Generate docs/index.html from module and README.md

Syntax: quickdocs [OPTION ...]

Options:

    * -: run with no options

    * --debug: Enable debugging traceback on exceptions

    * -h|--help|help: Display this help information

    * --withcss: Generate a template CSS file also

Description:

  The `quickdocs` script generates the documentation for a simple Python project.

  The script loads the module specified in the `pyproject.toml` file and
  outputs the `__doc__` property of the module. It then documents the python
  function and constants, followed by the project metadata.

Usage:

  To use `quickdocs` in a project you must do the following.

    1. Install `quickdocs` from the repo into the current `venv` by running the
       command 
       
         python3 -m pip install git+https://github.com/dchassin/quickdocs
        
    2. Run `quickdocs` in the project root folder by running the command
       
         python3 -m quickdocs -
       
       If you want to include the CSS file, use the option `--withcss`
       
    3. Add/push the new files to GitHub by running the commands 
       
         git commit -a -m "Add docs"
         git push

Text Formatting:

  Text encoding includes the following

    * `Syntax: text`: Syntax text

    * `text:`: Level 2 heading text in module docs or level 3 in function docs

    * `(blank line)`: New paragraph

    * `(four spaces)text`: Preformatted text

    * `(four spaces)*(space)text`: Bulleted list text

    * `(four spaces)(digit)(space)text`: Numbered list item

    * `(seven spaces)text`: List item text continuation

    * `(nine spaces)text`: Preformatted text in a list item

    * `**text**`: **Bold** text

    * `*text*`: *Italic* text
    
    * `!!text!!`: !!Highlight!! text

    * `~~text~~`: ~~strikeout~~ text
    * `__text__`: __underline__ text
    * `^word`: ^superscript word (ends at space)
    * `word`: _subscript word (ends at space)

    * ``text``: `code` text

    * `protocol://url/`: protocol://url/ formatting with active link
"""

import os
import sys
import importlib
import tomllib
import re
import datetime as dt
import shutil

class CommandError(Exception):
    """Error caused by an invalid or missing command line option"""

def main(argv:list[str]=sys.argv):
    """Main CLI

    Arguments:
        argv (list[str]): argument list (default is sys.argv)

    Returns:
        int: exit code
    """

    main.DEBUG = False
    withcss = False

    if len(sys.argv) == 1:
        print([x for x in __doc__.split("\n") if x.startswith("Syntax: ")][0])
        return 0

    if sys.argv[1] in ["-h","--help","help"]:
        print(__doc__)
        return 1

    for arg in argv[1:]:
        key,value = arg.split("=",1) if "=" in arg else (arg,None)
        if arg == "--debug":
            main.DEBUG = True
        elif key == "--withcss":
            withcss = value if value else "quickdocs.css"
        elif arg != "-":
            raise CommandError(f"invalid option '{arg}'")

    with open("pyproject.toml","rb") as fh:
        package = tomllib.load(fh)["project"]
        for item,key in {"authors":"name","maintainers":"name"}.items():
            package[item] = ",".join([x[key] for x in package[item]])
        for item,key in {"license":"text"}.items():
            package[item] = package[item][key]
        for item in ["keywords","classifiers","urls","dependencies"]:
            if isinstance(package[item],dict):
                package[item] = "<br/>".join([f"{x} = {y}" for x,y in package[item].items()])
            elif isinstance(package[item],list):
                package[item] = "<br/>".join(package[item])
            if not package[item]:
                package[item] = "None"
        for item in list(package):
            if item not in ["name","version","description","authors","maintainers",
                "requires-python","dependencies","keywords","license","classifiers","urls"]:
                del package[item]

    module = importlib.import_module(package["name"])
    package_name = package['name'].replace('_',' ').title()

    os.makedirs("docs",exist_ok=True)

    with open("docs/index.html","w",encoding="utf-8") as html:

        def write_html(text,md=True,nl=False):
            if md:
                rules = {
                    # False indicates result is protected from remaining rules once applied
                    r"``": (r"`",False),
                    r"`([^`]+)`": (r"<code>\1</code>",False),
                    r"([a-z]+)://([A-Za-z0-9/.:@+_?&]+)": 
                        (r"""<a href="\1://\2" target="_tab">\1://\2</a>""",False),
                    r"\*\*([^\*]+)\*\*": (r"<b>\1</b>",True),
                    r"\*([^\*]+)\*": (r"<i>\1</i>",True),
                    r"~~([^\+]+)~~": (r"<strike>\1</strike>",True),
                    r"__([^\+]+)__": (r"<u>\1</u>",True),
                    r"!!([^\+]+)!!": (r"""<font class="highlight">\1</font>""",True),
                    r"_([^ ]+)": (r"<sub>\1</sub>",True),
                    r"\^([^ ]+)": (r"<sup>\1</sup>",True),
                }
                hold = []
                for search,replace in rules.items():
                    if replace[1]:
                        text = re.sub(search,replace[0],text)
                    else:
                        result = re.search(search,text)
                        while result:
                            random = f"<protect#{len(hold)}>"
                            hold.append([random,search,replace[0],result])
                            text = re.subn(search,random,text,1)[0]
                            result = re.search(search,text)
                for random,search,replace,result in hold:
                    text = re.subn(random,re.sub(search,replace,result.group()),text,1)[0]

            html.write(text)
            if nl:
                html.write("\n")

        def set_mode(m):
            old = get_mode()
            if m == "pre":
                if not set_mode.pre:
                    write_html("<pre>")
                    set_mode.pre = True
                return old
            if set_mode.pre:
                write_html("</pre>")
                set_mode.pre = False
            if m == "li":
                write_html("<li>")
                set_mode.li = True
                return old
            if set_mode.li:
                write_html("</li>")
                set_mode.li = False
            if set_mode.pre:
                write_html("</pre>")
            if set_mode.mode and set_mode.mode != m:
                set_mode.pre = False
                if set_mode.mode in ["ul","ol"]:
                    write_html("</li>\n")
                write_html(f"</{set_mode.mode}>",nl=True)
                set_mode.mode = None
            if m and m != set_mode.mode:
                set_mode.mode = m
                write_html(f"<{set_mode.mode}>")
            return old
        set_mode.mode = None
        set_mode.pre = False
        set_mode.li = False
        def get_mode():
            return set_mode.mode

        write_html(f"""<!doctype html>
    <html>
    <head>
        <title>{package_name}</title>
        <meta name="expires" content="86400" />
        <link rel="stylesheet" href="quickdocs.css">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css">
    </head>
    <body>

    <!-- Sidebar -->
    <div class="w3-sidebar w3-light-grey w3-bar-block" style="width:180px">
      <center>
        <img src="https://avatars.githubusercontent.com/u/20801735?v=4" height="128px" width="128px"/>
        <br/><a href="https://www.chassin.org/">David P. Chassin</a>
        <br/><a href="https://www.eudoxys.com/">Eudoxys Sciences LLC</a>
      </center>
      <title class="w3-bar-item">{package_name}</title>
      <a href="#main" class="w3-bar-item w3-button">Command Line</a>
      <a href="#python" class="w3-bar-item w3-button">Python Library</a>
      <a href="#package" class="w3-bar-item w3-button">Package Metadata</a>
    </div>

    <!-- Page Content -->
    <div style="margin-left:220px">

    <h1 id="main" class="w3-container">Command Line</h1>

    <p/>""",md=False,nl=True)

        # document main docs
        for line in module.__doc__.split("\n"):
            if len(line) == 0:
                if get_mode() is None:
                    write_html("<p/>")

            # syntax line
            elif line.startswith("Syntax: "):
                write_html(f"Syntax: <code>{line[8:]}</code>")

            # list continuation
            elif get_mode() in ["ol","ul"] and line.startswith("       "):

                # preformatted list continuation
                if line.startswith("         "):
                    set_mode("pre")
                    write_html(f"{line[9:]}")

                # list text
                else:
                    set_mode(get_mode())
                    write_html(line[5:])

            # bulleted list
            elif line.startswith("    * "):
                set_mode("ul")
                line = line.split('*',1)[1][1:]
                if ":" in line:
                    part = line.split(":",1)
                    set_mode("li")
                    write_html(f"\n<code>{part[0]}</code>: {part[1]}")
                elif line.strip():
                    set_mode("li")
                    write_html(line)

            # numbered list
            elif re.match(r"    [0-9\.]+. ",line):
                set_mode("ol")
                line = line.split('.',1)[1]
                if line.strip():
                    set_mode("li")
                    write_html(line)

            # preformatted
            elif line.startswith("    "):
                set_mode("pre")
                write_html(line[4:],nl=True)

            # heading
            elif line.endswith(":") and not line.startswith(" "):
                set_mode(None)
                write_html(f"""\n<h2 class="w3-container">{line[:-1]}</h2>""",nl=True)

            # regular text
            else:
                set_mode(None)
                write_html(line,nl=True)

        set_mode(None)
        write_html("""\n<h1 id="python" class="w3-container">Python Library</h1>""",nl=True)

        # document functions
        for name in dir(module):
            set_mode(None)
            if name.startswith("_"):
                continue
            value = getattr(module,name)
            if callable(value):
                if isinstance(value.__doc__,str):
                    write_html(f"""\n<h2 class="w3-container"><code><b>{name}</b>(""")
                    args = [f"<b>{str(a)}</b>:{re.sub(r'([A-Za-z]+)',r'<i>\1</i>',b.__name__ if hasattr(b,"__name__") else str(b))}" for a,b in value.__annotations__.items() if a != "return"]
                    write_html(", ".join(args))
                    write_html(")")
                    try:
                        c = value.__annotations__["return"]
                        c = c.__name__ if hasattr(c,"__name__") else str(c)
                        write_html(f" &rightarrow; *{c}*")
                    except KeyError:
                        write_html(" &rightarrow; *None*")
                    write_html("</code></h2>\n")

                    for line in value.__doc__.split("\n"):
                        if len(line) == 0:
                            if get_mode() is None:
                                write_html("<p/>")
                        elif line.startswith("    ") and line.strip().endswith(":"):
                            set_mode(None)
                            write_html(f"""<h3 class="w3-container">{line.strip()[:-1]}</h3>\n""")
                        elif line.startswith("        "):
                            set_mode("ul")
                            part = line.strip().split(":",1)
                            if len(part) == 2:
                                write_html(f"<li><code>{part[0]}</code>: {part[1]}</li>\n",md=False)
                            else:
                                write_html(f"<li>{part[0]}</li>\n",md=False)
                        else:
                            set_mode(None)
                            write_html(f"<p/>{line}\n")
                else:
                    print(f"WARNING: function '{name}' has no __doc__")
            set_mode(None)

        # document metadata
        constant_header = False
        for name in dir(module):
            if name.startswith("__"):
                continue
            value = getattr(module,name)
            if type(value) in [int,float,list,dict,str] or value is None:
                if not constant_header:
                    write_html("""<h2 class="w3-container">Python Constants</h2>""")
                    constant_header = True
                write_html(f"<p/><code>{name} = {value}</code>")

        write_html("""\n<h1 id="package" class="w3-container">Package Metadata</h1>\n""")
        write_html("""<p/><table class="w3-container">\n""")
        for key,data in package.items():
            if not key.startswith("Description"):
                write_html(f"<tr><th><nobr>{key.title()}</nobr></th><td>:</td><td>{data}" +
                    "</td></tr>\n")
        write_html("</table>\n")

        # footer
        write_html(f"<hr/><p/><cite>Copyright &copy; {dt.datetime.now().year} David P. Chassin")

        write_html("""</body>
            </html>""",nl=True)

    if withcss:
        shutil.copy(withcss,"docs/quickdocs.css")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        e_type,e_value,e_trace = sys.exc_info()
        print(f"ERROR [{os.path.basename(sys.argv[0])[:-2] + e_type.__name__}]:" +
            f" {e_value}",file=sys.stderr)
        if main.DEBUG:
            raise
