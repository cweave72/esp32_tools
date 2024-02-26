# Common options for protorpc cli apps.
#
import functools
import click
import logging

from protorpc import build_api
from protorpc.cli import setup_logging

logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def cli_common_opts(func):
    """Decorator defining common options used for cli entrypoints.
    """
    @click.option("--loglevel", default='info', help="Debug logging level.")
    @click.option("-d", "--debug", is_flag=True, help="Shortcut for --loglevel=debug.")
    @click.option("--udp", is_flag=True, help="Use UDP connection.")
    @click.option("--ip", type=str, help="Device IP address.")
    @click.option("--port", type=int, help="RPC server port.")
    @click.option("--hostname", type=str, help="Device hostname.")
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper


def cli_init(ctx, params):
    """Standard cli entry initializations.
    """
    # Create the app root logger and setup logging.
    rlogger = logging.getLogger()
    loglevel = 'debug' if params.debug else params.loglevel
    setup_logging(rlogger, level=loglevel)

    # Write the params to the click ctx object.
    ctx.obj['cli_params'] = params

    try:
        # Import RpcFrame from rpc.lib which should be in the path of the cli
        # app calling this function.
        from rpc.lib import RpcFrame

        protocol = 'udp' if params.udp else 'tcp'

        # Build the RPC api and connection object.
        api, conn = build_api(RpcFrame,
                              protocol=protocol,
                              port=params.port,
                              addr=params.ip,
                              hostname=params.hostname)
    except Exception as e:
        logger.error("RPC api build error.")
        raise e

    return api, conn
