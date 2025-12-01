import os

from webassets import Bundle
from webassets.filter import register_filter
from webassets_jsx import React

# Register JSX filter if needed
register_filter(React)

# Define bundles
css_bundle = Bundle(
    "node_modules/bootstrap/dist/css/bootstrap.min.css",
    output="gen/packed.css",
    filters="cssmin",
    extra={"rel": "stylesheet/css"},
)

js_bundle = Bundle(
    "node_modules/bootstrap/dist/js/bootstrap.bundle.min.js",
    "node_modules/chart.js/dist/chart.umd.min.js",
    "node_modules/chartjs-adapter-date-fns/dist/chartjs-adapter-date-fns.min.js",
    "node_modules/chartjs-plugin-annotation/dist/chartjs-plugin-annotation.min.js",
    output="gen/packed.js",
    filters="jsmin",
)

# Configuration
debug = os.environ.get("FLASK_DEBUG") == "1"

config = {
    "debug": debug,
    "directory": "static",
    "url": "/static",
    "auto_build": debug,
    "bundles": {
        "css_all": css_bundle,
        "js_all": js_bundle,
    },
}
