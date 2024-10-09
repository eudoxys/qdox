"""Generate docs/index.html from module contents and metadata

Syntax: qdox [OPTION ...]

Options:

    * -: run with no options

    * --debug: Enable debugging traceback on exceptions

    * -h|--help|help: Display this help information

    * --tomlfile=TOMFILE: Use TOMFILE instead of "pyproject.toml"

    * --withcss[=CSSFILE]: Copy the CSS file to `docs/` (default is `qdox.css`)

Description:

  The `qdox` command generates the documentation for a simple Python
  project. The formatting is designed to use simple text layout as the input 
  so that the same documentation source can be used for both Python `help()` 
  output and the documentation pages.

  The command loads the module specified in the `pyproject.toml` file and
  outputs the `__doc__` property of the module as the command line
  documentation. It then outputs the python functions and constants,
  followed by the project metadata.

  You can use your project's `pages-build-deployment` workflow to deploy the
  documentation to `github.io` or to your own custom site by setting the
  following options in your project `Settings-->Pages`:

    * `Source`: Choose **Deploy from a branch**

    * `Branch`: Choose **main** and **/docs**.

    * `Custom domain`: Enter one if you have one.

Usage:

  To use `qdox` in a project you must do the following.

    1. Install `qdox` from the repo into the current `venv` by running the
       command 
       
         python3 -m pip install git+https://github.com/dchassin/qdox
        
    2. Run `qdox` in the project root folder by running the command
       
         qdox -
       
       If you want to include a CSS file, use the option `--withcss=CSSFILE`, e.g.,
       
         qdox --withcss=mystyles.css

       The `CSSFILE` defaults to `qdox.css` when omitted.
       
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
    
    * `_word`: _subscript word (ends at space)

    * ``text``: `code` text

    * `protocol://url/`: protocol://url/ formatting with active link

Pro-tips:

    The module you are documenting must be installed in the active Python
    environment for `qdox` to read information about the module. 

    If you want to output a colon at the end of a paragraph rather than a
    heading, place a space after the colon and before the end-of-line.
"""

#
# Disable link warnings for now, see issue#1
#
# pylint: disable=R0914,R1702,R0912,R0915,W0718,C0301,E0401,W0702
#

import os
import sys
import importlib
import tomllib
import re
import datetime as dt
import shutil
import json
import requests

def _get_json(*args,**kwargs):
    try:
        with requests.get(*args,**kwargs,timeout=60) as res:
            if res.status_code == 200:
                return json.loads(res.text)
            qargs = [repr(x) for x in args] + \
                [f"{str(x)}={repr(y)}" for x,y in kwargs.items()]
            return {
                "error": "request failed", 
                "message": f"requests.get({','.join(qargs)}) -> StatusCode={res.status_code}",
                }
    except:
        e_type, e_name, _ = sys.exc_info()
        qargs = [repr(x) for x in args] + \
            [f"{str(x)}={repr(y)}" for x,y in kwargs.items()]
        return {
            "error": "request failed", 
            "message": f"requests.get({','.join(qargs)}) -> {e_type.__name__}={e_name}",
            }

class QdoxError(Exception):
    """Error caused by an invalid or missing command line option"""

E_OK = 0
E_ERROR = 1

