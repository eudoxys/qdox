"""Generate `docs/index.html` from module contents and metadata

Syntax: `qdox [OPTION ...]`

Options:

    `-`: run with no options

    `--debug`: Enable debugging traceback on exceptions

    `-h|--help|help`: Display this help information

    `--tomlfile=TOMFILE`: Use `TOMFILE` instead of "pyproject.toml"

    `--withcss[=CSSFILE]`: Copy `CSSFILE` file to the `docs` folder
      (default is `qdox.css`)

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
  following options in your project `Settings-->Pages`.

    * `Source`: Choose **Deploy from a branch**

    * `Branch`: Choose **main** and **/docs**.

    * `Custom domain`: Enter one if you have one.

Usage:

  To use `qdox` in a project you must do the following:

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

  Text encoding includes the following:

    `Syntax[COLON] text`: Syntax text

    `text[COLON]`: Level 2 heading text in module docs or level 3 in function docs

    `[NEWLINE]`: New paragraph

    `[4 SPACES]*[SPACE]text: Bulleted list text

    `[4 SPACES][DIGIT].[SPACE]text: Numbered list item

    `[4 SPACES]label[COLON] text`: Preformatted text

    `[6 SPACES]text`: List item text continuation

    `[8 SPACES]text: Preformatted text

    `**text**`: **Bold** text

    `*text*`: *Italic* text

    `!!text!!`: !!Highlight!! text

    `~~text~~`: ~~strikeout~~ text

    `__text__`: __underline__ text

    `^text`: ^superscript word (ends at space)

    `_text`: _subscript word (ends at space)

    `[TIC]text[TIC]`: `code` text

    `protocol[COLON]//url/`: `protocol://url/` formatting with active link

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

# class Test(str):
#     """Test class"""
#     TEST = "test static"

#     def __init__(self,test:str=None):
#         """Test constructor

#         Arguments:

#             test: test string
#         """

#     def method(self,test:str=None) -> str:
#         """Test method

#         Arguments:

#              test: method string

#         Returns:

#              str: return value
#         """
#
# Module constants
#
E_OK = 0 # exit ok
E_ERROR = 1 # exit with error
E_SYNTAX = 2 # syntax error

