"""Minimal fake of the Streamlit API, used only to smoke-test the UI code."""
import contextlib

class RerunException(BaseException): pass
class StopException(BaseException): pass

class _State(dict):
    def __getattr__(self, k):
        try: return self[k]
        except KeyError: raise AttributeError(k)
    def __setattr__(self, k, v): self[k] = v

session_state = _State()
INPUTS = {}      # widget key/label -> value
CLICKS = set()   # widget keys/labels "clicked" in this run
LOG = []         # (kind, text) of every rendered message
DOWNLOADS = {}

def _rec(kind, text=""):
    LOG.append((kind, str(text)))

def _lookup(key, label, default):
    for k in (key, label):
        if k is not None and k in INPUTS:
            return INPUTS[k]
    return default

class Container:
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def __getattr__(self, name):
        fn = globals().get(name)
        if fn is None: raise AttributeError(name)
        return fn

sidebar = Container()

def cache_resource(f=None, **kw):
    def wrap(fn):
        cache = {}
        def inner(*a, **k):
            if "v" not in cache: cache["v"] = fn(*a, **k)
            return cache["v"]
        return inner
    return wrap(f) if callable(f) else wrap

def set_page_config(**kw): pass
def markdown(text="", **kw): _rec("markdown", text)
def caption(text="", **kw): _rec("caption", text)
def write(text="", **kw): _rec("write", text)
def code(text="", **kw): _rec("code", text)
def image(*a, **kw): _rec("image")
def error(text, **kw): _rec("error", text)
def success(text, **kw): _rec("success", text)
def warning(text, **kw): _rec("warning", text)
def info(text, **kw): _rec("info", text)
def metric(label, value, **kw): _rec("metric", f"{label}={value}")
def progress(v, **kw): _rec("progress", kw.get("text", v))
def dataframe(data, **kw): _rec("dataframe", len(data))
def bar_chart(data, **kw): _rec("bar_chart", len(data))
def line_chart(data, **kw): _rec("line_chart", len(data))
def container(**kw): return Container()
def expander(label, **kw): return Container()
def form(key, **kw): return Container()
def tabs(labels):
    _rec("tabs", "|".join(labels)); return [Container() for _ in labels]
def columns(spec, **kw):
    n = spec if isinstance(spec, int) else len(spec)
    return [Container() for _ in range(n)]
def rerun(): raise RerunException()
def stop(): raise StopException()

def text_input(label, value="", key=None, **kw): return _lookup(key, label, value)
def text_area(label, value="", key=None, **kw): return _lookup(key, label, value)
def selectbox(label, options, key=None, **kw):
    options = list(options); return _lookup(key, label, options[0])
def radio(label, options, key=None, **kw):
    options = list(options)
    v = _lookup(key, label, None)
    if v is None:
        idx = kw.get("index", 0) or 0
        v = options[idx]
    return v
def select_slider(label, options=None, value=None, key=None, **kw):
    return _lookup(key, label, value if value is not None else list(options)[0])
def checkbox(label, key=None, **kw): return _lookup(key, label, False)
def date_input(label, value=None, key=None, **kw): return _lookup(key, label, value)

def _clicked(key, label):
    return (key in CLICKS) or (label in CLICKS)
def button(label, key=None, disabled=False, **kw):
    return (not disabled) and _clicked(key, label)
def form_submit_button(label, **kw): return _clicked(None, label)
def download_button(label, data=None, file_name=None, key=None, **kw):
    DOWNLOADS[key or label] = (file_name, data); return False

def __getattr__(name):
    if name.startswith("__"):
        raise AttributeError(name)
    def _noop(*a, **kw):
        _rec(name, a[0] if a else "")
        return Container()
    return _noop
