from prometheus_client import Counter, Gauge
from prometheus_client import start_http_server
from prometheus_client import exposition
import threading

from open_webui.models.users import Users

number_completions_counter = Counter(
    "open_webui_number_completions_total",
    "Number of chat completions",
    ["model", "user"],
)

total_cost_counter = Counter(
    "open_webui_cost_total", "Total cost of chat completions", ["model", "user"]
)

total_cost_by_provider_counter = Counter(
    "open_webui_cost_by_provider_total",
    "Total cost of chat completions by provider",
    ["provider"],
)

input_tokens_counter = Counter(
    "open_webui_input_tokens_total", "Total number of input tokens", ["model", "user"]
)
output_tokens_counter = Counter(
    "open_webui_output_tokens_total", "Total number of output tokens", ["model", "user"]
)
thinking_tokens_counter = Counter(
    "open_webui_thinking_tokens_total",
    "Total number of thinking tokens",
    ["model", "user"],
)

number_users_total = Gauge(
    "open_webui_number_users_total",
    "Total number of users",
)
number_users_total.set_function(Users.count_users)

number_pending_users_total = Gauge(
    "open_webui_number_pending_users_total",
    "Total number of pending users",
)
number_pending_users_total.set_function(
    lambda: Users.count_users(filter_role="pending")
)


def start_metrics_server():
    start_http_server(11111)


def create_prometheus_server(port):
    """custom start method to fix problem descrbied in https://github.com/prometheus/client_python/issues/155"""
    app = exposition.make_wsgi_app()

    httpd = exposition.make_server(
        "",
        port,
        app,
        exposition.ThreadingWSGIServer,
        handler_class=exposition._SilentHandler,
    )
    t = threading.Thread(target=httpd.serve_forever)
    t.daemon = True
    t.start()
    return httpd