def _main(argv:list[str]) -> int:

    main.DEBUG = False
    withcss = False
    tomlfile = "pyproject.toml"

    if len(argv) == 0:
        print([x for x in __doc__.split("\n") if x.startswith("Syntax: ")][0])
        return E_SYNTAX

    if argv[0] in ["-h","--help","help"]:
        print(__doc__)
        return E_OK

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
                    set_mode.pre = "pre"
                return old
            if set_mode.pre:
                write_html("</pre>\n")
                set_mode.pre = None
            if set_mode.list:
                write_html(f"</{set_mode.list}>\n")
                set_mode.list = None
            if m in ["li","dd"]:
                write_html(f"<{m}>")
                set_mode.list = m
                return old
            if set_mode.mode and set_mode.mode != m:
                # set_mode.pre = None
                if set_mode.mode in ["ul","ol"]:
                    write_html(f"</{set_mode.list}>\n\n")
                    set_mode.list = None
                write_html(f"</{set_mode.mode}>\n\n",nl=True)
                set_mode.mode = None
            if m and m != set_mode.mode:
                assert isinstance(m,str) or m is None,f"invalid mode '{m}"
                set_mode.mode = m
                write_html(f"<{set_mode.mode}>")
            return old
        set_mode.mode = None
        set_mode.pre = None
        set_mode.list = None

        def get_mode():
            if set_mode.pre:
                return set_mode.pre
            if set_mode.list:
                return set_mode.list
            return set_mode.mode

        def write_docs(name,value):
            if name:
                write_html(f"""\n\n<h2 class="w3-container">{name}</h2>\n<p/>\n""")

            for line in value.__doc__.split("\n"):

                # new paragraph
                if len(line) == 0:

                    if get_mode() is None:
                        write_html("<p/>\n")

                # continued text
                elif line.strip() == "":

                    pass

                # preformatted text
                elif line.startswith(" "*8):

                    set_mode("pre")
                    write_html(line.strip(),md=False,nl=True)

                elif line.startswith(" "*6): # continued text

                    write_html(line,md=True,nl=True)

                elif line.startswith(" "*4): # lists

                    line = line.strip()

                    # bullets
                    if line.startswith('* '):

                        set_mode("ul")
                        set_mode("li")
                        write_html(line.split(" ",1)[1],md=True,nl=False)

                    # numbered
                    elif line[0] in "123456789" and line.split(' ',1)[0].endswith("."):

                        set_mode("ol")
                        set_mode("li")
                        write_html(line.split(". ",1)[1],md=True,nl=False)

                    # definition
                    elif ": " in line:

                        part = [x.strip() for x in line.split(": ",1)]
                        set_mode(None)
                        write_html(f"<dt>{part[0]}:</dt>\n",md=True,nl=False)
                        set_mode("dd")
                        write_html(part[1],md=True,nl=False)

                    # preformatted
                    else:

                        set_mode("pre")
                        write_html(line,md=False,nl=True)

                # subheading
                elif line[0] != " " and line.strip().endswith(":"):

                    set_mode(None)
                    write_html(f"""\n\n<h4 class="w3-container">{line.strip()[:-1]}</h4>""",nl=True)

                # regular text
                else:

                    set_mode(None)
                    write_html(line,md=True,nl=True)

        def write_args(name,value):
            set_mode(None)
            if isinstance(value.__doc__,str) and hasattr(value,"__annotations__"):
                write_html(f"""\n\n<h3 class="w3-container"><code><b>{name}</b>(""")
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
                    if value.__name__ != "__init__":
                        write_html(" &rightarrow; *None*")
                write_html("</code></h3>\n<p/>\n")

        def write_class(name,value):
            set_mode(None)
            if isinstance(value.__doc__,str):
                write_docs(f"Class {name}({'' if value.__mro__[1] == object else value.__mro__[1].__name__})",value)
                if "__init__" in dir(value) and hasattr(value.__init__,"__annotations__"):
                    write_method(name,value.__init__)
            for item in [x for x in dir(value) if not x.startswith("_") and x not in dir(value.__mro__[1])]:
                if callable(getattr(value,item)):
                    write_method(item,getattr(value,item))
            static_header = False
            set_mode(None)
            for item in [x for x in dir(value) if not x.startswith("_") and x not in dir(value.__mro__[1])]:
                if not callable(getattr(value,item)):
                    if not static_header:
                        write_html("""<h3 class="w3-container">Static Variables</h3>\n""")
                        static_header = True
                    write_html(f"<p/><code>{item} = {getattr(value,item)}</code>\n")

        def write_method(name,value):
            set_mode(None)
            write_args(name,value)
            if "__doc__" in dir(value):
                write_docs(None,value)

        def write_function(name,value):
            set_mode(None)
            write_args(name,value)
            if "__doc__" in dir(value):
                write_docs(None,value)
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
        write_docs(__name__,sys.modules[__name__])

        # document classes
        library_header = False
        set_mode(None)
        for name in sorted([x for x in dir(module) if not x.startswith("_")]):
            value = getattr(module,name)
            if not hasattr(value,"__doc__"):
                continue
            set_mode(None)
            if not library_header:
                write_html("""\n\n<h1 id="python" class="w3-container">Python Library</h1>""",nl=True)
                library_header = True
            if isinstance(value,type):
                write_class(f"{__name__}.{name}",value)

        # document functions
        function_header = False
        for name in sorted([x for x in dir(module) if not x.startswith("_")]):
            value = getattr(module,name)
            if not hasattr(value,"__doc__"):
                continue
            set_mode(None)
            if not function_header:
                write_html("""\n\n<h2 id="python" class="w3-container">Module Functions</h2>""",nl=True)
                function_header = True
            if not isinstance(value,type) and callable(value):
                write_function(name,value)

        # document constants
        constant_header = False
        set_mode(None)
        for name in sorted([x for x in dir(module) if not x.startswith("_")]):
            value = getattr(module,name)
            if type(value) in [int,float,list,dict,str] or value is None:
                if not constant_header:
                    write_html("""\n\n<h2 class="w3-container">Module Variables</h2>""")
                    constant_header = True
                write_html(f"<p/>\n`{name} = {repr(value)}`")

        # document metadata
        write_html("""\n\n<h1 id="package" class="w3-container">Package Metadata</h1>\n""")
        write_html("""<p/>\n<table class="w3-container">\n""")
        for key,data in package.items():
            if key in ["Description","Authors","License","Maintainers"] or '`' in data:
                write_html(f"<tr><th><nobr>{key.title()}</nobr></th><td>:</td><td>{data}" +
                    "</td></tr>\n",True)
            else:
                write_html(f"<tr><th><nobr>{key.title()}</nobr></th><td>:</td><td>{data}" +
                    "</td></tr>\n",False)
        write_html("</table>\n")

        # footer
        write_html(f"\n\n<hr/><p/><cite>Copyright &copy; {dt.datetime.now().year} Eudoxys Sciences LLC")

        write_html("""</body>
            </html>""",nl=True)

    return E_OK

def main(argv:list[str]=sys.argv[1:]) -> int:
    """Command line interface

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