def _main(argv:list[str]) -> int:

    main.DEBUG = False
    withcss = False
    tomlfile = "pyproject.toml"

    if len(argv) == 0:
        print([x for x in __doc__.split("\n") if x.startswith("Syntax: ")][0])
        return E_OK

    if argv[0] in ["-h","--help","help"]:
        print(__doc__)
        return E_ERROR

    for arg in argv:
        key,value = arg.split("=",1) if "=" in arg else (arg,None)
        if arg == "--debug":
            main.DEBUG = True
        elif key == "--withcss":
            if not __spec__:
                raise QdoxError("you must use --withcss=FILE when running in Python")
            withcss = value if value else os.path.join(os.path.dirname(__spec__.origin),"qdox.css")
        elif key == "--tomlfile":
            tomlfile = value if value else tomlfile
        elif arg != "-":
            raise QdoxError(f"invalid option '{arg}'")

    with open(tomlfile,"rb") as fh:
        package = tomllib.load(fh)["project"]
        homepage = package["urls"]["Homepage"]
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
        for item in ["scripts"]:
            package["scripts"] = "<br/>".join([f"`{x}` &rightarrow; `{y.split(':')[1]}()`" for x,y in package["scripts"].items()])
        for item in list(package):
            if item not in ["name","version","description","authors","maintainers","scripts",
                "requires-python","dependencies","keywords","license","classifiers","urls"]:
                del package[item]

    module = importlib.import_module(package["name"])
    package_name = package['name'].replace('_',' ').title()

    org = homepage.split("/")[-2]
    github_data = _get_json(f"https://api.github.com/users/{org}")
    if "error" in github_data:
        raise QdoxError(github_data["message"])

    os.makedirs("docs",exist_ok=True)

    if withcss:
        shutil.copy(withcss,"docs/qdox.css")

    with open("docs/index.html","w",encoding="utf-8") as html:

        def write_html(text,md=True,nl=False):
            if md:
                rules = {
                    # False indicates result is protected from remaining rules once applied
                    r"``": [r"`",False],
                    r"`([^`]+)`": [r"<code>\1</code>",False],
                    r"([a-z]+)://([A-Za-z0-9/.:@+_?&]+)": 
                        [r"""<a href="\1://\2" target="_tab">\1://\2</a>""",False],
                    r"\*\*([^\*]+)\*\*": [r"<b>\1</b>",True],
                    r"\*([^\*]+)\*": [r"<i>\1</i>",True],
                    r"~~([^\+]+)~~": [r"<strike>\1</strike>",True],
                    r"__([^\+]+)__": [r"<u>\1</u>",True],
                    r"!!([^\+]+)!!": [r"""<font class="highlight">\1</font>""",True],
                    r"_([^ ]+)": [r"<sub>\1</sub>",True],
                    r"\^([^ ]+)": [r"<sup>\1</sup>",True],
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
            if set_mode.li:
                write_html("</li>")
                set_mode.li = False
            if m == "li":
                write_html("<li>")
                set_mode.li = True
                return old
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

        def write_class(name,value):
            if isinstance(value.__doc__,str) and hasattr(value.__init__,"__annotations__"):
                write_html(f"""\n<h2 class="w3-container">{name}</h2><p/>""")
                
                for line in value.__doc__.split("\n"):
                    if len(line) == 0:
                        if get_mode() is None:
                            write_html("<p/>")
                    elif line.startswith("        "):
                        set_mode("ul")
                        part = line.strip().split(": ",1)
                        if len(part) == 2:
                            write_html(f"<li><code>{part[0]}</code>: ",md=False,nl=False)
                            write_html(f"{part[1]}</li>",nl=True)
                        else:
                            write_html(f"<li>{part[0]}</li>",md=True,nl=True)
                    elif line.startswith("      "):
                        set_mode("pre")
                        write_html(line.strip(),md=False,nl=True)
                    elif line.startswith("    "):
                        set_mode(None)
                        if line.strip().endswith(":"):
                            write_html(f"""<h3 class="w3-container">{line.strip()[:-1]}</h3>""",nl=True)
                        else:
                            write_html(f"<p/>{line}",md=True,nl=True)
                    else:
                        set_mode(None)
                        write_html(line,md=True,nl=True)

                write_html(f"""\n<h3 class="w3-container"><code><b>{name}</b>(""")
                args = [(f"<b>{str(a)}</b>:" +
                        re.sub(r'([A-Za-z]+)',r'<i>\1</i>',b.__name__)
                        if hasattr(b,"__name__") else str(b))
                    for a,b in value.__init__.__annotations__.items() if not a in ["self","return"]]
                write_html(", ".join(args))
                write_html(")")
                write_html("</code></h3>\n<p/>")

                for line in value.__init__.__doc__.split("\n"):
                    if len(line) == 0:
                        if get_mode() is None:
                            write_html("<p/>")
                    elif line.startswith("            "):
                        set_mode("ul")
                        part = line.strip().split(": ",1)
                        if len(part) == 2:
                            write_html(f"<li><code>{part[0]}</code>: ",md=False,nl=False)
                            write_html(f"{part[1]}</li>",nl=True)
                        else:
                            write_html(f"<li>{part[0]}</li>",md=True,nl=True)
                    elif line.startswith("        ") and line.strip().endswith(":"):
                        set_mode(None)
                        write_html(f"""<h4 class="w3-container">{line.strip()[:-1]}</h4>""",nl=True)
                    else:
                        set_mode(None)
                        write_html(line,md=True,nl=True)

            for item in dir(value):
                if item.startswith("_"):
                    continue
                ival = getattr(value,item)
                set_mode(None)
                if callable(ival):
                    write_method(".".join([name,item]),ival)
                set_mode(None)

        def write_method(name,value):
            if isinstance(value.__doc__,str) and hasattr(value,"__annotations__"):
                write_html(f"""\n<h3 class="w3-container"><code><b>{name}</b>(""")
                args = [(f"<b>{str(a)}</b>:" +
                        re.sub(r'([A-Za-z]+)',r'<i>\1</i>',b.__name__)
                        if hasattr(b,"__name__") else str(b))
                    for a,b in value.__annotations__.items() if not a in ["self","return"]]
                write_html(", ".join(args))
                write_html(")")
                try:
                    c = value.__annotations__["return"]
                    c = c.__name__ if hasattr(c,"__name__") else str(c)
                    write_html(f" &rightarrow; *{c}*")
                except KeyError:
                    write_html(" &rightarrow; *None*")
                write_html("</code></h3>\n<p/>")

                for line in value.__doc__.split("\n"):
                    if len(line) == 0:
                        if get_mode() is None:
                            write_html("<p/>")
                    elif line.startswith("            "):
                        set_mode("ul")
                        part = line.strip().split(":",1)
                        if len(part) == 2:
                            write_html(f"<li><code>{part[0]}</code>: ",md=False,nl=False)
                            write_html(f"{part[1]}</li>",nl=True)
                        else:
                            write_html(f"<li>{part[0]}</li>",md=True,nl=True)
                    elif line.startswith("        ") and line.strip().endswith(":"):
                        set_mode(None)
                        write_html(f"""<h4 class="w3-container">{line.strip()[:-1]}</h4>""",nl=True)
                    else:
                        set_mode(None)
                        write_html(line,md=True,nl=True)

        def write_function(name,value):
            if isinstance(value.__doc__,str):
                write_html(f"""\n<h2 class="w3-container"><code><b>{name}</b>(""")
                args = [(f"<b>{str(a)}</b>:" +
                        re.sub(r'([A-Za-z]+)',r'<i>\1</i>',b.__name__)
                        if hasattr(b,"__name__") else str(b))
                    for a,b in value.__annotations__.items() if a != "return"]
                write_html(", ".join(args))
                write_html(")")
                try:
                    c = value.__annotations__["return"]
                    c = c.__name__ if hasattr(c,"__name__") else str(c)
                    write_html(f" &rightarrow; *{c}*")
                except KeyError:
                    write_html(" &rightarrow; *None*")
                write_html("</code></h2>\n<p/>")

                for line in value.__doc__.split("\n"):
                    if len(line) == 0:
                        if get_mode() is None:
                            write_html("<p/>")
                    elif line.startswith("        "):
                        set_mode("ul")
                        part = line.strip().split(": ",1)
                        if len(part) == 2:
                            write_html(f"<li><code>{part[0]}</code>: ",md=False,nl=False)
                            write_html(f"{part[1]}</li>",nl=True)
                        else:
                            write_html(f"<li>{part[0]}</li>",md=True,nl=True)
                    elif line.startswith("    ") and line.strip().endswith(":"):
                        set_mode(None)
                        write_html(f"""<h3 class="w3-container">{line.strip()[:-1]}</h3>""",nl=True)
                    else:
                        set_mode(None)
                        write_html(line,md=True,nl=True)
            else:
                print(f"WARNING: function '{name}' has no __doc__")

        write_html(f"""<!doctype html>
    <html>
    <head>
        <title>{package_name}</title>
        <meta name="expires" content="86400" />
        <link rel="stylesheet" href="{os.path.basename(withcss) if withcss else 'qdox.css'}">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://www.w3schools.com/w3css/4/w3.css">
    </head>
    <body>

    <!-- Sidebar -->
    <div class="w3-sidebar w3-light-grey w3-bar-block" style="width:180px">
      <center>
        <img src="{github_data['avatar_url']}" height="128px" width="128px"/>
        <br/><a href="{github_data['html_url']}">{github_data['name']}</a>
        <br/><a href="https://github.com/{org}">{github_data['company'] if 'company' in github_data and github_data['company'] else ''}</a>
      </center>
      <title class="w3-bar-item">{package['name']}</title>
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
                if set_mode.pre:
                    set_mode.pre = False
                    write_html("</pre>")
                if set_mode.li:
                    set_mode.li = False
                    write_html("</li>")
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
                if ": " in line:
                    part = line.split(": ",1)
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
                write_html(line[4:],md=False,nl=True)

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
            if name.startswith("_"):
                continue
            value = getattr(module,name)
            set_mode(None)
            if isinstance(value,type):
                write_class(name,value)
            elif callable(value):
                write_function(name,value)
            set_mode(None)

        # document constants
        constant_header = False
        for name in dir(module):
            if name.startswith("__"):
                continue
            value = getattr(module,name)
            if type(value) in [int,float,list,dict,str] or value is None:
                if not constant_header:
                    write_html("""<h2 class="w3-container">Python Constants</h2>""")
                    constant_header = True
                write_html(f"<p/>`{name} = {repr(value)}`")

        # document metadata
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

    return E_OK

def main(argv:list[str]=sys.argv[1:]) -> int:
    """Main CLI

    Runs the main `qdox` program. Generates the `docs/index.html` from
    the `README.md` file and from the module created using the
    `pyproject.toml` file.  If the `WITHCSS` is set to a file that exists, it
    also copies that file to the `docs/` folder and references it in the HTML
    file.

    Arguments:
        argv (list[str]): argument list (default is sys.argv)

    Returns:
        int: exit code

    Properties:
        DEBUG (bool): enable debugging traceback on exception
        WITHCSS (str): enable copying CSS file to `docs/`

    Exceptions:
        Exception: exceptions are only raised if `DEBUG` is `True`.
        FileNotFoundError: exception raised when an input file is not found.
        QdoxError: exception raised when an invalid command argument is encountered.
    """
    try:
        rc = _main(argv)
    except Exception:
        e_type,e_value,_ = sys.exc_info()
        print(f"ERROR [qdox/{os.path.basename(sys.argv[0])}:{e_type.__name__}]:" +
            f" {e_value}",file=sys.stderr,flush=True)
        if main.DEBUG:
            raise
        rc = E_ERROR
    return rc

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
